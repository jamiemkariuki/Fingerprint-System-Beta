import logging
try:
    from rpi_lcd import LCD
except Exception:
    LCD = None  # type: ignore

logger = logging.getLogger(__name__)

class _NoopLcd:
    def clear(self):
        logger.debug("LCD clear (noop)")

    def text(self, message, line):
        logger.info("LCD[%d]: %s", line, message)

lcd = _NoopLcd()

if LCD:
    try:
        lcd = LCD()  # Initialize with default address 0x27
    except Exception as e:
        logger.warning("LCD init failed, using noop: %s", e)
