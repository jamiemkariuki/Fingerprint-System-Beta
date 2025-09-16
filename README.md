# Fingerprint System

A Flask web app and background listener for student attendance using a fingerprint sensor. Teachers can register students and view daily presence; admins manage teachers and students.

## Features
- Student registration with fingerprint enrollment
- Daily presence view (by class) for teachers, with attendance logged between 5 AM and 10 PM
- Admin management for teachers and students
- Background listener to match scans and log presence
- Configurable via environment variables

## Tech Stack
- Python (Flask, Flask-WTF)
- MySQL (mysql-connector)
- Adafruit fingerprint sensor (UART)
- Raspberry Pi LCD support (optional)

## Project Structure
```
Fingerprint_System/
  config.py            # Application configuration
  database.py          # Database connection and pooling
  fingerprint_listener.py# Background scanner
  wsgi.py              # WSGI entrypoint
  schema.sql           # MySQL schema
  requirements.txt     # Dependencies
  static/
    style.css          # Custom styles
  templates/
    *.html             # Jinja templates
  main/
    __init__.py        # Flask app creation and blueprint registration
    blueprints/
      admin.py         # Admin related routes
      main.py          # Main routes (e.g., home)
      teacher.py       # Teacher related routes
    hardware/
      fingerprint.py   # Fingerprint sensor handling
      lcd.py           # LCD display handling
    utils/
      pdf.py           # PDF generation utility
```

## Setup
1) Python and dependencies
```bash
python -m venv .venv
# Windows PowerShell
. .venv\Scripts\Activate.ps1
# Linux/macOS
# source .venv/bin/activate
pip install -r requirements.txt
```

2) Database (MySQL)
- Create DB and tables:
```bash
# Use a user with privileges or root
mysql -u root -p < schema.sql
```
- Create a dedicated DB user (optional, recommended):
```sql
CREATE USER 'fingerprint_user'@'%' IDENTIFIED BY 'strong-password';
GRANT ALL PRIVILEGES ON FingerprintDB.* TO 'fingerprint_user'@'%';
FLUSH PRIVILEGES;
```

3) Configure environment variables
You can set these in your shell or create a `.env` file in the project root. The app loads it automatically via python-dotenv.
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
```

Example `.env` file is supported; environment variables override `.env` if both are set.

## Running
### Development (built-in server)
```bash
# Ensure env vars are set
python wsgi.py
```
Visit http://localhost:5000

### Production (Windows)
Use Waitress WSGI server:
```bash
pip install waitress
waitress-serve --host=0.0.0.0 --port=5000 wsgi:application
```
Configure as a Windows Service or Task Scheduler task as needed.

### Production (Linux/Raspberry Pi)
Use Gunicorn:
```bash
pip install gunicorn
gunicorn -w 2 -b 0.0.0.0:5000 wsgi:application
```
Behind Nginx or another reverse proxy, also expose the /static/ path.

## Background Listener
Run the fingerprint listener in parallel with the web app to record scans:
```bash
python fingerprint_listener.py
```
Run as a service (systemd on Linux or Task Scheduler on Windows) and provide the same environment variables.

## Hardware Notes
- Fingerprint sensor is expected on `/dev/serial0` at 57600 baud (adjust in code if different)
- LCD drivers are optional; the app gracefully falls back when unavailable
- On non-Raspberry environments, hardware features are disabled via safe fallbacks

## Initial Admin
Create an admin via the Admin Signup page (`/admin_signup`). Passwords are stored using bcrypt.

## Security
- Secrets and DB credentials are read from environment variables
- Session cookies are `HttpOnly` and support `Secure`/`SameSite` configuration
- CSRF protection is enabled for all forms.
- Disable debug in production (`FLASK_DEBUG=false`)

## Troubleshooting
- Missing Python modules: run `pip install -r requirements.txt`
- MySQL connection errors: verify `DB_HOST/PORT/USER/PASSWORD/NAME` and that MySQL is running
- Hardware errors: verify UART device and permissions; app will log warnings and continue

## License
This project is provided as-is under your chosen license (add one if needed).