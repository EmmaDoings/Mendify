"""Mendify backend package.  Provides the shared `db` instance used by all subpackages."""

from __future__ import annotations

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

