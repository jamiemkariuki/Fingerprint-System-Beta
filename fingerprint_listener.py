import os
import logging
from dotenv import load_dotenv
import time
import mysql.connector
from main.database import get_db as connect_db
from main.hardware.lcd import lcd
from main.hardware.fingerprint import finger
from datetime import datetime, timedelta

load_dotenv()

# --- Constants ---
PERSON_TYPE_STUDENT = 'student'
PERSON_TYPE_TEACHER = 'teacher'
LCD_LINE_LENGTH = 16

# --- Logging ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO),
                    format="%(asctime)s %(levelname)s %(name)s - %(message)s")
logger = logging.getLogger("fingerprint_listener")

# --- In-memory cache for first scans ---
_first_scan_cache = {}

def _clear_old_scans():
    """Clears scans older than 24 hours or from a previous day's 10 PM cutoff."""
    now = datetime.now()
    keys_to_remove = []
    for key, scan_time in _first_scan_cache.items():
        # Clear if older than 24 hours or if it's past 10 PM today and scan was from yesterday
        if (now - scan_time) > timedelta(hours=24) or \
           (now.hour >= 22 and scan_time.date() < now.date()):
            keys_to_remove.append(key)
    for key in keys_to_remove:
        _first_scan_cache.pop(key)
        logger.info(f"Cleared old first scan for {key}")

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
            lcd.text("Clean finger", 1)
            lcd.text("& sensor", 2)
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

        person_type = None
        person_id = None

        # First check if ID belongs to student
        cursor.execute("SELECT * FROM Users WHERE fingerprint_id = %s", (matched_id,))
        user = cursor.fetchone()
        if user:
            person_type = PERSON_TYPE_STUDENT
            person_id = user["id"]
            display_name = user['name']
            if len(display_name) > LCD_LINE_LENGTH - len("Student: "):
                display_name = display_name[:LCD_LINE_LENGTH - len("Student: ") - 3] + "..."
            logger.info("Student: %s (Class %s)", user['name'], user['class'])
            if lcd:
                lcd.text(f"Student: {display_name}", 1)

        # Then check if ID belongs to teacher
        if not person_type:
            cursor.execute("SELECT * FROM Teachers WHERE fingerprint_id = %s", (matched_id,))
            teacher = cursor.fetchone()
            if teacher:
                person_type = PERSON_TYPE_TEACHER
                person_id = teacher["id"]
                display_name = teacher['name']
                if len(display_name) > LCD_LINE_LENGTH - len("Teacher: "):
                    display_name = display_name[:LCD_LINE_LENGTH - len("Teacher: ") - 3] + "..."
                logger.info("Teacher: %s", teacher['name'])
                if lcd:
                    lcd.text(f"Teacher: {display_name}", 1)

        if person_type and person_id:
            cache_key = (person_type, person_id)
            now = datetime.now()

            # Check if within 5 AM to 10 PM window
            if not (5 <= now.hour < 22):
                logger.info(f"Scan for {cache_key} outside 5 AM - 10 PM window. Not logging.")
                if lcd:
                    lcd.text("Out of hours", 1)
                return

            if cache_key in _first_scan_cache:
                # Second scan detected
                _first_scan_cache.pop(cache_key) # Remove from cache
                log_fingerprint(person_type, person_id)
                if lcd:
                    lcd.text("Logged!", 1)
            else:
                # First scan detected
                _first_scan_cache[cache_key] = now
                logger.info(f"First scan for {cache_key} recorded. Waiting for second scan.")
                if lcd:
                    lcd.text("Scan again!", 1)
        else:
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
        _clear_old_scans() # Clear old scans periodically
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
