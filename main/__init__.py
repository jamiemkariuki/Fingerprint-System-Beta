import os
import logging
from flask import Flask
from flask_wtf.csrf import CSRFProtect

from main.config import Config
from main.database import get_db
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
    # No db.init_app(app) needed as get_db is a function that returns a connection

    # Register blueprints
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(teacher_bp, url_prefix='/teacher')

    # Configure logging
    logging.basicConfig(level=getattr(logging, app.config["LOG_LEVEL"], logging.INFO),
                        format="%(asctime)s %(levelname)s %(name)s - %(message)s")

    # Start the fingerprint listener
    from main.hardware.fingerprint_listener import FingerprintListener
    import queue

    scan_queue = queue.Queue()
    fingerprint_thread = FingerprintListener(app, scan_queue)
    fingerprint_thread.start()

    # Create a blueprint for the API
    from flask import Blueprint, jsonify
    api_bp = Blueprint('api', __name__)

    @api_bp.route('/fingerprint_scans')
    def fingerprint_scans():
        scans = []
        while not scan_queue.empty():
            scans.append(scan_queue.get())
        return jsonify(scans)

    app.register_blueprint(api_bp, url_prefix='/api')

    return app