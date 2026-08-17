# ============================================================
# Mendify - Senior Full-Stack AI Engineer Backend
# Main Application Entry Point (app.py)
# ============================================================

import os
import sys
import logging
from flask import Flask, request, Response, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

# ── Dynamic Path Resolution ──────────────────────────────────
# Find the project root directory (one level up from this file if inside backend/)
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

# Ensure the parent directory is in sys.path so 'backend.*' absolute imports work
if parent_dir not in sys.path and os.path.basename(current_dir) == "backend":
    sys.path.insert(0, parent_dir)
elif current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# ── Environment Configurations ──────────────────────────────
# Load .env without overriding existing env vars (system env vars take precedence)
_dotenv_root = os.path.join(parent_dir, ".env")
if os.path.isfile(_dotenv_root):
    load_dotenv(_dotenv_root, override=False)

_dotenv_primary = os.path.join(current_dir, ".env")
if os.path.isfile(_dotenv_primary):
    load_dotenv(_dotenv_primary, override=False)

# Ensure .env is loaded before any imports that depend on env vars
load_dotenv(_dotenv_root, override=False) if os.path.isfile(_dotenv_root) else None
load_dotenv(_dotenv_primary, override=False) if os.path.isfile(_dotenv_primary) else None

from backend.models import db
from backend.routes.init import register_routes


# ── Logging Configuration ────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Application Factory ──────────────────────────────────────
def create_app(config_name: str | None = None) -> Flask:
    """
    Flask application factory.
    Accepts an optional config_name ('development', 'production', 'testing').
    Falls back to the APP_ENV environment variable, then 'development'.
    """
    app = Flask(__name__)

    # ── Resolve Configuration ────────────────────────────────
    env = config_name or os.getenv("APP_ENV", "development")
    config_map = {
        "development": "backend.config.DevelopmentConfig",
        "production":  "backend.config.ProductionConfig",
        "testing":     "backend.config.TestingConfig",
    }

    config_class = config_map.get(env, "backend.config.DevelopmentConfig")
    app.config.from_object(config_class)
    logger.info("Loaded config: %s  (env=%s)", config_class, env)

    # Enforce production config validation
    if env == "production":
        from backend.config import ProductionConfig
        ProductionConfig.validate()

    # ── Proxy trust (required behind nginx/reverse proxy) ──
    if env == "production":
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

    # ── Security Headers Middleware ──────────────────────────
    @app.after_request
    def set_security_headers(response):
        """Attach security-hardening HTTP headers to every response."""
        
        # FIX: Allow CORS preflight OPTIONS requests to bypass headers to avoid 404/500 errors
        if request.method == "OPTIONS":
            return response

        response.headers["X-Content-Type-Options"]    = "nosniff"
        response.headers["X-Frame-Options"]           = "DENY"
        response.headers["X-XSS-Protection"]          = "1; mode=block"
        response.headers["Referrer-Policy"]           = "strict-origin-when-cross-origin"
        
        api_origins = app.config.get("CORS_ORIGINS", ["http://localhost:3000"])
        connect_sources = "'self'"
        for origin in api_origins:
            connect_sources += f" {origin}"
        
        response.headers["Content-Security-Policy"]   = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data:; "
            f"connect-src {connect_sources} http: https:;"
        )
        if app.config.get("ENV") == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response

    # ── JWT ──────────────────────────────────────────────────
    jwt = JWTManager()
    jwt.init_app(app)
    logger.info("JWT Manager initialized.")

    # ── Rate Limiting ────────────────────────────────────────
    if app.config.get("RATELIMIT_ENABLED", False):
        limiter_storage = app.config.get("RATELIMIT_STORAGE_URL", "memory://")
        limiter = Limiter(
            key_func=get_remote_address,
            app=app,
            default_limits=[app.config.get("RATELIMIT_DEFAULT", "200 per day;50 per hour")],
            storage_uri=limiter_storage,
        )
        logger.info("Rate Limiter initialized.")
    else:
        logger.info("Rate Limiting disabled.")

    # ── CORS ─────────────────────────────────────────────────
    allowed_origins = app.config.get("CORS_ORIGINS", ["http://localhost:3000"])
    CORS(
        app,
        resources={r"/api/*": {"origins": allowed_origins}},
        supports_credentials=True,
    )

    # ── Database ─────────────────────────────────────────────
    db.init_app(app)
    with app.app_context():
        db.create_all()
        logger.info("Database tables verified / created.")

    # ── Routes ───────────────────────────────────────────────
    # Note: Make sure compiler_bp registration happens inside register_routes(app)
    register_routes(app)
    logger.info("All routes registered.")

    # ── Global Error Handlers ────────────────────────────────
    @app.errorhandler(400)
    def bad_request(err):
        return {"error": "Bad Request", "message": str(err)}, 400

    @app.errorhandler(401)
    def unauthorized(err):
        # Avoid logging Authorization headers (JWT leakage)
        return {"error": "Unauthorized", "message": str(err)}, 401



    @app.errorhandler(403)
    def forbidden(err):
        return {"error": "Forbidden", "message": str(err)}, 403

    @app.errorhandler(404)
    def not_found(err):
        return {"error": "Not Found", "message": str(err)}, 404

    @app.errorhandler(405)
    def method_not_allowed(err):
        return {"error": "Method Not Allowed", "message": str(err)}, 405

    @app.errorhandler(422)
    def unprocessable(err):
        # Avoid logging Authorization headers (JWT leakage)
        return {"error": "Unprocessable Entity", "message": str(err)}, 422



    @app.errorhandler(500)
    def internal_error(err):
        db.session.rollback()
        logger.exception("Internal server error: %s", err)
        return {"error": "Internal Server Error"}, 500

    # ── Serve Frontend ──────────────────────────────────────
    frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
    if os.path.isdir(frontend_dir):
        @app.route("/login.html")
        def serve_login():
            return send_from_directory(frontend_dir, "login.html")

        @app.route("/<path:filename>")
        def serve_frontend_static(filename):
            return send_from_directory(frontend_dir, filename)

        @app.route("/")
        def serve_frontend_index():
            html_path = os.path.join(frontend_dir, "index.html")
            if not os.path.isfile(html_path):
                return {"error": "Frontend not found"}, 404
            with open(html_path, encoding="utf-8") as f:
                html = f.read()
            script = '<script>window.MENDIFY_API_URL="";</script>'
            html = html.replace("</head>", f"{script}\n</head>")
            return Response(html, mimetype="text/html")

    return app


# ── Entry Point ──────────────────────────────────────────────
if __name__ == "__main__":
    application = create_app()
    env  = os.getenv("APP_ENV", "development")
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", 5000))
    # Never enable debug in production regardless of env var
    debug = env != "production" and os.getenv("FLASK_DEBUG", "false").lower() == "true"
    logger.info("Starting Mendify on %s:%s  env=%s  debug=%s", host, port, env, debug)
    application.run(host=host, port=port, debug=debug)
