# Discord Indexer Project Summary

**Discord Indexer** is a comprehensive Discord bot that automatically indexes all attachments and links posted in Discord servers, providing a powerful web interface for browsing and searching indexed content.

## 🎯 What It Does

- **Automatic Indexing**: Monitors Discord channels and automatically indexes all file attachments and links shared in messages
- **File Content Extraction**: Downloads and extracts text content from various file formats (PDFs, Office documents, text files, code files)
- **Search Functionality**: Provides text-based search capabilities for finding indexed content
- **Web Interface**: Provides a beautiful Flask-based web dashboard for browsing, searching, and viewing indexed content
- **User Management**: Includes authentication system with Discord OAuth2 integration
- **Real-time Processing**: Processes new content immediately as it's posted to Discord

## 🛠️ Tech Stack

### Backend
- **Python 3** - Core programming language
- **Discord.py** - Discord bot framework
- **Flask** - Web framework for the dashboard
- **SQLite** - Database for storing indexed content
- **aiohttp** - Async HTTP client for file downloads

### Search
- **SQLite FTS** - Full-text search capabilities for content searching

### File Processing
- **preview-generator** - Multi-format file content extraction
- **pdf2image** - PDF to image conversion
- **PIL (Pillow)** - Image processing

### Web & Auth
- **Flask-Login** - User session management
- **Flask-WTF** - Form handling and CSRF protection
- **Werkzeug** - WSGI utilities
- **Discord OAuth2** - Authentication via Discord

## 🏗️ Architecture

- **Discord Bot** (`bot.py`) - Monitors channels and indexes content in real-time
- **Web Application** (`web_app.py`) - Serves the dashboard and search interface
- **Search Manager** - Handles text-based search functionality
- **File Content Indexer** - Downloads and extracts text from various file formats
- **User Manager** - Handles authentication and user permissions

The system runs as two main processes: the Discord bot for real-time indexing and the Flask web server for the user interface, both sharing a common SQLite database.

## 📊 Database Schema

The system uses SQLite with the following main tables:
- `indexed_files` - Stores file attachments metadata
- `indexed_links` - Stores shared links metadata

- `indexing_stats` - Tracks indexing operations
- `users` - User management and authentication

## 🚀 Key Features

1. **Real-time Indexing**: Automatically processes new Discord messages
2. **Text Search**: Full-text search capabilities for finding content
3. **File Management**: Handles various file types and attachments
4. **Web Dashboard**: Beautiful interface for browsing and searching
5. **Discord Integration**: OAuth2 login and bot commands
6. **Document Viewing**: In-browser document viewing
8. **Statistics Tracking**: Monitor indexing performance

## 📁 Project Structure

```
discord-indexer/
├── bot.py                    # Discord bot main file
├── web_app.py               # Flask web application
├── search_manager.py        # Search functionality

├── discord_auth.py          # Discord OAuth2 integration
├── user_manager.py          # User management system
├── templates/               # HTML templates
├── static/                  # Static web assets
├── requirements.txt         # Python dependencies
└── *.sh                     # Management scripts
```

## 🔧 Management Scripts

- `start_apps.sh` - Start both bot and web app
- `start_apps.sh` - Start the Discord indexer services
- `stop_apps.sh` - Stop all services
- `status_apps.sh` - Check service status
- `update_search.sh` - Update search indexes
- `backup.sh` - Database backup utility

This project demonstrates a modern approach to Discord content management, combining real-time processing, AI-powered search, and a user-friendly web interface.