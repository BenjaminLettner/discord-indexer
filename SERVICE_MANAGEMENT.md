# Discord Indexer Service Management

This document explains how to run the Discord Indexer bot and web application as services on your server.

## Service Files

Two systemd service files have been created:

- `discord-indexer-bot.service` - Runs the Discord bot
- `discord-indexer-web.service` - Runs the web interface

These files are located in the project directory and can be installed as system services.

## Management Scripts

### Option 1: Systemd Services (Recommended for Production)

Use the `manage_services.sh` script to manage systemd services:

```bash
# Install and start both services
./manage_services.sh start

# Stop both services
./manage_services.sh stop

# Restart both services
./manage_services.sh restart

# Check service status
./manage_services.sh status

# View logs
./manage_services.sh logs bot    # Bot logs
./manage_services.sh logs web    # Web app logs
```

**Benefits:**
- Automatic startup on system boot
- Automatic restart on failure
- Better security isolation
- Centralized logging via journalctl
- Standard Linux service management

### Option 2: Direct Process Management (Simple)

Use the application scripts for direct process management:

```bash
# Start both applications
./start_apps.sh

# Stop both applications
./stop_apps.sh

# Check application status
./status_apps.sh
```

**Benefits:**
- Simple to use
- No root privileges required for basic operations
- Direct log files in project directory
- Easy debugging

## Service Configuration

### Bot Service (`discord-indexer-bot.service`)
- **Working Directory:** `/root/discord-indexer`
- **Python Path:** Uses virtual environment at `/root/discord-indexer/venv/bin/python`
- **Log Identifier:** `discord-indexer-bot`
- **Restart Policy:** Always restart on failure (10-second delay)

### Web Service (`discord-indexer-web.service`)
- **Working Directory:** `/root/discord-indexer`
- **Python Path:** Uses virtual environment at `/root/discord-indexer/venv/bin/python`
- **Environment:** Production Flask environment
- **Log Identifier:** `discord-indexer-web`
- **Restart Policy:** Always restart on failure (10-second delay)
- **Port:** 5000 (default Flask port)

## Security Features

Both services include security hardening:
- `NoNewPrivileges=true` - Prevents privilege escalation
- `PrivateTmp=true` - Isolated temporary directory
- `ProtectSystem=strict` - Read-only system directories
- `ReadWritePaths=/root/discord-indexer` - Only project directory is writable

## Logs and Monitoring

### Systemd Services
```bash
# View recent logs
sudo journalctl -u discord-indexer-bot.service -n 50
sudo journalctl -u discord-indexer-web.service -n 50

# Follow live logs
sudo journalctl -u discord-indexer-bot.service -f
sudo journalctl -u discord-indexer-web.service -f

# View logs since boot
sudo journalctl -u discord-indexer-bot.service -b
```

### Direct Process Management
```bash
# View log files
tail -f bot.log
tail -f web_app.log

# Check process status
./status_apps.sh
```

## Troubleshooting

### Common Issues

1. **Service fails to start:**
   - Check if virtual environment exists: `ls -la venv/`
   - Verify Python dependencies: `venv/bin/pip list`
   - Check configuration files exist

2. **Permission errors:**
   - Ensure service files have correct permissions
   - Check that `/root/discord-indexer` is accessible

3. **Port conflicts:**
   - Web app uses port 5000 by default
   - Check if port is already in use: `netstat -tlnp | grep 5000`

### Manual Service Commands

If you prefer to use systemctl directly:

```bash
# Enable services to start on boot
sudo systemctl enable discord-indexer-bot.service
sudo systemctl enable discord-indexer-web.service

# Start services
sudo systemctl start discord-indexer-bot.service
sudo systemctl start discord-indexer-web.service

# Check status
sudo systemctl status discord-indexer-bot.service
sudo systemctl status discord-indexer-web.service
```

## File Locations

- **Service Files:** `/etc/systemd/system/discord-indexer-*.service`
- **Application Files:** `/root/discord-indexer/`
- **Virtual Environment:** `/root/discord-indexer/venv/`
- **Logs (systemd):** `journalctl -u discord-indexer-*`
- **Logs (direct):** `/root/discord-indexer/*.log`
- **PID Files:** `/root/discord-indexer/*.pid`

## Next Steps

1. **For Production:** Use the systemd services with `./manage_services.sh start`
2. **For Development:** Use direct process management with `./start_apps.sh`
3. **Configure Firewall:** Ensure port 5000 is accessible if needed
4. **Set up Reverse Proxy:** Consider using nginx for the web interface
5. **Monitor Resources:** Set up monitoring for the services

The Discord Indexer is now ready to run as a service on your server!