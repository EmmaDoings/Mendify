from __future__ import annotations

from datetime import datetime, timezone

from . import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    reset_token = db.Column(db.String(255), nullable=True, index=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)

    # Convenience serialization
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

