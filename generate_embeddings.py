#!/usr/bin/env python3

import sys
import os
from ai_search_manager import AISearchManager
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    # Database path from config
    db_path = 'indexer.db'
    
    if not os.path.exists(db_path):
        logger.error(f"Database file {db_path} not found!")
        sys.exit(1)
    
    logger.info("Starting embedding generation...")
    
    # Initialize AI Search Manager
    ai_manager = AISearchManager(db_path)
    
    # Generate embeddings for all files and links
    try:
        results = ai_manager.generate_all_embeddings(batch_size=50)
        
        logger.info(f"Embedding generation completed:")
        logger.info(f"Files processed: {results['files_processed']}/{results['total_files']}")
        logger.info(f"Links processed: {results['links_processed']}/{results['total_links']}")
        
        if results['files_processed'] == results['total_files'] and results['links_processed'] == results['total_links']:
            logger.info("All embeddings generated successfully!")
        else:
            logger.warning("Some embeddings failed to generate. Check logs for details.")
            
    except Exception as e:
        logger.error(f"Error during embedding generation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()