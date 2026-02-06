import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_NAME = os.getenv('DB_NAME', 'fpsnsdb')

def init_db():
    print(f"Connecting to MySQL at {DB_HOST} as {DB_USER}...")
    try:
        # Connect to MySQL server (no database selected)
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = conn.cursor()
        
        # Create Database
        print(f"Creating database '{DB_NAME}' if not exists...")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
        conn.close()
        
        # Connect to the specific database
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        cursor = conn.cursor()
        
        # Read and apply schema
        print("Applying schema.sql...")
        schema_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'schema.sql')
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
            
        # Split by statements
        statements = schema_sql.split(';')
        for stmt in statements:
            if stmt.strip():
                try:
                    cursor.execute(stmt)
                except Exception as e:
                    print(f"Error executing statement: {e}")
        
        conn.commit()
        print("Database initialized successfully!")
        
        # Check if Admin exists
        cursor.execute("SELECT * FROM Admins WHERE username='admin'")
        if not cursor.fetchone():
            print("Creating default admin...")
            import bcrypt
            pw_hash = bcrypt.hashpw('admin123'.encode(), bcrypt.gensalt()).decode()
            cursor.execute("INSERT INTO Admins (username, password_hash) VALUES (%s, %s)", ('admin', pw_hash))
            conn.commit()
            print("Default admin created: admin / admin123")
            
        conn.close()
        
    except mysql.connector.Error as e:
        print(f"MySQL Error: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    init_db()
