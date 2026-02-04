# St. Nicholas Senior School - Biometric Attendance System

A comprehensive web-based attendance management system integrated with the **ZK9500 USB Fingerprint Scanner**. This system allows for student enrollment, live attendance tracking, and class management via a Flask web application.

## 🚀 Features

- **Biometric Integration**: Seamless connection with ZK9500 USB Scanner using `pyzkfp`.
- **Live Attendance**: Background listener automatically logs attendance when a registered finger is scanned.
- **Teacher Dashboard**: Manage students, enroll fingerprints, and view class attendance.
- **PDF Reports**: Generate attendance reports for individual students.
- **Role-Based Access**: Secure login for Admins, Teachers, Parents, and Students.
- **Robust Hardware Handling**: Auto-reconnect and device banning logic to handle unstable hardware connections.

## 📋 Prerequisites

Before running the application, ensure you have the following installed on your **Windows** machine:

1.  **Python 3.8+**: [Download Python](https://www.python.org/downloads/)
2.  **MySQL Server**: [Download MySQL Community Server](https://dev.mysql.com/downloads/mysql/)
3.  **ZK9500 Drivers**: Ensure the official ZKTEco drivers are installed and the device is recognized in Windows Device Manager.

## 🛠️ Installation & Setup

### 1. Clone/Setup Project
Navigate to the project directory:
```powershell
cd Fingerprint-System-Beta
```

### 2. Install Dependencies
It is recommended to use a virtual environment:
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Database Configuration
1.  Ensure your MySQL server is running.
2.  This project comes with an **auto-initialization script**. It will create the database `fpsnsdb` and the default admin user.
    ```powershell
    python init_db.py
    ```
    *Note: If your local MySQL setup has a password for the `root` user, you must edit `.env` first (see below).*

### 4. Configuration (.env)
A `.env` file is included in the project root. Update the keys if necessary:
```ini
# Flask
FLASK_PORT=5000
FLASK_DEBUG=true

# Database
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=       # Add your password here if set
DB_NAME=fpsnsdb

# Email (Optional)
SMTP_USERNAME=...
```

## ▶️ Running the Application

To start the server, verify your environment is set up and run:

```powershell
$env:PYTHONPATH="."
python wsgi.py
```

- **Access the Web App**: Open [http://localhost:5000](http://localhost:5000)
- **Default Admin Credentials**:
    - **Username**: `admin`
    - **Password**: `admin123`

## 📖 Usage Guide

### 1. Enrolling a Student (Capturing Fingerprint)
1.  Log in as a **Teacher** (or Admin).
2.  Navigate to the **Students** tab on the Dashboard.
3.  Fill in the student details (Name, Class, etc.).
4.  **CHECK** the box labeled **"Enroll Fingerprint Now"**.
5.  Click **Create Student**.
6.  The system will prompt you to place the finger on the ZK9500 scanner.
7.  Upon success, the student is saved, and the fingerprint template is stored in the database.

### 2. Live Attendance
- Once the server is running, the **Scanner Loop** runs in the background.
- Simply **place a registered finger** on the scanner at any time.
- The system will log the attendance to the `FingerprintLogs` table.
- Log in to the Dashboard to see the "Live Attendance" feed update.

## 🔧 Troubleshooting

### "Invalid Handle" or Hardware Errors
If the logs show "Invalid Handle", the system has built-in logic to handle this:
- It will **ignore** the faulty device index (e.g., Index 0) and try the next one (Index 1).
- It applies a **5-second cool-down** before trying to reconnect.
- **Action**: Ensure the USB cable is securely connected. If the issue persists, unplug and replug the scanner.

### ImportError: No module named 'src'
Ensure you are running the command with the python path set:
```powershell
$env:PYTHONPATH="."
python wsgi.py
```

### Database Connection Failed
- Check if MySQL service is running.
- Verify credentials in `.env`.
- Run `python init_db.py` to test the connection explicitly.

## 📂 Project Structure

- `src/main/`: Core application logic (Blueprints, Database).
- `src/main/hardware/`: Hardware interface (`fingerprint.py`, `fingerprint_listener.py`).
- `templates/`: HTML files for the frontend.
- `static/`: CSS, JS, and images.
- `schema.sql`: Database structure.
- `requirements.txt`: Python dependencies.
