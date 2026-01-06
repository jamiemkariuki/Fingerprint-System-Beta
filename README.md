# Fingerprint System — Raspberry Pi Edition

A Flask-based attendance system that uses a fingerprint sensor to log student presence. It runs on a Raspberry Pi with an optional LCD display and a background fingerprint listener. The codebase is designed for a single, Pi-friendly Linux service (systemd) and graceful hardware fallbacks so you can develop without dedicated sensors.

Table of contents:
- Overview
- What you’ll deploy
- Prerequisites
- Hardware and mock mode
- Project structure (high-level)
- Environment and configuration
- Setup and deployment (Pi-focused, single service)
- Systemd service details
- Running locally (dev workflow)
- Testing and validation plan
- Troubleshooting
- Contributing
- License

## Overview
- Core idea: A Flask app that exposes admin/teacher dashboards and a background listener that processes fingerprint scans and logs presence to a MySQL database. On the Pi, all hardware access is guarded with a fallback so you can run headless or with mocks.
- Single-service deployment: The web app is launched via a single systemd service fingerprint-web.service. The fingerprint listener runs inside the Flask app as a background thread, so lifecycle management is simpler on a Raspberry Pi.

## What you’ll deploy
- A single systemd service that runs the Flask web application (wsgi.py) with an in-app background fingerprint listener.
- Optional mock hardware support to test flows without physical devices.

## Prerequisites
- Raspberry Pi with Raspberry Pi OS (64-bit recommended) or Debian-based distro compatible with Python 3.
- Internet connection for package installs and updates.
- MySQL/MariaDB server (the repo uses MariaDB via MySQL client libraries).
- Python 3.8+ (the project uses a virtual environment).
- Git for repo management.
- Hardware (optional on Pi): fingerprint sensor connected to /dev/serial0 at 57600 baud; optional LCD connected via GPIO.

## Hardware and mock mode
- Hardware mode: Fingerprint sensor is accessed through main/hardware/fingerprint.py. If the hardware isn’t present, the code gracefully uses a noop fallback to allow development without a sensor.
- LCD: main/hardware/lcd.py provides a noop LCD when a physical LCD is not connected.
- Mock mode: You can enable a mock mode to simulate scans via environment variable MOCK_HARDWARE or similar flags (to be implemented in a follow-up patch). This enables testing of UI flows without hardware.

## Project structure (high-level)
- Fingerprint System entry points live in the main/ package:
  - main/__init__.py: Flask app factory and background listener startup.
  - main/config.py: App configuration pulled from envs and .env.
  - main/database.py: DB connection pool helper.
  - main/blueprints/: admin.py, main.py, teacher.py for routes.
  - main/hardware/: fingerprint.py, fingerprint_listener.py, lcd.py for hardware integration.
  - main/utils/: pdf.py, email.py, common.py for PDF generation, emails, and helpers.
  - wsgi.py: WSGI entrypoint used by the systemd service.
- Root artifacts:
  - schema.sql: MySQL/MariaDB schema.
  - requirements.txt: Python dependencies.
  - setup_pi.sh: The Raspberry Pi provisioning script (single-service mode).
  - daily_report_sender.py: Script to generate and email daily attendance reports.
  - README.md: This README.

## Environment and configuration
- The app loads environment variables via a .env file at the project root (dotenv).
- Key variables (examples):
  - Flask: SECRET_KEY, FLASK_HOST, FLASK_PORT, FLASK_DEBUG, LOG_LEVEL
  - Database: DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, DB_POOL_SIZE
  - Cookies: SESSION_COOKIE_SECURE, SESSION_COOKIE_SAMESITE
  - Email: SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD

- You can start from a sample .env file and tailor values. The recommended workflow is to run the Pi provisioning script which creates a proper .env file with generated secrets.

- See the example snippet below for a minimal template:

```
# Flask
SECRET_KEY=replace-with-strong-random
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
FLASK_DEBUG=false
LOG_LEVEL=INFO

# Database
DB_HOST=localhost
DB_PORT=3306
DB_USER=fingerprint_user
DB_PASSWORD=strong-password
DB_NAME=FingerprintDB
DB_POOL_SIZE=5

# Cookies
SESSION_COOKIE_SECURE=false
SESSION_COOKIE_SAMESITE=Lax

# Email
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USERNAME=you@example.com
SMTP_PASSWORD=your-password
```

> Note: The provisioning script (setup_pi.sh) will automatically create a .env with realistic defaults when run on the Pi.

## Running (development versus production)
- Development (local):
  - Create a Python virtual environment and install dependencies
  - Start the Flask app directly with wsgi.py or python -m flask run after exporting the required env vars
  - URL: http://localhost:5000

- Production (Raspberry Pi, single service):
  - The provisioning script creates a systemd service fingerprint-web.service that runs the app using the venv and wsgi.py.
  - Steps (high-level):
    - Install prerequisites and create .env (setup_pi.sh handles this)
    - Move to the repo and run: sudo bash setup_pi.sh
    - The script will create the systemd unit, enable, and start it.
    - Access: http://<Pi-IP>:5000

## Systemd service (fingerprint-web)
- Purpose: Run the Flask app as a persistent service.
- File: /etc/systemd/system/fingerprint-web.service
- Typical content:
```
[Unit]
Description=Fingerprint Web App
After=network.target mysql.service

[Service]
User=pi
Group=pi
WorkingDirectory=/home/pi/fingerprint-system
ExecStart=/home/pi/fingerprint-system/.venv/bin/python wsgi.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

- Commands to manage:
  - sudo systemctl daemon-reload
  - sudo systemctl enable fingerprint-web.service
  - sudo systemctl start fingerprint-web.service
  - sudo systemctl status fingerprint-web.service

## Local testing and validation
- Run the app locally (development):
  - Set env vars or use .env
  - python wsgi.py
  - Open http://localhost:5000
- Validate admin/teacher dashboards render HTML and fetch data from MySQL
- Validate PDF generation endpoints for attendance
- Validate the API endpoint /api/fingerprint_scans returns scans queued by the listener

## Testing the fingerprint and attendance workflow (Pi)
1) Ensure MySQL/MariaDB is running and accessible with credentials in .env
2) Start the web service (setup_pi.sh) and ensure it’s up
3) Simulate a login as Admin, create teachers and students, enroll fingerprints (requires hardware or mock mode)
4) Check FingerprintLogs in the DB for scans
5) Generate attendance PDFs and optional emails via daily reports

## Troubleshooting
- If the service won't start: check journal for fingerprint-web.service
  - sudo journalctl -u fingerprint-web.service -f
- DB connection errors: verify DB_HOST/PORT/USER/PASSWORD/NAME in .env and MySQL server status
- Hardware issues: verify /dev/serial0 exists; ensure user belongs to dialout or has necessary permissions
- If you’re not using hardware, ensure NOOP LCD and mock mode can be enabled to allow development/test flows

## Code map (quick reference)
- main/ – Flask app factory, config, blueprints, hardware integration
- main/config.py – configuration loaded from environment
- main/database.py – MySQL connection pool factory and get_db helper
- main/hardware/ – fingerprint.py (sensor), fingerprint_listener.py (background thread), lcd.py (display abstraction)
- main/blueprints/ – admin.py, main.py, teacher.py
- main/utils/ – pdf.py, email.py, common.py
- wsgi.py – entrypoint for Gunicorn/Waitress or development server
- schema.sql – DB schema
- requirements.txt – Python dependencies

## License
This project is provided as-is under your chosen license.

## Contributing
Contributions welcome. Please follow your project’s guidelines, run tests, and keep changes minimal and well-documented.
