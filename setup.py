import os
import sqlite3
import zipfile
import getpass
import json
import secrets
import uuid
import subprocess
from datetime import datetime
from werkzeug.security import generate_password_hash

# --- Configuration ---
BACKUP_DIR = 'backup'
DB_DIR = 'database'
LOGS_DIR = 'logs'
CONFIG_FILE = 'config.json'
MODELS_FILE = 'models.json'
USER_DB_PATH = os.path.join(DB_DIR, 'users.db')
USER_SCHEMA_PATH = os.path.join(DB_DIR, 'schema_login.sql')
FILE_EXTENSIONS_TO_BACKUP = ('.py', '.html', '.css', '.js', '.sql', '.db', '.json')

def gather_files_to_backup():
    """Walks through the project and collects all files that should be backed up."""
    print("1. Gathering files for backup...")
    file_paths = []
    for root, dirs, files in os.walk('.'):
        if BACKUP_DIR in dirs:
            dirs.remove(BACKUP_DIR)
        for file in files:
            if file.endswith(FILE_EXTENSIONS_TO_BACKUP):
                file_path = os.path.join(root, file)
                file_paths.append(file_path)
    print(f"   Found {len(file_paths)} files to back up.")
    return file_paths

def create_zip_archive(file_list):
    """Creates a timestamped zip archive of the provided files."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    zip_filename = f'backup_{timestamp}.zip'
    zip_filepath = os.path.join(BACKUP_DIR, zip_filename)
    print(f"\n2. Creating archive: '{zip_filepath}'...")
    try:
        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in file_list:
                zipf.write(file, arcname=file)
        print("   Archive created successfully.")
        return zip_filepath
    except Exception as e:
        print(f"   ERROR: Failed to create zip file. {e}")
        return None

def verify_zip_archive(zip_filepath):
    """Performs an integrity check on the zip file to verify checksums."""
    print(f"\n3. Verifying archive integrity...")
    try:
        with zipfile.ZipFile(zip_filepath, 'r') as zipf:
            bad_file = zipf.testzip()
            if bad_file is None:
                print("   Checksum OK. Archive is valid.")
                return True
            else:
                print(f"   ERROR: Archive is corrupt. First bad file: {bad_file}")
                return False
    except Exception as e:
        print(f"   ERROR: Could not verify zip file. {e}")
        return False

def clear_all_databases_and_logs():
    """Deletes all .db and log files to ensure a clean slate."""
    print("\n4. Clearing old databases and logs...")
    # Also clear the root-level models.json
    if os.path.exists(MODELS_FILE):
        os.remove(MODELS_FILE)
        print(f"   - Deleted '{MODELS_FILE}'")

    for directory in [DB_DIR, LOGS_DIR]:
        if not os.path.isdir(directory): continue
        for item in os.listdir(directory):
            if item.endswith(('.db', '.json')):
                try:
                    full_path = os.path.join(directory, item)
                    if os.path.isfile(full_path):
                        os.remove(full_path)
                        print(f"   - Deleted '{full_path}'")
                except Exception as e:
                    print(f"   ERROR: Could not delete '{item}'. {e}")

def reset_config_and_create_admin():
    """Generates a config.json and creates the root admin."""
    print("\n5. Setting up initial configuration...")

    # Run get_models.py to create models.json
    try:
        print("   - Running get_models.py to detect Ollama models...")
        subprocess.run(['python', 'get_models.py'], check=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"   - ERROR: Failed to run get_models.py. {e}")
        return False

    # Read models from models.json
    available_models = []
    try:
        with open(MODELS_FILE, 'r') as f:
            available_models = json.load(f)
        print(f"   - Found {len(available_models)} models from {MODELS_FILE}.")
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"   - WARNING: {MODELS_FILE} could not be read. No models will be available.")

    # ** FIXED: Dynamically set the default model **
    default_model = ""
    if available_models:
        # Set the default model to the first one in the list
        default_model = available_models[0].get('name')
        print(f"   - Setting default model to: '{default_model}'")
    else:
        print("   - WARNING: No models found, default model will be empty.")
    
    new_secret_key = secrets.token_hex(32)
    admin_uuid = str(uuid.uuid4())
    default_config = {
        "flask_secret_key": new_secret_key,
        "root_admin_chat_db_uuid": admin_uuid,
        "ollama_config": {
            "default_model": default_model, # Use the dynamically found model
            "restricted_keywords": ["dolphin", "uncensored"],
        },
        "server_config": { "host": "192.168.3.2", "port": 5000, "debug": True, "threaded": True }
    }
    
    default_pass = "123@Root!"
    prompt = f"Enter password for 'root' admin (or press Enter for default: {default_pass}): "
    password = getpass.getpass(prompt) or default_pass
    if password == default_pass: print("Used default password.")
    hashed_password = generate_password_hash(password)

    try:
        os.makedirs(DB_DIR, exist_ok=True)
        conn = sqlite3.connect(USER_DB_PATH)
        cursor = conn.cursor()
        with open(USER_SCHEMA_PATH, 'r') as f:
            cursor.executescript(f.read())
        cursor.execute(
            "INSERT INTO users (id, username, password, email, chat_db_uuid, role) VALUES (?, ?, ?, ?, ?, ?)",
            (1, 'root', hashed_password, 'admin@local.host', admin_uuid, 'admin')
        )
        conn.commit()
        conn.close()
        print("   - Root admin 'root' created successfully in users.db.")
    except Exception as e:
        print(f"   ERROR: Failed to create root admin. {e}")
        return False
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(default_config, f, indent=4)
        print(f"   - Default '{CONFIG_FILE}' created successfully.")
    except Exception as e:
        print(f"   ERROR: Failed to create {CONFIG_FILE}. {e}")
        return False
        
    return True

# --- CORRECT MAIN FUNCTION ---
def main():
    """Main function to run the backup and cleanup process."""
    print("--- Starting Project Backup & Setup Script ---")
    
    files_to_backup = gather_files_to_backup()
    if not files_to_backup:
        print("No files found to back up. Exiting.")
        return

    archive_path = create_zip_archive(files_to_backup)
    if not archive_path or not verify_zip_archive(archive_path):
        print("\n--- Process Aborted! ---")
        print("Backup creation or verification failed. No files were deleted.")
        return

    clear_all_databases_and_logs()
    
    if reset_config_and_create_admin():
        print("\n--- Process Complete! ---")
        print("Project backed up and system has been reset with a new root admin.")
    else:
        print("\n--- Setup Failed! ---")

if __name__ == '__main__':
    main()