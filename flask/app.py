import sqlite3
import random
import string
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from email_validator import validate_email, EmailNotValidError

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend requests

DB_NAME = 'users.db'

# Initialize DB
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT UNIQUE,
            email TEXT UNIQUE,
            is_verified INTEGER DEFAULT 0,
            created_at INTEGER
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS otps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT,
            email TEXT,
            otp TEXT,
            expires_at INTEGER
        )
    """)
    conn.commit()
    conn.close()

init_db()


def save_otp(phone=None, email=None, otp=None):
    expires_at = int(time.time()) + 300  # Expires in 5 minutes
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        'INSERT INTO otps (phone, email, otp, expires_at) VALUES (?, ?, ?, ?)',
        (phone, email, otp, expires_at)
    )
    conn.commit()
    conn.close()

def verify_otp(phone=None, email=None, otp=None):
    now = int(time.time())
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    if phone:
        c.execute(
            'SELECT id FROM otps WHERE phone=? AND otp=? AND expires_at > ? ORDER BY expires_at DESC LIMIT 1',
            (phone, otp, now)
        )
    else:
        c.execute(
            'SELECT id FROM otps WHERE email=? AND otp=? AND expires_at > ? ORDER BY expires_at DESC LIMIT 1',
            (email, otp, now)
        )
    row = c.fetchone()
    if row:
        otp_id = row[0]
        c.execute('DELETE FROM otps WHERE id=?', (otp_id,))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def create_user(phone=None, email=None):
    created_at = int(time.time())
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # Check if user already exists
    if phone:
        c.execute('SELECT id FROM users WHERE phone=?', (phone,))
        if c.fetchone():
            conn.close()
            return False

        c.execute('INSERT INTO users (phone, is_verified, created_at) VALUES (?, ?, ?)', (phone, 1, created_at))
    else:
        c.execute('SELECT id FROM users WHERE email=?', (email,))
        if c.fetchone():
            conn.close()
            return False

        c.execute('INSERT INTO users (email, is_verified, created_at) VALUES (?, ?, ?)', (email, 1, created_at))
    conn.commit()
    conn.close()
    return True

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    phone = data.get('phone')
    email = data.get('email')

    if not phone and not email:
        return jsonify({'success': False, 'message': 'Phone or email is required'}), 400

    if email:
        try:
            validate_email(email)
        except EmailNotValidError as e:
            return jsonify({'success': False, 'message': 'Invalid email'}), 400

    # Generate 6-digit numeric OTP
    otp = ''.join(random.choices(string.digits, k=6))

    # Store OTP associated with phone/email
    save_otp(phone=phone, email=email, otp=otp)

    # Simulate OTP sending
    if phone:
        print(f"[DEBUG] OTP for phone {phone} is {otp}")
    else:
        print(f"[DEBUG] OTP for email {email} is {otp}")

    return jsonify({'success': True, 'message': 'OTP sent to provided contact.'})


@app.route('/verify-otp', methods=['POST'])
def verify():
    data = request.json
    phone = data.get('phone')
    email = data.get('email')
    otp = data.get('otp')

    if not otp:
        return jsonify({'success': False, 'message': 'OTP is required'}), 400

    if not phone and not email:
        return jsonify({'success': False, 'message': 'Phone or email is required'}), 400

    if verify_otp(phone=phone, email=email, otp=otp):
        # Create user in DB if verified
        if create_user(phone=phone, email=email):
            return jsonify({'success': True, 'message': 'OTP verified and user registered successfully.'})
        else:
            return jsonify({'success': False, 'message': 'User already exists.'}), 409
    else:
        return jsonify({'success': False, 'message': 'Invalid or expired OTP.'}), 400


@app.route('/login', methods=['POST'])
def login():
    data = request.json
    phone = data.get('phone')
    email = data.get('email')

    if not phone and not email:
        return jsonify({'success': False, 'message': 'Phone or email is required'}), 400

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    if phone:
        c.execute('SELECT id, is_verified FROM users WHERE phone=?', (phone,))
    else:
        c.execute('SELECT id, is_verified FROM users WHERE email=?', (email,))
    user = c.fetchone()
    conn.close()

    if user:
        if user[1] == 1:
            return jsonify({'success': True, 'message': 'Login successful.'})
        else:
            return jsonify({'success': False, 'message': 'User not verified.'}), 403
    else:
        return jsonify({'success': False, 'message': 'User does not exist.'}), 404


if __name__ == '__main__':
    print("Starting server at http://127.0.0.1:5000")
    app.run(debug=True)

