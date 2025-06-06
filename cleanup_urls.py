#!/usr/bin/env python3
import sqlite3
import re

def cleanup_urls():
    """Clean up URLs in the database by removing trailing punctuation"""
    conn = sqlite3.connect('indexer.db')
    cursor = conn.cursor()
    
    # Get all URLs from the database
    cursor.execute('SELECT id, link_url FROM indexed_links')
    rows = cursor.fetchall()
    
    updated = 0
    deleted = 0
    for row_id, url in rows:
        # Remove trailing punctuation like ), ,, ., ;, :, !, ?
        cleaned_url = re.sub(r'[),.:;!?]+$', '', url)
        
        if cleaned_url != url:
            # Check if the cleaned URL already exists for the same message
            cursor.execute('SELECT message_id FROM indexed_links WHERE id = ?', (row_id,))
            message_id = cursor.fetchone()[0]
            
            cursor.execute('SELECT id FROM indexed_links WHERE message_id = ? AND link_url = ? AND id != ?', 
                         (message_id, cleaned_url, row_id))
            existing = cursor.fetchone()
            
            if existing:
                # Delete the duplicate entry with trailing punctuation
                cursor.execute('DELETE FROM indexed_links WHERE id = ?', (row_id,))
                deleted += 1
                print(f"Deleted duplicate: {url} (clean version already exists: {cleaned_url})")
            else:
                # Update the URL
                try:
                    cursor.execute('UPDATE indexed_links SET link_url = ? WHERE id = ?', (cleaned_url, row_id))
                    updated += 1
                    print(f"Updated: {url} -> {cleaned_url}")
                except sqlite3.IntegrityError:
                    # If update fails due to constraint, delete this entry
                    cursor.execute('DELETE FROM indexed_links WHERE id = ?', (row_id,))
                    deleted += 1
                    print(f"Deleted duplicate: {url} (constraint violation)")
    
    conn.commit()
    conn.close()
    
    print(f"\nUpdated {updated} URLs with trailing punctuation")
    print(f"Deleted {deleted} duplicate URLs")

if __name__ == '__main__':
    cleanup_urls()