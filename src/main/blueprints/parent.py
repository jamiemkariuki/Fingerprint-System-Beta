from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from datetime import datetime, timedelta
import bcrypt
import mysql.connector
from ..database import get_db
from ..utils.common import _get_student_attendance_status
import logging

logger = logging.getLogger(__name__)

parent_bp = Blueprint('parent', __name__)

@parent_bp.route('/login', methods=['GET', 'POST'])
def parent_login():
    return redirect(url_for("main.login"))

@parent_bp.route('/dashboard')
def parent_dashboard():
    if "parent_id" not in session:
        return redirect(url_for("parent.parent_login"))

    today = datetime.today().date()
    seven_days_ago = today - timedelta(days=7)

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Get parent info
        cursor.execute("SELECT * FROM Parents WHERE id = %s", (session["parent_id"],))
        parent_info = cursor.fetchone()

        # Get all children linked to this parent
        cursor.execute("""
            SELECT u.*, sp.relationship 
            FROM Users u
            JOIN StudentParents sp ON u.id = sp.student_id
            WHERE sp.parent_id = %s
            ORDER BY u.name
        """, (session["parent_id"],))
        children = cursor.fetchall()

        # For each child, get today's status and recent attendance
        for child in children:
            child["status"] = _get_student_attendance_status(cursor, child["id"], today)
            
            # Get attendance for last 7 days
            cursor.execute("""
                SELECT DATE(timestamp) as date, COUNT(*) as scan_count
                FROM FingerprintLogs
                WHERE person_type = 'student' AND person_id = %s
                AND DATE(timestamp) >= %s
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            """, (child["id"], seven_days_ago))
            child["recent_attendance"] = cursor.fetchall()

        return render_template("parent_dashboard.html", parent_info=parent_info, children=children)

    except mysql.connector.Error as e:
        logger.exception("MySQL Error on parent dashboard: %s", e)
        flash(f"Database error: {e}", "error")
        return redirect(url_for("parent.parent_dashboard"))
    finally:
        if conn:
            conn.close()

@parent_bp.route('/logout')
def parent_logout():
    session.pop("parent_id", None)
    return redirect(url_for("main.home"))
