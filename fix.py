import os
import sqlite3
import json
from datetime import datetime

# --- Configuration ---
LOGS_DIR = 'logs'
DATABASE_DIR = 'database'
ADMIN_DB_PATH = os.path.join(DATABASE_DIR, 'admin.db')
# ... (Full, correct code as provided in the previous step)

EXPECTED_DIRS = [DATABASE_DIR, "database/userchats", "static", "templates", "uploads", LOGS_DIR]
EXPECTED_FILES = [
    "app.py",
    os.path.join(DATABASE_DIR, "schema_login.sql"),
    os.path.join(DATABASE_DIR, "schema_chat.sql"),
    os.path.join(DATABASE_DIR, "schema_logs.sql"),
    os.path.join(DATABASE_DIR, "schema_security.sql"),
    os.path.join(DATABASE_DIR, "schema_admin.sql"),
    os.path.join("static", "style.css"),
    os.path.join("static", "main.js"),
    os.path.join("static", "ui.js"),
    os.path.join("templates", "base.html"),
    os.path.join("templates", "profile.html"),
    os.path.join("templates", "admin.html"),
]
EXPECTED_SCHEMAS = {
    "users.db": { "users": { "id": ("INTEGER", 1), "role": ("TEXT", 1) } },
    "logs.db": { "error_logs": { "id": ("INTEGER", 1), "error_message": ("TEXT", 1) } },
    "security.db": { "login_history": { "id": ("INTEGER", 1), "user_uuid": ("TEXT", 1) } }
}

# --- Functions ---
def get_db_connection(db_path):
    try: return sqlite3.connect(db_path)
    except Exception as e: return f"ERROR: {e}"

def check_structure(results):
    print("--- 1. Checking Project Structure ---")
    results["structure"] = {"directories": [], "files": []}
    for dir_path in EXPECTED_DIRS:
        status = "OK" if os.path.isdir(dir_path) else "MISSING"
        results["structure"]["directories"].append({"path": dir_path, "status": status})
    for file_path in EXPECTED_FILES:
        status = "OK" if os.path.isfile(file_path) else "MISSING"
        results["structure"]["files"].append({"path": file_path, "status": status})

def check_schemas(results):
    print("--- 2. Checking Database Schemas ---")
    results["schemas"] = []
    for db_file, tables in EXPECTED_SCHEMAS.items():
        db_path = os.path.join(DATABASE_DIR, db_file)
        report = {"database": db_file, "status": "OK", "tables": {}}
        if not os.path.exists(db_path):
            report["status"] = "NOT FOUND"
            results["schemas"].append(report)
            continue
        conn = get_db_connection(db_path)
        if isinstance(conn, str):
            report["status"] = conn
            results["schemas"].append(report)
            continue
        cursor = conn.cursor()
        for table_name, expected_cols in tables.items():
            try:
                cursor.execute(f"PRAGMA table_info({table_name})")
                actual_cols = {row[1]: (row[2], row[3]) for row in cursor.fetchall()}
                for col, (col_type, notnull) in expected_cols.item():
                    if col not in actual_cols or actual_cols[col][0] != col_type or actual_cols[col][1] != notnull:
                         report["tables"].setdefault(table_name, []).append(f"Column '{col}' MISMATCH")
            except: report["tables"].setdefault(table_name, []).append("MISSING or FAILED to read")
        if report["tables"]: report["status"] = "ERROR"
        results["schemas"].append(report)
        conn.close()

def save_report_to_db(report):
    print("--- 3. Saving Report to Admin DB ---")
    conn = get_db_connection(ADMIN_DB_PATH)
    if isinstance(conn, str):
        print(f"Could not connect to admin.db to save report: {conn}")
        return
    try:
        with open(os.path.join(DATABASE_DIR, 'schema_admin.sql'), 'r') as f:
            conn.cursor().executescript(f.read())
        conn.execute(
            "INSERT INTO FIX_REPORTS (timestamp, report_json) VALUES (?, ?)",
            (report["report_generated_at"], json.dumps(report))
        )
        conn.commit()
        print("Successfully saved report to admin.db.")
    except Exception as e:
        print(f"Error saving report to admin.db: {e}")
    finally:
        conn.close()

def main():
    results = {"report_generated_at": datetime.now().isoformat()}
    check_structure(results); check_schemas(results)
    os.makedirs(LOGS_DIR, exist_ok=True)
    report_filename = os.path.join(LOGS_DIR, f"fix-report_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json")
    with open(report_filename, 'w') as f:
        json.dump(results, f, indent=4)
    print(f"\nJSON report saved to '{report_filename}'")
    save_report_to_db(results)

if __name__ == "__main__":
    main()