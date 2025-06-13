#!/bin/bash

# Stop script for Discord Indexer applications

cd /root/discord-indexer

echo "Stopping Discord Indexer applications..."

# Function to kill processes by name
kill_processes() {
    local process_name=$1
    local pids=$(ps aux | grep "$process_name" | grep -v grep | awk '{print $2}')
    
    if [ -n "$pids" ]; then
        echo "Found $process_name processes: $pids"
        for pid in $pids; do
            echo "Stopping $process_name (PID: $pid)..."
            kill $pid 2>/dev/null
        done
        sleep 2
        
        # Force kill any remaining processes
        local remaining_pids=$(ps aux | grep "$process_name" | grep -v grep | awk '{print $2}')
        if [ -n "$remaining_pids" ]; then
            echo "Force stopping remaining $process_name processes..."
            for pid in $remaining_pids; do
                kill -9 $pid 2>/dev/null
            done
        fi
    else
        echo "No $process_name processes found."
    fi
}

# Stop bot processes
kill_processes "python3 bot.py"

# Stop web app processes
kill_processes "python3 web_app.py"

# Clean up PID files
rm -f bot.pid web_app.pid

echo "Discord Indexer applications stopped."