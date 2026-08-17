#!/usr/bin/env python3
"""
Mendify - Development Server Runner
This script sets up the Python path correctly and runs the Flask development server.
"""

import os
import sys

# Add the project root directory to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import and run the application
from app import create_app

if __name__ == "__main__":
    app = create_app()
    env = os.getenv("APP_ENV", "development")
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", 5000))
    debug = env != "production" and os.getenv("FLASK_DEBUG", "false").lower() == "true"
    
    print(f"""
+=========================================================+
|                                                         |
|   Mendify Backend Server                                |
|                                                         |
|   Running on: http://{host}:{port}                     |
|   Debug mode: {debug}                                   |
|   Environment: {env}                                    |
|                                                         |
|   API Endpoints:                                        |
|   - Health:  /api/v1/health/                            |
|   - Auth:    /api/v1/auth/*                             |
|   - Projects:/api/v1/projects/*                         |
|   - Bugs:    /api/v1/bugs/*                             |
|   - Security:/api/v1/security/*                         |
|   - Compiler:/api/v1/compiler/*                         |
|   - Debugger:/api/v1/debugger/*                         |
|   - AI Sec:  /api/v1/ai-security/*                      |
|   - AI Chat: /api/v1/chat/*                             |
|                                                         |
+=========================================================+
    """)
    
    app.run(host=host, port=port, debug=debug)