import logging
import serial
import time

try:
    from adafruit_fingerprint import Adafruit_Fingerprint
except ImportError:
    Adafruit_Fingerprint = None  # type: ignore

logger = logging.getLogger(__name__)

# Initialize fingerprint sensor
finger = None
try:
    uart = serial.Serial("/dev/serial0", baudrate=57600, timeout=1)
    if Adafruit_Fingerprint:
        finger = Adafruit_Fingerprint(uart)
        logger.info("Fingerprint sensor initialized successfully")
    else:
        logger.warning("Adafruit_Fingerprint library not available; sensor disabled")
except Exception as e:
    logger.warning("Fingerprint sensor initialization failed: %s", e)


def _wait_for_finger(lcd_obj, prompt="Place finger..."):
    """Wait until a finger is placed on the sensor."""
    if lcd_obj:
        lcd_obj.clear()
        lcd_obj.text(prompt, 1)
    # The loop waits while get_image() returns a non-zero value (no image/fail)
    while finger.get_image() != 0: 
        time.sleep(0.1)


def _image_to_template(lcd_obj, slot: int) -> bool:
    """Convert the scanned image to a template in the given slot."""
    if finger.image_2_tz(slot) != 0:
        if lcd_obj:
            lcd_obj.clear()
            lcd_obj.text(f"Scan fail {slot}", 1)
        logger.warning(f"Image to template failed at slot {slot}")
        return False
    return True


def _create_model(lcd_obj) -> bool:
    """Combine two templates to create a fingerprint model."""
    if finger.create_model() != 0:
        if lcd_obj:
            lcd_obj.clear()
            lcd_obj.text("No match!", 1)
        logger.warning("Model creation failed")
        return False
    return True


def _store_model(lcd_obj, fid: int):
    """Store the fingerprint model in a specified slot (fid)."""
    if finger.store_model(fid) == 0:
        if lcd_obj:
            lcd_obj.clear()
            lcd_obj.text(f"Saved ID:{fid}", 1)
        return fid
    
    # Store failed
    if lcd_obj:
        lcd_obj.clear()
        lcd_obj.text("Store failed", 1)
    logger.warning(f"Failed to store model at ID {fid}")
    return None


# --- FIXED ENROLLMENT FUNCTION ---
def enroll_fingerprint(db_id: int): 
    """Enroll a new fingerprint using a specific, pre-assigned ID (db_id)."""
    from main.hardware.lcd import lcd

    if not finger:
        logger.error("Fingerprint sensor unavailable")
        if lcd:
            lcd.clear()
            lcd.text("Sensor Error", 1)
        return None

    # 1. Validate the provided DB ID
    if db_id is None or db_id <= 0:
        if lcd:
            lcd.clear()
            lcd.text("Invalid ID", 1)
        logger.error("Invalid database ID provided for enrollment.")
        return None

    # STEP 1 — First scan
    _wait_for_finger(lcd, "Scan finger...")
    if not _image_to_template(lcd, 1):
        return None

    if lcd:
        lcd.clear()
        lcd.text("Remove finger", 1)
    time.sleep(2)

    # STEP 2 — Second scan
    _wait_for_finger(lcd, "Scan again...")
    if not _image_to_template(lcd, 2):
        return None

    # STEP 3 — Create model
    if not _create_model(lcd):
        return None

    # STEP 4 — Store model using the provided db_id
    # This ensures the Sensor ID matches the DB ID.
    stored_id = _store_model(lcd, db_id) 
    
    if stored_id is None:
        return None

    # Success
    logger.info(f"Fingerprint enrolled successfully → ID {stored_id}")
    return stored_id