from flask import Blueprint, render_template, request, redirect, url_for, session, flash, make_response, jsonify
from datetime import datetime
import bcrypt
import mysql.connector
from main.database import get_db
from main.utils.common import _get_student_attendance_status
from main.utils.pdf import generate_attendance_pdf, generate_class_attendance_pdf
from main.hardware.fingerprint import enroll_fingerprint
from main.hardware.lcd import lcd
import logging

logger = logging.getLogger(__name__)

teacher_bp = Blueprint('teacher', __name__)

@teacher_bp.route('/dashboard')
def teacher_dashboard():
    if "teacher_id" not in session:
        return redirect(url_for("teacher.teacher_login"))

    selected_class = request.args.get("class")
    today = datetime.today().date()

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Fetch teacher info
        cursor.execute("SELECT * FROM Teachers WHERE id = %s", (session["teacher_id"],))
        teacher_info = cursor.fetchone()

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
            user["status"] = _get_student_attendance_status(cursor, user["id"], today)

        return render_template(
            "teacher_dashboard.html",
            users=users,
            classes=classes,
            selected_class=selected_class,
            teacher_info=teacher_info
        )
    except mysql.connector.Error as e:
        logger.exception("MySQL Error on teacher dashboard: %s", e)
        flash(f"Database error: {e}", "error")
        return redirect(url_for("teacher.teacher_dashboard"))
    finally:
        if conn:
            conn.close()

@teacher_bp.route('/register', methods=['GET', 'POST'])
def register_user():
    if "admin_id" not in session and "teacher_id" not in session:
        return redirect(url_for("teacher.teacher_login"))

    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name")
    class_name = request.form.get("class")

    if not name or not class_name:
        flash("Missing name or class", "error")
        return redirect(url_for("teacher.register_user"))

    if lcd:
        lcd.clear()
        lcd.text("Registering...", 1)

    fingerprint_id = enroll_fingerprint()
    if fingerprint_id is None:
        flash("Fingerprint enrollment failed", "error")
        return redirect(url_for("teacher.register_user"))

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Users (name, class, fingerprint_id) VALUES (%s, %s, %s)",
            (name, class_name, fingerprint_id)
        )
        conn.commit()
        if lcd:
            lcd.clear()
            lcd.text(f"User: {name}", 1)
        flash("Student registered successfully!", "success")
        return redirect(url_for("teacher.teacher_dashboard"))
    except mysql.connector.Error as e:
        if lcd:
            lcd.clear()
            lcd.text("DB Error", 1)
        logger.exception("MySQL Error during registration: %s", e)
        flash(f"Database error: {e}", "error")
        return redirect(url_for("teacher.register_user"))
    finally:
        if conn:
            conn.close()

@teacher_bp.route("/register_student", methods=["GET", "POST"])
def register_student():
    if request.method == "POST":
        name = request.form.get("name")
        student_class = request.form.get("class")

        if not name or not student_class:
            flash("Missing name or class", "error")
            return redirect(url_for("teacher.register_student"))

        if lcd:
            lcd.clear()
            lcd.text("Place finger...", 1)
        fingerprint_id = enroll_fingerprint()

        if fingerprint_id is None:
            flash("Fingerprint enrollment failed", "error")
            return redirect(url_for("teacher.register_student"))

        conn = None
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Users (name, class, fingerprint_id) VALUES (%s, %s, %s)",
                           (name, student_class, fingerprint_id))
            conn.commit()

            if lcd:
                lcd.clear()
                lcd.text(f"Registered {name}", 1)
            flash("Student registered successfully!", "success")
            return redirect(url_for("teacher.teacher_dashboard"))
        except mysql.connector.Error as e:
            if lcd:
                lcd.clear()
                lcd.text("DB Error", 1)
            logger.exception("MySQL Error during registration: %s", e)
            flash(f"Database error: {e}", "error")
            return redirect(url_for("teacher.register_student"))
        finally:
            if conn:
                conn.close()

    return render_template("register.html")

@teacher_bp.route('/login', methods=['GET', 'POST'])
def teacher_login():
    if request.method == "GET":
        return render_template("teacher_login.html")

    username = request.form.get("username")
    password = request.form.get("password")

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Teachers WHERE username = %s", (username,))
        teacher = cursor.fetchone()

        if teacher and bcrypt.checkpw(password.encode(), teacher["password_hash"].encode()):
            session["teacher_id"] = teacher["id"]
            return redirect(url_for("teacher.teacher_dashboard"))
        else:
            flash("Invalid teacher credentials", "error")
            return redirect(url_for("teacher.teacher_login"))
    except mysql.connector.Error as e:
        logger.exception("MySQL Error during teacher login: %s", e)
        flash(f"Database error: {e}", "error")
        return redirect(url_for("teacher.teacher_login"))
    finally:
        if conn:
            conn.close()

@teacher_bp.route('/logout')
def teacher_logout():
    session.pop("teacher_id", None)
    return redirect(url_for("main.home"))

@teacher_bp.route('/student/<int:student_id>/attendance_pdf')
def student_attendance_pdf(student_id):
    # Check if user has permission (teacher or admin)
    if "teacher_id" not in session and "admin_id" not in session:
        return redirect(url_for("teacher.teacher_login"))
    
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        
        # Get student info
        cursor.execute("SELECT * FROM Users WHERE id = %s", (student_id,))
        student = cursor.fetchone()
        
        if not student:
            flash("Student not found", "error")
            return redirect(url_for("teacher.teacher_dashboard"))
        
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
        
        # Generate PDF
        response = make_response(generate_attendance_pdf(student, attendance_logs))
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{student["name"]}_attendance.pdf"'
        return response
        
    except mysql.connector.Error as e:
        logger.exception("MySQL Error generating PDF: %s", e)
        flash(f"Database error: {e}", "error")
        return redirect(url_for("teacher.teacher_dashboard"))
    finally:
        if conn:
            conn.close()

@teacher_bp.route('/class_attendance_pdf/<string:class_name>')
def class_attendance_pdf(class_name):
    if "teacher_id" not in session and "admin_id" not in session:
        return redirect(url_for("teacher.teacher_login"))

    today = datetime.today().date()

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Get all students for the given class
        cursor.execute("SELECT * FROM Users WHERE class = %s ORDER BY name", (class_name,))
        students = cursor.fetchall()

        # Determine attendance status for each student
        for student in students:
            student["status"] = _get_student_attendance_status(cursor, student["id"], today)

        # Generate PDF
        response = make_response(generate_class_attendance_pdf(class_name, students, today))
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename="{class_name}_attendance_{today}.pdf"'
        return response

    except mysql.connector.Error as e:
        logger.exception("MySQL Error generating class PDF: %s", e)
        flash(f"Database error: {e}", "error")
        return redirect(url_for("teacher.teacher_dashboard"))
    finally:
        if conn:
            conn.close()