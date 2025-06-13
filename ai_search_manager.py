import sqlite3
import numpy as np
import pickle
import logging
from typing import List, Dict, Tuple, Optional
from sentence_transformers import SentenceTransformer
import faiss
from datetime import datetime
import time

class AISearchManager:
    def __init__(self, db_path: str, model_name: str = 'all-MiniLM-L6-v2'):
        self.db_path = db_path
        self.model_name = model_name
        self.model = None
        self.file_index = None
        self.link_index = None
        self.file_id_map = []
        self.link_id_map = []
        self.logger = logging.getLogger(__name__)
        
    def _load_model(self):
        """Lazy load the sentence transformer model"""
        if self.model is None:
            self.logger.info(f"Loading sentence transformer model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
        return self.model
    
    def _get_db_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    def generate_file_embedding(self, file_id: int) -> bool:
        """Generate embedding for a specific file"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # Get file data
            cursor.execute("""
                SELECT filename, message_content, file_type, author_name, channel_name
                FROM indexed_files WHERE id = ?
            """, (file_id,))
            
            result = cursor.fetchone()
            if not result:
                return False
            
            filename, message_content, file_type, author_name, channel_name = result
            
            # Create searchable text
            content_parts = []
            if filename:
                content_parts.append(f"Filename: {filename}")
            if file_type:
                content_parts.append(f"Type: {file_type}")
            if author_name:
                content_parts.append(f"Author: {author_name}")
            if channel_name:
                content_parts.append(f"Channel: {channel_name}")
            if message_content:
                content_parts.append(f"Message: {message_content}")
            
            content_text = " ".join(content_parts)
            
            # Generate embedding
            model = self._load_model()
            embedding = model.encode(content_text)
            embedding_blob = pickle.dumps(embedding)
            
            # Store in database
            cursor.execute("""
                INSERT OR REPLACE INTO file_embeddings 
                (file_id, embedding, content_text, embedding_model, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (file_id, embedding_blob, content_text, self.model_name, datetime.now()))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            self.logger.error(f"Error generating file embedding for ID {file_id}: {e}")
            return False
    
    def generate_link_embedding(self, link_id: int) -> bool:
        """Generate embedding for a specific link"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # Get link data
            cursor.execute("""
                SELECT link_url, link_domain, message_content, author_name, channel_name
                FROM indexed_links WHERE id = ?
            """, (link_id,))
            
            result = cursor.fetchone()
            if not result:
                return False
            
            link_url, link_domain, message_content, author_name, channel_name = result
            
            # Create searchable text
            content_parts = []
            if link_url:
                content_parts.append(f"URL: {link_url}")
            if link_domain:
                content_parts.append(f"Domain: {link_domain}")
            if author_name:
                content_parts.append(f"Author: {author_name}")
            if channel_name:
                content_parts.append(f"Channel: {channel_name}")
            if message_content:
                content_parts.append(f"Message: {message_content}")
            
            content_text = " ".join(content_parts)
            
            # Generate embedding
            model = self._load_model()
            embedding = model.encode(content_text)
            embedding_blob = pickle.dumps(embedding)
            
            # Store in database
            cursor.execute("""
                INSERT OR REPLACE INTO link_embeddings 
                (link_id, embedding, content_text, embedding_model, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (link_id, embedding_blob, content_text, self.model_name, datetime.now()))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            self.logger.error(f"Error generating link embedding for ID {link_id}: {e}")
            return False
    
    def generate_all_embeddings(self, batch_size: int = 100) -> Dict[str, int]:
        """Generate embeddings for all files and links that don't have them"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        # Get files without embeddings
        cursor.execute("""
            SELECT f.id FROM indexed_files f
            LEFT JOIN file_embeddings fe ON f.id = fe.file_id
            WHERE fe.file_id IS NULL
        """)
        file_ids = [row[0] for row in cursor.fetchall()]
        
        # Get links without embeddings
        cursor.execute("""
            SELECT l.id FROM indexed_links l
            LEFT JOIN link_embeddings le ON l.id = le.link_id
            WHERE le.link_id IS NULL
        """)
        link_ids = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        files_processed = 0
        links_processed = 0
        
        # Process files in batches
        for i in range(0, len(file_ids), batch_size):
            batch = file_ids[i:i + batch_size]
            for file_id in batch:
                if self.generate_file_embedding(file_id):
                    files_processed += 1
        
        # Process links in batches
        for i in range(0, len(link_ids), batch_size):
            batch = link_ids[i:i + batch_size]
            for link_id in batch:
                if self.generate_link_embedding(link_id):
                    links_processed += 1
        
        return {
            'files_processed': files_processed,
            'links_processed': links_processed,
            'total_files': len(file_ids),
            'total_links': len(link_ids)
        }
    
    def _build_faiss_index(self, embeddings: List[np.ndarray]) -> faiss.IndexFlatIP:
        """Build FAISS index for similarity search"""
        if not embeddings:
            return None
        
        dimension = embeddings[0].shape[0]
        index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
        
        # Normalize embeddings for cosine similarity
        embeddings_array = np.array(embeddings).astype('float32')
        faiss.normalize_L2(embeddings_array)
        
        index.add(embeddings_array)
        return index
    
    def _load_embeddings_index(self):
        """Load all embeddings and build FAISS indices"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        # Load file embeddings
        cursor.execute("SELECT file_id, embedding FROM file_embeddings ORDER BY file_id")
        file_results = cursor.fetchall()
        
        file_embeddings = []
        self.file_id_map = []
        
        for file_id, embedding_blob in file_results:
            embedding = pickle.loads(embedding_blob)
            file_embeddings.append(embedding)
            self.file_id_map.append(file_id)
        
        # Load link embeddings
        cursor.execute("SELECT link_id, embedding FROM link_embeddings ORDER BY link_id")
        link_results = cursor.fetchall()
        
        link_embeddings = []
        self.link_id_map = []
        
        for link_id, embedding_blob in link_results:
            embedding = pickle.loads(embedding_blob)
            link_embeddings.append(embedding)
            self.link_id_map.append(link_id)
        
        conn.close()
        
        # Build indices
        self.file_index = self._build_faiss_index(file_embeddings)
        self.link_index = self._build_faiss_index(link_embeddings)
    
    def search(self, query: str, limit: int = 20, include_files: bool = True, 
              include_links: bool = True, user_id: Optional[int] = None, include_content: bool = True) -> Dict[str, List[Dict]]:
        """Perform AI-powered semantic search and optionally file content search"""
        start_time = time.time()
        
        # Generate query embedding
        model = self._load_model()
        query_embedding = model.encode(query)
        query_embedding = query_embedding.astype('float32').reshape(1, -1)
        faiss.normalize_L2(query_embedding)
        
        results = {'files': [], 'links': []}
        
        # Load indices if not already loaded
        if self.file_index is None or self.link_index is None:
            self._load_embeddings_index()
        
        # Search files
        if include_files and self.file_index is not None:
            scores, indices = self.file_index.search(query_embedding, min(limit, len(self.file_id_map)))
            file_results = self._get_file_details(indices[0], scores[0])
            results['files'] = file_results
            
            # Also search file content if enabled
            if include_content:
                try:
                    conn = self._get_db_connection()
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        SELECT f.*, fc.content_text, fc.extraction_method
                        FROM indexed_files f
                        JOIN file_content fc ON f.id = fc.file_id
                        WHERE fc.content_text LIKE ?
                        ORDER BY f.timestamp DESC
                        LIMIT ?
                    """, (f'%{query}%', limit * 2))
                    
                    content_results = cursor.fetchall()
                    
                    for row in content_results:
                        # Calculate a simple text similarity score
                        content_text = row[-2].lower()
                        query_lower = query.lower()
                        
                        # Simple scoring based on query term frequency
                        score = 0.0
                        query_terms = query_lower.split()
                        for term in query_terms:
                            score += content_text.count(term) / len(content_text) * 100
                        
                        # Boost score if query appears as exact phrase
                        if query_lower in content_text:
                            score += 0.5
                        
                        # Check if this file is already in results (from embedding search)
                        existing_result = next((r for r in results['files'] if r['id'] == row[0]), None)
                        if existing_result:
                            # Boost existing result's score
                            existing_result['similarity_score'] = max(existing_result['similarity_score'], score)
                            existing_result['content_match'] = True
                        else:
                            # Add new result from content search
                            results['files'].append({
                                'type': 'file',
                                'id': row[0],
                                'message_id': row[1],
                                'channel_name': row[3],
                                'guild_name': row[5],
                                'author_name': row[7],
                                'filename': row[8],
                                'file_url': row[9],
                                'file_size': row[10],
                                'file_type': row[11],
                                'message_content': row[12],
                                'timestamp': row[13],
                                'content_text': row[-2],
                                'extraction_method': row[-1],
                                'similarity_score': score,
                                'content_match': True
                            })
                    
                    conn.close()
                except Exception as e:
                    self.logger.error(f"Error searching file content: {e}")
        
        # Search links
        if include_links and self.link_index is not None:
            scores, indices = self.link_index.search(query_embedding, min(limit, len(self.link_id_map)))
            link_results = self._get_link_details(indices[0], scores[0])
            results['links'] = link_results
        
        # Log search query
        search_time_ms = int((time.time() - start_time) * 1000)
        total_results = len(results['files']) + len(results['links'])
        self._log_search_query(user_id, query, query_embedding, total_results, search_time_ms)
        
        return results
    
    def _get_file_details(self, indices: np.ndarray, scores: np.ndarray) -> List[Dict]:
        """Get detailed file information for search results"""
        if len(indices) == 0:
            return []
        
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        results = []
        for i, score in zip(indices, scores):
            if i >= len(self.file_id_map):
                continue
                
            file_id = self.file_id_map[i]
            cursor.execute("""
                SELECT f.*, fe.content_text
                FROM indexed_files f
                JOIN file_embeddings fe ON f.id = fe.file_id
                WHERE f.id = ?
            """, (file_id,))
            
            row = cursor.fetchone()
            if row:
                result = {
                    'id': row[0],
                    'message_id': row[1],
                    'channel_name': row[3],
                    'guild_name': row[5],
                    'author_name': row[7],
                    'filename': row[8],
                    'file_url': row[9],
                    'file_size': row[10],
                    'file_type': row[11],
                    'message_content': row[12],
                    'timestamp': row[13],
                    'content_text': row[-1],
                    'similarity_score': float(score),
                    'type': 'file'
                }
                results.append(result)
        
        conn.close()
        return results
    
    def _get_link_details(self, indices: np.ndarray, scores: np.ndarray) -> List[Dict]:
        """Get detailed link information for search results"""
        if len(indices) == 0:
            return []
        
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        results = []
        for i, score in zip(indices, scores):
            if i >= len(self.link_id_map):
                continue
                
            link_id = self.link_id_map[i]
            cursor.execute("""
                SELECT l.*, le.content_text
                FROM indexed_links l
                JOIN link_embeddings le ON l.id = le.link_id
                WHERE l.id = ?
            """, (link_id,))
            
            row = cursor.fetchone()
            if row:
                result = {
                    'id': row[0],
                    'message_id': row[1],
                    'channel_name': row[3],
                    'guild_name': row[5],
                    'author_name': row[7],
                    'link_url': row[8],
                    'link_domain': row[9],
                    'message_content': row[10],
                    'timestamp': row[11],
                    'content_text': row[-1],
                    'similarity_score': float(score),
                    'type': 'link'
                }
                results.append(result)
        
        conn.close()
        return results
    
    def _log_search_query(self, user_id: Optional[int], query: str, 
                         query_embedding: np.ndarray, results_count: int, search_time_ms: int):
        """Log search query for analytics"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            embedding_blob = pickle.dumps(query_embedding)
            
            cursor.execute("""
                INSERT INTO ai_search_queries 
                (user_id, query_text, query_embedding, results_count, search_time_ms)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, query, embedding_blob, results_count, search_time_ms))
            
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Error logging search query: {e}")
    
    def get_embedding_stats(self) -> Dict[str, int]:
        """Get statistics about embeddings"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM file_embeddings")
        file_embeddings_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM link_embeddings")
        link_embeddings_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM indexed_files")
        total_files = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM indexed_links")
        total_links = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'file_embeddings': file_embeddings_count,
            'link_embeddings': link_embeddings_count,
            'total_files': total_files,
            'total_links': total_links,
            'files_coverage': (file_embeddings_count / total_files * 100) if total_files > 0 else 0,
            'links_coverage': (link_embeddings_count / total_links * 100) if total_links > 0 else 0
        }