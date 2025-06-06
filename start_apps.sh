#!/bin/bash

# Simple startup script for Discord Indexer applications
# This script starts the applications directly without systemd

cd /root/discord-indexer

echo "Starting Discord Indexer applications..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Start bot in background
echo "Starting Discord bot..."
nohup python3 bot.py > bot.log 2>&1 &
BOT_PID=$!
echo "Bot started with PID: $BOT_PID"

# Wait a moment
sleep 2

# Start web app in background
echo "Starting web application..."
nohup python3 web_app.py > web_app.log 2>&1 &
WEB_PID=$!
echo "Web app started with PID: $WEB_PID"

# Save PIDs for later reference
echo $BOT_PID > bot.pid
echo $WEB_PID > web_app.pid

echo ""
echo "Discord Indexer started successfully!"
echo "Bot PID: $BOT_PID (log: bot.log)"
echo "Web App PID: $WEB_PID (log: web_app.log)"
echo "Web interface available at: http://localhost:5000"
echo ""
echo "To stop the applications, run: ./stop_apps.sh"
echo "To check status, run: ./status_apps.sh"