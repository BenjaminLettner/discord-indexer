#!/bin/bash

# Discord Indexer Installation Script
# This script sets up the Discord bot and web interface on your VPS

set -e  # Exit on any error

echo "🤖 Discord Indexer Installation Script"
echo "======================================"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run this script as root (use sudo)"
    exit 1
fi

# Update system packages
echo "📦 Updating system packages..."
apt update && apt upgrade -y

# Install Python and pip if not already installed
echo "🐍 Installing Python dependencies..."
apt install -y python3 python3-pip python3-venv

# Install system dependencies
echo "📚 Installing system dependencies..."
apt install -y git curl wget nginx certbot python3-certbot-nginx

# Create virtual environment
echo "🔧 Setting up Python virtual environment..."
cd /root/discord-indexer
python3 -m venv venv
source venv/bin/activate

# Install Python packages
echo "📦 Installing Python packages..."
pip install --upgrade pip
pip install discord.py==2.3.2
pip install Flask==2.3.3
pip install Flask-Login==0.6.3
pip install Flask-WTF==1.1.1
pip install WTForms==3.0.1
pip install requests==2.31.0
pip install werkzeug==2.3.7

# Make scripts executable
echo "🔐 Setting permissions..."
chmod +x src/bot.py
chmod +x src/web_app.py
chmod +x setup_db.py
chmod +x install.sh

# Initialize database
echo "🗄️ Setting up database..."
python3 setup_db.py

# Copy systemd service files
echo "⚙️ Installing systemd services..."
cp discord-indexer-bot.service /etc/systemd/system/
cp discord-indexer-web.service /etc/systemd/system/

# Reload systemd and enable services
systemctl daemon-reload
systemctl enable discord-indexer-bot.service
systemctl enable discord-indexer-web.service

# Create nginx configuration
echo "🌐 Setting up Nginx..."
cat > /etc/nginx/sites-available/discord-indexer << 'EOF'
server {
    listen 80;
    server_name lettner.tech www.lettner.tech;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
}
EOF

# Enable nginx site
ln -sf /etc/nginx/sites-available/discord-indexer /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx

# Create log rotation
echo "📝 Setting up log rotation..."
cat > /etc/logrotate.d/discord-indexer << 'EOF'
/root/discord-indexer/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 root root
    postrotate
        systemctl reload discord-indexer-bot.service
        systemctl reload discord-indexer-web.service
    endscript
}
EOF

# Create backup script
echo "💾 Creating backup script..."
cat > /root/discord-indexer/backup.sh << 'EOF'
#!/bin/bash
# Backup script for Discord Indexer

BACKUP_DIR="/root/discord-indexer-backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
cp /root/discord-indexer/indexer.db $BACKUP_DIR/indexer_$DATE.db

# Backup configuration
cp /root/discord-indexer/config/config.json $BACKUP_DIR/config_$DATE.json

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.db" -mtime +7 -delete
find $BACKUP_DIR -name "*.json" -mtime +7 -delete

echo "Backup completed: $DATE"
EOF

chmod +x /root/discord-indexer/backup.sh

# Add backup to crontab
echo "⏰ Setting up automated backups..."
(crontab -l 2>/dev/null; echo "0 2 * * * /root/discord-indexer/backup.sh >> /var/log/discord-indexer-backup.log 2>&1") | crontab -

echo ""
echo "✅ Installation completed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Edit /root/discord-indexer/config/config.json and add your Discord bot token"
echo "2. Change the default username/password in config/config.json"
echo "3. Start the services:"
echo "   systemctl start discord-indexer-bot"
echo "   systemctl start discord-indexer-web"
echo "4. Check service status:"
echo "   systemctl status discord-indexer-bot"
echo "   systemctl status discord-indexer-web"
echo "5. Set up SSL certificate:"
echo "   certbot --nginx -d lettner.tech -d www.lettner.tech"
echo ""
echo "🌐 Web interface will be available at: http://lettner.tech"
echo "📊 Default login: admin / admin123 (change this!)"
echo ""
echo "📝 Logs can be viewed with:"
echo "   journalctl -u discord-indexer-bot -f"
echo "   journalctl -u discord-indexer-web -f"
echo ""
echo "💾 Automatic backups are scheduled daily at 2 AM"
echo "📁 Backups location: /root/discord-indexer-backups"