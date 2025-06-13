#!/bin/bash

# Discord Indexer Service Management Script

case "$1" in
    start)
        echo "Starting Discord Indexer services..."
        # Copy service files to systemd directory
        sudo cp /root/discord-indexer/discord-indexer-bot.service /etc/systemd/system/
        sudo cp /root/discord-indexer/discord-indexer-web.service /etc/systemd/system/
        
        # Reload systemd and enable services
        sudo systemctl daemon-reload
        sudo systemctl enable discord-indexer-bot.service
        sudo systemctl enable discord-indexer-web.service
        
        # Start services
        sudo systemctl start discord-indexer-bot.service
        sudo systemctl start discord-indexer-web.service
        
        echo "Services started successfully!"
        ;;
    stop)
        echo "Stopping Discord Indexer services..."
        sudo systemctl stop discord-indexer-bot.service
        sudo systemctl stop discord-indexer-web.service
        echo "Services stopped."
        ;;
    restart)
        echo "Restarting Discord Indexer services..."
        sudo systemctl restart discord-indexer-bot.service
        sudo systemctl restart discord-indexer-web.service
        echo "Services restarted."
        ;;
    status)
        echo "Discord Indexer Bot Status:"
        sudo systemctl status discord-indexer-bot.service
        echo ""
        echo "Discord Indexer Web Status:"
        sudo systemctl status discord-indexer-web.service
        ;;
    logs)
        if [ "$2" = "bot" ]; then
            sudo journalctl -u discord-indexer-bot.service -f
        elif [ "$2" = "web" ]; then
            sudo journalctl -u discord-indexer-web.service -f
        else
            echo "Usage: $0 logs [bot|web]"
        fi
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs [bot|web]}"
        echo ""
        echo "Commands:"
        echo "  start   - Install and start both services"
        echo "  stop    - Stop both services"
        echo "  restart - Restart both services"
        echo "  status  - Show status of both services"
        echo "  logs    - Show logs (specify 'bot' or 'web')"
        exit 1
        ;;
esac