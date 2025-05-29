#!/usr/bin/env python3

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import sqlite3
import json
import hashlib
from datetime import datetime, timedelta
import os
from urllib.parse import urlparse
import logging
from user_manager import UserManager

# Load configuration
with open('config.json', 'r') as f:
    config = json.load(f)

app = Flask(__name__)
app.secret_key = config['web']['secret_key']

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
    
    @property
    def is_active(self):
        return self._is_active

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def get_files(self, page=1, per_page=50, search=None, file_type=None):
        """Get paginated files with optional search and filtering"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Build query
            query = '''
                SELECT id, message_id, channel_name, guild_name, author_name, 
                       filename, file_url, file_size, file_type, message_content, 
                       timestamp, indexed_at
                FROM indexed_files
            '''
            
            conditions = []
            params = []
            
            if search:
                conditions.append('(filename LIKE ? OR message_content LIKE ? OR author_name LIKE ?)')
                search_param = f'%{search}%'
                params.extend([search_param, search_param, search_param])
            
            if file_type:
                conditions.append('file_type LIKE ?')
                params.append(f'%{file_type}%')
            
            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)
            
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
            
            return files, total
        except Exception as e:
            print(f"Error getting files: {e}")
            return [], 0
        finally:
            conn.close()
    
    def get_links(self, page=1, per_page=50, search=None, domain=None):
        """Get paginated links with optional search and filtering"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            query = '''
                SELECT id, message_id, channel_name, guild_name, author_name, 
                       link_url, link_domain, message_content, timestamp, indexed_at
                FROM indexed_links
            '''
            
            conditions = []
            params = []
            
            if search:
                conditions.append('(link_url LIKE ? OR message_content LIKE ? OR author_name LIKE ?)')
                search_param = f'%{search}%'
                params.extend([search_param, search_param, search_param])
            
            if domain:
                conditions.append('link_domain LIKE ?')
                params.append(f'%{domain}%')
            
            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)
            
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
            
            return links, total
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
    
    return render_template('login.html')

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
    users = []
    if current_user.is_admin:
        users = user_manager.get_all_users()
    return render_template('profile.html', users=users)

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

@app.route('/add_user', methods=['POST'])
@login_required
def add_user():
    """Add new user (admin only)"""
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('profile'))
    
    username = request.form['username']
    email = request.form.get('email')
    password = request.form['password']
    is_admin = 'is_admin' in request.form
    
    if len(password) < 6:
        flash('Password must be at least 6 characters long', 'error')
        return redirect(url_for('profile'))
    
    if user_manager.create_user(username, password, email, is_admin):
        flash(f'User {username} created successfully', 'success')
    else:
        flash('Failed to create user. Username may already exist.', 'error')
    
    return redirect(url_for('profile'))

@app.route('/toggle_user_status/<int:user_id>', methods=['POST'])
@login_required
def toggle_user_status(user_id):
    """Toggle user active status (admin only)"""
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('profile'))
    
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
    
    return redirect(url_for('profile'))

@app.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    """Delete user (admin only)"""
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('profile'))
    
    user_data = user_manager.get_user_by_id(user_id)
    if user_data:
        if user_manager.delete_user(user_id):
            flash(f'User {user_data["username"]} deleted successfully', 'success')
        else:
            flash('Failed to delete user', 'error')
    else:
        flash('User not found', 'error')
    
    return redirect(url_for('profile'))

@app.route('/files')
@login_required
def files():
    """Files listing page"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    file_type = request.args.get('type', '')
    per_page = 50
    
    files_data, total = db.get_files(page=page, per_page=per_page, search=search, file_type=file_type)
    
    # Calculate pagination
    total_pages = (total + per_page - 1) // per_page
    
    return render_template('files.html', 
                         files=files_data, 
                         page=page, 
                         total_pages=total_pages, 
                         total=total,
                         search=search,
                         file_type=file_type)

@app.route('/links')
@login_required
def links():
    """Links listing page"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    domain = request.args.get('domain', '')
    per_page = 50
    
    links_data, total = db.get_links(page=page, per_page=per_page, search=search, domain=domain)
    
    # Calculate pagination
    total_pages = (total + per_page - 1) // per_page
    
    return render_template('links.html', 
                         links=links_data, 
                         page=page, 
                         total_pages=total_pages, 
                         total=total,
                         search=search,
                         domain=domain)

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

@app.route('/terms')
def terms_of_service():
    """Terms of Service page"""
    return render_template('terms.html')

@app.route('/privacy')
def privacy_policy():
    """Privacy Policy page"""
    return render_template('privacy.html')

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