import os
import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import logging
from dotenv import load_dotenv
import mysql.connector

from main.database import get_db
from main.utils.common import _get_student_attendance_status
from main.utils.pdf import generate_class_attendance_pdf

# Load environment variables from .env file
load_dotenv()

# --- Logging ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO),
                    format="%(asctime)s %(levelname)s %(name)s - %(message)s")
logger = logging.getLogger(__name__)

# --- Email Constants ---
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.office365.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

def send_email(recipient_email, subject, body, attachment_data, attachment_filename):
    if not all([SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD]):
        logger.error("SMTP settings are not configured. Cannot send email.")
        return

    message = MIMEMultipart()
    message["From"] = SMTP_USERNAME
    message["To"] = recipient_email
    message["Subject"] = subject

    message.attach(MIMEText(body, "plain"))

    part = MIMEApplication(attachment_data, Name=attachment_filename)
    part['Content-Disposition'] = f'attachment; filename="{attachment_filename}"'
    message.attach(part)

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(SMTP_USERNAME, recipient_email, message.as_string())
            logger.info(f"Successfully sent email to {recipient_email}")
    except Exception as e:
        logger.exception(f"Failed to send email to {recipient_email}: {e}")

def generate_and_send_reports():
    logger.info("Starting daily report generation...")
    today = datetime.today().date()
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM Teachers")
        teachers = cursor.fetchall()

        for teacher in teachers:
            teacher_email = teacher.get("email")
            teacher_class = teacher.get("class")

            if not teacher_email or not teacher_class:
                logger.warning(f"Teacher with ID {teacher['id']} is missing email or class. Skipping.")
                continue

            cursor.execute("SELECT * FROM Users WHERE class = %s ORDER BY name", (teacher_class,))
            students = cursor.fetchall()

            for student in students:
                student["status"] = _get_student_attendance_status(cursor, student["id"], today)

            pdf_data = generate_class_attendance_pdf(teacher_class, students, today)

            subject = f"Daily Attendance Report for Class {teacher_class} - {today.strftime('%Y-%m-%d')}"
            body = f"Please find attached the daily attendance report for your class, {teacher_class}."
            attachment_filename = f"{teacher_class}_attendance_{today}.pdf"

            send_email(teacher_email, subject, body, pdf_data, attachment_filename)

    except mysql.connector.Error as e:
        logger.exception(f"Database error during report generation: {e}")
    finally:
        if conn:
            conn.close()

    logger.info("Daily report generation finished.")
