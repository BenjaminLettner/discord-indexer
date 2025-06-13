#!/bin/bash

# Change to the project directory
cd /root/discord-indexer

# Function to kill processes by name
kill_processes() {
    local process_name="$1"
    echo "Stopping $process_name..."
    
    # Find and kill processes
    pids=$(ps aux | grep "$process_name" | grep -v grep | awk '{print $2}')
    
    if [ -n "$pids" ]; then
        echo "Found processes: $pids"
        # First try graceful kill
        kill $pids 2>/dev/null
        sleep 2
        
        # Check if any processes are still running and force kill
        remaining_pids=$(ps aux | grep "$process_name" | grep -v grep | awk '{print $2}')
        if [ -n "$remaining_pids" ]; then
            echo "Force killing remaining processes: $remaining_pids"
            kill -9 $remaining_pids 2>/dev/null
        fi
        echo "$process_name stopped."
    else
        echo "No $process_name processes found."
    fi
}

# Stop systemd services first (if they exist)
echo "Checking for systemd services..."
if [ -f "/etc/systemd/system/discord-indexer-web.service" ]; then
    echo "Stopping discord-indexer-web service..."
    sudo systemctl stop discord-indexer-web.service 2>/dev/null || echo "Service not running or failed to stop"
fi

if [ -f "/etc/systemd/system/discord-indexer-bot.service" ]; then
    echo "Stopping discord-indexer-bot service..."
    sudo systemctl stop discord-indexer-bot.service 2>/dev/null || echo "Service not running or failed to stop"
fi

# Stop the applications (fallback for manual processes)
kill_processes "python3 src/bot.py"
kill_processes "python3 src/web_app.py"

# Remove PID files if they exist
rm -f bot.pid web_app.pid

echo "All applications stopped."