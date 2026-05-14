"""
Initialize the SQLite database from database.sql (stdlib sqlite3 only; no MySQL).
"""
import os
import sqlite3

from db_path import DATABASE


def main():
    conn = sqlite3.connect(DATABASE)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        with open(os.path.join(os.path.dirname(__file__), "database.sql"), "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.commit()
        print(f"Database initialized at {os.path.abspath(DATABASE)}")
    except sqlite3.Error as err:
        print(f"SQLite error: {err}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
