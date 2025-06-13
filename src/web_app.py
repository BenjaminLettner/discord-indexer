#!/usr/bin/env python3

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_file
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import requests
import sqlite3
import json
import hashlib
from datetime import datetime, timedelta
import os
from urllib.parse import urlparse
import logging
from user_manager import UserManager
from discord_auth import DiscordOAuth2

import tempfile
import io
import base64
from PIL import Image
from pdf2image import convert_from_path
import subprocess

# Load configuration
with open('config/config.json', 'r') as f:
    config = json.load(f)

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.secret_key = config['web']['secret_key']

# Set logging level to INFO to capture debug messages
import logging
logging.basicConfig(level=logging.INFO)
app.logger.setLevel(logging.INFO)

# Initialize Discord OAuth2 if configured
discord_oauth = None
if config.get('discord_oauth', {}).get('enabled', False):
    oauth_config = config['discord_oauth']
    bot_token = config.get('discord', {}).get('token')  # Get bot token from existing config
    discord_oauth = DiscordOAuth2(
        client_id=oauth_config['client_id'],
        client_secret=oauth_config['client_secret'],
        redirect_uri=oauth_config['redirect_uri'],
        required_guild_id=oauth_config.get('required_guild_id'),
        required_roles=oauth_config.get('required_roles', []),
        admin_roles=oauth_config.get('admin_roles', []),
        bot_token=bot_token
    )

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['id'])
        self.username = user_data['username']
        self.email = user_data.get('email')
        self.is_admin = user_data.get('is_admin', False)
        self._is_active = user_data.get('is_active', True)
        self.auth_method = user_data.get('auth_method', 'local')
        self.discord_id = user_data.get('discord_id')
        self.avatar = user_data.get('avatar')
    
    @property
    def is_active(self):
        return self._is_active

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def get_files(self, page=1, per_page=50, search=None, file_type=None, tag_ids=None):
        """Get paginated files with optional search and filtering"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Build query
            if tag_ids:
                # Join with file_tags when filtering by tags
                query = '''
                    SELECT DISTINCT f.id, f.message_id, f.channel_name, f.guild_name, f.author_name, 
                           f.filename, f.file_url, f.file_size, f.file_type, f.message_content, 
                           f.timestamp, f.indexed_at
                    FROM indexed_files f
                    JOIN file_tags ft ON f.id = ft.file_id
                '''
            else:
                query = '''
                    SELECT id, message_id, channel_name, guild_name, author_name, 
                           filename, file_url, file_size, file_type, message_content, 
                           timestamp, indexed_at
                    FROM indexed_files
                '''
            
            conditions = []
            params = []
            
            if search:
                if tag_ids:
                    conditions.append('(f.filename LIKE ? OR f.message_content LIKE ? OR f.author_name LIKE ?)')
                else:
                    conditions.append('(filename LIKE ? OR message_content LIKE ? OR author_name LIKE ?)')
                search_param = f'%{search}%'
                params.extend([search_param, search_param, search_param])
            
            if file_type:
                if tag_ids:
                    conditions.append('f.file_type LIKE ?')
                else:
                    conditions.append('file_type LIKE ?')
                params.append(f'%{file_type}%')
            
            if tag_ids:
                if isinstance(tag_ids, list):
                    placeholders = ','.join(['?' for _ in tag_ids])
                    conditions.append(f'ft.tag_id IN ({placeholders})')
                    params.extend(tag_ids)
                else:
                    conditions.append('ft.tag_id = ?')
                    params.append(tag_ids)
            
            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)
            
            if tag_ids:
                query += ' ORDER BY f.timestamp DESC'
            else:
                query += ' ORDER BY timestamp DESC'
            
            # Get total count
            count_query = query.replace(
                'SELECT id, message_id, channel_name, guild_name, author_name, filename, file_url, file_size, file_type, message_content, timestamp, indexed_at',
                'SELECT COUNT(*)'
            )
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]
            
            # Add pagination
            offset = (page - 1) * per_page
            query += ' LIMIT ? OFFSET ?'
            params.extend([per_page, offset])
            
            cursor.execute(query, params)
            files = cursor.fetchall()
            
            # Add tags for each file
            files_with_tags = []
            for file in files:
                file_tags = self.get_file_tags(file[0])  # file[0] is the file ID
                files_with_tags.append(list(file) + [file_tags])
            
            return files_with_tags, total
        except Exception as e:
            print(f"Error getting files: {e}")
            return [], 0
        finally:
            conn.close()
    
    def get_links(self, page=1, per_page=50, search=None, domain=None, tag_ids=None):
        """Get paginated links with optional search and filtering"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Build query
            if tag_ids:
                # Join with link_tags when filtering by tags
                query = '''
                    SELECT DISTINCT l.id, l.message_id, l.channel_name, l.guild_name, l.author_name, 
                           l.link_url, l.link_domain, l.message_content, l.timestamp, l.indexed_at
                    FROM indexed_links l
                    JOIN link_tags lt ON l.id = lt.link_id
                '''
            else:
                query = '''
                    SELECT id, message_id, channel_name, guild_name, author_name, 
                           link_url, link_domain, message_content, timestamp, indexed_at
                    FROM indexed_links
                '''
            
            conditions = []
            params = []
            
            if search:
                if tag_ids:
                    conditions.append('(l.link_url LIKE ? OR l.message_content LIKE ? OR l.author_name LIKE ?)')
                else:
                    conditions.append('(link_url LIKE ? OR message_content LIKE ? OR author_name LIKE ?)')
                search_param = f'%{search}%'
                params.extend([search_param, search_param, search_param])
            
            if domain:
                if tag_ids:
                    conditions.append('l.link_domain LIKE ?')
                else:
                    conditions.append('link_domain LIKE ?')
                params.append(f'%{domain}%')
            
            if tag_ids:
                if isinstance(tag_ids, list):
                    placeholders = ','.join(['?' for _ in tag_ids])
                    conditions.append(f'lt.tag_id IN ({placeholders})')
                    params.extend(tag_ids)
                else:
                    conditions.append('lt.tag_id = ?')
                    params.append(tag_ids)
            
            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)
            
            if tag_ids:
                query += ' ORDER BY l.timestamp DESC'
            else:
                query += ' ORDER BY timestamp DESC'
            
            # Get total count
            count_query = query.replace(
                'SELECT id, message_id, channel_name, guild_name, author_name, link_url, link_domain, message_content, timestamp, indexed_at',
                'SELECT COUNT(*)'
            )
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]
            
            # Add pagination
            offset = (page - 1) * per_page
            query += ' LIMIT ? OFFSET ?'
            params.extend([per_page, offset])
            
            cursor.execute(query, params)
            links = cursor.fetchall()
            
            # Add tags for each link
            links_with_tags = []
            for link in links:
                link_tags = self.get_link_tags(link[0])  # link[0] is the link ID
                links_with_tags.append(list(link) + [link_tags])
            
            return links_with_tags, total
        except Exception as e:
            print(f"Error getting links: {e}")
            return [], 0
        finally:
            conn.close()
    
    def get_stats(self):
        """Get dashboard statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            stats = {}
            
            # Total counts
            cursor.execute('SELECT COUNT(*) FROM indexed_files')
            stats['total_files'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM indexed_links')
            stats['total_links'] = cursor.fetchone()[0]
            
            # Recent activity (last 24 hours)
            cursor.execute('''
                SELECT COUNT(*) FROM indexed_files 
                WHERE indexed_at > datetime('now', '-1 day')
            ''')
            stats['files_24h'] = cursor.fetchone()[0]
            
            cursor.execute('''
                SELECT COUNT(*) FROM indexed_links 
                WHERE indexed_at > datetime('now', '-1 day')
            ''')
            stats['links_24h'] = cursor.fetchone()[0]
            
            # Top file types
            cursor.execute('''
                SELECT file_type, COUNT(*) as count 
                FROM indexed_files 
                WHERE file_type IS NOT NULL 
                GROUP BY file_type 
                ORDER BY count DESC 
                LIMIT 10
            ''')
            stats['top_file_types'] = cursor.fetchall()
            
            # Top domains
            cursor.execute('''
                SELECT link_domain, COUNT(*) as count 
                FROM indexed_links 
                WHERE link_domain IS NOT NULL 
                GROUP BY link_domain 
                ORDER BY count DESC 
                LIMIT 10
            ''')
            stats['top_domains'] = cursor.fetchall()
            
            return stats
        except Exception as e:
            print(f"Error getting stats: {e}")
            return {}
        finally:
            conn.close()
    
    def get_all_tags(self):
        """Get all available tags"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT id, name, color, description, created_at FROM tags ORDER BY name')
            return cursor.fetchall()
        except Exception as e:
            print(f"Error getting tags: {e}")
            return []
        finally:
            conn.close()
    
    def create_tag(self, name, color='#007bff', description='', created_by=None):
        """Create a new tag"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO tags (name, color, description, created_by)
                VALUES (?, ?, ?, ?)
            ''', (name, color, description, created_by))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"Error creating tag: {e}")
            return None
        finally:
            conn.close()
    
    def update_tag(self, tag_id, name=None, color=None, description=None):
        """Update a tag's properties"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Build dynamic update query
            updates = []
            params = []
            
            if name is not None:
                updates.append('name = ?')
                params.append(name)
            if color is not None:
                updates.append('color = ?')
                params.append(color)
            if description is not None:
                updates.append('description = ?')
                params.append(description)
            
            if not updates:
                return True  # Nothing to update
            
            params.append(tag_id)
            query = f'UPDATE tags SET {', '.join(updates)} WHERE id = ?'
            
            cursor.execute(query, params)
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating tag: {e}")
            return False
        finally:
            conn.close()
    
    def delete_tag(self, tag_id):
        """Delete a tag and all its associations"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM tags WHERE id = ?', (tag_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting tag: {e}")
            return False
        finally:
            conn.close()
    
    def add_file_tag(self, file_id, tag_id, added_by=None):
        """Add a tag to a file"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO file_tags (file_id, tag_id, added_by)
                VALUES (?, ?, ?)
            ''', (file_id, tag_id, added_by))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding file tag: {e}")
            return False
        finally:
            conn.close()
    
    def remove_file_tag(self, file_id, tag_id):
        """Remove a tag from a file"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM file_tags WHERE file_id = ? AND tag_id = ?', (file_id, tag_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error removing file tag: {e}")
            return False
        finally:
            conn.close()
    
    def get_file_tags(self, file_id):
        """Get all tags for a specific file"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT t.id, t.name, t.color, t.description
                FROM tags t
                JOIN file_tags ft ON t.id = ft.tag_id
                WHERE ft.file_id = ?
                ORDER BY t.name
            ''', (file_id,))
            return cursor.fetchall()
        except Exception as e:
            print(f"Error getting file tags: {e}")
            return []
        finally:
            conn.close()
    
    def add_link_tag(self, link_id, tag_id, added_by=None):
        """Add a tag to a link"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO link_tags (link_id, tag_id, added_by)
                VALUES (?, ?, ?)
            ''', (link_id, tag_id, added_by))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding link tag: {e}")
            return False
        finally:
            conn.close()
    
    def remove_link_tag(self, link_id, tag_id):
        """Remove a tag from a link"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM link_tags WHERE link_id = ? AND tag_id = ?', (link_id, tag_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error removing link tag: {e}")
            return False
        finally:
            conn.close()
    
    def get_link_tags(self, link_id):
        """Get all tags for a specific link"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT t.id, t.name, t.color, t.description
                FROM tags t
                JOIN link_tags lt ON t.id = lt.tag_id
                WHERE lt.link_id = ?
                ORDER BY t.name
            ''', (link_id,))
            return cursor.fetchall()
        except Exception as e:
            print(f"Error getting link tags: {e}")
            return []
        finally:
            conn.close()

# Initialize managers
db = DatabaseManager(config['database']['path'])
user_manager = UserManager(config['database']['path'])

@login_manager.user_loader
def load_user(user_id):
    user_data = user_manager.get_user_by_id(int(user_id))
    if user_data:
        return User(user_data)
    return None

def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

app.jinja_env.filters['filesize'] = format_file_size

@app.route('/')
@login_required
def dashboard():
    """Main dashboard"""
    stats = db.get_stats()
    return render_template('dashboard.html', stats=stats)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember = 'remember' in request.form
        
        # Authenticate user with database
        user_data = user_manager.authenticate_user(username, password)
        if user_data:
            user = User(user_data)
            login_user(user, remember=remember, duration=timedelta(seconds=config['auth']['session_timeout']))
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    # Check if Discord OAuth is enabled
    discord_auth_url = None
    discord_oauth_enabled = discord_oauth and config.get('discord_oauth', {}).get('enabled', False)
    if discord_oauth_enabled:
        discord_auth_url = discord_oauth.get_authorization_url()
    
    return render_template('login.html', discord_auth_url=discord_auth_url, discord_oauth_enabled=discord_oauth_enabled)

@app.route('/auth/discord')
def discord_login():
    """Redirect to Discord OAuth2"""
    if not discord_oauth:
        flash('Discord authentication is not configured', 'error')
        return redirect(url_for('login'))
    
    auth_url = discord_oauth.get_authorization_url()
    app.logger.info(f"Redirecting to Discord OAuth URL: {auth_url}")
    app.logger.info(f"Configured redirect URI: {discord_oauth.redirect_uri}")
    return redirect(auth_url)

@app.route('/auth/discord/callback')
def discord_callback():
    """Handle Discord OAuth2 callback"""
    app.logger.info(f"Discord callback hit with args: {request.args}")
    app.logger.info(f"Request URL: {request.url}")
    app.logger.info(f"Request headers: {dict(request.headers)}")
    
    if not discord_oauth:
        flash('Discord authentication is not configured', 'error')
        return redirect(url_for('login'))
    
    code = request.args.get('code')
    error = request.args.get('error')
    error_description = request.args.get('error_description')
    
    if error:
        app.logger.error(f"Discord OAuth error: {error} - {error_description}")
        flash(f'Discord authorization failed: {error_description or error}', 'error')
        return redirect(url_for('login'))
    
    if not code:
        app.logger.error("No authorization code received from Discord")
        flash('Authorization failed: No code received from Discord', 'error')
        return redirect(url_for('login'))
    
    app.logger.info(f"Received authorization code: {code[:10]}...")
    
    try:
        app.logger.info("Attempting to authenticate user with Discord")
        # Authenticate with Discord
        user_data = discord_oauth.authenticate_user(code)
        if not user_data:
            app.logger.error("Discord authentication failed - no user data returned")
            flash('Discord authentication failed. Please ensure you are a member of the required Discord server and have the necessary roles.', 'error')
            return redirect(url_for('login'))
        
        app.logger.info(f"Successfully authenticated user: {user_data.get('username')}")
        
        # Create or update user in database
        discord_user = user_manager.get_or_create_discord_user(user_data)
        if discord_user:
            user = User(discord_user)
            login_user(user, duration=timedelta(seconds=config['auth']['session_timeout']))
            app.logger.info(f"User {user.username} successfully logged in")
            flash(f'Welcome, {user.username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            app.logger.error("Failed to create user account in database")
            flash('Failed to create user account', 'error')
            return redirect(url_for('login'))
    except Exception as e:
        app.logger.error(f"Discord authentication failed: {str(e)}", exc_info=True)
        flash(f'Authentication failed: {str(e)}', 'error')
        return redirect(url_for('login'))

@app.route('/logout')
@login_required
def logout():
    """Logout"""
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/profile')
@login_required
def profile():
    """User profile page"""
    return render_template('profile.html')

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    """Update user profile"""
    email = request.form.get('email')
    
    if user_manager.update_user_profile(int(current_user.id), email):
        flash('Profile updated successfully', 'success')
    else:
        flash('Failed to update profile', 'error')
    
    return redirect(url_for('profile'))

@app.route('/change_password', methods=['POST'])
@login_required
def change_password():
    """Change user password"""
    current_password = request.form['current_password']
    new_password = request.form['new_password']
    confirm_password = request.form['confirm_password']
    
    if new_password != confirm_password:
        flash('New passwords do not match', 'error')
        return redirect(url_for('profile'))
    
    if len(new_password) < 6:
        flash('Password must be at least 6 characters long', 'error')
        return redirect(url_for('profile'))
    
    if user_manager.change_password(int(current_user.id), current_password, new_password):
        flash('Password changed successfully', 'success')
    else:
        flash('Current password is incorrect', 'error')
    
    return redirect(url_for('profile'))



# Admin Dashboard Routes
@app.route('/admin')
@login_required
def admin_dashboard():
    """Admin dashboard page"""
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    # Get system stats
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Get total user count
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    
    # Get active user count (users who have logged in at least once)
    cursor.execute("SELECT COUNT(*) FROM users WHERE last_login IS NOT NULL")
    active_users = cursor.fetchone()[0]
    
    # Get admin user count
    cursor.execute('SELECT COUNT(*) FROM users WHERE is_admin = 1')
    admin_users = cursor.fetchone()[0]
    
    # Get file count
    cursor.execute('SELECT COUNT(*) FROM indexed_files')
    total_files = cursor.fetchone()[0]
    
    conn.close()
    
    stats = {
        'total_users': total_users,
        'active_users': active_users,
        'admin_users': admin_users,
        'total_files': total_files
    }
    
    return render_template('admin_dashboard.html', stats=stats)

@app.route('/admin/users')
@login_required
def admin_users():
    """Admin user management page"""
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    users = user_manager.get_all_users()
    return render_template('admin_users.html', users=users)

@app.route('/admin/config')
@login_required
def admin_config():
    """Admin configuration page"""
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Load current configuration
        with open('/root/discord-indexer/config/config.json', 'r') as f:
            current_config = json.load(f)
        
        # Map config structure to template expectations
        config_data = {
            'bot_token': current_config.get('discord', {}).get('token', ''),
            'guild_id': current_config.get('discord', {}).get('guild_id', ''),
            'channels': current_config.get('discord', {}).get('channels', []),
            'db_path': current_config.get('database', {}).get('path', ''),
            'backup_enabled': current_config.get('database', {}).get('backup_enabled', False),
            'backup_interval': current_config.get('database', {}).get('backup_interval', 24),
            'web_host': current_config.get('web', {}).get('host', '0.0.0.0'),
            'web_port': current_config.get('web', {}).get('port', 5000),
            'secret_key': current_config.get('web', {}).get('secret_key', ''),
            'max_file_size': current_config.get('web', {}).get('max_file_size', 50),
            'session_timeout': current_config.get('auth', {}).get('session_timeout', 3600) // 60,  # Convert to minutes
            'rate_limit': current_config.get('web', {}).get('rate_limit', 100),
            'log_level': current_config.get('logging', {}).get('level', 'INFO'),
            'log_file': current_config.get('logging', {}).get('file', ''),
            'log_rotation': current_config.get('logging', {}).get('backup_count', 0) > 0
        }
        
        return render_template('admin_config.html', config=config_data)
    except Exception as e:
        flash(f'Error loading configuration: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/config/update', methods=['POST'])
@login_required
def admin_config_update():
    """Update configuration"""
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Load current config
        with open('/root/discord-indexer/config/config.json', 'r') as f:
            current_config = json.load(f)
        
        # Update Discord settings
        if 'bot_token' in request.form:
            if 'discord' not in current_config:
                current_config['discord'] = {}
            current_config['discord']['token'] = request.form['bot_token']
        
        if 'guild_id' in request.form:
            if 'discord' not in current_config:
                current_config['discord'] = {}
            guild_id = request.form['guild_id'].strip()
            current_config['discord']['guild_id'] = guild_id if guild_id else None
        
        if 'channels' in request.form:
            if 'discord' not in current_config:
                current_config['discord'] = {}
            channels_text = request.form['channels'].strip()
            if channels_text:
                channels = [ch.strip() for ch in channels_text.split('\n') if ch.strip()]
                current_config['discord']['channels'] = channels
            else:
                current_config['discord']['channels'] = []
        
        # Update database settings
        if 'db_path' in request.form:
            if 'database' not in current_config:
                current_config['database'] = {}
            current_config['database']['path'] = request.form['db_path']
        
        if 'backup_enabled' in request.form:
            if 'database' not in current_config:
                current_config['database'] = {}
            current_config['database']['backup_enabled'] = request.form.get('backup_enabled') == 'on'
        
        if 'backup_interval' in request.form:
            if 'database' not in current_config:
                current_config['database'] = {}
            current_config['database']['backup_interval'] = int(request.form['backup_interval'])
        
        # Update web settings
        if 'web_host' in request.form:
            if 'web' not in current_config:
                current_config['web'] = {}
            current_config['web']['host'] = request.form['web_host']
        
        if 'web_port' in request.form:
            if 'web' not in current_config:
                current_config['web'] = {}
            current_config['web']['port'] = int(request.form['web_port'])
        
        if 'secret_key' in request.form:
            if 'web' not in current_config:
                current_config['web'] = {}
            current_config['web']['secret_key'] = request.form['secret_key']
        
        if 'max_file_size' in request.form:
            if 'web' not in current_config:
                current_config['web'] = {}
            current_config['web']['max_file_size'] = int(request.form['max_file_size'])
        
        if 'rate_limit' in request.form:
            if 'web' not in current_config:
                current_config['web'] = {}
            current_config['web']['rate_limit'] = int(request.form['rate_limit'])
        
        # Update auth settings
        if 'session_timeout' in request.form:
            if 'auth' not in current_config:
                current_config['auth'] = {}
            # Convert minutes to seconds
            current_config['auth']['session_timeout'] = int(request.form['session_timeout']) * 60
        
        # Update logging settings
        if 'log_level' in request.form:
            if 'logging' not in current_config:
                current_config['logging'] = {}
            current_config['logging']['level'] = request.form['log_level']
        
        if 'log_file' in request.form:
            if 'logging' not in current_config:
                current_config['logging'] = {}
            current_config['logging']['file'] = request.form['log_file']
        
        if 'log_rotation' in request.form:
             if 'logging' not in current_config:
                 current_config['logging'] = {}
             # Set backup_count based on log_rotation checkbox
             current_config['logging']['backup_count'] = 5 if request.form.get('log_rotation') == 'on' else 0
        
        # Save updated config
        with open('/root/discord-indexer/config/config.json', 'w') as f:
            json.dump(current_config, f, indent=4)
        
        flash('Configuration updated successfully!', 'success')
        return redirect(url_for('admin_config'))
    
    except Exception as e:
        flash(f'Error updating configuration: {str(e)}', 'error')
        return redirect(url_for('admin_config'))


# User management routes are defined later in the file

@app.route('/add_user', methods=['POST'])
@login_required
def add_user():
    """Add new user (admin only)"""
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('admin_users'))
    
    username = request.form['username']
    email = request.form.get('email')
    password = request.form['password']
    is_admin = 'is_admin' in request.form
    
    if len(password) < 6:
        flash('Password must be at least 6 characters long', 'error')
        return redirect(url_for('admin_users'))
    
    if user_manager.create_user(username, password, email, is_admin):
        flash(f'User {username} created successfully', 'success')
    else:
        flash('Failed to create user. Username may already exist.', 'error')
    
    return redirect(url_for('admin_users'))

@app.route('/toggle_user_status/<int:user_id>', methods=['POST'])
@login_required
def toggle_user_status(user_id):
    """Toggle user active status (admin only)"""
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('admin_users'))
    
    user_data = user_manager.get_user_by_id(user_id)
    if user_data:
        new_status = not user_data['is_active']
        if user_manager.toggle_user_status(user_id, new_status):
            status_text = 'activated' if new_status else 'deactivated'
            flash(f'User {user_data["username"]} {status_text} successfully', 'success')
        else:
            flash('Failed to update user status', 'error')
    else:
        flash('User not found', 'error')
    
    return redirect(url_for('admin_users'))

@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    """Delete user (admin only)"""
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('admin_users'))
    
    user_data = user_manager.get_user_by_id(user_id)
    if user_data:
        if user_manager.delete_user(user_id):
            flash(f'User {user_data["username"]} deleted successfully', 'success')
        else:
            flash('Failed to delete user', 'error')
    else:
        flash('User not found', 'error')
    
    return redirect(url_for('admin_users'))

@app.route('/toggle_user_admin/<int:user_id>', methods=['POST'])
@login_required
def toggle_user_admin(user_id):
    """Toggle user admin status (admin only)"""
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('admin_users'))
    
    user_data = user_manager.get_user_by_id(user_id)
    if user_data:
        new_admin_status = not user_data['is_admin']
        if user_manager.toggle_user_admin(user_id, new_admin_status):
            status_text = 'granted admin privileges' if new_admin_status else 'removed admin privileges'
            flash(f'User {user_data["username"]} {status_text} successfully', 'success')
        else:
            flash('Failed to update user admin status', 'error')
    else:
        flash('User not found', 'error')
    
    return redirect(url_for('admin_users'))

@app.route('/files')
@login_required
def files():
    """Files listing page"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    file_type = request.args.get('type', '')
    tag_ids = request.args.getlist('tags')
    per_page = 50
    
    # Convert tag_ids to integers if provided
    if tag_ids:
        tag_ids = [int(tag_id) for tag_id in tag_ids if tag_id.isdigit()]
        if not tag_ids:
            tag_ids = None
    else:
        tag_ids = None
    
    files_data, total = db.get_files(page=page, per_page=per_page, search=search, file_type=file_type, tag_ids=tag_ids)
    
    # Get all tags for the filter dropdown
    all_tags = db.get_all_tags()
    
    # Calculate pagination
    total_pages = (total + per_page - 1) // per_page
    
    return render_template('files.html', 
                         files=files_data, 
                         page=page, 
                         total_pages=total_pages, 
                         total=total,
                         search=search,
                         file_type=file_type,
                         all_tags=all_tags,
                         selected_tags=request.args.getlist('tags'))

@app.route('/links')
@login_required
def links():
    """Links listing page"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    domain = request.args.get('domain', '')
    tag_ids = request.args.getlist('tags')
    per_page = 50
    
    # Convert tag_ids to integers if provided
    if tag_ids:
        tag_ids = [int(tag_id) for tag_id in tag_ids if tag_id.isdigit()]
        if not tag_ids:
            tag_ids = None
    else:
        tag_ids = None
    
    links_data, total = db.get_links(page=page, per_page=per_page, search=search, domain=domain, tag_ids=tag_ids)
    
    # Get all tags for the filter dropdown
    all_tags = db.get_all_tags()
    
    # Calculate pagination
    total_pages = (total + per_page - 1) // per_page
    
    return render_template('links.html', 
                         links=links_data, 
                         page=page, 
                         total_pages=total_pages, 
                         total=total,
                         search=search,
                         domain=domain,
                         all_tags=all_tags,
                         selected_tags=request.args.getlist('tags'))



















@app.route('/api/stats')
@login_required
def api_stats():
    """API endpoint for statistics"""
    stats = db.get_stats()
    return jsonify(stats)

@app.route('/api/file/<int:file_id>')
def api_file_details(file_id):
    """API endpoint for file details"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT id, message_id, channel_id, channel_name, guild_id, guild_name, 
                   author_id, author_name, filename, file_url, file_size, file_type, 
                   message_content, timestamp, indexed_at
            FROM indexed_files 
            WHERE id = ?
        ''', (file_id,))
        
        file_data = cursor.fetchone()
        if not file_data:
            return jsonify({'error': 'File not found'}), 404
        
        # Convert to dictionary
        file_details = {
            'id': file_data[0],
            'message_id': file_data[1],
            'channel_id': file_data[2],
            'channel_name': file_data[3],
            'guild_id': file_data[4],
            'guild_name': file_data[5],
            'author_id': file_data[6],
            'author_name': file_data[7],
            'filename': file_data[8],
            'file_url': file_data[9],
            'file_size': file_data[10],
            'file_type': file_data[11],
            'message_content': file_data[12],
            'timestamp': file_data[13],
            'indexed_at': file_data[14]
        }
        
        return jsonify(file_details)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/link/<int:link_id>')
def api_link_details(link_id):
    """API endpoint for link details"""
    conn = db.get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT id, message_id, channel_id, channel_name, guild_id, guild_name,
                   author_id, author_name, link_url, link_domain, message_content, 
                   timestamp, indexed_at
            FROM indexed_links 
            WHERE id = ?
        ''', (link_id,))
        
        link_data = cursor.fetchone()
        if not link_data:
            return jsonify({'error': 'Link not found'}), 404
        
        # Convert to dictionary
        link_details = {
            'id': link_data[0],
            'message_id': link_data[1],
            'channel_id': link_data[2],
            'channel_name': link_data[3],
            'guild_id': link_data[4],
            'guild_name': link_data[5],
            'author_id': link_data[6],
            'author_name': link_data[7],
            'link_url': link_data[8],
            'link_domain': link_data[9],
            'message_content': link_data[10],
            'timestamp': link_data[11],
            'indexed_at': link_data[12]
        }
        
        return jsonify(link_details)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# Tag management routes (admin only)
@app.route('/tags')
@login_required
def manage_tags():
    """Tag management page (admin only)"""
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('dashboard'))
    
    tags = db.get_all_tags()
    return render_template('tags.html', tags=tags)

@app.route('/api/tags', methods=['POST'])
@login_required
def create_tag():
    """Create a new tag (admin only)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    name = data.get('name', '').strip()
    color = data.get('color', '#007bff')
    description = data.get('description', '').strip()
    
    if not name:
        return jsonify({'error': 'Tag name is required'}), 400
    
    tag_id = db.create_tag(name, color, description)
    if tag_id:
        return jsonify({'success': True, 'tag_id': tag_id})
    else:
        return jsonify({'error': 'Failed to create tag'}), 500

@app.route('/api/tags/<int:tag_id>', methods=['PUT'])
@login_required
def update_tag(tag_id):
    """Update a tag (admin only)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    name = data.get('name', '').strip() if data.get('name') else None
    color = data.get('color') if data.get('color') else None
    description = data.get('description', '').strip() if 'description' in data else None
    
    if db.update_tag(tag_id, name, color, description):
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to update tag'}), 500

@app.route('/api/tags/<int:tag_id>', methods=['DELETE'])
@login_required
def delete_tag(tag_id):
    """Delete a tag (admin only)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    if db.delete_tag(tag_id):
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to delete tag'}), 500

@app.route('/api/files/<int:file_id>/tags', methods=['POST'])
@login_required
def add_file_tag(file_id):
    """Add tag to file (admin only)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    tag_id = data.get('tag_id')
    
    if not tag_id:
        return jsonify({'error': 'Tag ID is required'}), 400
    
    if db.add_file_tag(file_id, tag_id):
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to add tag'}), 500

@app.route('/api/files/<int:file_id>/tags/<int:tag_id>', methods=['DELETE'])
@login_required
def remove_file_tag(file_id, tag_id):
    """Remove tag from file (admin only)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    if db.remove_file_tag(file_id, tag_id):
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to remove tag'}), 500

@app.route('/api/links/<int:link_id>/tags', methods=['POST'])
@login_required
def add_link_tag(link_id):
    """Add tag to link (admin only)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    tag_id = data.get('tag_id')
    
    if not tag_id:
        return jsonify({'error': 'Tag ID is required'}), 400
    
    if db.add_link_tag(link_id, tag_id):
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to add tag'}), 500

@app.route('/api/links/<int:link_id>/tags/<int:tag_id>', methods=['DELETE'])
@login_required
def remove_link_tag(link_id, tag_id):
    """Remove tag from link (admin only)"""
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    if db.remove_link_tag(link_id, tag_id):
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Failed to remove tag'}), 500

@app.route('/api/files/<int:file_id>/tags')
@login_required
def get_file_tags(file_id):
    """Get tags for a file"""
    tags_raw = db.get_file_tags(file_id)
    # Convert tuples to dictionaries for consistent API response
    tags = [{
        'id': tag[0],
        'name': tag[1],
        'color': tag[2],
        'description': tag[3]
    } for tag in tags_raw]
    return jsonify({'tags': tags})

@app.route('/api/links/<int:link_id>/tags')
@login_required
def get_link_tags(link_id):
    """Get tags for a link"""
    tags_raw = db.get_link_tags(link_id)
    # Convert tuples to dictionaries for consistent API response
    tags = [{
        'id': tag[0],
        'name': tag[1],
        'color': tag[2],
        'description': tag[3]
    } for tag in tags_raw]
    return jsonify({'tags': tags})

@app.route('/terms')
def terms_of_service():
    """Terms of Service page"""
    return render_template('terms.html')

@app.route('/privacy')
def privacy_policy():
    """Privacy Policy page"""
    return render_template('privacy.html')

@app.route('/document_viewer/<int:file_id>')
@login_required
def document_viewer(file_id):
    """Render document viewer page"""
    try:
        # Get file information from database
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT filename, file_url, file_type, file_size
            FROM indexed_files
            WHERE id = ?
        ''', (file_id,))
        file_data = cursor.fetchone()
        conn.close()
        
        if not file_data:
            flash('File not found', 'error')
            return redirect(url_for('files'))
            
        filename, file_url, file_type, file_size = file_data
        
        # Check if this is a document type that can be viewed
        viewer_supported_types = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-powerpoint',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'text/plain',
            'application/rtf',
            'image/png',
            'image/jpeg',
            'image/jpg',
            'image/gif',
            'image/bmp',
            'image/webp',
            'image/svg+xml'
        ]
        
        if file_type not in viewer_supported_types:
            flash('Document viewer not supported for this file type', 'error')
            return redirect(url_for('files'))
        
        # Check for embedded mode and search parameters
        embedded = request.args.get('embedded', 'false').lower() == 'true'
        search_query = request.args.get('search', '')
        
        return render_template('document_viewer.html', 
                             file_id=file_id,
                             filename=filename,
                             file_type=file_type,
                             file_size=file_size,
                             embedded=embedded,
                             search_query=search_query)
        
    except Exception as e:
        app.logger.error(f"Error in document_viewer for file {file_id}: {str(e)}")
        flash('Error loading document viewer', 'error')
        return redirect(url_for('files'))

@app.route('/api/document_pages/<int:file_id>')
@login_required
def api_document_pages(file_id):
    """Get document pages as images for viewer"""
    try:
        # Get file information from database
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT filename, file_url, file_type FROM indexed_files WHERE id = ?', (file_id,))
        file_data = cursor.fetchone()
        conn.close()
        
        if not file_data:
            return jsonify({'error': 'File not found'}), 404
            
        filename, file_url, file_type = file_data
        
        # Download the file temporarily
        response = requests.get(file_url)
        if response.status_code != 200:
            return jsonify({'error': 'Could not download file'}), 400
            
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as temp_file:
            temp_file.write(response.content)
            temp_file_path = temp_file.name
            
        try:
            pages = []
            
            if file_type.startswith('image/'):
                # Handle image files directly
                try:
                    import base64
                    with open(temp_file_path, 'rb') as img_file:
                        img_data = img_file.read()
                    img_base64 = base64.b64encode(img_data).decode('utf-8')
                    
                    # Determine the correct MIME type for the data URL
                    mime_type = file_type
                    pages.append({
                        'page_number': 1,
                        'image_data': f'data:{mime_type};base64,{img_base64}',
                        'is_text': False
                    })
                except Exception as e:
                    return jsonify({'error': f'Error processing image: {str(e)}'}), 500
                    
            elif file_type == 'application/pdf':
                # Handle PDF files with pdf2image
                try:
                    images = convert_from_path(temp_file_path, dpi=150)
                    for i, image in enumerate(images[:20]):  # Limit to first 20 pages
                        img_io = io.BytesIO()
                        image.save(img_io, 'JPEG', quality=85)
                        img_io.seek(0)
                        
                        # Convert to base64 for JSON response
                        import base64
                        img_base64 = base64.b64encode(img_io.getvalue()).decode('utf-8')
                        pages.append({
                            'page_number': i + 1,
                            'image_data': f'data:image/jpeg;base64,{img_base64}'
                        })
                except Exception as e:
                    return jsonify({'error': f'Error converting PDF: {str(e)}'}), 500
                    
            elif file_type in ['application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
                # Handle Word documents by converting to PDF first, then to images
                try:
                    # Use LibreOffice to convert to PDF
                    pdf_path = temp_file_path + '.pdf'
                    result = subprocess.run([
                        'libreoffice', '--headless', '--convert-to', 'pdf',
                        '--outdir', os.path.dirname(temp_file_path), temp_file_path
                    ], capture_output=True, text=True, timeout=30)
                    
                    if result.returncode == 0 and os.path.exists(pdf_path):
                        images = convert_from_path(pdf_path, dpi=150)
                        for i, image in enumerate(images[:20]):
                            img_io = io.BytesIO()
                            image.save(img_io, 'JPEG', quality=85)
                            img_io.seek(0)
                            
                            import base64
                            img_base64 = base64.b64encode(img_io.getvalue()).decode('utf-8')
                            pages.append({
                                'page_number': i + 1,
                                'image_data': f'data:image/jpeg;base64,{img_base64}'
                            })
                        os.unlink(pdf_path)
                except Exception as e:
                    return jsonify({'error': f'Error converting document: {str(e)}'}), 500
                    
            elif file_type == 'text/plain':
                # Handle text files by creating paginated text view
                try:
                    with open(temp_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    # Split content into pages (approximately 3000 characters per page)
                    page_size = 3000
                    for i in range(0, len(content), page_size):
                        page_content = content[i:i + page_size]
                        pages.append({
                            'page_number': (i // page_size) + 1,
                            'text_content': page_content,
                            'is_text': True
                        })
                        if len(pages) >= 20:  # Limit to 20 pages
                            break
                except Exception as e:
                    return jsonify({'error': f'Error reading text file: {str(e)}'}), 500
            
            return jsonify({
                'pages': pages,
                'total_pages': len(pages),
                'filename': filename,
                'file_type': file_type
            })
                
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except Exception as e:
        app.logger.error(f"Error in api_document_pages for file {file_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/preview/<int:file_id>')
@login_required
def preview_file(file_id):
    """Generate and serve a preview image for documents"""
    try:
        # Get file information from database
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT filename, file_url, file_type FROM indexed_files WHERE id = ?', (file_id,))
        file_data = cursor.fetchone()
        conn.close()
        
        if not file_data:
            return "File not found", 404
            
        filename, file_url, file_type = file_data
        
        # Check if this is a document type that can be previewed
        preview_supported_types = [
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-powerpoint',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'text/plain',
            'application/rtf'
        ]
        
        if file_type not in preview_supported_types:
            return "Preview not supported for this file type", 400
            
        # Download the file temporarily
        response = requests.get(file_url)
        if response.status_code != 200:
            return "Could not download file", 400
            
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as temp_file:
            temp_file.write(response.content)
            temp_file_path = temp_file.name
            
        try:
            preview_image = None
            
            if file_type == 'application/pdf':
                # Handle PDF files with pdf2image
                try:
                    images = convert_from_path(temp_file_path, first_page=1, last_page=1, dpi=150)
                    if images:
                        preview_image = images[0]
                except Exception as e:
                    logging.error(f"Error converting PDF to image: {str(e)}")
                    return "Error generating PDF preview", 500
                    
            elif file_type in ['application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                             'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                             'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation']:
                # Handle Office documents by converting to PDF first, then to image
                try:
                    # Convert to PDF using LibreOffice
                    with tempfile.TemporaryDirectory() as temp_dir:
                        result = subprocess.run([
                            'libreoffice', '--headless', '--convert-to', 'pdf',
                            '--outdir', temp_dir, temp_file_path
                        ], capture_output=True, text=True, timeout=30)
                        
                        if result.returncode == 0:
                            # Find the generated PDF
                            pdf_name = os.path.splitext(os.path.basename(temp_file_path))[0] + '.pdf'
                            pdf_path = os.path.join(temp_dir, pdf_name)
                            
                            if os.path.exists(pdf_path):
                                # Convert PDF to image
                                images = convert_from_path(pdf_path, first_page=1, last_page=1, dpi=150)
                                if images:
                                    preview_image = images[0]
                        else:
                            logging.error(f"LibreOffice conversion failed: {result.stderr}")
                            return "Error converting document to preview", 500
                except subprocess.TimeoutExpired:
                    return "Document conversion timeout", 500
                except Exception as e:
                    logging.error(f"Error converting document: {str(e)}")
                    return "Error generating document preview", 500
                    
            elif file_type == 'text/plain':
                # Handle text files by creating a simple image
                try:
                    with open(temp_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(2000)  # Read first 2000 characters
                    
                    # Create a simple text preview image
                    from PIL import Image, ImageDraw, ImageFont
                    
                    img_width, img_height = 800, 600
                    preview_image = Image.new('RGB', (img_width, img_height), color='white')
                    draw = ImageDraw.Draw(preview_image)
                    
                    try:
                        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 12)
                    except:
                        font = ImageFont.load_default()
                    
                    # Split content into lines and draw
                    lines = content.split('\n')[:40]  # First 40 lines
                    y_offset = 10
                    for line in lines:
                        if y_offset > img_height - 20:
                            break
                        draw.text((10, y_offset), line[:100], fill='black', font=font)  # First 100 chars per line
                        y_offset += 15
                        
                except Exception as e:
                    logging.error(f"Error creating text preview: {str(e)}")
                    return "Error generating text preview", 500
            
            if preview_image:
                # Convert PIL image to JPEG and return
                img_io = io.BytesIO()
                preview_image.save(img_io, 'JPEG', quality=85)
                img_io.seek(0)
                
                return send_file(
                    img_io,
                    mimetype='image/jpeg',
                    as_attachment=False
                )
            else:
                return "Could not generate preview", 500
                
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except Exception as e:
        logging.error(f"Error in preview_file for file {file_id}: {str(e)}")
        return "Internal server error", 500


if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    # Create static directory if it doesn't exist
    if not os.path.exists('static'):
        os.makedirs('static')
    
    app.run(
        host=config['web']['host'],
        port=config['web']['port'],
        debug=config['web']['debug']
    )