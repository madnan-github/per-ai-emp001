#!/usr/bin/env python3
"""
Authentication Manager Script
This script provides functionality to manage authentication and authorization for the system.
"""

import os
import json
import sqlite3
import hashlib
import secrets
import bcrypt
import jwt
import time
from datetime import datetime, timedelta
from pathlib import Path
import argparse
import re
from functools import wraps

# Database path
DB_PATH = Path.home() / "claude_data" / "users.db"
LOG_PATH = Path.home() / "claude_logs" / "auth_events.log"

def init_db():
    """Initialize the database with required tables"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            first_name TEXT,
            last_name TEXT,
            phone TEXT,
            is_active BOOLEAN DEFAULT 1,
            is_verified BOOLEAN DEFAULT 0,
            email_verified_at TIMESTAMP,
            password_reset_token TEXT,
            password_reset_expires TIMESTAMP,
            failed_login_attempts INTEGER DEFAULT 0,
            locked_until TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create roles table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create user_roles junction table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_roles (
            user_id INTEGER,
            role_id INTEGER,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (role_id) REFERENCES roles(id),
            PRIMARY KEY (user_id, role_id)
        )
    ''')

    # Create sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id INTEGER,
            token TEXT NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Insert default roles if they don't exist
    cursor.execute("INSERT OR IGNORE INTO roles (name, description) VALUES (?, ?)",
                   ("admin", "Administrator with full access"))
    cursor.execute("INSERT OR IGNORE INTO roles (name, description) VALUES (?, ?)",
                   ("user", "Regular user with standard access"))

    conn.commit()
    conn.close()

def log_auth_event(event_type, user_id=None, details=""):
    """Log authentication events to audit trail"""
    LOG_PATH.parent.mkdir(exist_ok=True)

    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] {event_type} | user_id: {user_id or 'N/A'} | details: {details}\n"

    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(log_entry)

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"

    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"

    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"

    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"

    return True, "Password is valid"

def hash_password(password, salt=None):
    """Hash password with bcrypt"""
    if salt is None:
        salt = bcrypt.gensalt()
    else:
        salt = salt.encode('utf-8')

    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8'), salt.decode('utf-8')

def generate_token(length=32):
    """Generate a secure random token"""
    return secrets.token_urlsafe(length)

def generate_jwt_token(user_id, email, roles, expiry_minutes=15):
    """Generate a JWT token"""
    secret = os.environ.get('JWT_SECRET', 'fallback_secret_for_testing')

    payload = {
        'user_id': user_id,
        'email': email,
        'roles': roles,
        'exp': datetime.utcnow() + timedelta(minutes=expiry_minutes),
        'iat': datetime.utcnow()
    }

    return jwt.encode(payload, secret, algorithm='HS256')

def verify_jwt_token(token):
    """Verify a JWT token"""
    secret = os.environ.get('JWT_SECRET', 'fallback_secret_for_testing')

    try:
        payload = jwt.decode(token, secret, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def create_user(email, password, username=None, first_name=None, last_name=None, phone=None):
    """Create a new user account"""
    # Validate inputs
    if not validate_email(email):
        return False, "Invalid email format"

    is_valid, msg = validate_password(password)
    if not is_valid:
        return False, msg

    # Hash password
    password_hash, salt = hash_password(password)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO users (email, username, password_hash, salt, first_name, last_name, phone)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (email, username, password_hash, salt, first_name, last_name, phone))

        user_id = cursor.lastrowid
        conn.commit()

        log_auth_event("USER_CREATED", user_id, f"User created with email: {email}")
        return True, f"User created successfully with ID: {user_id}"
    except sqlite3.IntegrityError as e:
        if "email" in str(e):
            return False, "Email already exists"
        elif "username" in str(e):
            return False, "Username already exists"
        else:
            return False, f"Database error: {str(e)}"
    finally:
        conn.close()

def authenticate_user(email, password, ip_address=None, user_agent=None):
    """Authenticate a user"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if user exists and get details
    cursor.execute('''
        SELECT id, password_hash, is_active, locked_until, failed_login_attempts
        FROM users WHERE email = ?
    ''', (email,))

    user = cursor.fetchone()

    if not user:
        conn.close()
        log_auth_event("LOGIN_FAILED", details=f"User not found: {email}")
        return False, "Invalid email or password"

    user_id, stored_hash, is_active, locked_until, failed_attempts = user

    # Check if account is locked
    if locked_until:
        locked_time = datetime.fromisoformat(locked_until)
        if datetime.now() < locked_time:
            conn.close()
            log_auth_event("LOGIN_FAILED", user_id, f"Account locked until {locked_until}")
            return False, "Account is locked due to too many failed attempts"

    # Check if account is active
    if not is_active:
        conn.close()
        log_auth_event("LOGIN_FAILED", user_id, "Account is inactive")
        return False, "Account is deactivated"

    # Verify password
    if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
        # Reset failed attempts on successful login
        cursor.execute('''
            UPDATE users SET failed_login_attempts = 0, locked_until = NULL
            WHERE id = ?
        ''', (user_id,))

        conn.commit()
        conn.close()

        # Get user roles
        cursor.execute('''
            SELECT r.name FROM roles r
            JOIN user_roles ur ON r.id = ur.role_id
            WHERE ur.user_id = ?
        ''', (user_id,))

        roles = [row[0] for row in cursor.fetchall()]

        # Generate session
        session_id = generate_token(32)
        token = generate_jwt_token(user_id, email, roles)

        # Store session
        session_conn = sqlite3.connect(DB_PATH)
        session_cursor = session_conn.cursor()
        session_cursor.execute('''
            INSERT INTO sessions (id, user_id, token, expires_at, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            session_id,
            user_id,
            token,
            datetime.now() + timedelta(hours=24),  # 24-hour session
            ip_address,
            user_agent
        ))
        session_conn.commit()
        session_conn.close()

        log_auth_event("LOGIN_SUCCESS", user_id, f"Successful login from IP: {ip_address}")
        return True, {"session_id": session_id, "token": token, "user_id": user_id, "roles": roles}
    else:
        # Increment failed attempts
        new_failed_attempts = failed_attempts + 1

        # Lock account after 5 failed attempts for 30 minutes
        locked_until_val = None
        if new_failed_attempts >= 5:
            locked_until_val = datetime.now() + timedelta(minutes=30)

        cursor.execute('''
            UPDATE users
            SET failed_login_attempts = ?, locked_until = ?
            WHERE id = ?
        ''', (new_failed_attempts, locked_until_val.isoformat() if locked_until_val else None, user_id))

        conn.commit()
        conn.close()

        log_auth_event("LOGIN_FAILED", user_id, f"Failed login attempt #{new_failed_attempts} from IP: {ip_address}")
        return False, "Invalid email or password"

def logout_user(session_id):
    """Logout a user by invalidating their session"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('SELECT user_id FROM sessions WHERE id = ?', (session_id,))
    result = cursor.fetchone()

    if result:
        user_id = result[0]
        cursor.execute('DELETE FROM sessions WHERE id = ?', (session_id,))
        conn.commit()
        conn.close()

        log_auth_event("LOGOUT", user_id, f"User logged out with session: {session_id}")
        return True, "Logged out successfully"
    else:
        conn.close()
        return False, "Invalid session"

def assign_role_to_user(user_id, role_name):
    """Assign a role to a user"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get role ID
    cursor.execute('SELECT id FROM roles WHERE name = ?', (role_name,))
    role_result = cursor.fetchone()

    if not role_result:
        conn.close()
        return False, f"Role '{role_name}' does not exist"

    role_id = role_result[0]

    try:
        cursor.execute('''
            INSERT INTO user_roles (user_id, role_id)
            VALUES (?, ?)
        ''', (user_id, role_id))

        conn.commit()
        conn.close()

        log_auth_event("ROLE_ASSIGNED", user_id, f"Role '{role_name}' assigned to user")
        return True, f"Role '{role_name}' assigned to user successfully"
    except sqlite3.IntegrityError:
        conn.close()
        return False, f"User already has role '{role_name}'"

def reset_password_request(email):
    """Initiate a password reset request"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if user exists
    cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()

    if not user:
        conn.close()
        return False, "No account found with that email"

    user_id = user[0]

    # Generate reset token
    reset_token = generate_token(32)
    expires_at = datetime.now() + timedelta(hours=1)  # Token expires in 1 hour

    # Update user record with reset token
    cursor.execute('''
        UPDATE users
        SET password_reset_token = ?, password_reset_expires = ?
        WHERE id = ?
    ''', (reset_token, expires_at.isoformat(), user_id))

    conn.commit()
    conn.close()

    log_auth_event("PASSWORD_RESET_REQUEST", user_id, f"Password reset requested for email: {email}")

    # In a real system, send email with reset link
    reset_link = f"https://yoursite.com/reset-password?token={reset_token}"
    print(f"Password reset link would be sent to {email}: {reset_link}")

    return True, f"Password reset link sent to {email}"

def reset_password_with_token(reset_token, new_password):
    """Reset password using a reset token"""
    # Validate new password
    is_valid, msg = validate_password(new_password)
    if not is_valid:
        return False, msg

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Check if token exists and is not expired
    cursor.execute('''
        SELECT id, email FROM users
        WHERE password_reset_token = ? AND password_reset_expires > ?
    ''', (reset_token, datetime.now().isoformat()))

    user = cursor.fetchone()

    if not user:
        conn.close()
        return False, "Invalid or expired reset token"

    user_id, email = user

    # Hash new password
    password_hash, salt = hash_password(new_password)

    # Update password and clear reset token
    cursor.execute('''
        UPDATE users
        SET password_hash = ?, password_reset_token = NULL, password_reset_expires = NULL
        WHERE id = ?
    ''', (password_hash, user_id))

    conn.commit()
    conn.close()

    log_auth_event("PASSWORD_RESET", user_id, f"Password reset completed for email: {email}")
    return True, "Password reset successfully"

def verify_session(session_id):
    """Verify if a session is valid"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT s.user_id, s.expires_at, u.email, u.is_active
        FROM sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.id = ?
    ''', (session_id,))

    session = cursor.fetchone()
    conn.close()

    if not session:
        return False, "Invalid session"

    user_id, expires_at, email, is_active = session

    # Check if session has expired
    if datetime.now() > datetime.fromisoformat(expires_at):
        # Clean up expired session
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM sessions WHERE id = ?', (session_id,))
        conn.commit()
        conn.close()
        return False, "Session expired"

    # Check if user account is still active
    if not is_active:
        return False, "Account is deactivated"

    # Get user roles
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT r.name FROM roles r
        JOIN user_roles ur ON r.id = ur.role_id
        WHERE ur.user_id = ?
    ''', (user_id,))

    roles = [row[0] for row in cursor.fetchall()]
    conn.close()

    return True, {"user_id": user_id, "email": email, "roles": roles}

def check_permission(user_id, required_role):
    """Check if a user has a specific role/permission"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT COUNT(*) FROM user_roles ur
        JOIN roles r ON ur.role_id = r.id
        WHERE ur.user_id = ? AND r.name = ?
    ''', (user_id, required_role))

    has_permission = cursor.fetchone()[0] > 0
    conn.close()

    return has_permission

def main():
    init_db()

    parser = argparse.ArgumentParser(description='Authentication Manager')
    parser.add_argument('--action', type=str, required=True,
                       choices=['register', 'login', 'logout', 'assign-role', 'reset-password-request', 'reset-password-token'],
                       help='Authentication action to perform')
    parser.add_argument('--email', type=str, help='User email')
    parser.add_argument('--password', type=str, help='User password')
    parser.add_argument('--username', type=str, help='User username')
    parser.add_argument('--first-name', type=str, help='User first name')
    parser.add_argument('--last-name', type=str, help='User last name')
    parser.add_argument('--phone', type=str, help='User phone number')
    parser.add_argument('--session-id', type=str, help='Session ID for logout')
    parser.add_argument('--user-id', type=int, help='User ID for role assignment')
    parser.add_argument('--role', type=str, help='Role to assign to user')
    parser.add_argument('--reset-token', type=str, help='Password reset token')
    parser.add_argument('--new-password', type=str, help='New password for reset')
    parser.add_argument('--ip-address', type=str, help='IP address for login logging')
    parser.add_argument('--user-agent', type=str, help='User agent for login logging')

    args = parser.parse_args()

    if args.action == 'register':
        if not args.email or not args.password:
            print("Email and password are required for registration")
            return

        success, message = create_user(
            email=args.email,
            password=args.password,
            username=args.username,
            first_name=args.first_name,
            last_name=args.last_name,
            phone=args.phone
        )

        if success:
            print(message)
        else:
            print(f"Registration failed: {message}")

    elif args.action == 'login':
        if not args.email or not args.password:
            print("Email and password are required for login")
            return

        success, result = authenticate_user(
            email=args.email,
            password=args.password,
            ip_address=args.ip_address,
            user_agent=args.user_agent
        )

        if success:
            print(json.dumps(result, indent=2))
        else:
            print(f"Login failed: {result}")

    elif args.action == 'logout':
        if not args.session_id:
            print("Session ID is required for logout")
            return

        success, message = logout_user(args.session_id)
        if success:
            print(message)
        else:
            print(f"Logout failed: {message}")

    elif args.action == 'assign-role':
        if not args.user_id or not args.role:
            print("User ID and role are required for role assignment")
            return

        success, message = assign_role_to_user(args.user_id, args.role)
        if success:
            print(message)
        else:
            print(f"Role assignment failed: {message}")

    elif args.action == 'reset-password-request':
        if not args.email:
            print("Email is required for password reset request")
            return

        success, message = reset_password_request(args.email)
        if success:
            print(message)
        else:
            print(f"Password reset request failed: {message}")

    elif args.action == 'reset-password-token':
        if not args.reset_token or not args.new_password:
            print("Reset token and new password are required for password reset")
            return

        success, message = reset_password_with_token(args.reset_token, args.new_password)
        if success:
            print(message)
        else:
            print(f"Password reset failed: {message}")

if __name__ == "__main__":
    main()