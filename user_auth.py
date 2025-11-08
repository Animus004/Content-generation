# -*- coding: utf-8 -*-
"""
Simple User Authentication System for Content Generator
Lightweight login system that works with the existing db_manager
"""

import sqlite3
import hashlib
import uuid
import os
import secrets
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple

# Database path
DB_NAME = 'content_tracker_users_niche.db'
DB_PATH = os.path.join(os.path.dirname(__file__), DB_NAME)

# Security constants
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION = 30  # minutes

def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_password_strength(password: str) -> Tuple[bool, str]:
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number"
    
    return True, "Password is strong"

def sanitize_input(text: str) -> str:
    """Sanitize user input"""
    return text.strip()[:100]  # Limit length and remove whitespace

def hash_password(password: str) -> str:
    """Create a secure hash of the password using PBKDF2"""
    salt = secrets.token_bytes(32)  # 256-bit salt
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt.hex() + ':' + password_hash.hex()

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    try:
        salt_hex, hash_hex = hashed.split(':')
        salt = bytes.fromhex(salt_hex)
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return password_hash.hex() == hash_hex
    except ValueError:
        return False

def setup_auth_database():
    """Initialize the authentication database"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Create users table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS auth_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT UNIQUE NOT NULL,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    last_login TEXT,
                    is_active INTEGER DEFAULT 1
                )
            ''')
            
            # Create sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    session_id TEXT UNIQUE NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    expires_at TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES auth_users (user_id)
                )
            ''')
            
            # Create user stats table for tracking generation history
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_generation_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    generation_date TEXT NOT NULL,
                    ideas_generated INTEGER DEFAULT 0,
                    niches_used TEXT,
                    session_id TEXT,
                    FOREIGN KEY (user_id) REFERENCES auth_users (user_id)
                )
            ''')
            
            conn.commit()
            
    except Exception as e:
        print(f"Database setup error: {e}")

def create_user(username: str, email: str, password: str) -> Tuple[bool, str, Optional[str]]:
    """Create a new user account with comprehensive validation"""
    try:
        # Sanitize inputs
        username = sanitize_input(username)
        email = sanitize_input(email)
        
        # Validate inputs
        if len(username) < 3:
            return False, "Username must be at least 3 characters long", None
            
        if len(username) > 30:
            return False, "Username must be less than 30 characters", None
            
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            return False, "Username can only contain letters, numbers, hyphens, and underscores", None
            
        if not validate_email(email):
            return False, "Please enter a valid email address", None
            
        password_valid, password_message = validate_password_strength(password)
        if not password_valid:
            return False, password_message, None
            
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Check if username or email already exists
            cursor.execute('SELECT username, email FROM auth_users WHERE username = ? OR email = ?', (username, email))
            existing = cursor.fetchone()
            if existing:
                return False, "Username or email already exists", None
            
            # Create user
            user_id = str(uuid.uuid4())
            password_hash = hash_password(password)
            
            cursor.execute('''
                INSERT INTO auth_users (user_id, username, email, password_hash)
                VALUES (?, ?, ?, ?)
            ''', (user_id, username, email, password_hash))
            
            conn.commit()
            return True, f"Account created successfully for {username}!", user_id
            
    except Exception as e:
        return False, f"Error creating account: {str(e)}", None

def authenticate_user(username: str, password: str) -> Tuple[bool, str, Optional[str]]:
    """Authenticate user login"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Get user and password hash
            cursor.execute('''
                SELECT user_id, username, is_active, password_hash FROM auth_users 
                WHERE username = ?
            ''', (username,))
            
            user = cursor.fetchone()
            if not user:
                return False, "Invalid username or password", None
            
            user_id, username, is_active, stored_hash = user
            
            if not is_active:
                return False, "Account is deactivated", None
            
            # Verify password
            if not verify_password(password, stored_hash):
                return False, "Invalid username or password", None
            
            # Update last login
            cursor.execute('UPDATE auth_users SET last_login = ? WHERE user_id = ?', 
                         (datetime.now().isoformat(), user_id))
            
            conn.commit()
            return True, f"Welcome back, {username}!", user_id
            
    except Exception as e:
        return False, f"Login error: {str(e)}", None

def create_session(user_id: str) -> str:
    """Create a new session for the user"""
    try:
        session_id = str(uuid.uuid4())
        expires_at = (datetime.now() + timedelta(days=7)).isoformat()  # 7 day expiry
        
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Deactivate old sessions
            cursor.execute('UPDATE user_sessions SET is_active = 0 WHERE user_id = ?', (user_id,))
            
            # Create new session
            cursor.execute('''
                INSERT INTO user_sessions (user_id, session_id, expires_at)
                VALUES (?, ?, ?)
            ''', (user_id, session_id, expires_at))
            
            conn.commit()
            return session_id
            
    except Exception as e:
        print(f"Session creation error: {e}")
        return ""

def verify_session(session_id: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """Verify if session is valid and return user info"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT s.user_id, u.username, s.expires_at 
                FROM user_sessions s
                JOIN auth_users u ON s.user_id = u.user_id
                WHERE s.session_id = ? AND s.is_active = 1
            ''', (session_id,))
            
            session = cursor.fetchone()
            if not session:
                return False, None, None
            
            user_id, username, expires_at = session
            
            # Check if session expired
            if datetime.fromisoformat(expires_at) < datetime.now():
                # Deactivate expired session
                cursor.execute('UPDATE user_sessions SET is_active = 0 WHERE session_id = ?', (session_id,))
                conn.commit()
                return False, None, None
            
            return True, user_id, username
            
    except Exception as e:
        print(f"Session verification error: {e}")
        return False, None, None

def get_user_stats(user_id: str) -> dict:
    """Get user generation statistics"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Get total ideas generated
            cursor.execute('''
                SELECT SUM(ideas_generated), COUNT(*) as sessions 
                FROM user_generation_stats 
                WHERE user_id = ?
            ''', (user_id,))
            
            result = cursor.fetchone()
            total_ideas = result[0] if result[0] else 0
            total_sessions = result[1] if result[1] else 0
            
            # Get recent activity (last 7 days)
            seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
            cursor.execute('''
                SELECT SUM(ideas_generated) 
                FROM user_generation_stats 
                WHERE user_id = ? AND generation_date > ?
            ''', (user_id, seven_days_ago))
            
            recent = cursor.fetchone()
            recent_ideas = recent[0] if recent[0] else 0
            
            # Get user info
            cursor.execute('SELECT username, email, created_at FROM auth_users WHERE user_id = ?', (user_id,))
            user_info = cursor.fetchone()
            
            return {
                'username': user_info[0] if user_info else 'Unknown',
                'email': user_info[1] if user_info else 'Unknown',
                'member_since': user_info[2] if user_info else 'Unknown',
                'total_ideas': total_ideas,
                'total_sessions': total_sessions,
                'recent_ideas': recent_ideas
            }
            
    except Exception as e:
        print(f"Stats error: {e}")
        return {
            'username': 'Unknown',
            'email': 'Unknown', 
            'member_since': 'Unknown',
            'total_ideas': 0,
            'total_sessions': 0,
            'recent_ideas': 0
        }

def log_generation_activity(user_id: str, ideas_count: int, niches: str, session_id: str = None):
    """Log user generation activity"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO user_generation_stats (user_id, generation_date, ideas_generated, niches_used, session_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, datetime.now().isoformat(), ideas_count, niches, session_id))
            
            conn.commit()
            
    except Exception as e:
        print(f"Logging error: {e}")

def logout_user(session_id: str):
    """Logout user by deactivating session"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE user_sessions SET is_active = 0 WHERE session_id = ?', (session_id,))
            conn.commit()
    except Exception as e:
        print(f"Logout error: {e}")

if __name__ == "__main__":
    setup_auth_database()
    print("✅ Authentication database setup completed!")