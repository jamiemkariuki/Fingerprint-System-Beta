import os
import logging
from dotenv import load_dotenv
import serial
import time
import mysql.connector
from mysql.connector import pooling
try:
    from adafruit_fingerprint import Adafruit_Fingerprint
except Exception:
    Adafruit_Fingerprint = None  # type: ignore
try:
    from rpi_lcd import LCD
except Exception:
    LCD = None  # type: ignore

load_dotenv()

# --- Logging ---
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO),
                    format="%(asctime)s %(levelname)s %(name)s - %(message)s")
logger = logging.getLogger("fingerprint_listener")

# --- LCD Setup ---
class _NoopLCD:
    def text(self, msg, *_args):
        logger.info("LCD: %s", msg)

lcd = _NoopLCD() if LCD is None else LCD()

# --- Fingerprint Sensor Setup ---
finger = None
try:
    uart = serial.Serial("/dev/serial0", baudrate=57600, timeout=1)
    if Adafruit_Fingerprint:
        finger = Adafruit_Fingerprint(uart)
    else:
        logger.warning("Adafruit_Fingerprint not available; sensor disabled")
except Exception as e:
    logger.warning("Fingerprint sensor init failed: %s", e)

# --- MySQL Config ---
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'fingerprint_user'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'FingerprintDB'),
    'port': int(os.getenv('DB_PORT', '3306')),
}

try:
    db_pool = pooling.MySQLConnectionPool(pool_name="fp_pool_listener", pool_size=int(os.getenv("DB_POOL_SIZE", "5")), **DB_CONFIG)
except Exception as e:
    logger.warning("DB pool init failed, falling back to direct connections: %s", e)
    db_pool = None

def connect_db():
    if db_pool:
        return db_pool.get_connection()
    return mysql.connector.connect(**DB_CONFIG)

def log_fingerprint(person_type, person_id):
    """Insert a scan log into FingerprintLogs table."""
    try:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO FingerprintLogs (person_type, person_id) VALUES (%s, %s)",
            (person_type, person_id)
        )
        conn.commit()
        conn.close()
        print(f"[LOG] {person_type} ID {person_id} logged successfully")
    except mysql.connector.Error as e:
        print("[DB ERROR]", e)

def match_fingerprint():
    """Wait for a finger, search for a match, and log it."""
    logger.info("Waiting for finger...")
    lcd.text("Waiting for scan", 1)

    # Wait until finger is detected
    while finger.get_image() != 0:
        time.sleep(0.1)

    if finger.image_2_tz(1) != 0:
        logger.warning("Failed to convert image")
        return

    if finger.finger_search() != 0:
        logger.info("No match found")
        lcd.text("No match!", 1)
        return

    # Match found
    matched_id = finger.finger_id
    confidence = finger.confidence
    logger.info("Match found! ID=%s, Confidence=%s", matched_id, confidence)
    lcd.text(f"Matched ID:{matched_id}", 1)

    # Look up in database
    try:
        conn = connect_db()
        cursor = conn.cursor(dictionary=True)

        # First check if ID belongs to student
        cursor.execute("SELECT * FROM Users WHERE fingerprint_id = %s", (matched_id,))
        user = cursor.fetchone()
        if user:
            logger.info("Student: %s (Class %s)", user['name'], user['class'])
            lcd.text(f"Student: {user['name']}", 1)
            log_fingerprint("student", user["id"])
            conn.close()
            return

        # Then check if ID belongs to teacher
        cursor.execute("SELECT * FROM Teachers WHERE fingerprint_id = %s", (matched_id,))
        teacher = cursor.fetchone()
        if teacher:
            logger.info("Teacher: %s", teacher['name'])
            lcd.text(f"Teacher: {teacher['name']}", 1)
            log_fingerprint("teacher", teacher["id"])
            conn.close()
            return

        conn.close()
        logger.warning("Match not found in DB (orphan ID)")
        lcd.text("Unknown ID", 1)

    except mysql.connector.Error as e:
        logger.exception("DB error during match lookup: %s", e)

# --- Main Loop ---
if __name__ == "__main__":
    logger.info("Fingerprint listener started. Waiting for scans...")
    lcd.text("Listener Ready", 1)
    while True:
        try:
            match_fingerprint()
            time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Exiting listener...")
            lcd.text("Listener Stopped", 1)
            break
        except Exception as e:
            logger.exception("Unhandled error in listener loop: %s", e)
            time.sleep(2)
