"""
API Database - SQLite operations for job storage and tracking
"""
import sqlite3
import json
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from pathlib import Path


class JobDatabase:
    """Manages job persistence in SQLite database"""
    
    def __init__(self, db_path: str = "jobs.db"):
        """
        Initialize database connection
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._initialize_db()
    
    def _initialize_db(self):
        """Create tables if they don't exist"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Jobs table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS jobs (
                        job_id TEXT PRIMARY KEY,
                        api_key TEXT NOT NULL,
                        status TEXT NOT NULL,
                        progress INTEGER DEFAULT 0,
                        message TEXT DEFAULT '',
                        market_script TEXT NOT NULL,
                        voice TEXT NOT NULL,
                        speed REAL NOT NULL,
                        video_type TEXT NOT NULL,
                        scheduled_datetime TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        completed_at TEXT,
                        videos_generated INTEGER DEFAULT 0,
                        videos_uploaded INTEGER DEFAULT 0,
                        estimated_videos INTEGER DEFAULT 0,
                        error TEXT,
                        session_id TEXT
                    )
                """)
                
                # Index for faster queries
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_status 
                    ON jobs(status)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_api_key 
                    ON jobs(api_key)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_created_at 
                    ON jobs(created_at)
                """)
                
                conn.commit()
                self.logger.info(f"✅ Database initialized: {self.db_path}")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    def create_job(self, 
                   api_key: str,
                   market_script: str,
                   voice: str,
                   speed: float,
                   video_type: str,
                   scheduled_datetime: str,
                   estimated_videos: int = 1,
                   job_id: Optional[str] = None) -> str:
        """
        Create a new job entry
        
        Args:
            api_key: API key used for authentication
            market_script: Video script content
            voice: Voice to use
            speed: Speech speed
            video_type: 'short' or 'regular'
            scheduled_datetime: When to upload
            estimated_videos: Estimated number of videos
            job_id: Optional job identifier (auto-generated if not provided)
            
        Returns:
            Job ID string if successful, None otherwise
        """
        try:
            # Generate job_id if not provided
            if job_id is None:
                import time
                import random
                import string
                timestamp = int(time.time())
                random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
                job_id = f"job_{timestamp}_{random_suffix}"
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO jobs (
                        job_id, api_key, status, progress, message,
                        market_script, voice, speed, video_type,
                        scheduled_datetime, created_at, estimated_videos
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job_id,
                    api_key,
                    "queued",
                    0,
                    "Job queued for processing",
                    market_script,
                    voice,
                    speed,
                    video_type,
                    scheduled_datetime,
                    datetime.now().isoformat(),
                    estimated_videos
                ))
                
                conn.commit()
                self.logger.info(f"✅ Created job: {job_id}")
                return job_id
                
        except Exception as e:
            self.logger.error(f"Failed to create job: {e}")
            return None
    
    def update_job_status(
        self,
        job_id: str,
        status: str,
        progress: int = 0,
        message: str = "",
        error: str = None,
        videos_generated: int = None,
        videos_uploaded: int = None,
        completed_at: str = None
    ) -> bool:
        """
        Update job status and progress
    
        Args:
            job_id: Job identifier
            status: New status (queued, processing, completed, failed, cancelled)
            progress: Progress percentage (0-100)
            message: Status message
            error: Error message if failed
            videos_generated: Number of videos generated
            videos_uploaded: Number of videos uploaded
            completed_at: Completion timestamp
        
        Returns:
            True if successful
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Build update query dynamically based on provided parameters
                update_fields = ["status = ?", "progress = ?", "message = ?"]
                params = [status, progress, message]
                
                if error is not None:
                    update_fields.append("error = ?")
                    params.append(error)
                
                if videos_generated is not None:
                    update_fields.append("videos_generated = ?")
                    params.append(videos_generated)
                
                if videos_uploaded is not None:
                    update_fields.append("videos_uploaded = ?")
                    params.append(videos_uploaded)
                
                if completed_at is not None:
                    update_fields.append("completed_at = ?")
                    params.append(completed_at)
                elif status in ['completed', 'failed', 'cancelled']:
                    # Auto-set completed_at if status is terminal
                    update_fields.append("completed_at = ?")
                    params.append(datetime.now().isoformat())
                
                # Add job_id to params
                params.append(job_id)
                
                query = f"""
                    UPDATE jobs 
                    SET {', '.join(update_fields)}
                    WHERE job_id = ?
                """
                
                cursor.execute(query, params)
                conn.commit()
                
                self.logger.info(f"Updated job {job_id}: status={status}, progress={progress}%")
                return True
            
        except Exception as e:
            self.logger.error(f"Failed to update job status: {e}")
            return False
    
    def get_job(self, job_id: str) -> Optional[Dict]:
        """
        Get job details by ID
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job dict or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
                row = cursor.fetchone()
                
                if row:
                    return dict(row)
                
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to get job {job_id}: {e}")
            return None
    
    def get_jobs_by_status(self, status: str, api_key: Optional[str] = None) -> List[Dict]:
        """
        Get all jobs with a specific status
        
        Args:
            status: Job status to filter by
            api_key: Optional API key to filter by
            
        Returns:
            List of job dicts
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                if api_key:
                    cursor.execute(
                        "SELECT * FROM jobs WHERE status = ? AND api_key = ? ORDER BY created_at DESC",
                        (status, api_key)
                    )
                else:
                    cursor.execute(
                        "SELECT * FROM jobs WHERE status = ? ORDER BY created_at DESC",
                        (status,)
                    )
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            self.logger.error(f"Failed to get jobs by status {status}: {e}")
            return []
    
    def get_jobs_by_api_key(self, api_key: str, status: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """
        Get all jobs for a specific API key
        
        Args:
            api_key: API key to filter by
            status: Optional status to filter by
            limit: Maximum number of jobs to return
            
        Returns:
            List of job dicts
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                if status:
                    cursor.execute(
                        "SELECT * FROM jobs WHERE api_key = ? AND status = ? ORDER BY created_at DESC LIMIT ?",
                        (api_key, status, limit)
                    )
                else:
                    cursor.execute(
                        "SELECT * FROM jobs WHERE api_key = ? ORDER BY created_at DESC LIMIT ?",
                        (api_key, limit)
                    )
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            self.logger.error(f"Failed to get jobs for API key: {e}")
            return []
    
    def count_active_jobs(self, api_key: str) -> int:
        """
        Count active jobs (queued or processing) for an API key
        
        Args:
            api_key: API key to count jobs for
            
        Returns:
            Number of active jobs
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT COUNT(*) FROM jobs 
                    WHERE api_key = ? AND status IN ('queued', 'processing')
                """, (api_key,))
                
                count = cursor.fetchone()[0]
                return count
                
        except Exception as e:
            self.logger.error(f"Failed to count active jobs: {e}")
            return 0
    
    def cleanup_old_jobs(self, days: int = 7) -> int:
        """
        Delete jobs older than specified days
        
        Args:
            days: Delete jobs older than this many days
            
        Returns:
            Number of jobs deleted
        """
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    DELETE FROM jobs 
                    WHERE created_at < ? AND status IN ('completed', 'failed', 'cancelled')
                """, (cutoff_date,))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                if deleted_count > 0:
                    self.logger.info(f"🧹 Cleaned up {deleted_count} old jobs")
                
                return deleted_count
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup old jobs: {e}")
            return 0
    
    def get_all_jobs(self, limit: int = 100) -> List[Dict]:
        """
        Get all jobs (for admin purposes)
        
        Args:
            limit: Maximum number of jobs to return
            
        Returns:
            List of job dicts
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute(
                    "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                )
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            self.logger.error(f"Failed to get all jobs: {e}")
            return []
    
    def close(self):
        """Close database connections (cleanup method)"""
        # SQLite connections are managed with context managers
        # so no persistent connection to close
        self.logger.debug("Database cleanup called")