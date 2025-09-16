import os
import logging
from flask import Flask
from flask_wtf.csrf import CSRFProtect

from main.config import Config
from main.database import db
from main.blueprints.main import main_bp
from main.blueprints.admin import admin_bp
from main.blueprints.teacher import teacher_bp

csrf = CSRFProtect()

def create_app(config_class=Config):
    # Get the absolute path to the project root
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    app = Flask(
        __name__,
        template_folder=os.path.join(project_root, 'templates'),
        static_folder=os.path.join(project_root, 'static')
    )
    app.config.from_object(config_class)

    # Initialize extensions
    csrf.init_app(app)
    try:
        db.init_app(app)
    except Exception as e:
        logging.error(f"Database initialization failed: {e}")
        # Depending on desired behavior, you might want to:
        # 1. Re-raise the exception if the app cannot function without DB.
        # 2. Set a flag to disable DB-dependent features.
        # For now, we'll just log and let the app potentially crash later if DB is critical.

    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(teacher_bp, url_prefix='/teacher')

    # Configure logging
    logging.basicConfig(level=getattr(logging, app.config["LOG_LEVEL"], logging.INFO),
                        format="%(asctime)s %(levelname)s %(name)s - %(message)s")

    return app
