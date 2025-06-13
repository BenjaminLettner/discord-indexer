#!/bin/bash
# Backup script for Discord Indexer

BACKUP_DIR="/root/discord-indexer-backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
cp /root/discord-indexer/indexer.db $BACKUP_DIR/indexer_$DATE.db

# Backup configuration
cp /root/discord-indexer/config/config.json $BACKUP_DIR/config_$DATE.json

# Keep only last 7 days of backups
find $BACKUP_DIR -name "*.db" -mtime +7 -delete
find $BACKUP_DIR -name "*.json" -mtime +7 -delete

echo "Backup completed: $DATE"
