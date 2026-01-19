from flask import Blueprint, render_template, request, redirect, url_for, session, flash, make_response
from datetime import datetime
import bcrypt
import mysql.connector
from ..database import get_db
from ..utils.common import _get_student_attendance_status
from ..utils.pdf import generate_attendance_pdf, generate_class_attendance_pdf
from ..hardware.fingerprint import enroll_fingerprint
from ..hardware.lcd import lcd
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

        cursor.execute("SELECT * FROM Teachers WHERE id = %s", (session["teacher_id"],))
        teacher_info = cursor.fetchone()

        cursor.execute("SELECT DISTINCT class FROM Users ORDER BY class")
        classes = [row["class"] for row in cursor.fetchall()]

        if selected_class:
            cursor.execute("SELECT * FROM Users WHERE class = %s ORDER BY name", (selected_class,))
        else:
            cursor.execute("SELECT * FROM Users ORDER BY class, name")
        users = cursor.fetchall()

        for user in users:
            user["status"] = _get_student_attendance_status(cursor, user["id"], today)

        cursor.execute("SELECT * FROM Parents ORDER BY name")
        parents = cursor.fetchall()

        cursor.execute("""
            SELECT sp.id, sp.relationship, u.name as student_name, p.name as parent_name
            FROM StudentParents sp
            JOIN Users u ON sp.student_id = u.id
            JOIN Parents p ON sp.parent_id = p.id
            ORDER BY u.name
        """)
        student_parent_links = cursor.fetchall()

        return render_template(
            "teacher_dashboard.html",
            users=users,
            classes=classes,
            selected_class=selected_class,
            teacher_info=teacher_info,
            parents=parents,
            student_parent_links=student_parent_links
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
    enroll_fp = request.form.get("enroll_fingerprint") == "yes"

    if not name or not class_name:
        flash("Missing name or class", "error")
        return redirect(url_for("teacher.register_user"))

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("INSERT INTO Users (name, class) VALUES (%s, %s)", (name, class_name))
        conn.commit()

        user_id = cursor.lastrowid

        if enroll_fp:
            if lcd:
                lcd.clear()
                lcd.text("Place finger...", 1)

            fingerprint_id = enroll_fingerprint(user_id)

            if fingerprint_id is None:
                flash("Student registered without fingerprint. You can enroll it later.", "warning")
            else:
                cursor.execute("UPDATE Users SET fingerprint_id = %s WHERE id = %s", (fingerprint_id, user_id))
                conn.commit()
                flash("Student registered with fingerprint successfully!", "success")

            if lcd:
                lcd.clear()
                lcd.text(f"User: {name}", 1)
        else:
            flash("Student registered without fingerprint. You can enroll it later.", "info")

        return redirect(url_for("teacher.teacher_dashboard"))

    except mysql.connector.Error as e:
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
        enroll_fp = request.form.get("enroll_fingerprint") == "yes"

        if not name or not student_class:
            flash("Missing name or class", "error")
            return redirect(url_for("teacher.register_student"))

        conn = None
        try:
            conn = get_db()
            cursor = conn.cursor()

            cursor.execute("INSERT INTO Users (name, class) VALUES (%s, %s)", (name, student_class))
            conn.commit()

            user_id = cursor.lastrowid

            if enroll_fp:
                if lcd:
                    lcd.clear()
                    lcd.text("Place finger...", 1)

                fingerprint_id = enroll_fingerprint(user_id)

                if fingerprint_id is None:
                    flash("Student registered without fingerprint. You can enroll it later.", "warning")
                else:
                    cursor.execute("UPDATE Users SET fingerprint_id = %s WHERE id = %s", (fingerprint_id, user_id))
                    conn.commit()
                    flash("Student registered with fingerprint successfully!", "success")

                if lcd:
                    lcd.clear()
                    lcd.text(f"Registered {name}", 1)
            else:
                flash("Student registered without fingerprint. You can enroll it later.", "info")

            return redirect(url_for("teacher.teacher_dashboard"))

        except mysql.connector.Error as e:
            logger.exception("MySQL Error during registration: %s", e)
            flash(f"Database error: {e}", "error")
            return redirect(url_for("teacher.register_student"))
        finally:
            if conn:
                conn.close()

    return render_template("register.html")

@teacher_bp.route('/enroll_fingerprint/<int:student_id>', methods=['POST'])
def enroll_student_fingerprint(student_id):
    if "teacher_id" not in session and "admin_id" not in session:
        return redirect(url_for("teacher.teacher_login"))

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM Users WHERE id = %s", (student_id,))
        student = cursor.fetchone()

        if not student:
            flash("Student not found", "error")
            return redirect(url_for("teacher.teacher_dashboard"))

        if student.get("fingerprint_id"):
            flash(f"{student['name']} already has a fingerprint enrolled.", "warning")
            return redirect(url_for("teacher.teacher_dashboard"))

        if lcd:
            lcd.clear()
            lcd.text(f"Enroll: {student['name'][:12]}", 1)
            lcd.text("Place finger...", 2)

        fingerprint_id = enroll_fingerprint(student_id)

        if fingerprint_id is None:
            flash(f"Fingerprint enrollment failed for {student['name']}", "error")
        else:
            cursor.execute("UPDATE Users SET fingerprint_id = %s WHERE id = %s", (fingerprint_id, student_id))
            conn.commit()
            flash(f"Fingerprint enrolled successfully for {student['name']}!", "success")

        if lcd:
            lcd.clear()

        return redirect(url_for("teacher.teacher_dashboard"))

    except mysql.connector.Error as e:
        logger.exception("MySQL Error enrolling fingerprint: %s", e)
        flash(f"Database error: {e}", "error")
        return redirect(url_for("teacher.teacher_dashboard"))
    finally:
        if conn:
            conn.close()

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
    if "teacher_id" not in session and "admin_id" not in session:
        return redirect(url_for("teacher.teacher_login"))
    
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM Users WHERE id = %s", (student_id,))
        student = cursor.fetchone()

        if not student:
            flash("Student not found", "error")
            return redirect(url_for("teacher.teacher_dashboard"))

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

        response = make_response(generate_attendance_pdf(student, attendance_logs))
        response.headers['Content-Type'] = 'application/pdf'

        # FIXED QUOTES
        filename = f"{student['name']}_attendance.pdf"
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'

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

        cursor.execute("SELECT * FROM Users WHERE class = %s ORDER BY name", (class_name,))
        students = cursor.fetchall()

        for student in students:
            student["status"] = _get_student_attendance_status(cursor, student["id"], today)

        response = make_response(generate_class_attendance_pdf(class_name, students, today))
        response.headers['Content-Type'] = 'application/pdf'

        # FIXED QUOTES
        filename = f"{class_name}_attendance_{today}.pdf"
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'

        return response

    except mysql.connector.Error as e:
        logger.exception("MySQL Error generating class PDF: %s", e)
        flash(f"Database error: {e}", "error")
        return redirect(url_for("teacher.teacher_dashboard"))
    finally:
        if conn:
            conn.close()

@teacher_bp.route('/create_parent', methods=['POST'])
def create_parent():
    if "teacher_id" not in session and "admin_id" not in session:
        return redirect(url_for("teacher.teacher_login"))

    name = request.form.get("name")
    username = request.form.get("username")
    email = request.form.get("email")
    phone = request.form.get("phone", "")
    password = request.form.get("password")

    if not name or not username or not email or not password:
        flash("Missing required fields", "error")
        return redirect(url_for("teacher.teacher_dashboard"))

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Parents (name, username, email, phone, password_hash) VALUES (%s, %s, %s, %s, %s)",
            (name, username, email, phone, password_hash)
        )
        conn.commit()
        flash(f"Parent account created successfully! Username: {username}", "success")
        return redirect(url_for("teacher.teacher_dashboard"))
    except mysql.connector.Error as e:
        logger.exception("MySQL Error creating parent: %s", e)
        flash(f"Database error: {e}", "error")
        return redirect(url_for("teacher.teacher_dashboard"))
    finally:
        if conn:
            conn.close()

@teacher_bp.route('/link_student_parent', methods=['POST'])
def link_student_parent():
    if "teacher_id" not in session and "admin_id" not in session:
        return redirect(url_for("teacher.teacher_login"))

    student_id = request.form.get("student_id")
    parent_id = request.form.get("parent_id")
    relationship = request.form.get("relationship", "Parent/Guardian")

    if not student_id or not parent_id:
        flash("Missing student or parent", "error")
        return redirect(url_for("teacher.teacher_dashboard"))

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO StudentParents (student_id, parent_id, relationship) VALUES (%s, %s, %s)",
            (student_id, parent_id, relationship)
        )
        conn.commit()
        flash("Student linked to parent successfully!", "success")
        return redirect(url_for("teacher.teacher_dashboard"))
    except mysql.connector.Error as e:
        logger.exception("MySQL Error linking student to parent: %s", e)
        if "Duplicate entry" in str(e):
            flash("This student is already linked to this parent.", "warning")
        else:
            flash(f"Database error: {e}", "error")
        return redirect(url_for("teacher.teacher_dashboard"))
    finally:
        if conn:
            conn.close()
