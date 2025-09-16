from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import datetime
import bcrypt
import mysql.connector
from main.database import get_db
from main.hardware.fingerprint import finger
import logging

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__)

def _get_student_attendance_status(cursor, student_id, today):
    cursor.execute("""
        SELECT 1 FROM FingerprintLogs
        WHERE person_type = 'student'
        AND person_id = %s
        AND DATE(timestamp) = %s
        AND TIME(timestamp) BETWEEN '05:00:00' AND '22:00:00'
        LIMIT 1
    """, (student_id, today))
    log = cursor.fetchone()
    return "Present" if log else "Absent"

@admin_bp.route('/dashboard')
def admin_dashboard():
    if "admin_id" not in session:
        return redirect(url_for("admin.admin_login"))

    today = datetime.today().date()

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM Teachers")
        teachers = cursor.fetchall()

        cursor.execute("SELECT * FROM Users")
        users = cursor.fetchall()

        for user in users:
            user["status"] = _get_student_attendance_status(cursor, user["id"], today)

        return render_template("admin_dashboard.html", teachers=teachers, users=users)
    except mysql.connector.Error as e:
        logger.exception("MySQL Error on admin dashboard: %s", e)
        flash(f"Database error: {e}", "error")
        return redirect(url_for("admin.admin_dashboard"))
    finally:
        if conn:
            conn.close()

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

@admin_bp.route('/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == "GET":
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

@admin_bp.route('/delete/student/<int:user_id>', methods=['POST'])
def delete_student(user_id):
    if "admin_id" not in session:
        return redirect(url_for("admin.admin_login"))
    conn = None
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
        flash("Student deleted successfully!", "success")
        return redirect(url_for("admin.admin_dashboard"))
    except mysql.connector.Error as e:
        logger.exception("MySQL Error deleting student: %s", e)
        flash(f"Database error: {e}", "error")
        return redirect(url_for("admin.admin_dashboard"))
    finally:
        if conn:
            conn.close()

@admin_bp.route('/delete/teacher/<int:teacher_id>', methods=['POST'])
def delete_teacher(teacher_id):
    if "admin_id" not in session:
        return redirect(url_for("admin.admin_login"))
    conn = None
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
        flash("Teacher deleted successfully!", "success")
        return redirect(url_for("admin.admin_dashboard"))
    except mysql.connector.Error as e:
        logger.exception("MySQL Error deleting teacher: %s", e)
        flash(f"Database error: {e}", "error")
        return redirect(url_for("admin.admin_dashboard"))
    finally:
        if conn:
            conn.close()

@admin_bp.route("/signup", methods=["GET", "POST"])
def admin_signup():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if password != confirm_password:
            flash("Passwords do not match!", "error")
            return redirect(url_for("admin.admin_signup"))

        hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        conn = None
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Admins (username, password_hash) VALUES (%s, %s)",
                           (username, hashed_pw))
            conn.commit()
            flash("Admin account created successfully! You can now log in.", "success")
            return redirect(url_for("admin.admin_login"))
        except mysql.connector.Error as err:
            logger.exception("Error creating admin: %s", err)
            flash(f"Error creating admin: {err}", "error")
            return redirect(url_for("admin.admin_signup"))
        finally:
            if conn:
                conn.close()

    return render_template("admin_signup.html")

@admin_bp.route('/logout')
def admin_logout():
    session.pop("admin_id", None)
    return redirect(url_for("main.home"))