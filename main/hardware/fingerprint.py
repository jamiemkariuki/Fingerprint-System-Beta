import logging
import serial
import time
try:
    from adafruit_fingerprint import Adafruit_Fingerprint
except Exception:
    Adafruit_Fingerprint = None  # type: ignore

logger = logging.getLogger(__name__)

finger = None
try:
    uart = serial.Serial("/dev/serial0", baudrate=57600, timeout=1)
    if Adafruit_Fingerprint:
        finger = Adafruit_Fingerprint(uart)
    else:
        logger.warning("Adafruit_Fingerprint not available; sensor disabled")
except Exception as e:
    logger.warning("Fingerprint sensor init failed: %s", e)

def _get_image(lcd_obj):
    if lcd_obj:
        lcd_obj.clear()
        lcd_obj.text("Place finger...", 1)
    while finger.get_image() != 0:
        pass

def _image_to_template(lcd_obj, slot):
    if finger.image_2_tz(slot) != 0:
        if lcd_obj:
            lcd_obj.clear()
            lcd_obj.text(f"Scan fail (slot {slot})", 1)
        return False
    return True

def _create_model(lcd_obj):
    if finger.create_model() != 0:
        if lcd_obj:
            lcd_obj.clear()
            lcd_obj.text("No match!", 1)
        return False
    return True

def _store_model(lcd_obj, fid):
    if finger.store_model(fid) == 0:
        if lcd_obj:
            lcd_obj.clear()
            lcd_obj.text(f"Saved ID:{fid}", 1)
        return fid
    return None

def enroll_fingerprint():
    from main.hardware.lcd import lcd

    if not finger:
        logger.error("Fingerprint sensor unavailable")
        if lcd:
            lcd.clear()
            lcd.text("Sensor Error", 1)
        return None

    _get_image(lcd)
    if not _image_to_template(lcd, 1):
        return None

    if lcd:
        lcd.clear()
        lcd.text("Remove finger", 1)
    time.sleep(2)

    _get_image(lcd)
    if not _image_to_template(lcd, 2):
        return None

    if not _create_model(lcd):
        return None

    for fid in range(1, 127):
        if finger.load_model(fid) != 0:
            stored_fid = _store_model(lcd, fid)
            if stored_fid is not None:
                return stored_fid

    if lcd:
        lcd.clear()
        lcd.text("No space!", 1)
    return None