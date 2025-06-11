import os
import re
import sqlite3
import uuid
import traceback
import json
import secrets
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from flask import (
    Flask, render_template, request, Response, jsonify,
    send_from_directory, session, redirect, url_for, g, flash
)
import ollama
import pypdf


# --- Configuration and Model Loading ---
def load_json_file(filename, error_msg):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"FATAL: {error_msg}. Please run setup.py or get_models.py.")
        exit()

CONFIG = load_json_file('config.json', 'config.json not found or is corrupt')
MODELS = load_json_file('models.json', 'models.json not found or is corrupt')

app = Flask(__name__)
app.secret_key = CONFIG.get('flask_secret_key')

# --- Path Configurations & App Config ---
DATABASE_DIR = 'database'
LOGS_DIR = 'logs'
USER_DB_PATH = os.path.join(DATABASE_DIR, 'users.db')
CHAT_DB_DIR = os.path.join(DATABASE_DIR, 'userchats')
LOGS_DB_PATH = os.path.join(DATABASE_DIR, 'logs.db')
SECURITY_DB_PATH = os.path.join(DATABASE_DIR, 'security.db')
ADMIN_DB_PATH = os.path.join(DATABASE_DIR, 'admin.db')
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_TEXT_EXTENSIONS = {'txt', 'md', 'py', 'csv', 'html', 'css', 'js'}
ALLOWED_PDF_EXTENSIONS = {'pdf'}
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# --- Database Connection Logic ---
def get_db(db_path, row_factory=False):
    db = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
    if row_factory: db.row_factory = sqlite3.Row
    return db
def get_user_db():
    if 'user_db' not in g: g.user_db = get_db(USER_DB_PATH, True)
    return g.user_db
def get_chat_db():
    if 'user_id' not in session: return None
    if 'chat_db' not in g:
        user_db = get_user_db()
        user = user_db.execute('SELECT chat_db_uuid FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if not user: raise ValueError("User not found.")
        path = os.path.join(CHAT_DB_DIR, f"{user['chat_db_uuid']}.db")
        if not os.path.exists(path):
            with app.app_context():
                init_db_on_startup(path, 'schema_chat.sql')
        g.chat_db = get_db(path, True)
    return g.chat_db
def get_logs_db():
    if 'logs_db' not in g: g.logs_db = get_db(LOGS_DB_PATH)
    return g.logs_db
def get_security_db():
    if 'security_db' not in g: g.security_db = get_db(SECURITY_DB_PATH)
    return g.security_db
def get_admin_db():
    if 'admin_db' not in g: g.admin_db = get_db(ADMIN_DB_PATH, True)
    return g.admin_db

@app.teardown_appcontext
def close_dbs(e=None):
    for attr in ['user_db', 'chat_db', 'logs_db', 'security_db', 'admin_db']:
        db = g.pop(attr, None)
        if db: db.close()

# --- Decorators & Error Handlers ---
def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if 'user_id' not in session: return redirect(url_for('login'))
        return view(**kwargs)
    return wrapped_view
def admin_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if session.get('role') != 'admin': return redirect(url_for('main_chat_redirect'))
        return view(**kwargs)
    return wrapped_view
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404
@app.errorhandler(500)
def internal_error(error):
    try:
        logs_db = get_logs_db()
        user_uuid = None
        if 'user_id' in session:
            user_db = get_user_db()
            if user_db:
                user_info = user_db.execute('SELECT chat_db_uuid FROM users WHERE id = ?', (session['user_id'],)).fetchone()
                if user_info: user_uuid = user_info['chat_db_uuid']
        error_trace = traceback.format_exc()
        if logs_db:
            logs_db.execute("INSERT INTO error_logs (user_uuid, request_method, request_url, ip_address, status_code, error_message) VALUES (?, ?, ?, ?, ?, ?)", (user_uuid, request.method, request.url, request.remote_addr, 500, error_trace))
            logs_db.commit()
    except Exception as e:
        print(f"CRITICAL: Failed to log error to database: {e}")
    return render_template('500.html', error_details=traceback.format_exc() if app.debug else None), 500

# --- Routes ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        try:
            db = get_user_db()
            db.execute(
                'INSERT INTO users (username, password, email, chat_db_uuid, role, phone, birthday, city, country) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (request.form['username'], generate_password_hash(request.form['password']), request.form['email'], str(uuid.uuid4()), 'user', request.form.get('phone'), request.form.get('birthday'), request.form.get('city'), request.form.get('country'))
            )
            db.commit()
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username or email already exists.', 'error')
            return redirect(url_for('signup'))
        except Exception:
            raise
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            db = get_user_db()
            user = db.execute('SELECT * FROM users WHERE username = ?', (request.form['username'],)).fetchone()
            if user and check_password_hash(user['password'], request.form['password']):
                session.clear()
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['role'] = user['role']
                session['selected_model'] = CONFIG.get('ollama_config', {}).get('default_model', '')
                
                security_db = get_security_db()
                security_db.execute("INSERT INTO login_history (user_uuid, ip_address, user_agent) VALUES (?, ?, ?)",(user['chat_db_uuid'], request.remote_addr, request.headers.get('User-Agent')))
                security_db.commit()
                return redirect(url_for('main_chat_redirect'))
            flash('Invalid username or password.', 'error')
            return redirect(url_for('login'))
        except Exception:
            raise
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/main')
@login_required
def main_chat_redirect():
    try:
        chat_db = get_chat_db()
        if not chat_db:
             flash("Could not connect to your chat history.", "error")
             return redirect(url_for('home'))
        last_convo = chat_db.execute('SELECT id FROM conversations ORDER BY created_at DESC LIMIT 1').fetchone()
        if last_convo:
            return redirect(url_for('main_chat', conversation_id=last_convo['id']))
        return redirect(url_for('new_chat'))
    except Exception:
        raise

@app.route('/chat/<conversation_id>')
@login_required
def main_chat(conversation_id):
    return render_template('main.html', conversation_id=conversation_id)

@app.route('/new_chat')
@login_required
def new_chat():
    try:
        chat_db = get_chat_db()
        new_convo_id = str(uuid.uuid4())
        chat_db.execute("INSERT INTO conversations (id, title) VALUES (?, ?)", (new_convo_id, "New Chat"))
        chat_db.commit()
        return redirect(url_for('main_chat', conversation_id=new_convo_id))
    except Exception:
        raise

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    try:
        user_db = get_user_db()
        user_data = user_db.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
        if request.method == 'POST':
            form_name = request.form.get('form_name')
            if form_name == 'update_info':
                user_db.execute("UPDATE users SET phone = ?, birthday = ?, city = ?, country = ? WHERE id = ?", (request.form.get('phone'), request.form.get('birthday'), request.form.get('city'), request.form.get('country'), session['user_id']))
                flash('Profile information updated successfully!', 'success')
            elif form_name == 'change_password':
                if not check_password_hash(user_data['password'], request.form['current_password']):
                    flash('Incorrect current password.', 'error')
                elif request.form['new_password'] != request.form['confirm_password']:
                    flash('New passwords do not match.', 'error')
                elif not re.fullmatch(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$', request.form['new_password']):
                    flash('Password does not meet complexity requirements.', 'error')
                else:
                    new_hashed_password = generate_password_hash(request.form['new_password'])
                    user_db.execute("UPDATE users SET password = ? WHERE id = ?", (new_hashed_password, session['user_id']))
                    flash('Password changed successfully!', 'success')
            user_db.commit()
            return redirect(url_for('profile'))
        return render_template('profile.html', user=user_data)
    except Exception:
        raise

@app.route('/admin')
@login_required
@admin_required
def admin_panel():
    try:
        user_db = get_user_db()
        all_users = user_db.execute("SELECT id, username, email, role FROM users ORDER BY id ASC").fetchall()
        return render_template('admin.html', users=all_users)
    except Exception:
        raise

@app.route('/admin/update_role', methods=['POST'])
@login_required
@admin_required
def update_user_role():
    try:
        user_id = request.form.get('user_id')
        new_role = request.form.get('new_role')
        if user_id and new_role in ['admin', 'user', 'restricted']:
            if int(user_id) == 1 and new_role != 'admin':
                flash("Cannot change the role of the primary admin (user ID 1).", 'error')
            else:
                db = get_user_db()
                db.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
                db.commit()
                flash(f"User {user_id}'s role updated to {new_role}.", 'success')
        return redirect(url_for('admin_panel'))
    except Exception:
        raise

@app.route('/settings')
@login_required
def settings():
    if session.get('role') == 'restricted':
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('main_chat_redirect'))
    return render_template('settings.html')

# --- API Routes ---
@app.route('/api/models')
@login_required
def get_models():
    try:
        user_role = session.get('role', 'user')
        if user_role == 'admin':
            allowed_models = MODELS
        else:
            restricted = CONFIG.get('ollama_config', {}).get('restricted_keywords', [])
            allowed_models = [m for m in MODELS if not any(k in m.get('name', '') for k in restricted)]
        
        return jsonify({
            "models": allowed_models,
            "default_model": session.get('selected_model')
        })
    except Exception:
        raise

@app.route('/api/load_model', methods=['POST'])
@login_required
def load_model():
    data = request.json
    model_name = data.get('model')
    if not model_name:
        return jsonify({'error': 'No model name provided'}), 400
    
    try:
        # *** FIXED: Use ollama.generate for a lightweight, non-hanging warm-up ***
        ollama.generate(model=model_name, prompt='.')
        session['selected_model'] = model_name
        return jsonify({'success': True, 'message': f'Model {model_name} is ready.'})
    except Exception as e:
        print(f"Error loading model {model_name}: {e}")
        return jsonify({'error': f'Failed to load model {model_name}.'}), 500


@app.route('/api/conversations', methods=['GET'])
@login_required
def get_conversations():
    try:
        chat_db = get_chat_db()
        convos = chat_db.execute('SELECT id, title FROM conversations ORDER BY created_at DESC').fetchall()
        return jsonify([dict(row) for row in convos])
    except Exception:
        raise

@app.route('/api/conversation/<conversation_id>', methods=['GET'])
@login_required
def get_conversation_messages(conversation_id):
    try:
        chat_db = get_chat_db()
        messages = chat_db.execute('SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC', (conversation_id,)).fetchall()
        return jsonify([dict(row) for row in messages])
    except Exception:
        raise

@app.route('/ask', methods=['POST'])
@login_required
def ask():
    try:
        data = request.json
        if not data: return Response("Error: Invalid request.", status=400)
        
        model = session.get('selected_model')
        user_message, conversation_id = data.get('message'), data.get('conversation_id')

        if not all([user_message, conversation_id, model]):
            error_details = f"Missing data: message={bool(user_message)}, convo_id={bool(conversation_id)}, model={bool(model)}"
            return Response(f"Error: Missing required data. Details: {error_details}", status=400)

        chat_db = get_chat_db()
        chat_db.execute("INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)", (conversation_id, 'user', user_message))
        chat_db.commit()

        history_rows = chat_db.execute("SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY timestamp ASC", (conversation_id,)).fetchall()
        conversation_history = [dict(row) for row in history_rows]
        
        stream = ollama.chat(model=model, messages=conversation_history, stream=True)
        
        ai_full_response = "".join(chunk['message']['content'] for chunk in stream)
        
        if ai_full_response:
            chat_db.execute("INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)", (conversation_id, 'assistant', ai_full_response))
            chat_db.commit()
            
        def generate():
            yield re.sub(r'(\d*\.?\s?)\*\*(.*?)\*\*', r'<h2>\1\2</h2>', ai_full_response)
            
        return Response(generate(), mimetype='text/html')
    except Exception:
        raise

# --- Initialization Function (for startup only) ---
def init_db_on_startup(db_path, schema_path_relative):
    schema_path = os.path.join(DATABASE_DIR, schema_path_relative)
    try:
        con = sqlite3.connect(db_path)
        with open(schema_path, 'r') as f:
            con.cursor().executescript(f.read())
        con.commit()
        con.close()
        print(f"Initialized database at {db_path} from {schema_path_relative}.")
    except Exception as e:
        print(f"Error initializing database {db_path}: {e}")

# --- Main Execution Block ---
if __name__ == '__main__':
    try:
        for path in [DATABASE_DIR, CHAT_DB_DIR, UPLOAD_FOLDER, LOGS_DIR]:
            os.makedirs(path, exist_ok=True)
        
        db_schemas = {
            USER_DB_PATH: 'schema_login.sql',
            LOGS_DB_PATH: 'schema_logs.sql',
            SECURITY_DB_PATH: 'schema_security.sql',
            ADMIN_DB_PATH: 'schema_admin.sql'
        }
        with app.app_context():
            for db_path, schema_file in db_schemas.items():
                if not os.path.exists(db_path):
                    init_db_on_startup(db_path, schema_file)
        
        server_cfg = CONFIG.get('server_config', {})
        app.run(
            host=server_cfg.get('host', '127.0.0.1'),
            port=server_cfg.get('port', 5000),
            debug=server_cfg.get('debug', True),
            threaded=server_cfg.get('threaded', True)
        )
    except Exception as e:
        print(f"FATAL: Failed to start application server. Error: {e}")