# Discord Indexer Setup Guide

This guide will walk you through setting up the Discord Indexer bot and web interface on your VPS with domain `lettner.tech`.

## Prerequisites

- VPS with Ubuntu/Debian Linux
- Root access to the server
- Domain `lettner.tech` pointing to your VPS IP
- Discord bot token (see Discord Bot Setup section)

## Step 1: Discord Bot Setup

### Create Discord Application
1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name (e.g., "Content Indexer")
3. Go to the "Bot" section
4. Click "Add Bot"
5. Copy the bot token (you'll need this later)
6. Enable the following bot permissions:
   - Read Messages/View Channels
   - Read Message History
   - Use Slash Commands

### Invite Bot to Server
1. Go to the "OAuth2" > "URL Generator" section
2. Select scopes: `bot` and `applications.commands`
3. Select bot permissions:
   - Read Messages/View Channels
   - Read Message History
   - Use Slash Commands
4. Copy the generated URL and open it in your browser
5. Select your Discord server and authorize the bot

## Step 2: Server Setup

### Run the Installation Script
```bash
# Make the install script executable
chmod +x /root/discord-indexer/install.sh

# Run the installation
sudo /root/discord-indexer/install.sh
```

The script will:
- Update system packages
- Install Python dependencies
- Set up the database
- Configure systemd services
- Set up Nginx reverse proxy
- Configure log rotation and backups

## Step 3: Configuration

### Configure the Bot
Edit the configuration file:
```bash
nano /root/discord-indexer/config.json
```

Update the following settings:
```json
{
  "discord": {
    "token": "YOUR_ACTUAL_BOT_TOKEN_HERE",
    "guild_id": null,
    "command_prefix": "/"
  },
  "web": {
    "host": "0.0.0.0",
    "port": 5000,
    "secret_key": "change-this-to-a-random-secret-key",
    "debug": false
  },
  "auth": {
    "username": "your_username",
    "password": "your_secure_password",
    "session_timeout": 86400
  }
}
```

**Important Security Notes:**
- Replace `YOUR_ACTUAL_BOT_TOKEN_HERE` with your Discord bot token
- Change the default username and password
- Generate a random secret key for the web interface
- Keep the config.json file secure (it contains sensitive information)

## Step 4: Start Services

### Start the Discord Bot
```bash
systemctl start discord-indexer-bot
systemctl status discord-indexer-bot
```

### Start the Web Interface
```bash
systemctl start discord-indexer-web
systemctl status discord-indexer-web
```

### Enable Auto-start on Boot
```bash
systemctl enable discord-indexer-bot
systemctl enable discord-indexer-web
```

## Step 5: SSL Certificate (HTTPS)

Set up free SSL certificate with Let's Encrypt:
```bash
certbot --nginx -d lettner.tech -d www.lettner.tech
```

Follow the prompts to:
- Enter your email address
- Agree to terms of service
- Choose whether to share email with EFF
- Select option 2 to redirect HTTP to HTTPS

## Step 6: Firewall Configuration

Configure UFW firewall:
```bash
# Enable UFW
ufw enable

# Allow SSH
ufw allow ssh

# Allow HTTP and HTTPS
ufw allow 80
ufw allow 443

# Check status
ufw status
```

## Step 7: Test the Setup

### Test Discord Bot
1. Go to your Discord server
2. Type `/stats` to see if the bot responds
3. Type `/index` to start indexing (this may take a while for large servers)

### Test Web Interface
1. Open your browser and go to `https://lettner.tech`
2. Log in with your configured username and password
3. Check the dashboard for statistics
4. Browse files and links sections

## Monitoring and Maintenance

### View Logs
```bash
# Bot logs
journalctl -u discord-indexer-bot -f

# Web interface logs
journalctl -u discord-indexer-web -f

# Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### Manual Backup
```bash
/root/discord-indexer/backup.sh
```

### Restart Services
```bash
# Restart bot
systemctl restart discord-indexer-bot

# Restart web interface
systemctl restart discord-indexer-web

# Restart nginx
systemctl restart nginx
```

### Update the Application
```bash
# Stop services
systemctl stop discord-indexer-bot
systemctl stop discord-indexer-web

# Backup current installation
cp -r /root/discord-indexer /root/discord-indexer-backup-$(date +%Y%m%d)

# Update code (if you have changes)
# ... make your changes ...

# Restart services
systemctl start discord-indexer-bot
systemctl start discord-indexer-web
```

## Troubleshooting

### Bot Not Responding
1. Check if the bot is online in Discord
2. Verify the bot token in config.json
3. Check bot logs: `journalctl -u discord-indexer-bot -f`
4. Ensure bot has proper permissions in Discord server

### Web Interface Not Accessible
1. Check if the service is running: `systemctl status discord-indexer-web`
2. Check nginx configuration: `nginx -t`
3. Verify domain DNS settings
4. Check firewall settings: `ufw status`

### Database Issues
1. Check database file permissions: `ls -la /root/discord-indexer/indexer.db`
2. Recreate database: `python3 /root/discord-indexer/setup_db.py`
3. Restore from backup if needed

### SSL Certificate Issues
1. Check certificate status: `certbot certificates`
2. Renew certificate: `certbot renew`
3. Test renewal: `certbot renew --dry-run`

## Security Recommendations

1. **Change Default Credentials**: Always change the default username/password
2. **Secure Config File**: Ensure config.json has proper permissions (600)
3. **Regular Updates**: Keep the system and dependencies updated
4. **Monitor Logs**: Regularly check logs for suspicious activity
5. **Backup Strategy**: Ensure backups are working and test restoration
6. **Firewall**: Only open necessary ports
7. **SSH Security**: Use key-based authentication and disable password login

## Performance Optimization

### For Large Discord Servers
1. **Increase Database Performance**:
   ```bash
   # Add to config.json
   "database": {
     "path": "indexer.db",
     "pragma": {
       "journal_mode": "WAL",
       "synchronous": "NORMAL",
       "cache_size": 10000
     }
   }
   ```

2. **Optimize Indexing**:
   - Run initial indexing during off-peak hours
   - Consider indexing channels separately
   - Monitor system resources during indexing

3. **Web Interface Optimization**:
   - Implement caching for statistics
   - Add pagination limits
   - Consider using a more robust database (PostgreSQL) for very large datasets

## File Locations

- **Application**: `/root/discord-indexer/`
- **Database**: `/root/discord-indexer/indexer.db`
- **Logs**: `/root/discord-indexer/indexer.log`
- **Backups**: `/root/discord-indexer-backups/`
- **Nginx Config**: `/etc/nginx/sites-available/discord-indexer`
- **Systemd Services**: `/etc/systemd/system/discord-indexer-*.service`

## Support

If you encounter issues:
1. Check the logs first
2. Verify all configuration settings
3. Ensure all services are running
4. Check Discord bot permissions
5. Verify domain DNS settings

The application includes comprehensive logging to help diagnose issues. Most problems can be resolved by checking the service logs and ensuring proper configuration.