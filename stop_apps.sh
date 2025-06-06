#!/bin/bash

# Stop script for Discord Indexer applications

cd /root/discord-indexer

echo "Stopping Discord Indexer applications..."

# Stop bot if PID file exists
if [ -f "bot.pid" ]; then
    BOT_PID=$(cat bot.pid)
    if kill -0 $BOT_PID 2>/dev/null; then
        echo "Stopping Discord bot (PID: $BOT_PID)..."
        kill $BOT_PID
        sleep 2
        # Force kill if still running
        if kill -0 $BOT_PID 2>/dev/null; then
            echo "Force stopping bot..."
            kill -9 $BOT_PID
        fi
    else
        echo "Bot process not running."
    fi
    rm -f bot.pid
else
    echo "No bot PID file found."
fi

# Stop web app if PID file exists
if [ -f "web_app.pid" ]; then
    WEB_PID=$(cat web_app.pid)
    if kill -0 $WEB_PID 2>/dev/null; then
        echo "Stopping web application (PID: $WEB_PID)..."
        kill $WEB_PID
        sleep 2
        # Force kill if still running
        if kill -0 $WEB_PID 2>/dev/null; then
            echo "Force stopping web app..."
            kill -9 $WEB_PID
        fi
    else
        echo "Web app process not running."
    fi
    rm -f web_app.pid
else
    echo "No web app PID file found."
fi

echo "Discord Indexer applications stopped."