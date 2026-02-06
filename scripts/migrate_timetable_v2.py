import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mysql.connector
from dotenv import load_dotenv

load_dotenv()

def migrate():
    print("Migrating database... Adding teacher_id to Timetable.")
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

        # Check if teacher_id already exists to avoid errors on re-run
        cursor.execute("SHOW COLUMNS FROM Timetable LIKE 'teacher_id'")
        if not cursor.fetchone():
            print("Adding teacher_id column...")
            cursor.execute("""
                ALTER TABLE `Timetable` 
                ADD COLUMN teacher_id INT UNSIGNED AFTER subject_id
            """)
            print("Adding foreign key constraint...")
            cursor.execute("""
                ALTER TABLE `Timetable` 
                ADD CONSTRAINT fk_timetable_teacher 
                FOREIGN KEY (teacher_id) REFERENCES `Teachers`(id) ON DELETE SET NULL
            """)
            print("Timetable table migrated successfully.")
        else:
            print("teacher_id column already exists in Timetable.")

        conn.commit()
    except mysql.connector.Error as e:
        print(f"Error migrating: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    migrate()
