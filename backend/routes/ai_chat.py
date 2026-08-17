# ============================================================
# routes/ai_chat.py  –  Isolated Generated Project Chatbot
# ============================================================

import os
import json
import re
import logging
from typing import Optional
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from marshmallow import Schema, fields, ValidationError

chat_bp = Blueprint("chat", __name__)
logger = logging.getLogger(__name__)


class ChatSchema(Schema):
    message = fields.Str(required=True, validate=lambda x: len(x) > 0)
    context = fields.Str(required=False, load_default="")


chat_schema = ChatSchema()

# Allowed extension types for code inspection
ALLOWED_TEXT_EXTS = (".py", ".js", ".html", ".css", ".json", ".md", ".yml", ".yaml", ".txt")


def _sandbox_root() -> str:
    """
    CRITICAL PROTECTION BOUNDARY:
    Creates and targets a completely isolated folder for generated apps.
    The AI cannot see your Mendify frontend or backend system files.
    """
    base_path = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
    sandbox = os.path.join(base_path, "generated_projects")
    
    # Automatically create the safe folder if it doesn't exist yet
    if not os.path.exists(sandbox):
        os.makedirs(sandbox, exist_ok=True)
        
    return sandbox


def _normalize_rel_path(file_path: str) -> str:
    return (file_path or "").replace("\\", "/").lstrip("/")


def _is_inside_sandbox(target_path: str) -> bool:
    try:
        base_real = os.path.realpath(_sandbox_root())
        target_real = os.path.realpath(target_path)
        return os.path.commonpath([base_real, target_real]) == base_real
    except ValueError:
        return False


def get_generated_structure() -> str:
    """Scans ONLY the safe isolated generated_projects folder layout."""
    base_path = _sandbox_root()
    
    structure = []
    for root, dirs, files in os.walk(base_path):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        
        level = root.replace(base_path, '').count(os.sep)
        indent = '  ' * level
        folder_name = os.path.basename(root) or os.path.basename(base_path)
        structure.append(f"{indent}{folder_name}/")
        
        sub_indent = '  ' * (level + 1)
        for file in files:
            if file.startswith(".") or not file.lower().endswith(ALLOWED_TEXT_EXTS):
                continue
            structure.append(f"{sub_indent}{file}")
    
    return '\n'.join(structure)


def read_generated_file(file_path: str) -> str:
    """Reads file content safely from within the generated_projects boundaries."""
    base_path = _sandbox_root()
    normalized = _normalize_rel_path(file_path)

    full_path = os.path.join(base_path, normalized)
    real_path = os.path.realpath(full_path)
    
    # Block directory traversal attacks entirely
    if not _is_inside_sandbox(real_path):
        return "Error: Access denied - target file rests outside the generation sandbox."
    
    if not real_path.lower().endswith(ALLOWED_TEXT_EXTS):
        return "Error: Unsupported file text format."

    try:
        with open(real_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except FileNotFoundError:
        return f"Error: File not found at {normalized}"
    except Exception as e:
        return f"Error reading target: {str(e)}"


# ── POST /api/v1/chat/ask ─────────────────────────────────────
@chat_bp.route("/ask", methods=["POST"])
# @jwt_required()

def chat_ask():
    """AI chatbot that can ONLY look at code inside generated_projects/."""
    try:
        data = chat_schema.load(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"error": "Validation failed", "details": exc.messages}), 422

    user_message = data["message"]
    conversation_context = data.get("context", "")

    # Gets tree map structure for the generated_projects sandbox ONLY
    project_structure = get_generated_structure()
    
    from backend.services.ai_service import ai_service
    
    path_pattern = r"[\"']?([\w./\\-]+)[\"']?"

    # Check if user wants the chatbot to read a generated file
    file_read_match = re.search(rf"\bread\s+(?:file\s+)?{path_pattern}", user_message, re.IGNORECASE)
    file_content = ""
    if file_read_match:
        file_path = file_read_match.group(1)
        file_content = read_generated_file(file_path)

    # Debug: confirm provider availability and keys seen by the running process.
    # (Useful because env loading can differ depending on how the server is started.)
    try:
        print("AI availability:", ai_service.is_available(), "status:", ai_service.status())
    except Exception as _e:
        print("AI availability check failed:", str(_e))

    if ai_service.is_available():

        system_prompt = f"""You are Mendify AI, an expert code analyzer. 
You can only see the folder structure and files inside the user's generated project workspace directory (the 'generated_projects' folder).
You cannot access the application's core code frontend or backend system scripts.

GENERATED PROJECT STRUCTURE:
{project_structure}

Current active file content being inspected:
{file_content[:3000] if file_content else 'None selected'}

Instructions:
1. Provide accurate code reviews and optimization suggestions for the provided generated code structure.
2. If the user asks about app.py or Mendify's core design files, politely remind them you only have access to their generated apps space.
"""
        try:
            response = ai_service.client.chat.completions.create(
                model=ai_service.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Context: {conversation_context}\nUser Question: {user_message}"}
                ],
                temperature=0.7,
                max_tokens=4096
            )
            
            def _extract_text_response(resp):
                """Safely extract assistant text from multiple provider/adapter shapes."""
                # 1) Direct string response (Gemini adapter in ai_service.py)
                if isinstance(resp, str):
                    return resp.strip()

                # 2) OpenAI-like dict response (Groq fallback adapter in ai_service.py)
                if isinstance(resp, dict):
                    choices = resp.get("choices")
                    if isinstance(choices, list) and choices:
                        choice0 = choices[0] or {}
                        msg = choice0.get("message") if isinstance(choice0, dict) else None
                        if isinstance(msg, dict) and isinstance(msg.get("content"), str):
                            return msg["content"].strip()

                # 3) OpenAI-like object response (defensive for other client adapters)
                choices = getattr(resp, "choices", None)
                if isinstance(choices, list) and choices:
                    c0 = choices[0]
                    msg = getattr(c0, "message", None)
                    content = getattr(msg, "content", None)
                    if isinstance(content, str):
                        return content.strip()

                # 4) Fallback: try common attributes
                content = getattr(resp, "content", None)
                if isinstance(content, str):
                    return content.strip()

                return None

            ai_response = _extract_text_response(response)
            if not ai_response:
                return jsonify({"error": "AI response parsing failed"}), 500

            return jsonify({
                "response": ai_response,
                "ai_generated": True,
                "project_structure": project_structure if "structure" in user_message.lower() or "list" in user_message.lower() else None,
                "file_content": file_content if file_content else None,
            }), 200
            
        except Exception as e:
            logger.exception("AI chat request failed")
            return jsonify({
                "error": "AI chat request failed",
                "ai_error": str(e),
                "ai_status": ai_service.status(),
                "ai_generated": False,
            }), 502
    else:
        return jsonify({
            "response": f"AI service engine is offline. Your message was: {user_message}",
            "ai_generated": False,
            "project_structure": project_structure,
            "file_content": file_content if file_content else None,
            "ai_status": ai_service.status(),
        }), 200
