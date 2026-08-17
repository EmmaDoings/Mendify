import os
import re
import json
import time
import hashlib
import logging
import threading
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Any, Dict, List, Optional

# Core Vendor SDK Integrations
import groq

# Configure service-specific logger
logger = logging.getLogger("AIService")
logging.basicConfig(level=logging.INFO)


class ThreadSafeTTLCache:
    """
    An in-memory, thread-safe LRU-evicting cache using an OrderedDict 
    with strict Time-To-Live (TTL) expiration constraints.
    """
    def __init__(self, ttl_seconds: int = 600, max_size: int = 1024):
        self.ttl = ttl_seconds
        self.max_size = max_size
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self.lock = threading.Lock()

    def _prune_expired(self, now: float) -> None:
        """Removes all expired entries from the active cache window."""
        expired_keys = [
            k for k, v in self.cache.items() if now > v["expires_at"]
        ]
        for k in expired_keys:
            del self.cache[k]

    def get(self, key: str) -> Optional[Any]:
        """Retrieves an unexpired cached item, moving it to the end of the LRU sequence."""
        now = time.time()
        with self.lock:
            self._prune_expired(now)
            if key not in self.cache:
                return None
            
            entry = self.cache[key]
            self.cache.move_to_end(key)
            return entry["value"]

    def set(self, key: str, value: Any) -> None:
        """Sets an item within the cache workspace, evicting oldest records if max_size is breached."""
        now = time.time()
        with self.lock:
            self._prune_expired(now)
            if key in self.cache:
                del self.cache[key]
            
            self.cache[key] = {
                "value": value,
                "expires_at": now + self.ttl
            }
            
            if len(self.cache) > self.max_size:
                self.cache.popitem(last=False)


AVAILABLE_GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
]

AVAILABLE_GROQ_MODELS = [
    {"id": "llama-3.3-70b-versatile",       "context": 131072},
    {"id": "llama-4-scout-17b-16e-instruct", "context": 1048576},
    {"id": "llama-4-maverick-17b-128e-instruct", "context": 1048576},
    {"id": "deepseek-r1-distill-llama-70b",  "context": 131072},
    {"id": "mixtral-8x7b-32768",             "context": 32768},
    {"id": "gemma2-9b-it",                   "context": 8192},
]


class AIService:
    """
    AI Abstraction Layer managing asynchronous multi-vendor failovers.

    Notes:
    - Some routes (e.g. backend/routes/ai_chat.py) expect an older/alternate
      interface: .is_available(), .status(), .model, and a .client adapter
      that supports: .client.chat.completions.create(...).

    This class now exposes that compatibility layer while keeping
    generate_project() as the canonical full-project generator.
    """
    def __init__(self) -> None:

        # 1. CLIENT INITIALIZATION
        gemini_key = os.environ.get("GEMINI_API_KEY")
        groq_key = os.environ.get("GROQ_API_KEY")
        self._gemini_key = gemini_key

        if not gemini_key:
            logger.warning("Environment variable 'GEMINI_API_KEY' is missing.")
        if not groq_key:
            logger.warning("Environment variable 'GROQ_API_KEY' is missing.")

        # Initialize Gemini lazily inside timed worker calls. In some local
        # environments importing google.genai can block app startup.
        self.gemini_client = None
        self.groq_client = groq.Groq(api_key=groq_key) if groq_key else None

        # 2. RUNTIME MODEL CONFIG (overridable via API)
        self.gemini_model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
        self.gemini_max_tokens = int(os.environ.get("GEMINI_MAX_TOKENS", "8192"))
        self.groq_model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.groq_max_tokens = int(os.environ.get("GROQ_MAX_TOKENS", "32768"))
        self.request_timeout_seconds = int(os.environ.get("MENDIFY_AI_TIMEOUT_SECONDS", "12"))
        # Full-project generation produces very large outputs (up to max_tokens).
        # Give it a dedicated, generous timeout so long Gemini runs can complete.
        self.project_timeout_seconds = int(os.environ.get("MENDIFY_PROJECT_TIMEOUT_SECONDS", "60"))

        # 3. GLOBAL CONCURRENCY GATING
        # Reused across all incoming network execution worker contexts
        self._executor = ThreadPoolExecutor(max_workers=3)

        # 4. CACHE MECHANISM
        self._cache = ThreadSafeTTLCache(ttl_seconds=600, max_size=512)

    def _generate_stable_key(self, idea: str, frontend: str, backend: str) -> str:
        """Generates an execution-safe SHA-256 fingerprint from configuration payloads."""
        payload = f"idea:{idea.strip()}||front:{frontend.strip()}||back:{backend.strip()}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _invoke_gemini_primary(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """Internal execution target routing payloads via Google Gen AI Engine."""
        if not self._gemini_key:
            raise ValueError("Gemini API key not configured.")
        if not self.gemini_client:
            from google import genai
            from google.genai import types

            self.gemini_client = genai.Client(api_key=self._gemini_key)
        else:
            from google.genai import types
        effective_max = max_tokens if max_tokens is not None else self.gemini_max_tokens
        config_kwargs = {}
        if effective_max:
            config_kwargs["max_output_tokens"] = effective_max

        config = types.GenerateContentConfig(**config_kwargs) if config_kwargs else None
        
        response = self.gemini_client.models.generate_content(
            model=self.gemini_model,
            contents=prompt,
            config=config
        )
        text = getattr(response, "text", None)
        if not text:
            raise ValueError(
                "Primary Gemini engine returned an empty string or unset token text payload."
            )
        return text


    def _invoke_groq_fallback(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """Internal execution target routing payloads via Groq Engine using high-capacity models."""
        if not self.groq_client:
            raise ValueError("Groq API key not configured.")
        effective_max = max_tokens if max_tokens is not None else self.groq_max_tokens
        kwargs = {
            "model": self.groq_model,
            "messages": [
                {
                    "role": "system", 
                    "content": "You are an expert systems engineer architecture assistant mapping high-performance application layouts."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ]
        }
        if effective_max:
            kwargs["max_tokens"] = effective_max

        response = self.groq_client.chat.completions.create(**kwargs)
        choices = response.choices
        if not choices:
            raise ValueError("Fallback Groq engine returned an empty choices array.")
        content = choices[0].message.content
        if not content:
            raise ValueError("Fallback Groq engine returned an empty completion variant.")
        return content

    # 4. GENERATION PIPELINE WITH AUTO-FALLBACK
    @property
    def model(self) -> str:
        """Compatibility with routes expecting ai_service.model."""
        return self.gemini_model

    def is_available(self) -> bool:
        """Compatibility with routes expecting ai_service.is_available()."""
        gemini_key = os.environ.get("GEMINI_API_KEY")
        groq_key = os.environ.get("GROQ_API_KEY")
        return bool(gemini_key or groq_key)

    def status(self) -> dict:
        """Compatibility with routes expecting ai_service.status()."""
        return {
            "available": self.is_available(),
            "providers": {
                "gemini": bool(os.environ.get("GEMINI_API_KEY")),
                "groq": bool(os.environ.get("GROQ_API_KEY")),
            },
            "config": self.get_config(),
        }

    def get_config(self) -> dict:
        """Return current runtime AI config."""
        return {
            "gemini_model": self.gemini_model,
            "gemini_max_tokens": self.gemini_max_tokens,
            "groq_model": self.groq_model,
            "groq_max_tokens": self.groq_max_tokens,
            "request_timeout_seconds": self.request_timeout_seconds,
            "project_timeout_seconds": self.project_timeout_seconds,
        }

    def update_config(self, updates: dict) -> None:
        """Update runtime AI config from a dict of optional keys."""
        valid_keys = {"gemini_model", "gemini_max_tokens", "groq_model", "groq_max_tokens", "request_timeout_seconds", "project_timeout_seconds"}
        for key, value in updates.items():
            if key not in valid_keys:
                continue
            if key.endswith("_max_tokens") or key == "request_timeout_seconds":
                setattr(self, key, int(value))
            else:
                setattr(self, key, str(value))

    def _run_with_timeout(self, fn, *args, timeout_seconds: Optional[int] = None):
        """Run a provider request with a bounded wait so routes can fall back."""
        timeout = timeout_seconds or self.request_timeout_seconds
        future = self._executor.submit(fn, *args)
        try:
            return future.result(timeout=timeout)
        except TimeoutError:
            future.cancel()
            raise TimeoutError(f"AI provider request timed out after {timeout} seconds")

    @staticmethod
    def get_available_models() -> dict:
        return {
            "gemini": AVAILABLE_GEMINI_MODELS,
            "groq": AVAILABLE_GROQ_MODELS,
        }

    @property
    def client(self):
        """Compatibility adapter for routes expecting ai_service.client.chat.completions.create()."""

        class _ClientAdapter:
            def __init__(self, outer: "AIService") -> None:
                self._outer = outer
                self.chat = self
                self.completions = self

            def create(self, model: str, messages: list, temperature: float = 0.7, max_tokens: Optional[int] = None):
                prompt = "\n".join([m.get("content", "") for m in messages if isinstance(m, dict)])

                try:
                    gemini_text = self._outer._run_with_timeout(
                        self._outer._invoke_gemini_primary,
                        prompt,
                        max_tokens,
                    )
                    return {"choices": [{"message": {"content": gemini_text}}]}
                except Exception:
                    try:
                        fallback_text = self._outer._run_with_timeout(
                            self._outer._invoke_groq_fallback,
                            prompt,
                            max_tokens,
                        )
                        return {"choices": [{"message": {"content": fallback_text}}]}
                    except Exception:
                        raise

        return _ClientAdapter(self)

    def generate_project(
        self, 
        idea: str, 
        frontend: str, 
        backend: str, 
        max_tokens: Optional[int] = None
    ) -> str:

        """
        Orchestrates full-stack codebase layout syntheses through decoupled
        LLM architectures over a strict background operational pool thread gate.
        """
        # Resolve tracking cache signature keys
        cache_key = self._generate_stable_key(idea, frontend, backend)
        cached_response = self._cache.get(cache_key)
        
        if cached_response:
            logger.info(f"Cache Hit verified for Signature ID: {cache_key}. Suppressing network traversal.")
            return cached_response

        # Compile strict instructions payload
        prompt = (
            f"You are a principal systems automation expert. Generate a production-ready software project blueprint.\n"
            f"Functional Objective Idea: {idea}\n"
            f"Target Frontend UI Stack: {frontend}\n"
            f"Target Backend API Architecture Stack: {backend}\n\n"
            f"RESPOND WITH VALID JSON ONLY in this exact format:\n"
            f'{{\n  "tree": "project-name/\\n|-- file1.py\\n|-- file2.js",\n  "files": {{\n    "file1.py": "content here",\n    "file2.js": "content here"\n  }}\n}}\n\n'
            f"Rules:\n"
            f"- Include ALL files needed for a complete runnable project\n"
            f"- Use proper file paths with directories (e.g., 'src/App.jsx', 'backend/app.py')\n"
            f"- Include package.json, requirements.txt, README.md as appropriate\n"
            f"- Tree must be a string showing the directory structure\n"
            f"- Files object maps path -> content\n"
            f"- NO markdown, NO explanations, ONLY the JSON object"
        )

        # Primary Run via Thread Pool Executor (Gemini)
        try:
            logger.info(f"Dispatching upstream prompt tasks to Primary Worker Pool [{self.gemini_model}].")
            result = self._run_with_timeout(
                self._invoke_gemini_primary,
                prompt,
                max_tokens,
                timeout_seconds=self.project_timeout_seconds,
            )
            
            # Commit generated pipeline layout to TTL engine
            self._cache.set(cache_key, result)
            return result

        except Exception as gemini_exception:
            logger.warning(
                f"Primary engine core execution fault raised: {str(gemini_exception)}. "
                f"Initiating auto-fallback migration pipeline tracking routes."
            )

            # Fallback Run via Thread Pool Executor (Groq)
            try:
                logger.info(f"Dispatching processing instructions to Fallback Worker Pool [{self.groq_model}].")
                fallback_result = self._run_with_timeout(
                    self._invoke_groq_fallback,
                    prompt,
                    max_tokens,
                    timeout_seconds=self.project_timeout_seconds,
                )
                
                # Commit validated fallback context to memory matrix
                self._cache.set(cache_key, fallback_result)
                return fallback_result

            except Exception as groq_exception:
                critical_error_msg = (
                    f"Fatal Operational Failure: Core AI pipeline processing bounds dropped out. "
                    f"Primary Engine Error: {str(gemini_exception)} | "
                    f"Fallback Engine Error: {str(groq_exception)}"
                )
                logger.error(critical_error_msg)
                raise RuntimeError(critical_error_msg)

    # ── Pattern-based debug checks ────────────────────────────
    DEBUG_RULES = {
        "python": [
            (r"\beval\s*\(", "high", "Use of eval()", "eval() can execute arbitrary code. Use ast.literal_eval() instead."),
            (r"^print\s+[^()]", "low", "Python 2 style print", "In Python 3, print requires parentheses."),
            (r"\binput\s*\(.*\)", "low", "Input without .strip()", "Consider using .strip() on input values."),
        ],
        "javascript": [
            (r"\beval\s*\(", "high", "Use of eval()", "eval() can execute unsafe code."),
            (r"\bvar\s+", "low", "Use of var", "Prefer let or const over var."),
            (r"document\.write\s*\(", "high", "Use of document.write()", "Prefer DOM methods like textContent."),
            (r"(?<![!=])==(?!=)|(?<!!)!=(?!=)", "medium", "Loose equality", "Prefer === or !=="),
        ],
    }
    SECURITY_RULES = [
        (r"execute\s*\(\s*[\"'].*%.*[\"']", "high", "SQL Injection Risk", "Use parameterised queries."),
        (r"(password|secret|api_key|token)\s*=\s*[\"'][^\"']{4,}[\"']", "high", "Hardcoded Secret", "Move secrets to env vars."),
        (r"\beval\s*\(", "high", "Use of eval()", "eval() allows arbitrary code execution."),
        (r"debug\s*=\s*True", "medium", "Debug Mode Enabled", "Disable debug in production."),
        (r"os\.system\s*\(|subprocess\.call\s*\(.*shell\s*=\s*True", "high", "Shell Injection Risk", "Use subprocess with arg list."),
        (r"\.innerHTML\s*=", "high", "XSS via innerHTML", "Use textContent instead."),
        (r"\bpickle\.loads?\s*\(", "high", "Insecure Deserialization", "Use JSON instead of pickle."),
        (r"hashlib\.(md5|sha1)\s*\(", "medium", "Weak Hash Algorithm", "Use SHA-256 or stronger."),
    ]

    def _local_debug(self, code: str, language: str) -> Dict[str, Any]:
        issues = []
        lines = str(code or "").splitlines()
        rules = list(self.DEBUG_RULES.get(language, []))
        if language not in self.DEBUG_RULES and language != "python":
            rules += self.DEBUG_RULES.get("javascript", [])

        for pattern, severity, title, desc in rules:
            compiled = re.compile(pattern)
            for lineno, line in enumerate(lines, start=1):
                if compiled.search(line):
                    issues.append({
                        "severity": severity,
                        "title": title,
                        "description": f"Line {lineno}: {desc}",
                    })

        # Fix common issues
        fixed = str(code or "")
        if language == "python":
            fixed = re.sub(r"^print\s+(.+)$", r"print(\1)", fixed, flags=re.MULTILINE)
        if language in ("javascript", "html"):
            fixed = re.sub(r'(?<!=)==(?!=)', '===', fixed)
            fixed = re.sub(r'(?<!!)!=(?!=)', '!==', fixed)
            fixed = fixed.replace("var ", "let ")

        return {
            "issues": issues or [{"severity": "low", "title": "No critical issues detected",
                                  "description": f"Basic {language} checks passed."}],
            "fixed": fixed,
            "ai_generated": False,
            "ai_error": None,
        }

    def _local_security_audit(self, code: str) -> Dict[str, Any]:
        issues = []
        lines = str(code or "").splitlines()

        for pattern, severity, name, desc in self.SECURITY_RULES:
            compiled = re.compile(pattern, re.IGNORECASE)
            for lineno, line in enumerate(lines, start=1):
                if compiled.search(line):
                    issues.append({
                        "rule_id": f"SEC{len(issues)+1:03d}",
                        "name": name,
                        "severity": severity,
                        "description": desc,
                        "line_number": lineno,
                        "line_content": line.strip(),
                        "filename": "unknown",
                    })

        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for issue in issues:
            sev = issue["severity"]
            if sev in counts:
                counts[sev] += 1

        severity_score = {"critical": 10, "high": 7, "medium": 4, "low": 1}
        total = sum(severity_score.get(i["severity"], 0) for i in issues)
        max_score = max(len(issues) * 10, 1)
        score = max(0, 100 - int((total / max_score) * 100))

        return {
            "issues": issues,
            "score": {"score": score, "label": "safe" if score >= 80 else "risky" if score >= 50 else "danger"},
            "hardened": code,
            "ai_generated": False,
            "ai_error": None,
        }

    def debug_code(self, code: str, language: str) -> Dict[str, Any]:
        try:
            prompt = (
                f"Analyze the following {language} code for bugs and issues. "
                f"Return valid JSON with keys: issues (array of {{severity, title, description, line_number}}), "
                f"fixed (the corrected code as a string). Only respond with JSON.\n\n{code}"
            )
            raw = self._run_with_timeout(self._invoke_gemini_primary, prompt, 4096)
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r'^```(?:json)?\s+|\s+```$', '', cleaned).strip()
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict) and "issues" in parsed:
                parsed.setdefault("fixed", code)
                parsed["ai_generated"] = True
                return parsed
        except Exception as exc:
            logger.info("AI debugger unavailable, using local fallback: %s", exc)

        return self._local_debug(code, language)

    def audit_security(self, code: str, language: str = "python") -> Dict[str, Any]:
        try:
            prompt = (
                f"Perform a security audit on the following {language} code. "
                f"Return valid JSON with keys: issues (array of {{severity, name, description, line_number}}), "
                f"score (object with score int 0-100 and label string), hardened (the code with fixes applied). "
                f"Only respond with JSON.\n\n{code}"
            )
            raw = self._run_with_timeout(self._invoke_gemini_primary, prompt, 4096)
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r'^```(?:json)?\s+|\s+```$', '', cleaned).strip()
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict) and "issues" in parsed:
                parsed.setdefault("hardened", code)
                parsed["ai_generated"] = True
                return parsed
        except Exception as exc:
            logger.info("AI security audit unavailable, using local fallback: %s", exc)

        return self._local_security_audit(code)

# ============================================================
# Global Service Instance for Application Imports
# ============================================================
ai_service = AIService()

