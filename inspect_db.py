"""
Print all SQLite tables and columns for the app's database (same file as db_path.py).

Run: python inspect_db.py
"""
import sqlite3

from db_path import DATABASE


def main():
    print("Database file:", DATABASE)
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )
    tables = [r[0] for r in cur.fetchall()]
    if not tables:
        print("(no user tables)")
        conn.close()
        return
    for t in tables:
        print(f"\n--- {t} ---")
        cur.execute(f'PRAGMA table_info("{t}")')
        for cid, name, ctype, notnull, dflt, pk in cur.fetchall():
            nn = " NOT NULL" if notnull else ""
            pkf = " PRIMARY KEY" if pk else ""
            d = f" DEFAULT {dflt}" if dflt is not None else ""
            print(f"  {name}: {ctype}{nn}{pkf}{d}")
    conn.close()


if __name__ == "__main__":
    main()
