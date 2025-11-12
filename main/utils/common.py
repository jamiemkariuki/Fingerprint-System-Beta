from datetime import datetime
from main.database import get_db
import mysql.connector

def get_setting(key):
    """Fetches a setting value from the database."""
    db = None
    cursor = None
    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT value FROM Settings WHERE `key` = %s", (key,))
        result = cursor.fetchone()
        return result['value'] if result else None
    except mysql.connector.Error as e:
        print(f"Database error in get_setting: {e}")
        return None
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()

def update_setting(key, value):
    """Updates a setting value in the database."""
    db = None
    cursor = None
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("INSERT INTO Settings (`key`, value) VALUES (%s, %s) ON DUPLICATE KEY UPDATE value = %s", (key, value, value))
        db.commit()
        return True
    except mysql.connector.Error as e:
        print(f"Database error in update_setting: {e}")
        db.rollback()
        return False
    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


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
