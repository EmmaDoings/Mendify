# ============================================================
# routes/init.py  –  Route registration hub
# ============================================================

from flask import Flask

from .health    import health_bp
from .project  import projects_bp
from .bugs      import bugs_bp
from .compiler  import compiler_bp
from .auth      import auth_bp
from .ai_debugger import debugger_bp
from .ai_security import ai_security_bp
from .ai_chat import chat_bp
from .chat_apply_edit import chat_apply_edit_bp
from .ai_config import ai_config_bp



def register_routes(app: Flask) -> None:
    """
    Register every Blueprint with its URL prefix.
    All API routes live under /api/v1/ for clean versioning.
    """
    blueprints = [
        (auth_bp,          "/api/v1/auth"),
        (health_bp,        "/api/v1/health"),
        (projects_bp,      "/api/v1/projects"),
        (bugs_bp,          "/api/v1/bugs"),
        (compiler_bp,      "/api/v1/compiler"),
        (debugger_bp,      "/api/v1/debugger"),
        (ai_security_bp,   "/api/v1/ai-security"),
        (chat_bp,          "/api/v1/chat"),
        (chat_apply_edit_bp, "/api/v1/chat"),
        (ai_config_bp,       "/api/v1/ai/config"),
    ]
    for blueprint, prefix in blueprints:
        app.register_blueprint(blueprint, url_prefix=prefix)

