# ============================================================
# routes/projects.py  –  CRUD for Projects
# ============================================================

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import Schema, fields, validate, ValidationError

from backend.models import db
from backend.models.project import Project

projects_bp = Blueprint("projects", __name__)


# ── Validation schema ────────────────────────────────────────
class ProjectSchema(Schema):
    name        = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    description = fields.Str(load_default="")
    language    = fields.Str(load_default="python")
    framework   = fields.Str(load_default="flask")


project_schema = ProjectSchema()


# ── GET /api/v1/projects/ ────────────────────────────────────
@projects_bp.route("/", methods=["GET"])
@jwt_required()
def list_projects():
    """Return all projects owned by the authenticated user."""
    user_id = int(get_jwt_identity())
    projects = Project.query.filter_by(user_id=user_id).order_by(
        Project.created_at.desc()
    ).all()
    return jsonify({"projects": [p.to_dict() for p in projects]}), 200


# ── POST /api/v1/projects/ ───────────────────────────────────
@projects_bp.route("/", methods=["POST"])
@jwt_required()
def create_project():
    """Create a new project for the authenticated user."""
    user_id = int(get_jwt_identity())
    try:
        data = project_schema.load(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"error": "Validation failed", "details": exc.messages}), 422

    project = Project(
        name        = data["name"],
        description = data["description"],
        language    = data["language"],
        framework   = data["framework"],
        user_id     = user_id,
    )
    db.session.add(project)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500

    return jsonify({"message": "Project created", "project": project.to_dict()}), 201


# ── GET /api/v1/projects/<id> ────────────────────────────────
@projects_bp.route("/<int:project_id>", methods=["GET"])
@jwt_required()
def get_project(project_id: int):
    """Fetch a single project (must belong to the authenticated user)."""
    user_id = int(get_jwt_identity())
    project = db.session.get(Project, project_id)
    if not project or project.user_id != user_id:
        return jsonify({"error": "Project not found"}), 404
    return jsonify({"project": project.to_dict()}), 200


# ── PUT /api/v1/projects/<id> ────────────────────────────────
@projects_bp.route("/<int:project_id>", methods=["PUT"])
@jwt_required()
def update_project(project_id: int):
    """Update an existing project."""
    user_id = int(get_jwt_identity())
    project = db.session.get(Project, project_id)
    if not project or project.user_id != user_id:
        return jsonify({"error": "Project not found"}), 404

    try:
        # partial=True allows updating only supplied fields
        data = ProjectSchema(partial=True).load(
            request.get_json(silent=True) or {}
        )
    except ValidationError as exc:
        return jsonify({"error": "Validation failed", "details": exc.messages}), 422

    for field, value in data.items():
        setattr(project, field, value)

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500

    return jsonify({"message": "Project updated", "project": project.to_dict()}), 200


# ── DELETE /api/v1/projects/<id> ─────────────────────────────
@projects_bp.route("/<int:project_id>", methods=["DELETE"])
@jwt_required()
def delete_project(project_id: int):
    """Permanently delete a project and its associated data."""
    user_id = int(get_jwt_identity())
    project = db.session.get(Project, project_id)
    if not project or project.user_id != user_id:
        return jsonify({"error": "Project not found"}), 404

    db.session.delete(project)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Database error"}), 500
    return jsonify({"message": "Project deleted"}), 200 