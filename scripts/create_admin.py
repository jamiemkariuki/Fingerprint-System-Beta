#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import getpass
import bcrypt
try:
    from src.main.database import get_db
except Exception as e:
    raise SystemExit("Cannot import get_db from the new src.main layout. Please ensure the new structure exists.") from e


def main():
    print("Admin creation via terminal (CLI)")
    username = input("Username: ").strip()
    if not username:
        print("Error: Username is required.")
        sys.exit(1)

    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM Admins WHERE username = %s", (username,))
        if cursor.fetchone():
            print(f"Admin '{username}' already exists.")
            sys.exit(1)

        while True:
            pw = getpass.getpass("Password: ")
            pw2 = getpass.getpass("Confirm password: ")
            if pw != pw2:
                print("Passwords do not match. Try again.")
                continue
            if len(pw) < 8:
                print("Password must be at least 8 characters.")
                continue
            break

        hashed = bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
        cursor.execute("INSERT INTO Admins (username, password_hash) VALUES (%s, %s)", (username, hashed))
        conn.commit()
        print(f"Admin '{username}' created successfully.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    main()
