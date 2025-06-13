#!/bin/bash

# Status script for Discord Indexer applications

cd /root/discord-indexer

echo "Discord Indexer Application Status"
echo "==================================="
echo ""

# Check systemd services first
echo "Systemd Services:"
if [ -f "/etc/systemd/system/discord-indexer-bot.service" ]; then
    echo "  Bot Service: $(sudo systemctl is-active discord-indexer-bot.service 2>/dev/null || echo 'inactive')"
else
    echo "  Bot Service: not installed"
fi

if [ -f "/etc/systemd/system/discord-indexer-web.service" ]; then
    echo "  Web Service: $(sudo systemctl is-active discord-indexer-web.service 2>/dev/null || echo 'inactive')"
else
    echo "  Web Service: not installed"
fi

echo ""
echo "Manual Processes:"

# Check bot status
echo "Discord Bot:"
if [ -f "bot.pid" ]; then
    BOT_PID=$(cat bot.pid)
    if kill -0 $BOT_PID 2>/dev/null; then
        echo "  Status: RUNNING (PID: $BOT_PID)"
        echo "  Log file: logs/bot.log"
        if [ -f "logs/bot.log" ]; then
            echo "  Last log entry: $(tail -n 1 logs/bot.log)"
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
        echo "  Log file: logs/web_app.log"
        echo "  URL: http://localhost:5000"
        if [ -f "logs/web_app.log" ]; then
            echo "  Last log entry: $(tail -n 1 logs/web_app.log)"
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
echo "Log files in logs directory:"
ls -la logs/*.log 2>/dev/null || echo "  No log files found"