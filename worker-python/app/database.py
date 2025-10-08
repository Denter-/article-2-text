"""
Database operations for Python AI Worker
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import Optional, Dict, Any
from datetime import datetime
import logging
import uuid

logger = logging.getLogger(__name__)


class Database:
    """Database connection manager"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self._conn = None
    
    def connect(self):
        """Establish database connection"""
        self._conn = psycopg2.connect(self.database_url)
        logger.info("Connected to PostgreSQL")
    
    def close(self):
        """Close database connection"""
        if self._conn:
            self._conn.close()
            logger.info("Closed PostgreSQL connection")
    
    @contextmanager
    def get_cursor(self):
        """Get a cursor with automatic commit/rollback"""
        cursor = self._conn.cursor(cursor_factory=RealDictCursor)
        try:
            yield cursor
            self._conn.commit()
        except Exception as e:
            self._conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            cursor.close()
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job by ID"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM jobs WHERE id = %s
            """, (job_id,))
            return cursor.fetchone()
    
    def update_job_status(self, job_id: str, status: str, 
                         progress: int = None, message: str = None,
                         error: str = None):
        """Update job status"""
        updates = ["status = %s"]
        params = [status]
        
        if progress is not None:
            updates.append("progress_percent = %s")
            params.append(progress)
        
        if message is not None:
            updates.append("progress_message = %s")
            params.append(message)
        
        if error is not None:
            updates.append("error_message = %s")
            params.append(error)
        
        if status == "processing":
            updates.append("started_at = NOW()")
        elif status == "completed":
            updates.append("completed_at = NOW()")
            # Only set progress_percent to 100 if no explicit progress was provided
            if progress is None:
                updates.append("progress_percent = 100")
        
        query = f"UPDATE jobs SET {', '.join(updates)} WHERE id = %s"
        params.append(job_id)
        
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
    
    def update_job_result(self, job_id: str, result_path: str,
                         title: str = None, author: str = None,
                         word_count: int = None, image_count: int = None,
                         markdown_content: str = None):
        """Update job with extraction results"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                UPDATE jobs
                SET result_path = %s,
                    title = %s,
                    author = %s,
                    word_count = %s,
                    image_count = %s,
                    markdown_content = %s
                WHERE id = %s
            """, (result_path, title, author, word_count, image_count, markdown_content, job_id))
    
    def get_site_config(self, domain: str) -> Optional[Dict[str, Any]]:
        """Get site configuration by domain"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM site_configs WHERE domain = %s
            """, (domain,))
            return cursor.fetchone()
    
    def save_site_config(self, domain: str, config_yaml: str, 
                        requires_browser: bool, learned_by_user_id: str):
        """Save or update site configuration"""
        with self.get_cursor() as cursor:
            cursor.execute("""
                INSERT INTO site_configs 
                (domain, config_yaml, requires_browser, learned_by_user_id, 
                 learned_at, last_checked_at, next_check_at)
                VALUES (%s, %s, %s, %s, NOW(), NOW(), NOW() + INTERVAL '30 days')
                ON CONFLICT (domain) 
                DO UPDATE SET
                    config_yaml = EXCLUDED.config_yaml,
                    requires_browser = EXCLUDED.requires_browser,
                    learned_at = NOW(),
                    last_checked_at = NOW()
            """, (domain, config_yaml, requires_browser, learned_by_user_id))

