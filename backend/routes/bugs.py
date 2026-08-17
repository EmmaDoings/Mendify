# ============================================================
# routes/bugs.py  –  Auto-Debugger: bug tracking & severity
# ============================================================

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import Schema, fields, validate, ValidationError

from backend.models import db
from backend.models.bug import Bug
from backend.models.project import Project

bugs_bp = Blueprint("bugs", __name__)

SEVERITY_LEVELS = ["low", "medium", "high", "critical"]
STATUS_OPTIONS  = ["open", "in_progress", "resolved", "closed"]


# ── Validation schema ────────────────────────────────────────
class BugSchema(Schema):
    title       = fields.Str(required=True, validate=validate.Length(min=1, max=300))
    description = fields.Str(load_default="")
    severity    = fields.Str(
        load_default="medium",
        validate=validate.OneOf(SEVERITY_LEVELS),
    )
    status      = fields.Str(
        load_default="open",
        validate=validate.OneOf(STATUS_OPTIONS),
    )
    file_path   = fields.Str(load_default="")
    line_number = fields.Int(load_default=None, allow_none=True)
    fix_snippet = fields.Str(load_default="")


bug_schema = BugSchema()


def _get_project_or_404(project_id: int, user_id: int):
    """Helper: fetch project and verify ownership."""
    project = db.session.get(Project, project_id)
    if not project or project.user_id != user_id:
        return None
    return project


# ── GET /api/v1/bugs/project/<project_id> ───────────────────
@bugs_bp.route("/project/<int:project_id>", methods=["GET"])
@jwt_required()
def list_bugs(project_id: int):
    """List all bugs for a project, with optional severity filter."""
    user_id  = int(get_jwt_identity())
    project  = _get_project_or_404(project_id, user_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    severity_filter = request.args.get("severity")
    query = Bug.query.filter_by(project_id=project_id)
    if severity_filter and severity_filter in SEVERITY_LEVELS:
        query = query.filter_by(severity=severity_filter)

    bugs = query.order_by(Bug.created_at.desc()).all()
    return jsonify({
        "bugs":  [b.to_dict() for b in bugs],
        "total": len(bugs),
    }), 200


# ── POST /api/v1/bugs/project/<project_id> ──────────────────
@bugs_bp.route("/project/<int:project_id>", methods=["POST"])
@jwt_required()
def create_bug(project_id: int):
    """Log a new bug against a project."""
    user_id = int(get_jwt_identity())
    project = _get_project_or_404(project_id, user_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    try:
        data = bug_schema.load(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"error": "Validation failed", "details": exc.messages}), 422

    bug = Bug(project_id=project_id, **data)
    db.session.add(bug)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Database error creating bug"}), 500
    return jsonify({"message": "Bug logged", "bug": bug.to_dict()}), 201


# ── GET /api/v1/bugs/<bug_id> ────────────────────────────────
@bugs_bp.route("/<int:bug_id>", methods=["GET"])
@jwt_required()
def get_bug(bug_id: int):
    """Fetch a single bug by ID."""
    user_id = int(get_jwt_identity())
    bug     = db.session.get(Bug, bug_id)
    if not bug:
        return jsonify({"error": "Bug not found"}), 404

    # Verify ownership via the parent project
    project = _get_project_or_404(bug.project_id, user_id)
    if not project:
        return jsonify({"error": "Bug not found"}), 404

    return jsonify({"bug": bug.to_dict()}), 200


# ── PUT /api/v1/bugs/<bug_id> ────────────────────────────────
@bugs_bp.route("/<int:bug_id>", methods=["PUT"])
@jwt_required()
def update_bug(bug_id: int):
    """Update bug details or change its status/severity."""
    user_id = int(get_jwt_identity())
    bug     = db.session.get(Bug, bug_id)
    if not bug:
        return jsonify({"error": "Bug not found"}), 404

    project = _get_project_or_404(bug.project_id, user_id)
    if not project:
        return jsonify({"error": "Bug not found"}), 404

    try:
        data = BugSchema(partial=True).load(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"error": "Validation failed", "details": exc.messages}), 422

    for field, value in data.items():
        setattr(bug, field, value)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Database error updating bug"}), 500
    return jsonify({"message": "Bug updated", "bug": bug.to_dict()}), 200


# ── DELETE /api/v1/bugs/<bug_id> ─────────────────────────────
@bugs_bp.route("/<int:bug_id>", methods=["DELETE"])
@jwt_required()
def delete_bug(bug_id: int):
    """Remove a bug record."""
    user_id = int(get_jwt_identity())
    bug     = db.session.get(Bug, bug_id)
    if not bug:
        return jsonify({"error": "Bug not found"}), 404

    project = _get_project_or_404(bug.project_id, user_id)
    if not project:
        return jsonify({"error": "Bug not found"}), 404

    db.session.delete(bug)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Database error deleting bug"}), 500
    return jsonify({"message": "Bug deleted"}), 200


# ── GET /api/v1/bugs/project/<project_id>/summary ───────────
@bugs_bp.route("/project/<int:project_id>/summary", methods=["GET"])
@jwt_required()
def bug_summary(project_id: int):
    """Return a severity breakdown summary for a project."""
    user_id = int(get_jwt_identity())
    project = _get_project_or_404(project_id, user_id)
    if not project:
        return jsonify({"error": "Project not found"}), 404

    summary = {}
    for level in SEVERITY_LEVELS:
        summary[level] = Bug.query.filter_by(
            project_id=project_id, severity=level
        ).count()

    summary["total"] = sum(summary.values())
    return jsonify({"project_id": project_id, "summary": summary}), 200