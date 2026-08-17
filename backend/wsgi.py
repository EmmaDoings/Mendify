import os
import sys

# Ensure the backend directory is on sys.path so absolute imports work
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Ensure the project root is on sys.path so 'backend.*' imports work
project_root = os.path.dirname(backend_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app import create_app

app = create_app()

if __name__ == "__main__":
    env = os.getenv("APP_ENV", "development")
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", 5000))
    debug = env != "production" and os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host=host, port=port, debug=debug)
