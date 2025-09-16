import os
import logging
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash, make_response
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import serial
import mysql.connector
from mysql.connector import pooling
import time
import bcrypt
try:
    from adafruit_fingerprint import Adafruit_Fingerprint
except Exception:
    Adafruit_Fingerprint = None  # type: ignore
try:
    from rpi_lcd import LCD
except Exception:
    LCD = None  # type: ignore
from datetime import datetime

load_dotenv()
app = Flask(__name__)

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO),
                    format="%(asctime)s %(levelname)s %(name)s - %(message)s")
logger = logging.getLogger("fingerprint_app")

# Security/session config
app.secret_key = os.getenv("SECRET_KEY", os.urandom(32))
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
app.config["SESSION_COOKIE_SECURE"] = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"

# --- LCD Setup ---
class _NoopLcd:
    def clear(self):
        logger.debug("LCD clear (noop)")

    def text(self, message, line):
        logger.info("LCD[%d]: %s", line, message)

if LCD:
    try:
        lcd = LCD()  # Initialize with default address 0x27
    except Exception as e:
        logger.warning("LCD init failed, using noop: %s", e)
        lcd = _NoopLcd()
else:
    lcd = _NoopLcd()

# --- Fingerprint Sensor Setup ---
finger = None
try:
    uart = serial.Serial("/dev/serial0", baudrate=57600, timeout=1)
    if Adafruit_Fingerprint:
        finger = Adafruit_Fingerprint(uart)
    else:
        logger.warning("Adafruit_Fingerprint not available; sensor disabled")
except Exception as e:
    logger.warning("Fingerprint sensor init failed: %s", e)

# --- MySQL Config ---
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'fingerprint_user'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'FingerprintDB'),
    'port': int(os.getenv('DB_PORT', '3306')),
}

try:
    db_pool = pooling.MySQLConnectionPool(pool_name="fp_pool", pool_size=int(os.getenv("DB_POOL_SIZE", "5")), **DB_CONFIG)
except Exception as e:
    logger.warning("DB pool init failed, falling back to direct connections: %s", e)
    db_pool = None

def get_db():
    if db_pool:
        return db_pool.get_connection()
    return mysql.connector.connect(**DB_CONFIG)

# --- Helper Functions ---
def enroll_fingerprint():
    lcd.clear()
    lcd.text("Place finger...", 1)
    if not finger:
        logger.error("Fingerprint sensor unavailable")
        return None
    while finger.get_image() != 0:
        pass
    if finger.image_2_tz(1) != 0:
        lcd.clear()
        lcd.text("First scan fail", 1)
        return None

    lcd.clear()
    lcd.text("Remove finger", 1)
    time.sleep(2)

    lcd.clear()
    lcd.text("Scan again...", 1)
    while finger.get_image() != 0:
        pass
    if finger.image_2_tz(2) != 0:
        lcd.clear()
        lcd.text("Second scan fail", 1)
        return None

    if finger.create_model() != 0:
        lcd.clear()
        lcd.text("No match!", 1)
        return None

    for fid in range(1, 127):
        if finger.load_model(fid) != 0:
            if finger.store_model(fid) == 0:
                lcd.clear()
                lcd.text(f"Saved ID:{fid}", 1)
                return fid

    lcd.clear()
    lcd.text("No space!", 1)
    return None

# --- HOME PAGE ---
@app.route('/')
def home():
    return render_template('home.html')

# --- USER REGISTRATION ---
@app.route('/register', methods=['GET', 'POST'])
def register_user():
    if "admin_id" not in session and "teacher_id" not in session:
        return redirect(url_for("teacher_login"))

    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name")
    class_name = request.form.get("class")

    if not name or not class_name:
        return jsonify({"status": "error", "message": "Missing name or class"}), 400

    lcd.clear()
    lcd.text("Registering...", 1)

    fingerprint_id = enroll_fingerprint()
    if fingerprint_id is None:
        return jsonify({"status": "error", "message": "Fingerprint enrollment failed"}), 500

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Users (name, class, fingerprint_id) VALUES (%s, %s, %s)",
            (name, class_name, fingerprint_id)
        )
        conn.commit()
        conn.close()
        lcd.clear()
        lcd.text(f"User: {name}", 1)
        return redirect(url_for("teacher_dashboard"))
    except mysql.connector.Error as e:
        lcd.clear()
        lcd.text("DB Error", 1)
        logger.exception("MySQL Error during registration: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/register_student", methods=["GET", "POST"])
def register_student():
    if request.method == "POST":
        name = request.form.get("name")
        student_class = request.form.get("class")

        if not name or not student_class:
            return jsonify({"status": "error", "message": "Missing name or class"}), 400

        lcd.clear()
        lcd.text("Place finger...", 1)
        fingerprint_id = enroll_fingerprint()

        if fingerprint_id is None:
            return jsonify({"status": "error", "message": "Fingerprint enrollment failed"}), 500

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Users (name, class, fingerprint_id) VALUES (%s, %s, %s)",
                       (name, student_class, fingerprint_id))
        conn.commit()
        cursor.close()
        conn.close()

        lcd.clear()
        lcd.text(f"Registered {name}", 1)
        return redirect(url_for("teacher_dashboard"))

    return render_template("register.html")


# --- TEACHER DASHBOARD ---
@app.route('/teacher/dashboard')
def teacher_dashboard():

    selected_class = request.args.get("class")
    today = datetime.today().date()

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Fetch distinct classes for filter dropdown
        cursor.execute("SELECT DISTINCT class FROM Users ORDER BY class")
        classes = [row["class"] for row in cursor.fetchall()]

        # Fetch students based on class filter
        if selected_class:
            cursor.execute("SELECT * FROM Users WHERE class = %s ORDER BY name", (selected_class,))
        else:
            cursor.execute("SELECT * FROM Users ORDER BY class, name")
        users = cursor.fetchall()

        # Mark each student as Present/Absent
        for user in users:
            cursor.execute("""
                SELECT 1 FROM FingerprintLogs
                WHERE person_type = 'student'
                AND person_id = %s
                AND DATE(timestamp) = %s
                LIMIT 1
            """, (user["id"], today))
            log = cursor.fetchone()
            user["status"] = "Present" if log else "Absent"

        conn.close()

        return render_template(
            "teacher_dashboard.html",
            users=users,
            classes=classes,
            selected_class=selected_class
        )
    except mysql.connector.Error as e:
        logger.exception("MySQL Error on teacher dashboard: %s", e)
        return f"Database error: {e}", 500
# --- ADMIN DASHBOARD ---
@app.route('/admin/dashboard')
def admin_dashboard():
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    today = datetime.today().date()

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM Teachers")
        teachers = cursor.fetchall()

        cursor.execute("SELECT * FROM Users")
        users = cursor.fetchall()

        for user in users:
            cursor.execute("""
                SELECT 1 FROM FingerprintLogs
                WHERE person_type = 'student'
                AND person_id = %s
                AND DATE(timestamp) = %s
                LIMIT 1
            """, (user["id"], today))
            log = cursor.fetchone()
            user["status"] = "Present" if log else "Absent"

        conn.close()

        return render_template("admin_dashboard.html", teachers=teachers, users=users)
    except mysql.connector.Error as e:
        logger.exception("MySQL Error on admin dashboard: %s", e)
        return f"Database error: {e}", 500


@app.route('/admin/create_teacher', methods=['POST'])
def create_teacher():
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    name = request.form.get("name")
    username = request.form.get("username")
    password = request.form.get("password")

    if not name or not username or not password:
        return "Missing fields", 400

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Teachers (name, username, password_hash) VALUES (%s, %s, %s)",
            (name, username, password_hash)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("admin_dashboard"))
    except mysql.connector.Error as e:
        logger.exception("MySQL Error creating teacher: %s", e)
        return f"Database error: {e}", 500

# --- LOGIN ROUTES ---
@app.route('/teacher/login', methods=['GET', 'POST'])
def teacher_login():
    if request.method == "GET":
        return render_template("teacher_login.html")

    username = request.form.get("username")
    password = request.form.get("password")

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Teachers WHERE username = %s", (username,))
        teacher = cursor.fetchone()
        conn.close()

        if teacher and bcrypt.checkpw(password.encode(), teacher["password_hash"].encode()):
            session["teacher_id"] = teacher["id"]
            return redirect(url_for("teacher_dashboard"))
        else:
            return "Invalid teacher credentials", 401
    except mysql.connector.Error as e:
        logger.exception("MySQL Error during teacher login: %s", e)
        return f"Database error: {e}", 500

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == "GET":
        return render_template("admin_login.html")

    username = request.form.get("username")
    password = request.form.get("password")

    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Admins WHERE username = %s", (username,))
        admin = cursor.fetchone()
        conn.close()

        if admin and bcrypt.checkpw(password.encode(), admin["password_hash"].encode()):
            session["admin_id"] = admin["id"]
            return redirect(url_for("admin_dashboard"))
        else:
            return "Invalid admin credentials", 401
    except mysql.connector.Error as e:
        logger.exception("MySQL Error during admin login: %s", e)
        return f"Database error: {e}", 500

# --- DELETE STUDENT ---
@app.route('/delete/student/<int:user_id>', methods=['POST'])
def delete_student(user_id):
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT fingerprint_id FROM Users WHERE id = %s", (user_id,))
        user = cursor.fetchone()

        if user and user["fingerprint_id"]:
            fid = user["fingerprint_id"]
            try:
                if finger and finger.delete_model(fid) == 0:
                    logger.info("Fingerprint ID %s deleted from sensor.", fid)
            except Exception as e:
                logger.warning("Could not delete fingerprint from sensor: %s", e)

        cursor.execute("DELETE FROM Users WHERE id = %s", (user_id,))
        conn.commit()
        conn.close()
        return redirect(url_for("admin_dashboard"))
    except mysql.connector.Error as e:
        logger.exception("MySQL Error deleting student: %s", e)
        return f"Database error: {e}", 500

# --- DELETE TEACHER ---
@app.route('/delete/teacher/<int:teacher_id>', methods=['POST'])
def delete_teacher(teacher_id):
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT fingerprint_id FROM Teachers WHERE id = %s", (teacher_id,))
        teacher = cursor.fetchone()

        if teacher and teacher["fingerprint_id"]:
            fid = teacher["fingerprint_id"]
            try:
                if finger and finger.delete_model(fid) == 0:
                    logger.info("Fingerprint ID %s deleted from sensor.", fid)
            except Exception as e:
                logger.warning("Could not delete fingerprint from sensor: %s", e)

        cursor.execute("DELETE FROM Teachers WHERE id = %s", (teacher_id,))
        conn.commit()
        conn.close()
        return redirect(url_for("admin_dashboard"))
    except mysql.connector.Error as e:
        logger.exception("MySQL Error deleting teacher: %s", e)
        return f"Database error: {e}", 500

# --- ADMIN SIGNUP ---
@app.route("/admin_signup", methods=["GET", "POST"])
def admin_signup():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            flash("Passwords do not match!", "error")
            return redirect(url_for("admin_signup"))

        hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        try:
            db = get_db()
            cursor = db.cursor()
            cursor.execute("INSERT INTO Admins (username, password_hash) VALUES (%s, %s)",
                           (username, hashed_pw))
            db.commit()
            cursor.close()
            db.close()
            flash("Admin account created successfully! You can now log in.", "success")
            return redirect(url_for("admin_login"))
        except mysql.connector.Error as err:
            logger.exception("Error creating admin: %s", err)
            flash(f"Error creating admin: {err}", "error")
            return redirect(url_for("admin_signup"))

    return render_template("admin_signup.html")

# --- PDF GENERATION ---
@app.route('/student/<int:student_id>/attendance_pdf')
def student_attendance_pdf(student_id):
    # Check if user has permission (teacher or admin)
    if "teacher_id" not in session and "admin_id" not in session:
        return redirect(url_for("teacher_login"))
    
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # Get student info
        cursor.execute("SELECT * FROM Users WHERE id = %s", (student_id,))
        student = cursor.fetchone()
        
        if not student:
            conn.close()
            return "Student not found", 404
        
        # Get attendance logs
        cursor.execute("""
            SELECT DATE(timestamp) as date, 
                   COUNT(*) as scan_count,
                   MIN(timestamp) as first_scan,
                   MAX(timestamp) as last_scan
            FROM FingerprintLogs 
            WHERE person_type = 'student' AND person_id = %s
            GROUP BY DATE(timestamp)
            ORDER BY date DESC
        """, (student_id,))
        attendance_logs = cursor.fetchall()
        
        conn.close()
        
        # Generate PDF
        response = make_response(generate_attendance_pdf(student, attendance_logs))
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{student["name"]}_attendance.pdf"'
        return response
        
    except mysql.connector.Error as e:
        logger.exception("MySQL Error generating PDF: %s", e)
        return f"Database error: {e}", 500

def generate_attendance_pdf(student, attendance_logs):
    """Generate PDF content for student attendance report"""
    from io import BytesIO
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=1  # Center alignment
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12
    )
    
    # Build PDF content
    story = []
    
    # Title
    story.append(Paragraph("Student Attendance Report", title_style))
    story.append(Spacer(1, 20))
    
    # Student info
    story.append(Paragraph("Student Information", heading_style))
    student_info = [
        ["Name:", student["name"]],
        ["Class:", student["class"]],
        ["Student ID:", str(student["id"])],
        ["Fingerprint ID:", str(student["fingerprint_id"]) if student["fingerprint_id"] else "Not assigned"]
    ]
    
    student_table = Table(student_info, colWidths=[1.5*inch, 3*inch])
    student_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(student_table)
    story.append(Spacer(1, 20))
    
    # Attendance summary
    total_days = len(attendance_logs)
    story.append(Paragraph(f"Attendance Summary ({total_days} days recorded)", heading_style))
    
    if attendance_logs:
        # Table headers
        table_data = [["Date", "Scans", "First Scan", "Last Scan"]]
        
        for log in attendance_logs:
            table_data.append([
                log["date"].strftime("%Y-%m-%d"),
                str(log["scan_count"]),
                log["first_scan"].strftime("%H:%M:%S"),
                log["last_scan"].strftime("%H:%M:%S")
            ])
        
        attendance_table = Table(table_data, colWidths=[1.2*inch, 0.8*inch, 1.2*inch, 1.2*inch])
        attendance_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
        ]))
        story.append(attendance_table)
    else:
        story.append(Paragraph("No attendance records found.", styles['Normal']))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# --- LOGOUT ROUTES ---
@app.route('/teacher/logout')
def teacher_logout():
    session.pop("teacher_id", None)
    return redirect(url_for("teacher_login"))

@app.route('/admin/logout')
def admin_logout():
    session.pop("admin_id", None)
    return redirect(url_for("admin_login"))

# --- MAIN ENTRY POINT ---
if __name__ == "__main__":
    lcd.clear()
    lcd.text("System Ready", 1)
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host=host, port=port, debug=debug)

