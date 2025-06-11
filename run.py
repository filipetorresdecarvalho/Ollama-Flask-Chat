from waitress import serve
from app import app  # Imports the 'app' object from your app.py file

if __name__ == '__main__':
    print("Starting production server with Waitress...")
    # Use '0.0.0.0' to listen on all available network interfaces
    serve(app, host='0.0.0.0', port=8080)