#!/bin/bash

# Discord Indexer Quick Start Script
# This script helps you configure and start the Discord indexer

set -e

echo "🤖 Discord Indexer Quick Start"
echo "=============================="

# Check if config is already set up
if grep -q "YOUR_DISCORD_BOT_TOKEN_HERE" config.json; then
    echo "⚠️  Configuration needed!"
    echo ""
    echo "Please follow these steps:"
    echo "1. Get your Discord bot token from https://discord.com/developers/applications"
    echo "2. Edit config.json and replace 'YOUR_DISCORD_BOT_TOKEN_HERE' with your actual token"
    echo "3. Change the default username and password in config.json"
    echo "4. Run this script again"
    echo ""
    echo "Example config.json changes:"
    echo '  "token": "your_actual_bot_token_here"'
    echo '  "username": "your_username"'
    echo '  "password": "your_secure_password"'
    echo ""
    exit 1
fi

echo "✅ Configuration looks good!"
echo ""

# Copy systemd service files
echo "📋 Installing systemd services..."
sudo cp discord-indexer-bot.service /etc/systemd/system/
sudo cp discord-indexer-web.service /etc/systemd/system/
sudo systemctl daemon-reload

# Enable services
echo "🔧 Enabling services..."
sudo systemctl enable discord-indexer-bot.service
sudo systemctl enable discord-indexer-web.service

# Start services
echo "🚀 Starting services..."
sudo systemctl start discord-indexer-bot.service
sudo systemctl start discord-indexer-web.service

# Wait a moment for services to start
sleep 3

# Check service status
echo ""
echo "📊 Service Status:"
echo "=================="
echo "Bot Service:"
sudo systemctl status discord-indexer-bot.service --no-pager -l
echo ""
echo "Web Service:"
sudo systemctl status discord-indexer-web.service --no-pager -l

echo ""
echo "✅ Setup complete!"
echo ""
echo "🌐 Your web interface should be available at:"
echo "   http://$(curl -s ifconfig.me):5000"
echo "   or http://lettner.tech:5000 (if DNS is configured)"
echo ""
echo "📋 Default login credentials:"
echo "   Username: admin"
echo "   Password: admin123"
echo "   (Change these in config.json!)"
echo ""
echo "📝 To view logs:"
echo "   Bot logs: sudo journalctl -u discord-indexer-bot -f"
echo "   Web logs: sudo journalctl -u discord-indexer-web -f"
echo ""
echo "🔧 To restart services:"
echo "   sudo systemctl restart discord-indexer-bot"
echo "   sudo systemctl restart discord-indexer-web"
echo ""
echo "📚 For full setup including HTTPS, see SETUP_GUIDE.md"