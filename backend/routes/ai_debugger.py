# ============================================================
# routes/ai_debugger.py  –  AI-Powered Auto-Debugger
# ============================================================

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from marshmallow import Schema, fields, validate, ValidationError

debugger_bp = Blueprint("debugger", __name__)


# ── Validation schema ────────────────────────────────────────
class DebugSchema(Schema):
    code = fields.Str(required=True, validate=lambda x: len(x) > 0)
    language = fields.Str(
        required=False,
        load_default="javascript",
        validate=validate.OneOf(["javascript", "python", "html", "css", "go", "php", "java", "cpp"]),
    )


debug_schema = DebugSchema()


# ── POST /api/v1/debugger/analyze ─────────────────────────────
@debugger_bp.route("/analyze", methods=["POST"])
@jwt_required()
def analyze_code():
    """Analyze code for bugs and issues using AI with local fallback."""
    try:
        data = debug_schema.load(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"error": "Validation failed", "details": exc.messages}), 422

    code = data["code"]
    language = data["language"]

    from backend.services.ai_service import ai_service

    result = ai_service.debug_code(code, language)

    return jsonify(
        {
            "language": language,
            "issues": result.get("issues", []),
            "fixed": result.get("fixed", code),
            "ai_generated": bool(result.get("ai_generated")),
            "ai_status": ai_service.status(),
            "ai_error": result.get("ai_error"),
        }
    ), 200
