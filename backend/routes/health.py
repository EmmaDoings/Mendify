# ============================================================
# routes/health.py  –  Health-check endpoint
# ============================================================

from flask import Blueprint, jsonify
from sqlalchemy import text
from backend.models import db

health_bp = Blueprint("health", __name__)


@health_bp.route("/", methods=["GET"])
def health_check():
    """
    Lightweight liveness + readiness probe.
    Returns 200 when the app and DB are reachable, 503 otherwise.
    """
    db_status = "ok"
    try:
        db.session.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = f"error: {exc}"

    status_code = 200 if db_status == "ok" else 503
    return jsonify({
        "status":   "healthy" if db_status == "ok" else "degraded",
        "database": db_status,
        "service":  "Mendify API",
        "version":  "1.0.0",
    }), status_code