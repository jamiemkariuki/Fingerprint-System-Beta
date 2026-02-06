import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mysql.connector
from dotenv import load_dotenv

load_dotenv()

def migrate():
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "fpsnsdb")
        )
        cursor = conn.cursor()

        print("Creating ExamResults table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS `ExamResults` (
              `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
              `student_id` INT UNSIGNED NOT NULL,
              `subject_id` INT UNSIGNED NOT NULL,
              `teacher_id` INT UNSIGNED,
              `exam_type` VARCHAR(50) NOT NULL,
              `term` VARCHAR(20) NOT NULL,
              `score` DECIMAL(5,2) NOT NULL,
              `max_score` DECIMAL(5,2) DEFAULT 100.00,
              `grade` VARCHAR(5) DEFAULT NULL,
              `remarks` TEXT,
              `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
              FOREIGN KEY (`student_id`) REFERENCES `Users`(`id`) ON DELETE CASCADE,
              FOREIGN KEY (`subject_id`) REFERENCES `Subjects`(`id`) ON DELETE CASCADE,
              FOREIGN KEY (`teacher_id`) REFERENCES `Teachers`(`id`) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        
        conn.commit()
        print("✓ ExamResults table created successfully!")

    except mysql.connector.Error as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    migrate()
