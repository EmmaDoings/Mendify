# ============================================================
# routes/ai_security.py  –  AI-Powered Security Audit
# ============================================================

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from marshmallow import Schema, fields, validate, ValidationError

ai_security_bp = Blueprint("ai_security", __name__)


# ── Validation schema ────────────────────────────────────────
class AuditSchema(Schema):
    code = fields.Str(required=True, validate=lambda x: len(x) > 0)
    language = fields.Str(
        required=False,
        load_default="javascript",
        validate=validate.OneOf(["javascript", "python", "html", "css", "go", "php", "java", "cpp"]),
    )


audit_schema = AuditSchema()


# ── POST /api/v1/ai-security/audit ─────────────────────────────
@ai_security_bp.route("/audit", methods=["POST"])
@jwt_required()
def ai_audit_code():
    """Perform security audit on code using AI with local fallback."""
    try:
        data = audit_schema.load(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"error": "Validation failed", "details": exc.messages}), 422

    code = data["code"]
    language = data["language"]

    from backend.services.ai_service import ai_service

    result = ai_service.audit_security(code, language)
    score_payload = result.get("score", 0)
    score_label = None
    if isinstance(score_payload, dict):
        score_label = score_payload.get("label")
        score_payload = score_payload.get("score", 0)
    try:
        score_value = int(score_payload)
    except (TypeError, ValueError):
        score_value = 0
    if not score_label:
        score_label = "safe" if score_value >= 80 else "risky" if score_value >= 50 else "danger"

    return jsonify(
        {
            "language": language,
            "issues": result.get("issues", []),
            "score": score_value,
            "score_label": score_label,
            "hardened": result.get("hardened", code),
            "ai_generated": bool(result.get("ai_generated")),
            "ai_status": ai_service.status(),
            "ai_error": result.get("ai_error"),
        }
    ), 200
