# ============================================================
# config.py  –  Application configuration classes
# ============================================================

import os
from datetime import timedelta


class BaseConfig:
    """Shared settings for all environments."""

    # ── Flask core ───────────────────────────────────────────
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY environment variable is required. Set it in backend/.env")
    JSON_SORT_KEYS: bool = False
    MAX_CONTENT_LENGTH: int = 16 * 1024 * 1024   # 16 MB upload limit

    # ── SQLAlchemy ───────────────────────────────────────────
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    # NOTE: SQLite (used in testing/dev) doesn't accept all SQLAlchemy engine
    # pool kwargs. Keep this minimal and let SQLAlchemy/Flask-SQLAlchemy
    # choose safe defaults per dialect.
    SQLALCHEMY_ENGINE_OPTIONS: dict = {
        "pool_pre_ping": True,  # safe across most dialects
    }


    # ── JWT / session ────────────────────────────────────────
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY")
    if not JWT_SECRET_KEY:
        raise ValueError("JWT_SECRET_KEY environment variable is required. Set it in backend/.env")
    JWT_ACCESS_TOKEN_EXPIRES  = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

    # flask-jwt-extended expects these config keys
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_HEADER_NAME = "Authorization"
    JWT_HEADER_TYPE = "Bearer"


    # ── CORS ─────────────────────────────────────────────────
    CORS_ORIGINS: list = os.getenv(
        "CORS_ORIGINS", "http://localhost:3000"
    ).split(",")

    # ── Rate limiting ────────────────────────────────────────
    RATELIMIT_DEFAULT: str = "200 per day;50 per hour"
    RATELIMIT_STORAGE_URL: str = os.getenv("REDIS_URL", "memory://")
    RATELIMIT_ENABLED: bool = False


class DevelopmentConfig(BaseConfig):
    """Local development – verbose, SQLite for convenience."""
    ENV:   str  = "development"
    DEBUG: bool = True
    SQLALCHEMY_DATABASE_URI: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///devhelper_dev.db",
    )
    SQLALCHEMY_ECHO: bool = True   # Log every SQL statement
    
    # SQLite thread safety for development
    SQLALCHEMY_ENGINE_OPTIONS: dict = {
        "pool_pre_ping": True,
        "connect_args": {"check_same_thread": False},
    }


class ProductionConfig(BaseConfig):
    """Production – strict, requires real env vars."""
    ENV:   str  = "production"
    DEBUG: bool = False
    TESTING: bool = False
    SQLALCHEMY_DATABASE_URI: str = os.getenv(
        "DATABASE_URL",
        "postgresql://localhost/mendify_prod",
    )
    SQLALCHEMY_ECHO: bool = False

    @classmethod
    def validate(cls) -> None:
        """Call during app init to fail fast on missing critical config."""
        if not os.getenv("DATABASE_URL"):
            raise RuntimeError("DATABASE_URL must be set in production.")


class TestingConfig(BaseConfig):
    """Automated tests – in-memory DB, CSRF off."""
    ENV:     str  = "testing"
    TESTING: bool = True
    DEBUG:   bool = True
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///:memory:"
    WTF_CSRF_ENABLED: bool = False
    RATELIMIT_ENABLED: bool = False