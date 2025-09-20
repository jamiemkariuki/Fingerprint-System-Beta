from datetime import datetime

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
