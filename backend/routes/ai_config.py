from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from backend.services.ai_service import ai_service

ai_config_bp = Blueprint("ai_config", __name__)


@ai_config_bp.route("/", methods=["GET"])
@jwt_required()
def get_ai_config():
    """Return current AI runtime config and available model options."""
    return jsonify({
        "config": ai_service.get_config(),
        "available_models": ai_service.get_available_models(),
        "providers": {
            "gemini": bool(__import__("os").environ.get("GEMINI_API_KEY")),
            "groq": bool(__import__("os").environ.get("GROQ_API_KEY")),
        },
    }), 200


@ai_config_bp.route("/", methods=["PUT"])
@jwt_required()
def update_ai_config():
    """Update AI runtime config (model selection, max tokens)."""
    data = request.get_json(silent=True) or {}
    ai_service.update_config(data)
    return jsonify({
        "message": "AI config updated",
        "config": ai_service.get_config(),
    }), 200
