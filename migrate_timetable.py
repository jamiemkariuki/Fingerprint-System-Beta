import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

def migrate():
    print("Migrating database... Adding Timetable table.")
    conn = None
    try:
        conn = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "fpsnsdb")
        )
        cursor = conn.cursor()

        # Create Timetable Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS `Timetable` (
          id INT UNSIGNED NOT NULL AUTO_INCREMENT,
          class VARCHAR(64) NOT NULL,
          subject_id INT UNSIGNED NOT NULL,
          day_of_week VARCHAR(20) NOT NULL,
          start_time TIME NOT NULL,
          end_time TIME NOT NULL,
          created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (id),
          FOREIGN KEY (subject_id) REFERENCES `Subjects`(id) ON DELETE CASCADE,
          KEY idx_timetable_class (class)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """)
        
        print("Timetable table created/verified.")
        conn.commit()
        
    except mysql.connector.Error as e:
        print(f"Error migrating: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    migrate()
