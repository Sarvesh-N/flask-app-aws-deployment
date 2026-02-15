from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import re
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'super_secret_key'  # Change for production

# Database Configuration
db_config = {
    'host': 'flaskapp-db.c5ko68gmyjyf.ap-south-1.rds.amazonaws.com',
    'user': 'admin',
    'password': 'sarvs7899',
    'database': 'event_management'
}

def get_db_connection():
    try:
        conn = mysql.connector.connect(**db_config)
        return conn
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None

# Use this to initialize DB if empty
def init_db():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        with open('schema.sql', 'r') as f:
            commands = f.read().split(';')
            for command in commands:
                if command.strip():
                    try:
                        cursor.execute(command)
                    except mysql.connector.Error as err:
                        print(f"Schema Error: {err}")
        conn.commit()
        
        # Check if admin exists, create if not
        cursor.execute("SELECT * FROM users WHERE username = 'admin'")
        if not cursor.fetchone():
            hashed_password = generate_password_hash('admin123')
            cursor.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, 'admin')", ('admin', hashed_password))
            conn.commit()
            print("Admin user created (admin/admin123)")
            
        cursor.close()
        conn.close()

# Routes
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if user and check_password_hash(user['password'], password):
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        return jsonify({'success': True, 'role': user['role']})
    
    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'user') # Default user
    
    conn = get_db_connection()
    if not conn: return jsonify({'success': False}), 500
    
    cursor = conn.cursor()
    hashed_password = generate_password_hash(password)
    try:
        cursor.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", (username, hashed_password, role))
        conn.commit()
        success = True
    except mysql.connector.Error:
        success = False
    finally:
        cursor.close()
        conn.close()
        
    if success:
        return jsonify({'success': True, 'message': 'User registered'})
    return jsonify({'success': False, 'message': 'Username already exists'}), 400

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('home'))
    return render_template('dashboard.html', username=session['username'], role=session['role'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# API Routes for Events
@app.route('/api/events', methods=['GET', 'POST'])
def handle_events():
    conn = get_db_connection()
    if not conn: return jsonify({'error': 'DB Error'}), 500
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'GET':
        cursor.execute("SELECT * FROM events")
        events = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(events)
    
    if request.method == 'POST':
        if session.get('role') != 'admin':
            return jsonify({'error': 'Unauthorized'}), 403
            
        data = request.json
        try:
            cursor.execute("INSERT INTO events (title, description, date, location) VALUES (%s, %s, %s, %s)", 
                           (data['title'], data['description'], data['date'], data['location']))
            conn.commit()
            return jsonify({'success': True, 'message': 'Event created'})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 400
        finally:
            cursor.close()
            conn.close()

@app.route('/api/events/<int:event_id>', methods=['PUT', 'DELETE'])
def manage_event(event_id):
    if session.get('role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == 'DELETE':
        cursor.execute("DELETE FROM events WHERE id = %s", (event_id,))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True, 'message': 'Event deleted'})
        
    if request.method == 'PUT':
        data = request.json
        # Only update fields provided
        updates = []
        params = []
        for key in ['title', 'description', 'date', 'location']:
            if key in data:
                updates.append(f"{key} = %s")
                params.append(data[key])
        params.append(event_id)
        
        sql = f"UPDATE events SET {', '.join(updates)} WHERE id = %s"
        cursor.execute(sql, tuple(params))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'success': True})

@app.route('/api/registrations', methods=['POST', 'GET'])
def registrations():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        user_id = session.get('user_id')
        data = request.json
        event_id = data.get('event_id')
        
        # Admin can register others via agent
        if 'target_user' in data and session.get('role') == 'admin':
             cursor.execute("SELECT id FROM users WHERE username = %s", (data['target_user'],))
             target = cursor.fetchone()
             if target: user_id = target['id']
             
        try:
            cursor.execute("INSERT INTO registrations (user_id, event_id) VALUES (%s, %s)", (user_id, event_id))
            conn.commit()
            return jsonify({'success': True, 'message': 'Registered successfully'})
        except mysql.connector.Error as err:
            return jsonify({'success': False, 'message': 'Already registered or error'}), 400
        finally:
            cursor.close()
            conn.close()

    if request.method == 'GET':
        if session.get('role') == 'admin':
             cursor.execute("""
                SELECT r.id, u.username, e.title 
                FROM registrations r 
                JOIN users u ON r.user_id = u.id 
                JOIN events e ON r.event_id = e.id
            """)
        else:
             cursor.execute("""
                SELECT r.id, e.title, e.date, e.location 
                FROM registrations r 
                JOIN events e ON r.event_id = e.id 
                WHERE r.user_id = %s
            """, (session.get('user_id'),))
             
        regs = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify(regs)

# AI Agent Implementation
@app.route('/api/agent', methods=['POST'])
def agent_command():
    if 'user_id' not in session:
        return jsonify({'response': 'Please login to use the agent.'}), 401
        
    command = request.json.get('command', '').lower()
    response = "I didn't understand that command."
    
    # 1. Create Event (Admin only)
    # Pattern: "create event [Title] on [Date] at [Location]"
    create_match = re.search(r'create event (.*?) on (.*?) at (.*)', command)
    if create_match:
        if session.get('role') != 'admin':
             return jsonify({'response': 'Only admins can create events.'})
             
        title, date_str, location = create_match.groups()
        # Try to parse date broadly or just store as string if schema allows, but schema is DATETIME
        # Expected format YYYY-MM-DD for simplicity in regex
        try:
            # simple validation, in real usage would use dateparser
            date_obj = date_str.strip() 
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO events (title, description, date, location) VALUES (%s, %s, %s, %s)", 
                           (title.strip(), "Created by AI Agent", date_obj, location.strip()))
            conn.commit()
            cursor.close()
            conn.close()
            response = f"Event '{title}' created successfully."
        except Exception as e:
            response = f"Failed to create event. Error: {str(e)}. Please use date format YYYY-MM-DD HH:MM:SS"
            
    # 2. List Events
    elif 'list events' in command or 'show events' in command:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT title, date, location FROM events")
        events = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not events:
            response = "No events found."
        else:
            response = "Here are the events:\n" + "\n".join([f"- {e['title']} ({e['date']}) at {e['location']}" for e in events])

    # 3. Register User (User for self, Admin for others)
    # Pattern: "register me for [Event Name]" or "register [User] for [Event Name]"
    elif 'register' in command:
        target_user = session.get('username')
        event_name = ""
        
        reg_match = re.search(r'register me for (.*)', command)
        if reg_match:
            event_name = reg_match.group(1).strip()
        else:
            admin_match = re.search(r'register (.*?) for (.*)', command)
            if admin_match:
                if session.get('role') != 'admin':
                    return jsonify({'response': 'Only admins can register other users.'})
                target_user = admin_match.group(1).strip()
                event_name = admin_match.group(2).strip()
        
        if event_name:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Find event
            cursor.execute("SELECT id FROM events WHERE title LIKE %s", (f"%{event_name}%",))
            event = cursor.fetchone()
            
            # Find user
            cursor.execute("SELECT id FROM users WHERE username = %s", (target_user,))
            user = cursor.fetchone()
            
            if event and user:
                try:
                    cursor.execute("INSERT INTO registrations (user_id, event_id) VALUES (%s, %s)", (user['id'], event['id']))
                    conn.commit()
                    response = f"Successfully registered {target_user} for '{event_name}'."
                except:
                    response = f"User {target_user} is already registered for this event."
            else:
                response = f"Could not find event '{event_name}' or user '{target_user}'."
            
            cursor.close()
            conn.close()
    
    return jsonify({'response': response})

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
