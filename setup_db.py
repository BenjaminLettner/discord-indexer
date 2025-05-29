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
    
    # Create indexes for better performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_channel ON indexed_files(channel_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_author ON indexed_files(author_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_files_timestamp ON indexed_files(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_links_channel ON indexed_links(channel_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_links_author ON indexed_links(author_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_links_timestamp ON indexed_links(timestamp)')
    
    # Commit changes and close connection
    conn.commit()
    conn.close()
    
    print(f"Database initialized successfully at {db_path}")
    print("Tables created:")
    print("- indexed_files")
    print("- indexed_links")
    print("- indexing_stats")

if __name__ == '__main__':
    if not os.path.exists('config.json'):
        print("Error: config.json not found. Please create it first.")
        exit(1)
    
    setup_database()