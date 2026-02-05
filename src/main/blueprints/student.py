from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import bcrypt
import mysql.connector
from ..database import get_db
from ..utils.common import _get_student_attendance_status
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

student_bp = Blueprint('student', __name__)


@student_bp.route('/login', methods=['GET', 'POST'])
def student_login():
    return redirect(url_for("main.login"))


@student_bp.route('/dashboard')
def student_dashboard():
    if "student_id" not in session:
        return redirect(url_for("student.student_login"))

    student_id = session["student_id"]
    today = datetime.today().date()

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        # Student info
        cursor.execute("SELECT * FROM Users WHERE id = %s", (student_id,))
        student = cursor.fetchone()

        # All enrolled subjects and their clearance status
        cursor.execute("""
            SELECT ss.subject_id, sa.id as audit_id, s.name as subject_name, sa.status, sa.notes, sa.updated_at
            FROM StudentSubjects ss
            JOIN Subjects s ON ss.subject_id = s.id
            LEFT JOIN StudentAudit sa ON (ss.student_id = sa.student_id AND ss.subject_id = sa.subject_id)
            WHERE ss.student_id = %s
            ORDER BY s.name
        """, (student_id,))
        audit_records = cursor.fetchall()
        enrolled_subject_ids = [r['subject_id'] for r in audit_records]

        # Attendance today
        status = _get_student_attendance_status(cursor, student_id, today)

        # Weekly attendance summary
        cursor.execute("""
            SELECT DATE(timestamp) as date, COUNT(*) as count
            FROM FingerprintLogs
            WHERE person_type = 'student' AND person_id = %s
            AND timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY DATE(timestamp)
            ORDER BY date DESC
        """, (student_id,))
        history = cursor.fetchall()

        # Fetch Timetable for student's class
        cursor.execute("""
            SELECT t.day_of_week, s.name as subject_name, t.start_time, t.end_time, te.name as teacher_name, t.subject_id
            FROM Timetable t
            JOIN Subjects s ON t.subject_id = s.id
            LEFT JOIN Teachers te ON t.teacher_id = te.id
            WHERE t.class = %s
            ORDER BY FIELD(t.day_of_week, 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'), t.start_time
        """, (student['class'],))
        timetable = cursor.fetchall()

        return render_template(
            "student_dashboard.html",
            student=student,
            audit_records=audit_records,
            enrolled_subject_ids=enrolled_subject_ids,
            status=status,
            history=history,
            timetable=timetable
        )

    except mysql.connector.Error as e:
        logger.exception("MySQL Error on student dashboard: %s", e)
        flash(f"Database error: {e}", "error")
        return redirect(url_for("main.home"))
    finally:
        if conn:
            conn.close()


@student_bp.route('/logout')
def student_logout():
    session.pop("student_id", None)
    session.pop("student_name", None)
    return redirect(url_for("main.home"))


@student_bp.route('/audit_note/<int:audit_id>', methods=['POST'])
def audit_note(audit_id):
    if "student_id" not in session:
        return redirect(url_for("student.student_login"))
    note = request.form.get("note", "").strip()
    if not note:
        flash("Note cannot be empty", "error")
        return redirect(request.referrer or url_for("student.student_dashboard"))
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, notes FROM StudentAudit WHERE id = %s AND student_id = %s", (audit_id, session["student_id"]))
        audit = cursor.fetchone()
        if not audit:
            flash("Audit not found", "error")
            return redirect(url_for("student.student_dashboard"))
        current_notes = audit.get("notes")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_notes = (current_notes + "\n" if current_notes else "") + f"{timestamp} {note}"
        cursor.execute("UPDATE StudentAudit SET notes = %s WHERE id = %s", (new_notes, audit_id))
        conn.commit()
        flash("Note added to audit record", "success")
    except mysql.connector.Error as e:
        logger.exception("MySQL Error adding note to audit: %s", e)
        flash(f"Database error: {e}", "error")
    finally:
        if conn:
            conn.close()
    return redirect(url_for("student.student_dashboard"))
@student_bp.route('/my_audit_pdf')
def my_audit_pdf():
    if "student_id" not in session:
        return redirect(url_for("student.student_login"))

    student_id = session["student_id"]
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM Users WHERE id = %s", (student_id,))
        student = cursor.fetchone()

        cursor.execute("""
            SELECT s.name as subject_name, sa.status, sa.notes
            FROM StudentAudit sa
            JOIN Subjects s ON sa.subject_id = s.id
            WHERE sa.student_id = %s
            ORDER BY s.name
        """, (student_id,))
        audit_records = cursor.fetchall()

        from ..utils.pdf import generate_audit_report_pdf
        pdf_data = generate_audit_report_pdf(student, audit_records)

        from flask import Response
        response = Response(pdf_data, mimetype='application/pdf')
        response.headers['Content-Disposition'] = 'attachment; filename=my_clearance.pdf'
        return response

    except mysql.connector.Error as e:
        logger.exception("MySQL Error generating student audit PDF: %s", e)
        flash(f"Database error: {e}", "error")
        return redirect(url_for("student.student_dashboard"))
    finally:
        if conn:
            conn.close()
