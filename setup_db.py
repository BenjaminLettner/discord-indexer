#!/usr/bin/env python3

import sqlite3
import json
import os
from datetime import datetime

def load_config():
    """Load configuration from config.json"""
    with open('config.json', 'r') as f:
        return json.load(f)

def setup_database():
    """Initialize the SQLite database with required tables"""
    config = load_config()
    db_path = config['database']['path']
    
    # Create database connection
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create indexed_files table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS indexed_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            channel_name TEXT,
            guild_id TEXT,
            guild_name TEXT,
            author_id TEXT NOT NULL,
            author_name TEXT,
            filename TEXT NOT NULL,
            file_url TEXT NOT NULL,
            file_size INTEGER,
            file_type TEXT,
            message_content TEXT,
            timestamp DATETIME NOT NULL,
            indexed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(message_id, file_url)
        )
    ''')
    
    # Create indexed_links table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS indexed_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            channel_name TEXT,
            guild_id TEXT,
            guild_name TEXT,
            author_id TEXT NOT NULL,
            author_name TEXT,
            link_url TEXT NOT NULL,
            link_domain TEXT,
            message_content TEXT,
            timestamp DATETIME NOT NULL,
            indexed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(message_id, link_url)
        )
    ''')
    
    # Create indexing_stats table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS indexing_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation_type TEXT NOT NULL,
            channel_id TEXT,
            channel_name TEXT,
            messages_processed INTEGER DEFAULT 0,
            files_indexed INTEGER DEFAULT 0,
            links_indexed INTEGER DEFAULT 0,
            started_at DATETIME NOT NULL,
            completed_at DATETIME,
            status TEXT DEFAULT 'running'
        )
    ''')
    
    # Create tags table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(50) UNIQUE NOT NULL,
            color VARCHAR(7) DEFAULT '#007bff',
            description TEXT,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create file_tags table (many-to-many relationship)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS file_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            added_by INTEGER,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (file_id) REFERENCES indexed_files (id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE,
            UNIQUE(file_id, tag_id)
        )
    ''')
    
    # Create link_tags table (many-to-many relationship)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS link_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            link_id INTEGER NOT NULL,
            tag_id INTEGER NOT NULL,
            added_by INTEGER,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (link_id) REFERENCES indexed_links (id) ON DELETE CASCADE,
            FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE,
            UNIQUE(link_id, tag_id)
        )
    ''')

    # Create indexes for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_channel ON indexed_files(channel_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_author ON indexed_files(author_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_timestamp ON indexed_files(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_links_channel ON indexed_links(channel_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_links_author ON indexed_links(author_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_links_timestamp ON indexed_links(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_tags_file ON file_tags(file_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_file_tags_tag ON file_tags(tag_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_link_tags_link ON link_tags(link_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_link_tags_tag ON link_tags(tag_id)')
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print(f"Database initialized successfully at {db_path}")
    print("Tables created:")
    print("- indexed_files")
    print("- indexed_links")
    print("- indexing_stats")
    print("- tags")
    print("- file_tags")
    print("- link_tags")

if __name__ == '__main__':
    if not os.path.exists('config.json'):
        print("Error: config.json not found. Please create it first.")
        exit(1)
    
    setup_database()