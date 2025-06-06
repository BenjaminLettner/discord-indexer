#!/usr/bin/env python3

import discord
from discord.ext import commands, tasks
import json
import sqlite3
import re
import logging
from datetime import datetime
import asyncio
from urllib.parse import urlparse
import aiohttp

# Load configuration
with open('config.json', 'r') as f:
    config = json.load(f)

# Setup logging
logging.basicConfig(
    level=getattr(logging, config['logging']['level']),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config['logging']['file']),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('DiscordIndexer')

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True

bot = commands.Bot(command_prefix=config['discord']['command_prefix'], intents=intents)

class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        # Enable WAL mode for better concurrent access
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA busy_timeout=30000')
        return conn
    
    def insert_file(self, message, attachment):
        """Insert a file attachment into the database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO indexed_files 
                (message_id, channel_id, channel_name, guild_id, guild_name, 
                 author_id, author_name, filename, file_url, file_size, file_type, 
                 message_content, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                str(message.id),
                str(message.channel.id),
                message.channel.name,
                str(message.guild.id) if message.guild else None,
                message.guild.name if message.guild else None,
                str(message.author.id),
                str(message.author),
                attachment.filename,
                attachment.url,
                attachment.size,
                attachment.content_type,
                message.content,
                message.created_at
            ))
            conn.commit()
            logger.info(f"Indexed file: {attachment.filename} from message {message.id}")
        except Exception as e:
            logger.error(f"Error inserting file: {e}")
        finally:
            conn.close()
    
    def insert_link(self, message, url):
        """Insert a link into the database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            
            cursor.execute('''
                INSERT OR IGNORE INTO indexed_links 
                (message_id, channel_id, channel_name, guild_id, guild_name, 
                 author_id, author_name, link_url, link_domain, message_content, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                str(message.id),
                str(message.channel.id),
                message.channel.name,
                str(message.guild.id) if message.guild else None,
                message.guild.name if message.guild else None,
                str(message.author.id),
                str(message.author),
                url,
                domain,
                message.content,
                message.created_at
            ))
            conn.commit()
            logger.info(f"Indexed link: {url} from message {message.id}")
        except Exception as e:
            logger.error(f"Error inserting link: {e}")
        finally:
            conn.close()
    
    def get_stats(self):
        """Get indexing statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get file count
            cursor.execute('SELECT COUNT(*) FROM indexed_files')
            file_count = cursor.fetchone()[0]
            
            # Get link count
            cursor.execute('SELECT COUNT(*) FROM indexed_links')
            link_count = cursor.fetchone()[0]
            
            # Get latest indexing operation
            cursor.execute('''
                SELECT operation_type, started_at, completed_at, status, 
                       messages_processed, files_indexed, links_indexed
                FROM indexing_stats 
                ORDER BY started_at DESC LIMIT 1
            ''')
            latest_op = cursor.fetchone()
            
            return {
                'total_files': file_count,
                'total_links': link_count,
                'latest_operation': latest_op
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return None
        finally:
            conn.close()
    
    def start_indexing_operation(self, operation_type, channel_id=None, channel_name=None):
        """Record the start of an indexing operation"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO indexing_stats 
                (operation_type, channel_id, channel_name, started_at, status)
                VALUES (?, ?, ?, ?, 'running')
            ''', (operation_type, channel_id, channel_name, datetime.now()))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error starting indexing operation: {e}")
            return None
        finally:
            conn.close()
    
    def complete_indexing_operation(self, operation_id, messages_processed, files_indexed, links_indexed):
        """Mark an indexing operation as complete"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE indexing_stats 
                SET completed_at = ?, status = 'completed', 
                    messages_processed = ?, files_indexed = ?, links_indexed = ?
                WHERE id = ?
            ''', (datetime.now(), messages_processed, files_indexed, links_indexed, operation_id))
            conn.commit()
        except Exception as e:
            logger.error(f"Error completing indexing operation: {e}")
        finally:
            conn.close()
    
    async def refresh_file_urls(self):
        """Refresh all file URLs in the database"""
        try:
            # Get all files that need URL refresh
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT id, message_id, channel_id, filename FROM indexed_files')
            files = cursor.fetchall()
            conn.close()
            
            refreshed_count = 0
            batch_size = 10  # Process in smaller batches
            
            for i in range(0, len(files), batch_size):
                batch = files[i:i + batch_size]
                
                for file_id, message_id, channel_id, filename in batch:
                    try:
                        # Try to get the message and update the URL
                        channel = bot.get_channel(int(channel_id))
                        if channel:
                            message = await channel.fetch_message(int(message_id))
                            if message and message.attachments:
                                # Find the matching attachment by filename
                                for attachment in message.attachments:
                                    if attachment.filename == filename:
                                        # Update the URL in database with retry logic
                                        for retry in range(3):
                                            conn = None
                                            try:
                                                conn = self.get_connection()
                                                cursor = conn.cursor()
                                                # Check if this would create a duplicate entry
                                                cursor.execute(
                                                    'SELECT COUNT(*) FROM indexed_files WHERE message_id = ? AND file_url = ? AND id != ?',
                                                    (str(message_id), attachment.url, file_id)
                                                )
                                                if cursor.fetchone()[0] == 0:
                                                    cursor.execute(
                                                        'UPDATE indexed_files SET file_url = ? WHERE id = ?',
                                                        (attachment.url, file_id)
                                                    )
                                                else:
                                                    logger.warning(f"Skipping URL update for file {filename} (ID: {file_id}) - would create duplicate entry")
                                                conn.commit()
                                                conn.close()
                                                refreshed_count += 1
                                                break
                                            except sqlite3.OperationalError as db_e:
                                                if conn:
                                                    conn.close()
                                                if "database is locked" in str(db_e) and retry < 2:
                                                    await asyncio.sleep(1 + retry)  # Exponential backoff
                                                    continue
                                                else:
                                                    raise db_e
                                            except Exception as e:
                                                if conn:
                                                    conn.close()
                                                raise e
                                        break
                    except Exception as e:
                        logger.warning(f"Could not refresh URL for file {filename} (ID: {file_id}): {e}")
                        continue
                
                # Small delay between batches to reduce database pressure
                if i + batch_size < len(files):
                    await asyncio.sleep(0.1)
            
            logger.info(f"Refreshed {refreshed_count} file URLs")
            return refreshed_count
            
        except Exception as e:
            logger.error(f"Error refreshing file URLs: {e}")
            return 0

# Initialize database manager
db = DatabaseManager(config['database']['path'])

def extract_urls(text):
    """Extract URLs from text"""
    url_pattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )
    urls = url_pattern.findall(text)
    
    # Clean up URLs by removing trailing punctuation that's commonly found at sentence ends
    cleaned_urls = []
    for url in urls:
        # Remove trailing punctuation like ), ,, ., ;, :, !, ?
        cleaned_url = re.sub(r'[),.:;!?]+$', '', url)
        cleaned_urls.append(cleaned_url)
    
    return cleaned_urls

async def process_message(message):
    """Process a message for attachments and links"""
    if message.author.bot:
        return 0, 0  # Skip bot messages
    
    files_indexed = 0
    links_indexed = 0
    
    # Process attachments
    for attachment in message.attachments:
        db.insert_file(message, attachment)
        files_indexed += 1
    
    # Process links in message content
    if message.content:
        urls = extract_urls(message.content)
        for url in urls:
            db.insert_link(message, url)
            links_indexed += 1
    
    return files_indexed, links_indexed

@tasks.loop(hours=24)
async def daily_url_refresh():
    """Daily task to refresh all file URLs"""
    logger.info("Starting daily URL refresh...")
    try:
        refreshed_count = await db.refresh_file_urls()
        logger.info(f"Daily URL refresh completed. Refreshed {refreshed_count} URLs.")
    except Exception as e:
        logger.error(f"Error during daily URL refresh: {e}")

@bot.event
async def on_ready():
    logger.info(f'{bot.user} has connected to Discord!')
    
    # Start the daily URL refresh task
    if not daily_url_refresh.is_running():
        daily_url_refresh.start()
        logger.info("Started daily URL refresh task")
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} command(s)")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")

@bot.event
async def on_message(message):
    """Automatically index new messages"""
    if message.author.bot:
        return
    
    # Process the message for attachments and links
    files_indexed, links_indexed = await process_message(message)
    
    if files_indexed > 0 or links_indexed > 0:
        logger.info(f"Auto-indexed message {message.id}: {files_indexed} files, {links_indexed} links")
    
    # Process commands
    await bot.process_commands(message)

@bot.tree.command(name="stats", description="Display indexing statistics")
async def stats_command(interaction: discord.Interaction):
    """Display current indexing statistics"""
    await interaction.response.defer()
    
    stats = db.get_stats()
    if not stats:
        await interaction.followup.send("❌ Error retrieving statistics.")
        return
    
    embed = discord.Embed(
        title="📊 Indexing Statistics",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name="📁 Total Files Indexed",
        value=f"{stats['total_files']:,}",
        inline=True
    )
    
    embed.add_field(
        name="🔗 Total Links Indexed",
        value=f"{stats['total_links']:,}",
        inline=True
    )
    
    embed.add_field(
        name="📈 Total Items",
        value=f"{stats['total_files'] + stats['total_links']:,}",
        inline=True
    )
    
    if stats['latest_operation']:
        op = stats['latest_operation']
        embed.add_field(
            name="🔄 Latest Operation",
            value=f"Type: {op[0]}\nStatus: {op[3]}\nProcessed: {op[4]} messages",
            inline=False
        )
    
    embed.set_footer(text="Discord Indexer Bot")
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="index", description="Index all channels and historical messages")
async def index_command(interaction: discord.Interaction):
    """Index all channels with historical messages"""
    await interaction.response.defer()
    
    if not interaction.guild:
        await interaction.followup.send("❌ This command can only be used in a server.")
        return
    
    # Start indexing operation
    operation_id = db.start_indexing_operation("full_index", str(interaction.guild.id), interaction.guild.name)
    
    embed = discord.Embed(
        title="🔄 Starting Full Index",
        description="Indexing all channels and historical messages...",
        color=discord.Color.orange()
    )
    
    await interaction.followup.send(embed=embed)
    
    total_messages = 0
    total_files = 0
    total_links = 0
    
    try:
        # Process all text channels
        for channel in interaction.guild.text_channels:
            try:
                logger.info(f"Indexing channel: {channel.name}")
                
                async for message in channel.history(limit=None):
                    files_indexed, links_indexed = await process_message(message)
                    total_messages += 1
                    total_files += files_indexed
                    total_links += links_indexed
                    
                    # Update progress every 100 messages
                    if total_messages % 100 == 0:
                        logger.info(f"Progress: {total_messages} messages processed")
                        
            except discord.Forbidden:
                logger.warning(f"No permission to read channel: {channel.name}")
            except Exception as e:
                logger.error(f"Error indexing channel {channel.name}: {e}")
        
        # Complete the operation
        if operation_id:
            db.complete_indexing_operation(operation_id, total_messages, total_files, total_links)
        
        # Send completion message
        completion_embed = discord.Embed(
            title="✅ Indexing Complete",
            color=discord.Color.green()
        )
        
        completion_embed.add_field(
            name="📊 Results",
            value=f"Messages: {total_messages:,}\nFiles: {total_files:,}\nLinks: {total_links:,}",
            inline=False
        )
        
        await interaction.followup.send(embed=completion_embed)
        logger.info(f"Full indexing completed: {total_messages} messages, {total_files} files, {total_links} links")
        
    except Exception as e:
        logger.error(f"Error during full indexing: {e}")
        error_embed = discord.Embed(
            title="❌ Indexing Error",
            description=f"An error occurred during indexing: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=error_embed)

@bot.tree.command(name="refresh_urls", description="Manually refresh all file URLs to prevent expiration")
async def refresh_urls_command(interaction: discord.Interaction):
    """Manually trigger URL refresh"""
    await interaction.response.defer()
    
    try:
        # Start refresh
        start_embed = discord.Embed(
            title="🔄 Refreshing URLs",
            description="Starting to refresh all file URLs...",
            color=discord.Color.orange()
        )
        await interaction.followup.send(embed=start_embed)
        
        # Perform refresh
        refreshed_count = await db.refresh_file_urls()
        
        # Send completion message
        completion_embed = discord.Embed(
            title="✅ URL Refresh Complete",
            description=f"Successfully refreshed {refreshed_count} file URLs",
            color=discord.Color.green()
        )
        
        completion_embed.add_field(
            name="📊 Results",
            value=f"Refreshed URLs: {refreshed_count:,}",
            inline=False
        )
        
        completion_embed.add_field(
            name="ℹ️ Info",
            value="File URLs are automatically refreshed daily to prevent expiration.",
            inline=False
        )
        
        await interaction.edit_original_response(embed=completion_embed)
        logger.info(f"Manual URL refresh completed: {refreshed_count} URLs refreshed")
        
    except Exception as e:
        logger.error(f"Error during manual URL refresh: {e}")
        error_embed = discord.Embed(
            title="❌ Refresh Error",
            description=f"An error occurred during URL refresh: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.edit_original_response(embed=error_embed)

@bot.tree.command(name="dashboard", description="Get the web dashboard link")
async def dashboard_command(interaction: discord.Interaction):
    """Provide dashboard link"""
    await interaction.response.defer()
    
    embed = discord.Embed(
        title="🌐 Web Dashboard",
        description="Access the Discord Indexer web interface",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="🔗 Dashboard URL",
        value="https://lettner.tech",
        inline=False
    )
    
    embed.add_field(
        name="📋 Features",
        value="• Browse indexed files and links\n• View server statistics\n• Search through indexed content\n• Download files",
        inline=False
    )
    
    embed.set_footer(text="Discord Indexer Bot")
    
    await interaction.followup.send(embed=embed)

if __name__ == '__main__':
    # Check if token is configured
    if config['discord']['token'] == 'YOUR_DISCORD_BOT_TOKEN_HERE':
        logger.error("Please configure your Discord bot token in config.json")
        exit(1)
    
    # Run the bot
    bot.run(config['discord']['token'])