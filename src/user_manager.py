#!/usr/bin/env python3

import sqlite3
import hashlib
import secrets
from datetime import datetime
from typing import Optional, Dict, List

class UserManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def hash_password(self, password: str) -> str:
        """Hash a password with salt using SHA-256"""
        salt = secrets.token_hex(32)
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}:{password_hash}"
    
    def verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify a password against its hash"""
        try:
            salt, password_hash = stored_hash.split(':')
            return hashlib.sha256((password + salt).encode()).hexdigest() == password_hash
        except ValueError:
            return False
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate a user and return user data if successful"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT id, username, password_hash, email, is_admin, is_active
                FROM users WHERE username = ? AND is_active = 1
            ''', (username,))
            
            user_data = cursor.fetchone()
            if user_data and self.verify_password(password, user_data[2]):
                # Update last login
                cursor.execute('''
                    UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?
                ''', (user_data[0],))
                conn.commit()
                
                return {
                    'id': user_data[0],
                    'username': user_data[1],
                    'email': user_data[3],
                    'is_admin': bool(user_data[4]),
                    'is_active': bool(user_data[5])
                }
            return None
        finally:
            conn.close()
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user data by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT id, username, email, is_admin, is_active, created_at, last_login
                FROM users WHERE id = ?
            ''', (user_id,))
            
            user_data = cursor.fetchone()
            if user_data:
                return {
                    'id': user_data[0],
                    'username': user_data[1],
                    'email': user_data[2],
                    'is_admin': bool(user_data[3]),
                    'is_active': bool(user_data[4]),
                    'created_at': user_data[5],
                    'last_login': user_data[6]
                }
            return None
        finally:
            conn.close()
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user data by username"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT id, username, email, is_admin, is_active, created_at, last_login
                FROM users WHERE username = ?
            ''', (username,))
            
            user_data = cursor.fetchone()
            if user_data:
                return {
                    'id': user_data[0],
                    'username': user_data[1],
                    'email': user_data[2],
                    'is_admin': bool(user_data[3]),
                    'is_active': bool(user_data[4]),
                    'created_at': user_data[5],
                    'last_login': user_data[6]
                }
            return None
        finally:
            conn.close()
    
    def create_user(self, username: str, password: str, email: str = None, is_admin: bool = False) -> bool:
        """Create a new user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if username already exists
            cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
            if cursor.fetchone():
                return False
            
            password_hash = self.hash_password(password)
            cursor.execute('''
                INSERT INTO users (username, password_hash, email, is_admin, is_active)
                VALUES (?, ?, ?, ?, 1)
            ''', (username, password_hash, email, is_admin))
            
            conn.commit()
            return True
        except sqlite3.Error:
            return False
        finally:
            conn.close()
    
    def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """Change user password after verifying old password"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get current password hash
            cursor.execute('SELECT password_hash FROM users WHERE id = ?', (user_id,))
            result = cursor.fetchone()
            
            if not result or not self.verify_password(old_password, result[0]):
                return False
            
            # Update password
            new_password_hash = self.hash_password(new_password)
            cursor.execute('''
                UPDATE users SET password_hash = ? WHERE id = ?
            ''', (new_password_hash, user_id))
            
            conn.commit()
            return True
        except sqlite3.Error:
            return False
        finally:
            conn.close()
    
    def update_user_profile(self, user_id: int, email: str = None) -> bool:
        """Update user profile information"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE users SET email = ? WHERE id = ?
            ''', (email, user_id))
            
            conn.commit()
            return True
        except sqlite3.Error:
            return False
        finally:
            conn.close()
    
    def get_all_users(self) -> List[Dict]:
        """Get all users (admin only)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT id, username, email, is_admin, is_active, created_at, last_login
                FROM users ORDER BY created_at DESC
            ''')
            
            users = []
            for row in cursor.fetchall():
                users.append({
                    'id': row[0],
                    'username': row[1],
                    'email': row[2],
                    'is_admin': bool(row[3]),
                    'is_active': bool(row[4]),
                    'created_at': row[5],
                    'last_login': row[6]
                })
            return users
        finally:
            conn.close()
    
    def toggle_user_status(self, user_id: int, is_active: bool) -> bool:
        """Enable/disable user account (admin only)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE users SET is_active = ? WHERE id = ?
            ''', (is_active, user_id))
            
            conn.commit()
            return True
        except sqlite3.Error:
            return False
        finally:
            conn.close()
    
    def toggle_user_admin(self, user_id: int, is_admin: bool) -> bool:
        """Grant/revoke admin privileges (admin only)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE users SET is_admin = ? WHERE id = ?
            ''', (is_admin, user_id))
            
            conn.commit()
            return True
        except sqlite3.Error:
            return False
        finally:
            conn.close()
    
    def delete_user(self, user_id: int) -> bool:
        """Delete user account (admin only)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
            conn.commit()
            return True
        except sqlite3.Error:
            return False
        finally:
            conn.close()
    
    def get_user_by_discord_id(self, discord_id: str) -> Optional[Dict]:
        """Get user data by Discord ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT id, username, email, is_admin, is_active, discord_id, avatar_url, auth_method
                FROM users WHERE discord_id = ?
            ''', (discord_id,))
            
            user_data = cursor.fetchone()
            if user_data:
                return {
                    'id': user_data[0],
                    'username': user_data[1],
                    'email': user_data[2],
                    'is_admin': bool(user_data[3]),
                    'is_active': bool(user_data[4]),
                    'discord_id': user_data[5],
                    'avatar': user_data[6],
                    'auth_method': user_data[7] or 'local'
                }
            return None
        finally:
            conn.close()
    
    def create_discord_user(self, discord_data: Dict) -> Optional[Dict]:
        """Create a new user from Discord OAuth data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Check if Discord user already exists
            existing_user = self.get_user_by_discord_id(discord_data['id'])
            if existing_user:
                return existing_user
            
            # Create username from Discord data
            username = discord_data['username']
            if discord_data.get('discriminator') and discord_data['discriminator'] != '0':
                username = f"{username}#{discord_data['discriminator']}"
            
            # Check if username already exists and make it unique
            base_username = username
            counter = 1
            while True:
                cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
                if not cursor.fetchone():
                    break
                username = f"{base_username}_{counter}"
                counter += 1
            
            # Create avatar URL if avatar hash exists
            avatar_url = None
            if discord_data.get('avatar'):
                avatar_url = f"https://cdn.discordapp.com/avatars/{discord_data['id']}/{discord_data['avatar']}.png"
            
            # Generate a random password hash for Discord users (they won't use it)
            dummy_password_hash = self.hash_password(f"discord_user_{discord_data['id']}_{username}")
            
            cursor.execute('''
                INSERT INTO users (username, password_hash, email, is_admin, is_active, discord_id, avatar_url, auth_method)
                VALUES (?, ?, ?, ?, 1, ?, ?, 'discord')
            ''', (
                username,
                dummy_password_hash,
                discord_data.get('email'),
                discord_data.get('is_admin', False),
                discord_data['id'],
                avatar_url
            ))
            
            user_id = cursor.lastrowid
            conn.commit()
            
            # Return the created user data
            return {
                'id': user_id,
                'username': username,
                'email': discord_data.get('email'),
                'is_admin': discord_data.get('is_admin', False),
                'is_active': True,
                'discord_id': discord_data['id'],
                'avatar': avatar_url,
                'auth_method': 'discord'
            }
        except sqlite3.Error as e:
            print(f"Database error creating Discord user: {e}")
            return None
        finally:
            conn.close()
    
    def update_discord_user(self, discord_data: Dict) -> Optional[Dict]:
        """Update existing Discord user data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Create avatar URL if avatar hash exists
            avatar_url = None
            if discord_data.get('avatar'):
                avatar_url = f"https://cdn.discordapp.com/avatars/{discord_data['id']}/{discord_data['avatar']}.png"
            
            cursor.execute('''
                UPDATE users SET 
                    email = COALESCE(?, email),
                    avatar_url = ?,
                    last_login = CURRENT_TIMESTAMP
                WHERE discord_id = ?
            ''', (
                discord_data.get('email'),
                avatar_url,
                discord_data['id']
            ))
            
            conn.commit()
            
            # Return updated user data
            return self.get_user_by_discord_id(discord_data['id'])
        except sqlite3.Error as e:
            print(f"Database error updating Discord user: {e}")
            return None
        finally:
            conn.close()
    
    def get_or_create_discord_user(self, discord_data: Dict) -> Optional[Dict]:
        """Get existing Discord user or create new one"""
        # Try to get existing user
        existing_user = self.get_user_by_discord_id(discord_data['id'])
        
        if existing_user:
            # Update user data and return
            return self.update_discord_user(discord_data)
        else:
            # Create new user
            return self.create_discord_user(discord_data)