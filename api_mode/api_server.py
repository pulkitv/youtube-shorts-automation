import os
import sys
import logging
import threading
import time
import yaml
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from pathlib import Path

from flask import Flask, request, jsonify
from flask_restx import Api, Resource, fields
from werkzeug.exceptions import BadRequest, Unauthorized, NotFound, TooManyRequests

# Add parent directory to path FIRST to import existing modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now import from parent directory
from pdf_api_client import PDFAPIClient, RegularVoiceoverAPIClient
from youtube_uploader import YouTubeUploader
from make_webhook_client import MakeWebhookClient

# Load configuration
config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

# Load parent .env for YouTube and Make.com credentials
from dotenv import load_dotenv
parent_env = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(parent_env)

# Initialize Flask app
app = Flask(__name__)
app.config['RESTX_MASK_SWAGGER'] = False

# Import API mode specific modules
from api_models import (
    VideoGenerationRequest, 
    VideoGenerationResponse,
    JobStatusResponse,
    JobListResponse,
    validate_video_generation_request
)
from api_database import JobDatabase
from api_auth import require_api_key, check_rate_limit, check_concurrent_jobs

# Initialize Flask-RESTX for Swagger UI
api = Api(
    app,
    version='1.0',
    title='YouTube Shorts Automation API',
    description='API for automated YouTube Shorts and Posts generation',
    doc='/api/docs'
)

# Create namespaces
ns_videos = api.namespace('api/videos', description='Video generation operations')
ns_jobs = api.namespace('api/jobs', description='Job management operations')
ns_health = api.namespace('health', description='Health check')

# Initialize database
db = JobDatabase()

# Setup logging
log_config = config['logging']
logging.basicConfig(
    level=getattr(logging, log_config['level']),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_config['file']),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global state for background worker
background_worker_running = False
background_worker_thread = None

# API Models for Swagger documentation
video_generation_model = api.model('VideoGeneration', {
    'market_script': fields.String(required=True, description='Script with company data and — pause — markers'),
    'voice': fields.String(description='Voice type (alloy, echo, fable, onyx, nova, shimmer)', default='onyx'),
    'speed': fields.Float(description='Speech speed (0.5-2.0)', default=1.2),
    'video_type': fields.String(required=True, description='Video type: "short" or "regular"', enum=['short', 'regular']),
    'scheduled_datetime': fields.String(required=True, description='ISO format datetime for scheduling (e.g., 2025-12-20T10:30:00)')
})

job_status_model = api.model('JobStatus', {
    'job_id': fields.String(description='Unique job identifier'),
    'status': fields.String(description='Job status', enum=['queued', 'processing', 'completed', 'failed', 'cancelled']),
    'progress': fields.Integer(description='Progress percentage (0-100)'),
    'message': fields.String(description='Current status message'),
    'created_at': fields.String(description='Job creation timestamp'),
    'completed_at': fields.String(description='Job completion timestamp'),
    'videos_generated': fields.Integer(description='Number of videos generated'),
    'videos_uploaded': fields.Integer(description='Number of videos uploaded'),
    'error': fields.String(description='Error message if failed')
})

# ==================== ENDPOINTS ====================

@ns_health.route('')
class HealthCheck(Resource):
    """Health check endpoint"""
    
    def get(self):
        """Check API health and database status"""
        try:
            # Check database connection
            with sqlite3.connect(db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM jobs")
                job_count = cursor.fetchone()[0]
            
            # Get processing jobs count (across all API keys)
            processing_jobs = db.get_jobs_by_status('processing')
            
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "database": {
                    "connected": True,
                    "total_jobs": job_count,
                    "processing_jobs": len(processing_jobs)
                },
                "version": "1.0.0"
            }, 200
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }, 503

@ns_videos.route('/generate')
class VideoGeneration(Resource):
    @api.expect(video_generation_model)
    @api.response(200, 'Success', fields.Nested(api.model('VideoGenerationResponse', {
        'success': fields.Boolean(),
        'job_id': fields.String(),
        'message': fields.String(),
        'status': fields.String(),
        'estimated_videos': fields.Integer(),
        'check_status_url': fields.String()
    })))
    @api.response(400, 'Bad Request')
    @api.response(401, 'Unauthorized')
    @api.response(429, 'Too Many Requests')
    @require_api_key
    def post(self):
        """Generate YouTube Shorts or Posts from market script"""
        try:
            # Get API key from request context
            api_key = request.headers.get('X-API-Key')
            
            # Check rate limit
            if not check_rate_limit(api_key):
                return {
                    'success': False,
                    'error': 'Rate limit exceeded. Maximum {} requests per minute.'.format(
                        config['limits']['max_requests_per_minute']
                    )
                }, 429
            
            # Check concurrent jobs limit
            active_jobs = db.get_jobs_by_api_key(api_key, status='processing')
            if len(active_jobs) >= config['limits']['max_concurrent_jobs']:
                return {
                    'success': False,
                    'error': 'Concurrent job limit reached. Maximum {} active jobs allowed.'.format(
                        config['limits']['max_concurrent_jobs']
                    )
                }, 429
            
            # Validate request
            data = request.get_json()
            validation_result = validate_video_generation_request(data)
            
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': validation_result['error']
                }, 400
            
            # Create job in database
            job_data = {
                'api_key': api_key,
                'market_script': data['market_script'],
                'voice': data.get('voice', config['video_defaults']['voice']),
                'speed': data.get('speed', config['video_defaults']['speed']),
                'video_type': data['video_type'],
                'scheduled_datetime': data['scheduled_datetime']
            }
            
            job_id = db.create_job(**job_data)
            
            logger.info(f"Created job {job_id} for API key {api_key[:10]}...")
            
            # Estimate number of videos
            estimated_videos = data['market_script'].count('— pause —') + 1 if data['video_type'] == 'short' else 1
            
            return {
                'success': True,
                'job_id': job_id,
                'message': 'Video generation started',
                'status': 'queued',
                'estimated_videos': estimated_videos,
                'check_status_url': f'/api/jobs/{job_id}'
            }, 200
            
        except Exception as e:
            logger.error(f"Error in video generation: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'Internal server error: {str(e)}'
            }, 500

@ns_jobs.route('/<string:job_id>')
class JobStatus(Resource):
    @api.response(200, 'Success', job_status_model)
    @api.response(401, 'Unauthorized')
    @api.response(404, 'Job not found')
    @require_api_key
    def get(self, job_id):
        """Get job status by ID"""
        try:
            api_key = request.headers.get('X-API-Key')
            
            job = db.get_job(job_id)
            
            if not job:
                return {
                    'success': False,
                    'error': 'Job not found'
                }, 404
            
            # Verify API key matches
            if job['api_key'] != api_key:
                return {
                    'success': False,
                    'error': 'Unauthorized access to job'
                }, 401
            
            return {
                'job_id': job['job_id'],
                'status': job['status'],
                'progress': job['progress'],
                'message': job.get('message', ''),
                'created_at': job['created_at'],
                'completed_at': job.get('completed_at'),
                'videos_generated': job['videos_generated'],
                'videos_uploaded': job['videos_uploaded'],
                'error': job.get('error')
            }, 200
            
        except Exception as e:
            logger.error(f"Error getting job status: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'Internal server error: {str(e)}'
            }, 500
    
    @api.response(200, 'Job cancelled')
    @api.response(401, 'Unauthorized')
    @api.response(404, 'Job not found')
    @require_api_key
    def delete(self, job_id):
        """Cancel a job"""
        try:
            api_key = request.headers.get('X-API-Key')
            
            job = db.get_job(job_id)
            
            if not job:
                return {
                    'success': False,
                    'error': 'Job not found'
                }, 404
            
            # Verify API key matches
            if job['api_key'] != api_key:
                return {
                    'success': False,
                    'error': 'Unauthorized access to job'
                }, 401
            
            # Only allow cancelling queued or processing jobs
            if job['status'] in ['completed', 'failed', 'cancelled']:
                return {
                    'success': False,
                    'error': f'Cannot cancel job with status: {job["status"]}'
                }, 400
            
            # Update job status to cancelled
            db.update_job_status(
                job_id=job_id,
                status='cancelled',
                message='Job cancelled by user',
                progress=0
            )
            
            logger.info(f"Job {job_id} cancelled by API key {api_key[:10]}...")
            
            return {
                'success': True,
                'message': 'Job cancelled successfully',
                'job_id': job_id
            }, 200
            
        except Exception as e:
            logger.error(f"Error cancelling job: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'Internal server error: {str(e)}'
            }, 500

@ns_jobs.route('')
class JobList(Resource):
    @api.response(200, 'Success')
    @api.response(401, 'Unauthorized')
    @require_api_key
    def get(self):
        """List all jobs for the authenticated API key"""
        try:
            api_key = request.headers.get('X-API-Key')
            
            # Get query parameters
            status_filter = request.args.get('status')  # Optional: filter by status
            limit = int(request.args.get('limit', 50))  # Default: 50 jobs
            
            # Get jobs for this API key
            jobs = db.get_jobs_by_api_key(api_key, status=status_filter, limit=limit)
            
            return {
                'success': True,
                'count': len(jobs),
                'jobs': [
                    {
                        'job_id': job['job_id'],
                        'status': job['status'],
                        'progress': job['progress'],
                        'video_type': job['video_type'],
                        'created_at': job['created_at'],
                        'completed_at': job.get('completed_at'),
                        'videos_generated': job['videos_generated'],
                        'videos_uploaded': job['videos_uploaded']
                    }
                    for job in jobs
                ]
            }, 200
            
        except Exception as e:
            logger.error(f"Error listing jobs: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'Internal server error: {str(e)}'
            }, 500

# ==================== BACKGROUND JOB PROCESSOR ====================

class BackgroundJobProcessor:
    """Processes jobs in the background"""
    
    def __init__(self):
        self.running = False
        self.automation = None
        self.api_client = None
        self.voiceover_client = None
        self.youtube_uploader = None
        self.make_webhook_client = None
        
    def initialize_clients(self):
        """Initialize API clients and automation"""
        try:
            # Load parent .env file
            from dotenv import load_dotenv
            parent_env = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
            load_dotenv(parent_env)
            
            # Initialize API clients
            base_url = os.getenv('PDF_API_BASE_URL', 'http://localhost:5000')
            self.api_client = PDFAPIClient(
                base_url=base_url,
                endpoint='/api/v1/generate-shorts'
            )
            self.voiceover_client = RegularVoiceoverAPIClient(base_url=base_url)
            
            # Initialize YouTube uploader
            client_id = os.getenv('YOUTUBE_CLIENT_ID')
            client_secret = os.getenv('YOUTUBE_CLIENT_SECRET')
            refresh_token = os.getenv('YOUTUBE_REFRESH_TOKEN')
            
            if client_id and client_secret and refresh_token:
                self.youtube_uploader = YouTubeUploader(
                    client_id=client_id,
                    client_secret=client_secret,
                    refresh_token=refresh_token
                )
                logger.info("✅ YouTube uploader initialized")
            else:
                logger.warning("⚠️  YouTube credentials not found in .env, YouTube upload disabled")
            
            # Initialize Make.com webhook client
            webhook_url = os.getenv('MAKE_WEBHOOK_URL')
            make_api_key = os.getenv('MAKE_API_KEY')
            
            if webhook_url and make_api_key:
                self.make_webhook_client = MakeWebhookClient(
                    webhook_url=webhook_url,
                    api_key=make_api_key
                )
                logger.info("✅ Make.com webhook client initialized")
            else:
                logger.warning("⚠️  Make.com credentials not found, Twitter posting disabled")
            
            logger.info("✅ API clients initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize clients: {e}", exc_info=True)
            return False
    
    def process_job(self, job: Dict):
        """Process a single job"""
        job_id = job['job_id']
        
        try:
            logger.info(f"Processing job {job_id} (type: {job['video_type']})")
            
            # Update status to processing
            db.update_job_status(
                job_id=job_id,
                status='processing',
                message='Starting video generation...',
                progress=10
            )
            
            # Generate videos based on type
            if job['video_type'] == 'short':
                video_files = self._generate_shorts(job)
            else:
                video_files = self._generate_regular_video(job)
            
            if not video_files:
                raise Exception("No videos generated")
            
            # Update progress
            db.update_job_status(
                job_id=job_id,
                status='processing',
                message=f'Generated {len(video_files)} video(s). Processing uploads...',
                progress=60,
                videos_generated=len(video_files)
            )
            
            # Upload videos immediately if scheduled time is now or in the past
            # Otherwise, add to upload queue for scheduled upload
            uploaded_count = self._process_uploads(job, video_files)
            
            # Mark as completed
            db.update_job_status(
                job_id=job_id,
                status='completed',
                message=f'Successfully generated {len(video_files)} video(s), uploaded {uploaded_count}',
                progress=100,
                videos_uploaded=uploaded_count,
                completed_at=datetime.now().isoformat()
            )
            
            logger.info(f"✅ Job {job_id} completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Job {job_id} failed: {e}", exc_info=True)
            db.update_job_status(
                job_id=job_id,
                status='failed',
                message=f'Error: {str(e)}',
                error=str(e),
                completed_at=datetime.now().isoformat()
            )
    
    def _generate_shorts(self, job: Dict) -> List[str]:
        """Generate YouTube Shorts"""
        logger.info(f"Generating shorts for job {job['job_id']}")
        
        # Ensure clients are initialized
        if not self.api_client:
            raise Exception("API client not initialized. Please check client initialization.")
        
        # Download folder from parent directory
        download_folder = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'downloads'
        )
        
        # Update progress
        db.update_job_status(
            job_id=job['job_id'],
            status='processing',
            message='Calling video generation API...',
            progress=20
        )
        
        # Generate shorts using existing API client
        video_files = self.api_client.generate_and_download_videos(
            script=job['market_script'],
            download_folder=download_folder,
            voice=job['voice'],
            speed=job['speed']
        )
        
        db.update_job_status(
            job_id=job['job_id'],
            status='processing',
            message=f'Downloaded {len(video_files)} video(s)',
            progress=50
        )
        
        return video_files
    
    def _generate_regular_video(self, job: Dict) -> List[str]:
        """Generate regular format video"""
        logger.info(f"Generating regular video for job {job['job_id']}")
        
        # Ensure clients are initialized
        if not self.voiceover_client:
            raise Exception("Voiceover client not initialized. Please check client initialization.")
        
        download_folder = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'downloads'
        )
        
        # Update progress
        db.update_job_status(
            job_id=job['job_id'],
            status='processing',
            message='Calling voiceover API...',
            progress=20
        )
        
        # Generate video using existing voiceover client
        video_file = self.voiceover_client.generate_and_download_video(
            script=job['market_script'],
            download_folder=download_folder,
            voice=job['voice'],
            speed=job['speed']
        )
        
        if not video_file:
            return []
        
        db.update_job_status(
            job_id=job['job_id'],
            status='processing',
            message='Video downloaded successfully',
            progress=50
        )
        
        return [video_file]
    
    def _process_uploads(self, job: Dict, video_files: List[str]) -> int:
        """Process video uploads - upload immediately but schedule for future publish"""
        scheduled_time = datetime.fromisoformat(job['scheduled_datetime'])
        
        # Get interval from parent .env
        interval_hours = float(os.getenv('SCHEDULE_INTERVAL_HOURS', 2.5))
        
        uploaded_count = 0
        
        for i, video_path in enumerate(video_files):
            video_scheduled_time = scheduled_time + timedelta(hours=interval_hours * i)
            
            logger.info(f"Uploading video immediately, scheduled to publish at {video_scheduled_time.strftime('%Y-%m-%d %H:%M')}: {os.path.basename(video_path)}")
            
            if self._upload_video_now(job, video_path, video_scheduled_time):
                uploaded_count += 1
                
                # Update progress
                progress = 60 + int((40 * (i + 1)) / len(video_files))
                db.update_job_status(
                    job_id=job['job_id'],
                    status='processing',
                    message=f'Uploaded {uploaded_count}/{len(video_files)} video(s)',
                    progress=progress,
                    videos_uploaded=uploaded_count
                )
        
        return uploaded_count

    def _upload_video_now(self, job: Dict, video_path: str, scheduled_publish_time: datetime) -> bool:
        """Upload a video to YouTube immediately and schedule it for future publishing"""
        try:
            if not self.youtube_uploader:
                logger.error("YouTube uploader not initialized")
                return False
            
            filename = os.path.basename(video_path)
            title = os.path.splitext(filename)[0].replace('_', ' ')
            
            # Check if scheduled time is in the future
            now = datetime.now()
            is_future = scheduled_publish_time > now
            
            # Determine privacy status based on scheduled time
            privacy_status = 'private' if is_future else 'public'
            
            # Prepare video metadata
            video_metadata = {
                'title': title[:100],  # YouTube title limit
                'description': (
                    "A different way of journaling. Bringing to you my favorite content in a concise, readable format. "
                    "Have included a bit of research into my thoughts. Some real-world examples. "
                    "You will find here some thought-provoking ideas and some very less known facts. "
                    "And possibly some learnings that I undergo in my journey. "
                    "Wrapped around some research and use of AI tools to present the content in a better format."
                ),
                'tags': [
                    'BusinessStories', 'Marketing', 'CaseStudy', 'IndianBusiness', 
                    'Entrepreneurship', 'Strategy', 'news', 'shorts', 'ai', 'automation', 
                    'daily', 'market', 'stocks', 'finance', 'business', 'updates', 
                    'summary', 'key insights', 'market signals', 'listed companies', 
                    'investing', 'financial news'
                ],
                'category_id': '22',  # People & Blogs
            }
            
            logger.info(f"📤 Uploading to YouTube: {title}")
            logger.info(f"   Privacy: {privacy_status}")
            
            # Step 1: Upload the video
            video_id = self.youtube_uploader.upload_video(
                video_path=video_path,
                title=video_metadata['title'],
                description=video_metadata['description'],
                tags=video_metadata['tags'],
                category_id=video_metadata['category_id'],
                privacy_status=privacy_status,
                video_type=job['video_type']  # 'short' or 'post'
            )
            
            if not video_id:
                logger.error(f"Failed to upload video: {filename}")
                return False
            
            logger.info(f"✅ Video uploaded successfully. Video ID: {video_id}")
            logger.info(f"🔗 Video URL: https://www.youtube.com/watch?v={video_id}")
            
            # Step 2: Schedule the video if it's for future publishing
            if is_future:
                logger.info(f"🕒 Scheduling video for: {scheduled_publish_time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                schedule_success = self.youtube_uploader.schedule_video(
                    video_id=video_id,
                    publish_time=scheduled_publish_time
                )
                
                if schedule_success:
                    logger.info(f"⏰ Video scheduled successfully for: {scheduled_publish_time.strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    logger.warning(f"⚠️  Failed to schedule video, but video is uploaded as private")
            else:
                logger.info(f"✅ Video published immediately (scheduled time has passed)")
            
            # Step 3: Send to Make.com webhook with scheduled time for Twitter posting
            if self.make_webhook_client:
                self._post_to_twitter(video_id, title, job, scheduled_publish_time)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload video: {e}", exc_info=True)
            return False

    def _post_to_twitter(self, video_id: str, title: str, job: Dict, scheduled_publish_time: datetime):
        """Send video info to Make.com webhook with scheduled time for Twitter posting"""
        try:
            if not self.make_webhook_client:
                logger.warning("⚠️  Make.com webhook client not initialized, skipping Twitter notification")
                return
            
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            # ✅ FIX: Use the full script from job instead of title
            full_script = job.get('market_script', title)

            logger.info(f"🐦 Sending to Make.com webhook for Twitter posting at {scheduled_publish_time.strftime('%Y-%m-%d %H:%M')}: {title}")
            logger.info(f"📝 Full script length: {len(full_script)} characters")
            
            # Send to Make.com webhook with scheduled time
            response = self.make_webhook_client.send_tweet_data(
                video_url=video_url,
                scheduled_time=scheduled_publish_time,
                full_content=full_script  # ✅ Pass full script instead of title
            )
            
            if response:
                logger.info(f"✅ Successfully sent to Make.com webhook (scheduled for {scheduled_publish_time.strftime('%Y-%m-%d %H:%M')})")
            else:
                logger.warning(f"⚠️  Failed to send to Make.com webhook")
                
        except Exception as e:
            logger.error(f"Failed to send to Make.com webhook: {e}", exc_info=True)

    def _add_to_upload_queue(self, job: Dict, video_files: List[str], start_index: int = 0):
        """This method is no longer needed - all uploads are immediate"""
        # Kept for backward compatibility but does nothing
        logger.info("Note: _add_to_upload_queue called but all uploads are now immediate")
        pass
    
    def run(self):
        """Main background processing loop"""
        self.running = True
        logger.info("🚀 Background job processor started")
        
        if not self.initialize_clients():
            logger.error("Failed to initialize clients, stopping processor")
            self.running = False
            return
        
        poll_interval = config['processing']['poll_interval_seconds']
        
        while self.running:
            try:
                # Get all queued jobs
                queued_jobs = db.get_jobs_by_status('queued')
                
                if queued_jobs:
                    logger.info(f"Found {len(queued_jobs)} queued job(s)")
                    
                    for job in queued_jobs:
                        if not self.running:
                            break
                        
                        self.process_job(job)
                
                # Sleep before next poll
                time.sleep(poll_interval)
                
            except Exception as e:
                logger.error(f"Error in background processor: {e}", exc_info=True)
                time.sleep(poll_interval)
        
        logger.info("🛑 Background job processor stopped")
    
    def stop(self):
        """Stop the background processor"""
        self.running = False

# Global processor instance
job_processor = BackgroundJobProcessor()

def start_background_worker():
    """Start background worker thread"""
    global background_worker_running, background_worker_thread
    
    if background_worker_running:
        logger.warning("Background worker already running")
        return
    
    background_worker_running = True
    background_worker_thread = threading.Thread(target=job_processor.run, daemon=True)
    background_worker_thread.start()
    logger.info("✅ Background worker thread started")

def stop_background_worker():
    """Stop background worker thread"""
    global background_worker_running
    
    if not background_worker_running:
        return
    
    logger.info("Stopping background worker...")
    job_processor.stop()
    background_worker_running = False
    
    if background_worker_thread:
        background_worker_thread.join(timeout=5)
    
    logger.info("✅ Background worker stopped")



# ==================== MAIN ====================

if __name__ == '__main__':
    try:
        logger.info("=" * 80)
        logger.info("🚀 Starting YouTube Shorts Automation API Server")
        logger.info("=" * 80)
        
        # Start background worker
        start_background_worker()
        
        # Start Flask server
        host = config['api']['host']
        port = config['api']['port']
        debug = config['api']['debug']
        
        logger.info(f"📡 API Server starting on http://{host}:{port}")
        logger.info(f"📚 API Documentation available at http://localhost:{port}/api/docs")
        logger.info(f"🔑 API Keys configured: {len(config['api']['api_keys'])}")
        logger.info("=" * 80)
        
        app.run(
            host=host,
            port=port,
            debug=debug,
            use_reloader=False  # Disable reloader to prevent double initialization
        )
        
    except KeyboardInterrupt:
        logger.info("\n🛑 Received shutdown signal")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
    finally:
        stop_background_worker()
        db.close()
        logger.info("👋 API Server shutdown complete")
