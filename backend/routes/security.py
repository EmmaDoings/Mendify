# ============================================================
# routes/security.py  –  Security Audit endpoints
# ============================================================

import re
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from marshmallow import Schema, fields, ValidationError

security_bp = Blueprint("security", __name__)


# ── Vulnerability rule definitions ──────────────────────────
PYTHON_RULES = [
    {
        "id":          "PY001",
        "name":        "SQL Injection Risk",
        "severity":    "high",
        "pattern":     r'execute\s*\(\s*["\'].*%.*["\']|execute\s*\(\s*f["\']',
        "description": "String-formatted SQL queries are vulnerable to injection. "
                       "Use parameterised queries / ORM methods instead.",
    },
    {
        "id":          "PY002",
        "name":        "Hardcoded Secret",
        "severity":    "high",
        "pattern":     r'(password|secret|api_key|token)\s*=\s*["\'][^"\']{4,}["\']',
        "description": "Hardcoded credentials detected. Move secrets to environment "
                       "variables or a secrets manager.",
    },
    {
        "id":          "PY003",
        "name":        "Use of eval()",
        "severity":    "high",
        "pattern":     r'\beval\s*\(',
        "description": "eval() executes arbitrary code. Replace with ast.literal_eval() "
                       "or a safer alternative.",
    },
    {
        "id":          "PY004",
        "name":        "Debug Mode Enabled",
        "severity":    "medium",
        "pattern":     r'debug\s*=\s*True',
        "description": "Debug mode must be disabled in production to prevent "
                       "information disclosure.",
    },
    {
        "id":          "PY005",
        "name":        "Shell Injection Risk",
        "severity":    "high",
        "pattern":     r'os\.system\s*\(|subprocess\.call\s*\(.*shell\s*=\s*True',
        "description": "Shell=True or os.system() with user input can lead to "
                       "command injection. Use subprocess with a list of arguments.",
    },
    {
        "id":          "PY006",
        "name":        "Insecure Deserialization",
        "severity":    "high",
        "pattern":     r'\bpickle\.loads?\s*\(',
        "description": "pickle.load/loads on untrusted data allows arbitrary code "
                       "execution. Use JSON or a safe serialisation format.",
    },
    {
        "id":          "PY007",
        "name":        "Weak Hash Algorithm",
        "severity":    "medium",
        "pattern":     r'hashlib\.(md5|sha1)\s*\(',
        "description": "MD5 and SHA-1 are cryptographically broken. "
                       "Use SHA-256 or stronger.",
    },
    {
        "id":          "JS001",
        "name":        "XSS via innerHTML",
        "severity":    "high",
        "pattern":     r'\.innerHTML\s*=',
        "description": "Assigning to innerHTML with unsanitised input enables XSS. "
                       "Use textContent or a sanitisation library.",
    },
    {
        "id":          "JS002",
        "name":        "Use of eval() in JavaScript",
        "severity":    "high",
        "pattern":     r'\beval\s*\(',
        "description": "eval() executes arbitrary JavaScript. Refactor to avoid it.",
    },
    {
        "id":          "JS003",
        "name":        "document.write Usage",
        "severity":    "medium",
        "pattern":     r'document\.write\s*\(',
        "description": "document.write can overwrite the entire page and is an XSS "
                       "vector. Use DOM manipulation methods instead.",
    },
]


# ── Validation schema ────────────────────────────────────────
class AuditSchema(Schema):
    code     = fields.Str(required=True)
    language = fields.Str(load_default="python")
    filename = fields.Str(load_default="unknown")


audit_schema = AuditSchema()


def _run_audit(code: str, language: str, filename: str) -> list:
    """
    Scan source code against all rules.
    Returns a list of finding dicts with line numbers.
    """
    findings = []
    lines    = code.splitlines()

    for rule in PYTHON_RULES:
        pattern = re.compile(rule["pattern"], re.IGNORECASE)
        for line_no, line in enumerate(lines, start=1):
            if pattern.search(line):
                findings.append({
                    "rule_id":     rule["id"],
                    "name":        rule["name"],
                    "severity":    rule["severity"],
                    "description": rule["description"],
                    "line_number": line_no,
                    "line_content": line.strip(),
                    "filename":    filename,
                })

    return findings


# ── POST /api/v1/security/audit ──────────────────────────────
@security_bp.route("/audit", methods=["POST"])
@jwt_required()
def audit_code():
    """
    Perform a static security audit on submitted source code.
    Returns categorised findings sorted by severity.
    """
    try:
        data = audit_schema.load(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"error": "Validation failed", "details": exc.messages}), 422

    findings = _run_audit(data["code"], data["language"], data["filename"])

    # Sort: critical → high → medium → low
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    findings.sort(key=lambda f: severity_order.get(f["severity"], 99))

    # Aggregate counts
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in findings:
        counts[f["severity"]] = counts.get(f["severity"], 0) + 1

    return jsonify({
        "filename":       data["filename"],
        "language":       data["language"],
        "total_findings": len(findings),
        "severity_counts": counts,
        "findings":       findings,
    }), 200


# ── GET /api/v1/security/rules ───────────────────────────────
@security_bp.route("/rules", methods=["GET"])
@jwt_required()
def list_rules():
    """Return all available security audit rules (without regex patterns)."""
    safe_rules = [
        {k: v for k, v in rule.items() if k != "pattern"}
        for rule in PYTHON_RULES
    ]
    return jsonify({"rules": safe_rules, "total": len(safe_rules)}), 200