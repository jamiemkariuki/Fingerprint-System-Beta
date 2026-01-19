from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import datetime
import bcrypt
import mysql.connector
from ..database import get_db
from ..utils.common import _get_student_attendance_status
from ..utils.pdf import generate_attendance_pdf
import logging

logger = logging.getLogger(__name__)

teacher_bp = Blueprint('teacher', __name__)

@teacher_bp.route('/dashboard')
def teacher_dashboard():
    if "teacher_id" not in session:
        return redirect(url_for("teacher.teacher_login"))

    teacher_id = session["teacher_id"]
    today = datetime.today().date()

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Get teacher info
        cursor.execute("SELECT * FROM Teachers WHERE id = %s", (teacher_id,))
        teacher = cursor.fetchone()

        # Get students in teacher's class
        cursor.execute("SELECT * FROM Users WHERE class = %s", (teacher['class'],))
        users = cursor.fetchall()

        for user in users:
            user["status"] = _get_student_attendance_status(cursor, user["id"], today)

        # Get parents
        cursor.execute("SELECT * FROM Parents ORDER BY name")
        parents = cursor.fetchall()

        # Get subjects
        cursor.execute("SELECT * FROM Subjects ORDER BY name")
        subjects = cursor.fetchall()

        # Get audit links for teacher's class
        cursor.execute("""
            SELECT sa.id, u.name as student_name, s.name as subject_name, sa.status, sa.notes
            FROM StudentAudit sa
            JOIN Users u ON sa.student_id = u.id
            JOIN Subjects s ON sa.subject_id = s.id
            WHERE u.class = %s
            ORDER BY u.name
        """, (teacher['class'],))
        audit_links = cursor.fetchall()

        return render_template("teacher_dashboard.html",
                               teacher=teacher,
                               users=users,
                               parents=parents,
                               subjects=subjects,
                               audit_links=audit_links)

    except mysql.connector.Error as e:
        logger.exception("MySQL Error on teacher dashboard: %s", e)
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
            session["teacher_name"] = teacher["name"]
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
    session.pop("teacher_name", None)
    return redirect(url_for("main.home"))

@teacher_bp.route('/create_parent', methods=['POST'])
def create_parent():
    if "teacher_id" not in session:
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

@teacher_bp.route('/create_student', methods=['POST'])
def create_student():
    if "teacher_id" not in session:
        return redirect(url_for("teacher.teacher_login"))

    name = request.form.get("name")
    username = request.form.get("username")
    class_ = request.form.get("class")
    password = request.form.get("password")

    if not name or not username or not class_ or not password:
        flash("Missing required fields", "error")
        return redirect(url_for("teacher.teacher_dashboard"))

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Users (name, username, class, password_hash) VALUES (%s, %s, %s, %s)",
            (name, username, class_, password_hash)
        )
        conn.commit()
        flash(f"Student account created successfully! Username: {username}", "success")
        return redirect(url_for("teacher.teacher_dashboard"))
    except mysql.connector.Error as e:
        logger.exception("MySQL Error creating student: %s", e)
        flash(f"Database error: {e}", "error")
        return redirect(url_for("teacher.teacher_dashboard"))
    finally:
        if conn:
            conn.close()

@teacher_bp.route('/link_student_parent', methods=['POST'])
def link_student_parent():
    if "teacher_id" not in session:
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

@teacher_bp.route('/update_audit_status', methods=['POST'])
def update_audit_status():
    if "teacher_id" not in session:
        return redirect(url_for("teacher.teacher_login"))
    
    audit_id = request.form.get("audit_id")
    status = request.form.get("status")
    notes = request.form.get("notes", "")

    if not audit_id or not status:
        flash("Audit ID and status are required.", "error")
        return redirect(url_for("teacher.teacher_dashboard"))

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE StudentAudit SET status = %s, notes = %s WHERE id = %s",
            (status, notes, audit_id)
        )
        conn.commit()
        flash("Audit status updated successfully!", "success")
    except mysql.connector.Error as e:
        logger.exception("MySQL Error updating audit status: %s", e)
        flash(f"Database error: {e}", "error")
    finally:
        if conn:
            conn.close()
    
    return redirect(url_for("teacher.teacher_dashboard"))

@teacher_bp.route('/student_attendance_pdf/<int:student_id>')
def student_attendance_pdf(student_id):
    if "teacher_id" not in session and "admin_id" not in session and "parent_id" not in session:
        return redirect(url_for("teacher.teacher_login"))

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM Users WHERE id = %s", (student_id,))
        student = cursor.fetchone()
        if not student:
            flash("Student not found", "error")
            return redirect(request.referrer or url_for("main.home"))

        # Get attendance logs for the last 30 days
        cursor.execute("""
            SELECT DATE(timestamp) as date, COUNT(*) as scan_count,
                   MIN(TIME(timestamp)) as first_scan, MAX(TIME(timestamp)) as last_scan
            FROM FingerprintLogs
            WHERE person_type = 'student' AND person_id = %s
            AND timestamp >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            GROUP BY DATE(timestamp)
            ORDER BY date DESC
        """, (student_id,))
        attendance_logs = cursor.fetchall()

        pdf_data = generate_attendance_pdf(student, attendance_logs)

        from flask import Response
        response = Response(pdf_data, mimetype='application/pdf')
        response.headers['Content-Disposition'] = f'attachment; filename=student_{student_id}_attendance.pdf'
        return response

    except mysql.connector.Error as e:
        logger.exception("MySQL Error generating PDF: %s", e)
        flash(f"Database error: {e}", "error")
        return redirect(request.referrer or url_for("main.home"))
    finally:
        if conn:
            conn.close()