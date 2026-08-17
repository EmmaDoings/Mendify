from __future__ import annotations

from datetime import datetime, timezone

from . import db


class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)

    # Owned by user
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")

    language = db.Column(db.String(50), nullable=False, default="python")
    framework = db.Column(db.String(50), nullable=False, default="flask")

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Helpful for route queries
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "description": self.description,
            "language": self.language,
            "framework": self.framework,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

