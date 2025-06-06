#!/bin/bash

# Status script for Discord Indexer applications

cd /root/discord-indexer

echo "Discord Indexer Application Status"
echo "==================================="
echo ""

# Check bot status
echo "Discord Bot:"
if [ -f "bot.pid" ]; then
    BOT_PID=$(cat bot.pid)
    if kill -0 $BOT_PID 2>/dev/null; then
        echo "  Status: RUNNING (PID: $BOT_PID)"
        echo "  Log file: bot.log"
        if [ -f "bot.log" ]; then
            echo "  Last log entry: $(tail -n 1 bot.log)"
        fi
    else
        echo "  Status: NOT RUNNING (stale PID file)"
        rm -f bot.pid
    fi
else
    echo "  Status: NOT RUNNING (no PID file)"
fi

echo ""

# Check web app status
echo "Web Application:"
if [ -f "web_app.pid" ]; then
    WEB_PID=$(cat web_app.pid)
    if kill -0 $WEB_PID 2>/dev/null; then
        echo "  Status: RUNNING (PID: $WEB_PID)"
        echo "  Log file: web_app.log"
        echo "  URL: http://localhost:5000"
        if [ -f "web_app.log" ]; then
            echo "  Last log entry: $(tail -n 1 web_app.log)"
        fi
    else
        echo "  Status: NOT RUNNING (stale PID file)"
        rm -f web_app.pid
    fi
else
    echo "  Status: NOT RUNNING (no PID file)"
fi

echo ""

# Check for any python processes related to the project
echo "Related Python Processes:"
ps aux | grep -E "(bot\.py|web_app\.py)" | grep -v grep | while read line; do
    echo "  $line"
done

echo ""
echo "Log files in directory:"
ls -la *.log 2>/dev/null || echo "  No log files found"