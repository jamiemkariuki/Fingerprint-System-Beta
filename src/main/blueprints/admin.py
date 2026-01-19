from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import datetime
import bcrypt
import mysql.connector
from ..database import get_db
from ..utils.common import _get_student_attendance_status
from ..utils.email import generate_and_send_reports
import logging

logger = logging.getLogger(__name__)

# Admin blueprint
admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard')
def admin_dashboard():
    if "admin_id" not in session:
        return redirect(url_for("admin.admin_login"))

    today = datetime.today().date()

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Core data
        cursor.execute("SELECT * FROM Teachers")
        teachers = cursor.fetchall()

        cursor.execute("SELECT * FROM Users")
        users = cursor.fetchall()

        for user in users:
            user["status"] = _get_student_attendance_status(cursor, user["id"], today)

        cursor.execute("SELECT `value` FROM Settings WHERE `key` = 'send_days'")
        send_days_setting = cursor.fetchone()
        send_days = send_days_setting['value'].split(',') if send_days_setting else []

        cursor.execute("SELECT `value` FROM `Settings` WHERE `key` = 'fingerprint_listener_enabled'")
        listener_setting = cursor.fetchone()
        listener_enabled = listener_setting['value'] == '1' if listener_setting else True

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

        cursor.execute("SELECT * FROM Subjects ORDER BY name")
        subjects = cursor.fetchall()

        cursor.execute("""
            SELECT sa.id, u.name as student_name, s.name as subject_name, sa.status, sa.notes
            FROM StudentAudit sa
            JOIN Users u ON sa.student_id = u.id
            JOIN Subjects s ON sa.subject_id = s.id
            ORDER BY u.name
        """)
        audit_links = cursor.fetchall()

        # Metrics for overview bar
        student_count = len(users)
        teacher_count = len(teachers)
        subject_count = len(subjects)
        audit_count = len(audit_links)

        cursor.execute("SELECT COUNT(*) as cnt FROM StudentAudit")
        total_audit = cursor.fetchone().get("cnt", 0)
        cursor.execute("SELECT COUNT(*) as cnt FROM StudentAudit WHERE status = 'Pending'")
        pending_count = cursor.fetchone().get("cnt", 0)

        return render_template(
            "admin_dashboard.html",
            teachers=teachers,
            users=users,
            parents=parents,
            student_parent_links=student_parent_links,
            subjects=subjects,
            audit_links=audit_links,
            send_days=send_days,
            listener_enabled=listener_enabled,
            student_count=student_count,
            teacher_count=teacher_count,
            subject_count=subject_count,
            audit_count=audit_count,
            pending_count=pending_count,
            total_audit=total_audit
        )

    except mysql.connector.Error as e:
        logger.exception("MySQL Error on admin dashboard: %s", e)
        flash(f"Database error: {e}", "error")
        return redirect(url_for("admin.admin_dashboard"))
    finally:
        if conn:
            conn.close()

@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'GET':
        return render_template("admin_login.html")

    username = request.form.get("username")
    password = request.form.get("password")

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Admins WHERE username = %s", (username,))
        admin = cursor.fetchone()

        if admin and bcrypt.checkpw(password.encode(), admin["password_hash"].encode()):
            session["admin_id"] = admin["id"]
            return redirect(url_for("admin.admin_dashboard"))
        else:
            flash("Invalid admin credentials", "error")
            return redirect(url_for("admin.admin_login"))
    except mysql.connector.Error as e:
        logger.exception("MySQL Error during admin login: %s", e)
        flash(f"Database error: {e}", "error")
        return redirect(url_for("admin.admin_login"))
    finally:
        if conn:
            conn.close()

@admin_bp.route('/logout')
def admin_logout():
    session.pop("admin_id", None)
    return redirect(url_for("main.home"))

@admin_bp.route('/send_reports', methods=['POST'])
def send_reports():
    if "admin_id" not in session:
        return redirect(url_for("admin.admin_login"))

    try:
        flash("Sending reports... This may take a moment.", "info")
        generate_and_send_reports()
        flash("Reports sent successfully!", "success")
    except Exception as e:
        logger.exception(f"Error sending reports: {e}")
        flash(f"An error occurred while sending the reports: {e}", "error")

    return redirect(url_for("admin.admin_dashboard"))

@admin_bp.route('/create_teacher', methods=['POST'])
def create_teacher():
    if "admin_id" not in session:
        return redirect(url_for("admin.admin_login"))

    name = request.form.get("name")
    username = request.form.get("username")
    email = request.form.get("email")
    teacher_class = request.form.get("class")
    password = request.form.get("password")

    if not name or not username or not email or not teacher_class or not password:
        flash("Missing fields", "error")
        return redirect(url_for("admin.admin_dashboard"))

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Teachers (name, username, email, class, password_hash) VALUES (%s, %s, %s, %s, %s)",
            (name, username, email, teacher_class, password_hash)
        )
        conn.commit()
        flash("Teacher created successfully!", "success")
        return redirect(url_for("admin.admin_dashboard"))
    except mysql.connector.Error as e:
        logger.exception("MySQL Error creating teacher: %s", e)
        flash(f"Database error: {e}", "error")
        return redirect(url_for("admin.admin_dashboard"))
    finally:
        if conn:
            conn.close()
