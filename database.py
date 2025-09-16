import os
import mysql.connector
from mysql.connector import pooling
import logging

logger = logging.getLogger(__name__)

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'fingerprint_user'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'FingerprintDB'),
    'port': int(os.getenv('DB_PORT', '3306')),
}

db_pool = None
try:
    db_pool = pooling.MySQLConnectionPool(pool_name="fp_pool", pool_size=int(os.getenv("DB_POOL_SIZE", "5")), **DB_CONFIG)
except mysql.connector.Error as e:
    logger.error("DB pool init failed: %s", e)

def get_db():
    try:
        if db_pool:
            return db_pool.get_connection()
        else:
            # Fallback to direct connection if pool failed to initialize
            conn = mysql.connector.connect(**DB_CONFIG)
            logger.warning("Using direct DB connection (pool not available).")
            return conn
    except mysql.connector.Error as e:
        logger.exception("Failed to get database connection: %s", e)
        raise # Re-raise the exception after logging