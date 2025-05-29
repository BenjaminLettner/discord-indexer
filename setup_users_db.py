#!/usr/bin/env python3

import sqlite3
import hashlib
import secrets
import json
from datetime import datetime

def hash_password(password):
    """Hash a password with salt using SHA-256"""
    salt = secrets.token_hex(32)
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}:{password_hash}"

def verify_password(password, stored_hash):
    """Verify a password against its hash"""
    try:
        salt, password_hash = stored_hash.split(':')
        return hashlib.sha256((password + salt).encode()).hexdigest() == password_hash
    except ValueError:
        return False

def setup_users_table(db_path):
    """Create users table and add default admin user"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            is_admin BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    # Load current config to get existing admin credentials
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        admin_username = config['auth']['username']
        admin_password = config['auth']['password']
    except:
        admin_username = 'admin'
        admin_password = 'admin123'
    
    # Check if admin user already exists
    cursor.execute('SELECT id FROM users WHERE username = ?', (admin_username,))
    if not cursor.fetchone():
        # Create default admin user
        admin_password_hash = hash_password(admin_password)
        cursor.execute('''
            INSERT INTO users (username, password_hash, is_admin, is_active)
            VALUES (?, ?, 1, 1)
        ''', (admin_username, admin_password_hash))
        print(f"Created admin user: {admin_username}")
    else:
        print(f"Admin user {admin_username} already exists")
    
    conn.commit()
    conn.close()
    print("Users table setup complete")

if __name__ == '__main__':
    # Load database path from config
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        db_path = config['database']['path']
    except:
        db_path = 'indexer.db'
    
    setup_users_table(db_path)