# Discord Indexer Bot & Web Interface

A comprehensive Discord bot that automatically indexes all attachments and links posted in your Discord server, with a beautiful web interface for browsing and searching the indexed content.

## 🚀 Quick Start

### 1. Get Your Discord Bot Token
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application or use an existing one
3. Go to the "Bot" section
4. Copy the bot token
5. Invite the bot to your server with appropriate permissions

### 2. Configure the Bot
Edit `config.json` and update:
```json
{
  "token": "your_actual_bot_token_here",
  "username": "your_username",
  "password": "your_secure_password"
}
```

### 3. Start Everything
```bash
./quick_start.sh
```

That's it! Your Discord indexer is now running.

## 🌐 Access Your Web Interface

- **Local**: http://localhost:5000
- **Public**: http://lettner.tech:5000 (or your domain)
- **Default Login**: admin / admin123 (change this!)

## 🤖 Discord Commands

- `/stats` - Display indexing statistics
- `/index` - Perform full historical indexing of all channels

## 📁 Project Structure

```
discord-indexer/
├── bot.py                          # Discord bot main script
├── web_app.py                      # Flask web application
├── setup_db.py                     # Database initialization
├── config.json                     # Configuration file
├── indexer.db                      # SQLite database
├── quick_start.sh                  # Quick setup script
├── install.sh                      # Full installation script
├── SETUP_GUIDE.md                  # Detailed setup guide
├── templates/                      # HTML templates
│   ├── base.html
│   ├── dashboard.html
│   ├── files.html
│   ├── links.html
│   └── login.html
├── discord-indexer-bot.service     # Systemd service for bot
├── discord-indexer-web.service     # Systemd service for web app
└── venv/                           # Python virtual environment
```

## 🔧 Management Commands

### View Logs
```bash
# Bot logs
sudo journalctl -u discord-indexer-bot -f

# Web app logs
sudo journalctl -u discord-indexer-web -f
```

### Restart Services
```bash
# Restart bot
sudo systemctl restart discord-indexer-bot

# Restart web app
sudo systemctl restart discord-indexer-web

# Restart both
sudo systemctl restart discord-indexer-bot discord-indexer-web
```

### Check Status
```bash
# Check bot status
sudo systemctl status discord-indexer-bot

# Check web app status
sudo systemctl status discord-indexer-web
```

## 🔒 Security Setup (Recommended)

### 1. Change Default Credentials
Edit `config.json` and change the default username/password.

### 2. Setup HTTPS with Let's Encrypt
```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d lettner.tech
```

### 3. Configure Firewall
```bash
# Install UFW
sudo apt install ufw

# Allow SSH, HTTP, and HTTPS
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

## 📊 Features

### Discord Bot
- ✅ Automatic indexing of new attachments and links
- ✅ Historical indexing with `/index` command
- ✅ Statistics display with `/stats` command
- ✅ Comprehensive logging
- ✅ Systemd service integration

### Web Interface
- ✅ User authentication with remember me
- ✅ Dashboard with statistics and charts
- ✅ File browser with search and filtering
- ✅ Link browser with search and filtering
- ✅ Responsive design with Bootstrap
- ✅ Pagination for large datasets
- ✅ File type and domain statistics

### Database
- ✅ SQLite database for reliability
- ✅ Indexed columns for performance
- ✅ Automatic backups
- ✅ Statistics tracking

## 🛠️ Troubleshooting

### Bot Not Responding
1. Check if the bot is online in Discord
2. Verify the token in `config.json`
3. Check bot permissions in your server
4. View logs: `sudo journalctl -u discord-indexer-bot -f`

### Web Interface Not Accessible
1. Check if the service is running: `sudo systemctl status discord-indexer-web`
2. Verify port 5000 is not blocked by firewall
3. Check logs: `sudo journalctl -u discord-indexer-web -f`

### Database Issues
1. Check if `indexer.db` exists and is writable
2. Re-run database setup: `./setup_db.py`
3. Check disk space: `df -h`

## 📚 Additional Resources

- **Detailed Setup Guide**: See `SETUP_GUIDE.md`
- **Installation Script**: Use `install.sh` for fresh installations
- **Discord.py Documentation**: https://discordpy.readthedocs.io/
- **Flask Documentation**: https://flask.palletsprojects.com/

## 🎯 Next Steps

1. **Configure your bot token** in `config.json`
2. **Run the quick start script**: `./quick_start.sh`
3. **Access the web interface** and change default credentials
4. **Set up HTTPS** for production use
5. **Configure backups** and monitoring

---

**Enjoy your Discord indexer!** 🎉

For support or questions, check the logs first, then refer to the troubleshooting section in `SETUP_GUIDE.md`.