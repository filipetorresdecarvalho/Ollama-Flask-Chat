import os
import sys
import json
import importlib
from datetime import datetime

# --- Configuration ---
LOGS_DIR = 'logs'
REQUIRED_MODULES = ['flask', 'werkzeug', 'ollama', 'pypdf']
RESULTS = {
    "report_generated_at": datetime.now().isoformat(),
    "python_version": sys.version,
    "platform": sys.platform,
    "dependencies": {},
    "app_import_test": {}
}

def check_dependencies():
    """Checks if required Python libraries are installed."""
    print("--- 1. Checking Dependencies ---")
    for module_name in REQUIRED_MODULES:
        try:
            importlib.import_module(module_name)
            status = "OK"
        except ImportError:
            status = f"MISSING! Please run: pip install {module_name}"
        RESULTS["dependencies"][module_name] = status
        print(f"Module '{module_name}': {status}")
    print("... Done\n")

def test_app_import():
    """Tries to import the main app.py to catch SyntaxErrors."""
    print("--- 2. Testing app.py for Syntax/Import Errors ---")
    try:
        # This is the crucial step. If app.py has a syntax error, this will fail.
        import app
        status = "OK"
        message = "app.py was imported successfully (no syntax errors found)."
        RESULTS["app_import_test"] = {"status": status, "message": message}
        print(f"Status: {status}\n{message}")
        return True # Return True on success to run next checks
    except Exception as e:
        status = "FAILED"
        # format_exc() gives the full traceback, including file and line number
        import traceback
        error_details = traceback.format_exc()
        message = f"Failed to import app.py. The application cannot start. Error:\n{error_details}"
        RESULTS["app_import_test"] = {"status": status, "message": message}
        print(f"Status: {status}\n{message}")
        return False # Return False on failure
    finally:
        print("... Done\n")

def run_file_and_schema_checks():
    """Runs the checks from our original fix.py script."""
    print("--- 3. Running File Structure & Schema Checks ---")
    try:
        # We can import and run the main function from fix.py
        import fix
        # Create a placeholder for its results
        fix_results = {}
        fix.check_structure(fix_results)
        fix.check_schemas(fix_results)
        RESULTS["project_health_check"] = fix_results
        print("... File and schema checks completed.")
    except Exception as e:
        RESULTS["project_health_check"] = {"status": "FAILED", "error": str(e)}
        print(f"Could not run the checks from fix.py. Error: {e}")
    finally:
        print("... Done\n")


def main():
    """Runs all diagnostics and saves the report."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    
    check_dependencies()
    
    # Only run the detailed file checks if the app itself is valid
    if test_app_import():
        run_file_and_schema_checks()

    # Generate JSON report
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    report_filename = os.path.join(LOGS_DIR, f"debug_report_{timestamp}.json")
    
    with open(report_filename, 'w') as f:
        json.dump(RESULTS, f, indent=4)
        
    print(f"--- All checks complete. Debug report saved to '{report_filename}' ---")

if __name__ == "__main__":
    main()