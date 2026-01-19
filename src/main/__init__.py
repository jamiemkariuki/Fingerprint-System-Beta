import os
import logging
from flask import Flask
from flask_wtf.csrf import CSRFProtect

from .config import Config
from .database import get_db
from .blueprints.main import main_bp
from .blueprints.admin import admin_bp
from .blueprints.teacher import teacher_bp

csrf = CSRFProtect()

def create_app(config_class=Config):
    # Compute repo root (two levels up from this file)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
    
    # Fallback to /app if we are in Docker and the root seems wrong
    if not os.path.exists(os.path.join(project_root, 'templates')) and os.path.exists('/app/templates'):
        project_root = '/app'

    print(f"DEBUG: Initializing Flask with root_path: {project_root}", flush=True)
    print(f"DEBUG: Templates directory: {os.path.join(project_root, 'templates')}", flush=True)
    print(f"DEBUG: Templates exist: {os.path.exists(os.path.join(project_root, 'templates'))}", flush=True)

    app = Flask(
        __name__,
        root_path=project_root,
        template_folder='templates',
        static_folder='static'
    )
    app.config.from_object(config_class)

    # Secondary check after initialization
    print(f"DEBUG: Flask template_folder: {app.template_folder}", flush=True)
    if os.path.exists(app.template_folder):
        print(f"DEBUG: Found templates: {os.listdir(app.template_folder)}", flush=True)
    else:
        print(f"DEBUG: ERROR - Template folder NOT FOUND at {app.template_folder}", flush=True)

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
    from .hardware.fingerprint_listener import FingerprintListener
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
