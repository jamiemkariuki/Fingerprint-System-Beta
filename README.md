# Fingerprint System — Dockerized Deployment

A Flask-based attendance system that uses a fingerprint sensor to log student presence. It runs with a containerized deployment that can run on any Linux host (including Raspberry Pi) without requiring systemd services. It supports hardware or mock mode for development.

Table of contents:
- Overview
- What you’ll deploy
- Prerequisites
- Hardware and mock mode
- Project structure (high-level)
- Environment and configuration
- Docker-based deployment
- Local development workflow
- Testing and validation plan
- Troubleshooting
- Contributing
- License

## Overview
- Core idea: A Flask app that exposes admin/teacher dashboards and a background listener that processes fingerprint scans and logs presence to a MySQL/MariaDB database. The codebase is designed to run in a containerized environment with hardware guardrails so you can develop with mocks or full hardware.
- Containerized deployment: The web app is run inside a Docker container using Gunicorn as the WSGI server. The fingerprint listener runs in the same container as the Flask app or can be swapped for mocks when hardware isn’t present.

## What you’ll deploy
- A containerized, production-ready deployment using Docker and optionally docker-compose to run the web app and a MariaDB database.
- The app listens on port 5000 by default; you can override via environment variables.

## Prerequisites
- Docker and Docker Compose installed on your host
- Git for repo management
- If deploying on a Raspberry Pi, ensure the host supports multi-arch containers (arm64 or arm/v7 as appropriate)

## Hardware and mock mode
- Hardware: Fingerprint sensor is accessed through main/hardware/fingerprint.py. If not present, the code gracefully uses a noop LCD and mock mode.
- Mock mode: You can enable mock mode via environment variables (to be implemented in the patch) to test UI flows without a sensor.
- LCD: main/hardware/lcd.py provides a noop LCD when a physical LCD is not connected.

## Project structure (high-level)
- main/ – Flask app factory, config, blueprints, hardware integration
- main/config.py – configuration loaded from environment
- main/database.py – DB connection pool helper
- main/hardware/ – fingerprint.py, fingerprint_listener.py, lcd.py for hardware integration
- main/blueprints/ – admin.py, main.py, teacher.py
- main/utils/ – pdf.py, email.py, common.py
- wsgi.py – WSGI entrypoint used by Gunicorn
- schema.sql – DB schema
- requirements.txt – Python dependencies
- Dockerfile – container image build for the app
- docker-compose.yml – orchestrates app and DB

## Environment and configuration
- The app loads environment variables via a .env file or Docker Compose environment settings.
- Key variables (examples):
  - Flask: SECRET_KEY, FLASK_HOST, FLASK_PORT, FLASK_DEBUG, LOG_LEVEL
  - Database: DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, DB_POOL_SIZE
  - Cookies: SESSION_COOKIE_SECURE, SESSION_COOKIE_SAMESITE
  - Email: SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD

- You can start from a sample .env file and tailor values.

- See docker-compose.yml for example configuration.

## Docker-based deployment
- Dockerfile builds the app with Python and installs dependencies from requirements.txt. Gunicorn serves the app.
- docker-compose.yml provides a minimal stack with a MariaDB container and the web app container.
- Example docker-compose.yml (adjust as needed):

```
version: "3.9"
services:
  db:
    image: mariadb:10.11
    container_name: fingerprint-db
    environment:
      - MYSQL_ROOT_PASSWORD=rootpassword
      - MYSQL_DATABASE=FingerprintDB
      - MYSQL_USER=fingerprint_user
      - MYSQL_PASSWORD=secret
    volumes:
      - db_data:/var/lib/mysql
      - ./schema.sql:/docker-entrypoint-initdb.d/01_schema.sql
    ports:
      - "3306:3306"
  web:
    build: .
    container_name: fingerprint-web
    depends_on:
      - db
    environment:
      - FLASK_HOST=0.0.0.0
      - FLASK_PORT=5000
      - DB_HOST=db
      - DB_PORT=3306
      - DB_NAME=FingerprintDB
      - DB_USER=fingerprint_user
      - DB_PASSWORD=secret
      - SMTP_HOST=smtp.office365.com
      - SMTP_PORT=587
      - SMTP_USERNAME=you@example.com
      - SMTP_PASSWORD=your-password
    ports:
      - "5000:5000"
volumes:
  db_data:
```

- To deploy: run `docker-compose up --build -d` in the repository root. The DB will initialize with schema.sql on first startup.
- Access: http://localhost:5000 (or your host IP)

## Local development workflow
- Development (local):
  - Create a Python virtual environment and install dependencies
  - Start the Flask app directly with wsgi.py or python -m flask run after exporting the required env vars
  - URL: http://localhost:5000
- Development in Docker: use `docker-compose up --build` to start the containers in the foreground, then browse to http://localhost:5000

## Testing and validation plan
- Validate login for Admin, create teachers, and enroll fingerprints (requires hardware or mock mode)
- Validate FingerprintLogs in DB after scans
- Validate PDF generation endpoints for attendance
- Validate the API endpoint /api/fingerprint_scans returns scans queued by the listener

## Troubleshooting
- Docker logs: `docker-compose logs web` or `docker-compose logs db` for DB issues
- DB connection errors: verify DB_HOST/PORT/USER/PASSWORD/NAME in environment and MySQL status
- Hardware issues: verify /dev/serial0 exists; ensure user has permissions; if hardware not present, mocks provide alternatives

## Contributing
Contributions welcome. Please follow your project’s guidelines, run tests, and keep changes minimal and well-documented.

## License
This project is provided as-is under your chosen license.


Note: The Raspberry Pi provisioning script setup_pi.sh has been removed. All provisioning is now handled via Docker-based deployment (docker-compose). To enable GPIO in Docker containers, pass through devices: /dev/ttyAMA0 and /dev/serial0, and ensure the host runs pigpio or pigpiod (the container entrypoint will start pigpiod if available).