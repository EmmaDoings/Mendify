# ============================================================
# routes/auth.py  –  Authentication (register / login / refresh)
# ============================================================

import secrets
from datetime import datetime, timedelta, timezone

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
)
from marshmallow import Schema, fields, validate, ValidationError
from werkzeug.security import generate_password_hash, check_password_hash

from backend.models import db
from backend.models.user import User

auth_bp = Blueprint("auth", __name__)


# ── Validation schemas ───────────────────────────────────────
class RegisterSchema(Schema):
    username = fields.Str(
        required=True,
        validate=validate.Length(min=3, max=80),
    )
    email    = fields.Email(required=True)
    password = fields.Str(
        required=True,
        validate=validate.Length(min=8),
        load_only=True,
    )


class LoginSchema(Schema):
    email    = fields.Email(required=True)
    password = fields.Str(required=True, load_only=True)


register_schema = RegisterSchema()
login_schema    = LoginSchema()


# ── POST /api/v1/auth/register ───────────────────────────────
@auth_bp.route("/register", methods=["POST"])
def register():
    """Create a new user account."""
    try:
        data = register_schema.load(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"error": "Validation failed", "details": exc.messages}), 422

    # Duplicate checks
    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already registered"}), 409
    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"error": "Username already taken"}), 409

    user = User(
        username      = data["username"],
        email         = data["email"],
        password_hash = generate_password_hash(data["password"]),
    )
    db.session.add(user)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Database error during registration"}), 500

    access_token  = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    return jsonify({
        "message":       "User registered successfully",
        "user":          user.to_dict(),
        "access_token":  access_token,
        "refresh_token": refresh_token,
    }), 201


# ── POST /api/v1/auth/login ──────────────────────────────────
@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate a user and return JWT tokens."""
    try:
        data = login_schema.load(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"error": "Validation failed", "details": exc.messages}), 422

    user = User.query.filter_by(email=data["email"]).first()

    # Use constant-time comparison via check_password_hash to prevent timing attacks
    if not user or not check_password_hash(user.password_hash, data["password"]):
        return jsonify({"error": "Invalid email or password"}), 401

    access_token  = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    return jsonify({
        "message":       "Login successful",
        "user":          user.to_dict(),
        "access_token":  access_token,
        "refresh_token": refresh_token,
    }), 200


# ── POST /api/v1/auth/refresh ────────────────────────────────
@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    """Issue a new access token using a valid refresh token."""
    identity     = get_jwt_identity()
    access_token = create_access_token(identity=identity)
    return jsonify({"access_token": access_token}), 200


# ── GET /api/v1/auth/me ──────────────────────────────────────
@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    """Return the currently authenticated user's profile."""
    user_id = get_jwt_identity()
    user    = db.session.get(User, int(user_id))
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"user": user.to_dict()}), 200


# ── PUT /api/v1/auth/me ──────────────────────────────────────
class UpdateProfileSchema(Schema):
    username = fields.Str(validate=validate.Length(min=3, max=80))
    email    = fields.Email()


update_profile_schema = UpdateProfileSchema()


@auth_bp.route("/me", methods=["PUT"])
@jwt_required()
def update_profile():
    """Update the currently authenticated user's profile."""
    user_id = get_jwt_identity()
    user    = db.session.get(User, int(user_id))
    if not user:
        return jsonify({"error": "User not found"}), 404

    try:
        data = update_profile_schema.load(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"error": "Validation failed", "details": exc.messages}), 422

    if not data:
        return jsonify({"error": "No fields to update"}), 400

    if "username" in data and data["username"] != user.username:
        if User.query.filter_by(username=data["username"]).first():
            return jsonify({"error": "Username already taken"}), 409
        user.username = data["username"]

    if "email" in data and data["email"] != user.email:
        if User.query.filter_by(email=data["email"]).first():
            return jsonify({"error": "Email already registered"}), 409
        user.email = data["email"]

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Database error updating profile"}), 500
    return jsonify({"user": user.to_dict(), "message": "Profile updated"}), 200


# ── POST /api/v1/auth/forgot-password ────────────────────────
class ForgotPasswordSchema(Schema):
    email = fields.Email(required=True)


forgot_password_schema = ForgotPasswordSchema()


@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    """Generate a password reset token. In development, returns it directly."""
    try:
        data = forgot_password_schema.load(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"error": "Validation failed", "details": exc.messages}), 422

    user = User.query.filter_by(email=data["email"]).first()
    if not user:
        return jsonify({"error": "No account found with that email address."}), 404

    token = secrets.token_urlsafe(48)
    user.reset_token = token
    user.reset_token_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Database error processing reset request"}), 500

    # In production, send this token via email.
    # For development, return it directly so the user can test the flow.
    return jsonify({
        "message": "Password reset link sent. Check your inbox.",
        "reset_token": token,
        "note": "Development mode — the reset token is returned here for testing. In production it would be emailed."
    }), 200


# ── POST /api/v1/auth/reset-password ─────────────────────────
class ResetPasswordSchema(Schema):
    token = fields.Str(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=8))


reset_password_schema = ResetPasswordSchema()


@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    """Validate a reset token and update the password."""
    try:
        data = reset_password_schema.load(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"error": "Validation failed", "details": exc.messages}), 422

    user = User.query.filter_by(reset_token=data["token"]).first()
    if not user:
        return jsonify({"error": "Invalid or expired reset token."}), 400

    if not user.reset_token_expiry or datetime.now(timezone.utc) > user.reset_token_expiry:
        user.reset_token = None
        user.reset_token_expiry = None
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
        return jsonify({"error": "Reset token has expired. Request a new one."}), 400

    user.password_hash = generate_password_hash(data["password"])
    user.reset_token = None
    user.reset_token_expiry = None
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Database error resetting password"}), 500

    return jsonify({"message": "Password reset successful. You can now log in with your new password."}), 200