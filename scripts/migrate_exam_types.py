import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mysql.connector
from dotenv import load_dotenv

load_dotenv()

def migrate():
    print("Migrating database... Adding ExamTypes table.")
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

        # Create ExamTypes Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS `ExamTypes` (
          `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
          `name` VARCHAR(50) NOT NULL UNIQUE,
          `is_active` BOOLEAN DEFAULT TRUE,
          `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        print("ExamTypes table created/verified.")

        # Seed initial data if empty
        cursor.execute("SELECT COUNT(*) FROM ExamTypes")
        count = cursor.fetchone()[0]
        
        if count == 0:
            print("Seeding initial exam types...")
            initial_types = ['Mid Term', 'End of Term', 'Mock', 'Final']
            for et in initial_types:
                try:
                    cursor.execute("INSERT INTO ExamTypes (name) VALUES (%s)", (et,))
                    print(f" - Added: {et}")
                except mysql.connector.Error as err:
                    print(f" - Error adding {et}: {err}")
            conn.commit()
            print("Seeding complete.")
        else:
            print("ExamTypes table already has data. Skipping seed.")
        
    except mysql.connector.Error as e:
        print(f"Error migrating: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    migrate()
