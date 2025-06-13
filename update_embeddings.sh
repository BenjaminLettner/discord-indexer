#!/bin/bash

# Script to manually update/generate embeddings for all indexed content
# Useful for maintenance or after bulk imports

cd /root/discord-indexer

echo "Updating AI Search embeddings..."
echo "This may take a few minutes depending on the amount of indexed content."
echo ""

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the embedding generation script
python3 generate_embeddings.py

echo ""
echo "Embedding update completed!"
echo "AI Search is now up to date with all indexed content."