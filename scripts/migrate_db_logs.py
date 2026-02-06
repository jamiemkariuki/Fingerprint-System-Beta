import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mysql.connector
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', 'fpsnsdb')

def migrate_db():
    print(f"Connecting to MySQL database '{DB_NAME}'...")
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("SHOW COLUMNS FROM FingerprintLogs LIKE 'log_type'")
        result = cursor.fetchone()
        
        if not result:
            print("Adding 'log_type' column to FingerprintLogs table...")
            sql = "ALTER TABLE FingerprintLogs ADD COLUMN log_type ENUM('IN', 'OUT') NOT NULL DEFAULT 'IN'"
            cursor.execute(sql)
            conn.commit()
            print("Column added successfully.")
        else:
            print("'log_type' column already exists.")
            
        conn.close()
        
    except mysql.connector.Error as e:
        print(f"MySQL Error: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    migrate_db()
