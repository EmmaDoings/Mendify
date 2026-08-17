from __future__ import annotations

from datetime import datetime, timezone

from . import db


class Bug(db.Model):
    __tablename__ = "bugs"

    id = db.Column(db.Integer, primary_key=True)

    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False)

    title = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")

    severity = db.Column(db.String(20), nullable=False, default="medium")
    status = db.Column(db.String(30), nullable=False, default="open")

    file_path = db.Column(db.String(500), nullable=False, default="")
    line_number = db.Column(db.Integer, nullable=True)

    fix_snippet = db.Column(db.Text, nullable=False, default="")

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "status": self.status,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "fix_snippet": self.fix_snippet,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

