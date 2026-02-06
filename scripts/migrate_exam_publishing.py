import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mysql.connector
from dotenv import load_dotenv

load_dotenv()

def migrate():
    print("Migrating database... Adding PublishedExams table.")
    conn = None
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "fpsnsdb"),
            port=int(os.getenv("DB_PORT", 3306))
        )
        cursor = conn.cursor()

        # Create PublishedExams Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS `PublishedExams` (
          `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
          `term` VARCHAR(20) NOT NULL,
          `exam_type` VARCHAR(50) NOT NULL,
          `is_published` BOOLEAN DEFAULT FALSE,
          `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          UNIQUE KEY `unique_exam_publish` (`term`, `exam_type`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        print("PublishedExams table created/verified.")
        
    except mysql.connector.Error as e:
        print(f"Error migrating: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    migrate()
