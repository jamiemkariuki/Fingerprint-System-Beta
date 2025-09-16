import os
import logging
from dotenv import load_dotenv
import time
import mysql.connector
from database import get_db as connect_db
from main.hardware.lcd import lcd
from main.hardware.fingerprint import finger

load_dotenv()

# --- Logging ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO),
                    format="%(asctime)s %(levelname)s %(name)s - %(message)s")
logger = logging.getLogger("fingerprint_listener")

def log_fingerprint(person_type, person_id):
    """Insert a scan log into FingerprintLogs table."""
    conn = None
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO FingerprintLogs (person_type, person_id) VALUES (%s, %s)",
            (person_type, person_id)
        )
        conn.commit()
        logger.info(f"[LOG] {person_type} ID {person_id} logged successfully")
    except mysql.connector.Error as e:
        logger.exception("DB error during logging: %s", e)
    except Exception as e:
        logger.exception("Unexpected error during logging: %s", e)
    finally:
        if conn:
            conn.close()

def match_fingerprint():
    """Wait for a finger, search for a match, and log it."""
    logger.info("Waiting for finger...")
    if lcd:
        lcd.text("Waiting for scan", 1)

    if not finger:
        logger.error("Fingerprint sensor unavailable.")
        if lcd:
            lcd.text("Sensor Error", 1)
        time.sleep(2)
        return

    # Wait until finger is detected
    while finger.get_image() != 0:
        time.sleep(0.1)

    if finger.image_2_tz(1) != 0:
        logger.warning("Failed to convert image")
        if lcd:
            lcd.text("Scan Failed", 1)
        return

    if finger.finger_search() != 0:
        logger.info("No match found")
        if lcd:
            lcd.text("No match!", 1)
        return

    # Match found
    matched_id = finger.finger_id
    confidence = finger.confidence
    logger.info("Match found! ID=%s, Confidence=%s", matched_id, confidence)
    if lcd:
        lcd.text(f"Matched ID:{matched_id}", 1)

    conn = None
    try:
        conn = connect_db()
        cursor = conn.cursor(dictionary=True)

        # First check if ID belongs to student
        cursor.execute("SELECT * FROM Users WHERE fingerprint_id = %s", (matched_id,))
        user = cursor.fetchone()
        if user:
            logger.info("Student: %s (Class %s)", user['name'], user['class'])
            if lcd:
                lcd.text(f"Student: {user['name']}", 1)
            log_fingerprint("student", user["id"])
            return

        # Then check if ID belongs to teacher
        cursor.execute("SELECT * FROM Teachers WHERE fingerprint_id = %s", (matched_id,))
        teacher = cursor.fetchone()
        if teacher:
            logger.info("Teacher: %s", teacher['name'])
            if lcd:
                lcd.text(f"Teacher: {teacher['name']}", 1)
            log_fingerprint("teacher", teacher["id"])
            return

        logger.warning("Match not found in DB (orphan ID)")
        if lcd:
            lcd.text("Unknown ID", 1)

    except mysql.connector.Error as e:
        logger.exception("DB error during match lookup: %s", e)
        if lcd:
            lcd.text("DB Error", 1)
    except Exception as e:
        logger.exception("Unexpected error during match lookup: %s", e)
        if lcd:
            lcd.text("Error", 1)
    finally:
        if conn:
            conn.close()

# --- Main Loop ---
if __name__ == "__main__":
    logger.info("Fingerprint listener started. Waiting for scans...")
    if lcd:
        lcd.text("Listener Ready", 1)
    while True:
        try:
            match_fingerprint()
            time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Exiting listener...")
            if lcd:
                lcd.text("Listener Stopped", 1)
            break
        except Exception as e:
            logger.exception("Unhandled error in listener loop: %s", e)
            if lcd:
                lcd.text("Error in Loop", 1)
            time.sleep(2)
