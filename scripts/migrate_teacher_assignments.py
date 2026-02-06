"""
Migration script to add TeacherSubjectAssignments table.
Run this script to update existing databases with the new table.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mysql.connector
from dotenv import load_dotenv

load_dotenv()

def migrate():
    """Add TeacherSubjectAssignments table to the database."""
    conn = None
    try:
        conn = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', ''),
            database=os.getenv('DB_NAME', 'fingerprint_db'),
            port=int(os.getenv('DB_PORT', 3306))
        )
        cursor = conn.cursor()
        
        # Create TeacherSubjectAssignments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS `TeacherSubjectAssignments` (
                id INT UNSIGNED NOT NULL AUTO_INCREMENT,
                teacher_id INT UNSIGNED NOT NULL,
                subject_id INT UNSIGNED NOT NULL,
                class VARCHAR(64) NOT NULL,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (id),
                FOREIGN KEY (teacher_id) REFERENCES `Teachers`(id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES `Subjects`(id) ON DELETE CASCADE,
                UNIQUE KEY uniq_teacher_subject_class (teacher_id, subject_id, class)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        
        conn.commit()
        print("✓ TeacherSubjectAssignments table created successfully!")
        
    except mysql.connector.Error as e:
        print(f"✗ MySQL Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    migrate()
