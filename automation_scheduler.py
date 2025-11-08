import os
import json
import logging
import schedule
import time
import threading
import sys
import importlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dotenv import load_dotenv
from pathlib import Path

from youtube_uploader import YouTubeUploader
from pdf_api_client import PDFAPIClient, RegularVoiceoverAPIClient

class YouTubeShortsAutomation:
    """Main automation class that coordinates API calls, video downloads, and YouTube uploads"""
    
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Initialize logging
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        self.config = self.load_config()
        
        # Initialize components
        self.youtube_uploader = YouTubeUploader(
            client_id=self.config['youtube']['client_id'],
            client_secret=self.config['youtube']['client_secret'],
            refresh_token=self.config['youtube']['refresh_token']
        )
        
        # Initialize both API clients
        self.api_client = PDFAPIClient(
            base_url=self.config['api']['base_url'],
            endpoint=self.config['api']['endpoint']
        )
        
        self.voiceover_client = RegularVoiceoverAPIClient(
            base_url=self.config['api']['base_url']
        )
        
        # Upload queue management
        self.upload_queue_file = self.config['files']['upload_queue_file']
        self.upload_queue = self.load_upload_queue()
        
        # Create directories
        self.create_directories()
        
        # Add iteration tracking
        self.iteration_stats = {
            'total_videos_generated': 0,
            'successful_uploads': 0,
            'failed_uploads': 0,
            'last_iteration_time': None,
            'performance_metrics': []
        }
        
        # Enhanced retry configuration
        self.retry_config = {
            'max_retries': 5,
            'backoff_factor': 2,
            'retry_delay_minutes': [5, 15, 30, 60, 120]  # Progressive delays
        }
        
        self.logger.info("Enhanced automation with iteration tracking initialized")
        
        self.logger.info("YouTube Shorts & Posts Automation initialized successfully")
    
    def setup_logging(self):
        """Configure logging"""
        log_level = os.getenv('LOG_LEVEL', 'INFO')
        log_file = os.getenv('LOG_FILE', 'youtube_automation.log')
        
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
    
    def load_config(self) -> Dict:
        """Load configuration from environment variables"""
        return {
            'youtube': {
                'client_id': os.getenv('YOUTUBE_CLIENT_ID'),
                'client_secret': os.getenv('YOUTUBE_CLIENT_SECRET'),
                'refresh_token': os.getenv('YOUTUBE_REFRESH_TOKEN'),
                'channel_id': os.getenv('CHANNEL_ID'),
                'default_title_prefix': os.getenv('DEFAULT_TITLE_PREFIX', 'Daily News Shorts'),
                'default_description': os.getenv('DEFAULT_DESCRIPTION', 'Automated YouTube Shorts generated from news content'),
                'default_tags': os.getenv('DEFAULT_TAGS', 'news,shorts,ai,automation,daily').split(',')
            },
            'api': {
                'base_url': os.getenv('PDF_API_BASE_URL', 'http://localhost:5000'),
                'endpoint': os.getenv('PDF_API_ENDPOINT', '/api/v1/generate-shorts')
            },
            'scheduling': {
                'videos_per_batch': int(os.getenv('VIDEOS_PER_BATCH', 2)),
                'interval_hours': float(os.getenv('SCHEDULE_INTERVAL_HOURS', 2.5)),
                'max_retries': int(os.getenv('MAX_RETRIES', 3))
            },
            'files': {
                'download_folder': os.getenv('DOWNLOAD_FOLDER', 'downloads'),
                'processed_folder': os.getenv('PROCESSED_FOLDER', 'processed'),
                'upload_queue_file': os.getenv('UPLOAD_QUEUE_FILE', 'upload_queue.json')
            }
        }
    
    def create_directories(self):
        """Create necessary directories"""
        for folder in [self.config['files']['download_folder'], 
                      self.config['files']['processed_folder']]:
            os.makedirs(folder, exist_ok=True)
    
    def load_upload_queue(self) -> List[Dict]:
        """Load the upload queue from file"""
        if os.path.exists(self.upload_queue_file):
            try:
                with open(self.upload_queue_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Failed to load upload queue: {e}")
        return []
    
    def save_upload_queue(self):
        """Save the upload queue to file"""
        try:
            with open(self.upload_queue_file, 'w') as f:
                json.dump(self.upload_queue, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Failed to save upload queue: {e}")
    
    def add_videos_to_queue(self, video_files: List[str], script_info: Dict, custom_start_time: Optional[datetime] = None, video_type: str = "short"):
        """Add videos to the upload queue with scheduled publication times"""
        timestamp = datetime.now()
        
        # Calculate next available publication slots
        if custom_start_time:
            # Use the custom start time provided by user
            last_scheduled_time = custom_start_time - timedelta(hours=self.config['scheduling']['interval_hours'])
            self.logger.info(f"Using custom start time: {custom_start_time}")
        else:
            # Use automatic scheduling based on last scheduled time
            last_scheduled_time = self.get_last_scheduled_time()
            self.logger.info(f"Using automatic scheduling from: {last_scheduled_time}")
        
        interval_hours = self.config['scheduling']['interval_hours']
        
        for i, video_path in enumerate(video_files):
            # Extract filename without extension for the title
            filename = os.path.basename(video_path)
            title = os.path.splitext(filename)[0]  # Remove .mp4 extension
            
            # Remove 'api' prefix if present
            if title.lower().startswith('api_'):
                title = title[4:]  # Remove 'api_' prefix
            elif title.lower().startswith('api '):
                title = title[4:]  # Remove 'api ' prefix
            
            # Replace underscores with spaces for better readability
            title = title.replace('_', ' ')
            
            # Calculate scheduled publication time
            scheduled_time = last_scheduled_time + timedelta(hours=interval_hours * (i + 1))
            
            # Adjust description based on video type
            base_description = f"{self.config['youtube']['default_description']}\n\nGenerated on: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
            if video_type == "post":
                # For regular posts, add more detailed description
                description = f"📊 Market Analysis & Business Updates\n\n{base_description}\n\n🎯 Stay updated with the latest market trends and business news."
            else:
                # For shorts, keep it concise
                description = base_description
            
            video_info = {
                'video_path': video_path,
                'title': title,  # Use cleaned filename as title
                'description': description,
                'tags': self.config['youtube']['default_tags'],
                'added_at': timestamp,
                'scheduled_publish_time': scheduled_time,
                'script_info': script_info,
                'upload_attempts': 0,
                'status': 'pending',
                'video_type': video_type  # Store video type
            }
            self.upload_queue.append(video_info)
            
            video_type_label = "YouTube Short" if video_type == "short" else "YouTube Post"
            self.logger.info(f"Scheduled '{title}' as {video_type_label} for {scheduled_time.strftime('%Y-%m-%d %H:%M')} ({scheduled_time.strftime('%I:%M %p')} IST)")
        
        self.save_upload_queue()
        video_type_label = "YouTube Shorts" if video_type == "short" else "YouTube Posts"
        self.logger.info(f"Added {len(video_files)} videos to upload queue as {video_type_label} with scheduled publication times")

    def get_last_scheduled_time(self) -> datetime:
        """Get the last scheduled publication time from the queue, or current time if none"""
        current_time = datetime.now()
        scheduled_times = []
        
        for video in self.upload_queue:
            if 'scheduled_publish_time' in video and video.get('status') in ['scheduled', 'pending']:
                if isinstance(video['scheduled_publish_time'], str):
                    scheduled_time = datetime.fromisoformat(video['scheduled_publish_time'].replace('Z', '+00:00'))
                else:
                    scheduled_time = video['scheduled_publish_time']
                
                # Only consider future scheduled times
                if scheduled_time > current_time:
                    scheduled_times.append(scheduled_time)
        
        if scheduled_times:
            return max(scheduled_times)
        else:
            # If no future videos scheduled, start from current time
            return current_time
    
    def generate_videos_from_script(self, script: str, voice: str = "onyx", speed: float = 1.2) -> List[str]:
        """Generate videos from a script using the API"""
        self.logger.info("Starting video generation from script")
        
        try:
            video_files = self.api_client.generate_and_download_videos(
                script=script,
                download_folder=self.config['files']['download_folder'],
                voice=voice,
                speed=speed
            )
            
            if video_files:
                # Add videos to upload queue
                script_info = {
                    'script': script[:200] + '...' if len(script) > 200 else script,
                    'voice': voice,
                    'speed': speed,
                    'generated_at': datetime.now()
                }
                self.add_videos_to_queue(video_files, script_info)
                
            return video_files
            
        except Exception as e:
            self.logger.error(f"Failed to generate videos: {e}")
            return []
    
    def generate_youtube_posts_from_script(self, script: str, voice: str = "onyx", speed: float = 1.2) -> List[str]:
        """Generate YouTube Posts (landscape videos) from a script using the Regular Format Voiceover API"""
        self.logger.info("Starting YouTube Posts generation from script")
        
        try:
            video_path = self.voiceover_client.generate_and_download_video(
                script=script,
                download_folder=self.config['files']['download_folder'],
                voice=voice,
                speed=speed
            )
            
            if video_path:
                # Add video to upload queue with 'post' type
                script_info = {
                    'script': script[:200] + '...' if len(script) > 200 else script,
                    'voice': voice,
                    'speed': speed,
                    'generated_at': datetime.now()
                }
                self.add_videos_to_queue([video_path], script_info, video_type="post")
                return [video_path]
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"Failed to generate YouTube Posts: {e}")
            return []
    
    def upload_pending_videos(self):
        """Upload pending videos and schedule them for publication"""
        current_time = datetime.now()
        max_retries = self.config['scheduling']['max_retries']
        
        # Get videos that are ready to be uploaded (not already uploaded/scheduled)
        pending_videos = [v for v in self.upload_queue if v['status'] == 'pending']
        
        if not pending_videos:
            self.logger.info("No pending videos to upload")
            return
        
        # Upload all pending videos as private (they'll be scheduled for later publication)
        for video_info in pending_videos:
            try:
                video_path = video_info['video_path']
                
                if not os.path.exists(video_path):
                    self.logger.error(f"Video file not found: {video_path}")
                    video_info['status'] = 'failed'
                    video_info['error'] = 'File not found'
                    continue
                
                scheduled_time = video_info.get('scheduled_publish_time')
                if isinstance(scheduled_time, str):
                    scheduled_time = datetime.fromisoformat(scheduled_time.replace('Z', '+00:00'))
                
                # Get video type (default to 'short' for backward compatibility)
                video_type = video_info.get('video_type', 'short')
                video_type_label = "YouTube Short" if video_type == "short" else "YouTube Post"
                
                self.logger.info(f"Uploading {video_type_label} as private: {video_info['title']} (scheduled for {scheduled_time})")
                
                # Upload as private initially with video type
                video_id = self.youtube_uploader.upload_video(
                    video_path=video_path,
                    title=video_info['title'],
                    description=video_info['description'],
                    tags=video_info['tags'],
                    privacy_status="private",  # Upload as private
                    video_type=video_type  # Pass video type to uploader
                )
                
                if video_id:
                    video_info['status'] = 'uploaded_private'
                    video_info['video_id'] = video_id
                    video_info['uploaded_at'] = datetime.now()
                    
                    # Schedule for publication
                    if scheduled_time and self.youtube_uploader.schedule_video(video_id, scheduled_time):
                        video_info['status'] = 'scheduled'
                        video_info['scheduled_at'] = datetime.now()
                        self.logger.info(f"Successfully scheduled: {video_info['title']} (ID: {video_id}) for {scheduled_time}")
                        self.logger.info("✅ YouTube will automatically publish this video at the scheduled time")
                    else:
                        # If scheduling fails, just mark as failed
                        self.logger.error(f"Failed to schedule video: {video_info['title']}")
                        video_info['status'] = 'schedule_failed'
                    
                    # Move processed file
                    self.move_processed_file(video_path)
                    
                else:
                    video_info['upload_attempts'] += 1
                    if video_info['upload_attempts'] >= max_retries:
                        video_info['status'] = 'failed'
                        video_info['error'] = 'Max retries exceeded'
                        self.logger.error(f"Failed to upload after {max_retries} attempts: {video_info['title']}")
                    else:
                        self.logger.warning(f"Upload attempt {video_info['upload_attempts']} failed, will retry: {video_info['title']}")
                
            except Exception as e:
                self.logger.error(f"Error uploading video {video_info['title']}: {e}")
                video_info['upload_attempts'] += 1
                if video_info['upload_attempts'] >= max_retries:
                    video_info['status'] = 'failed'
                    video_info['error'] = str(e)
        
        self.save_upload_queue()
    
    def check_and_publish_scheduled_videos(self):
        """Check for videos that are ready to be published and make them public"""
        current_time = datetime.now()
        
        # Find videos that are scheduled and ready to be published
        for video_info in self.upload_queue:
            if video_info.get('status') == 'scheduled':
                scheduled_time = video_info.get('scheduled_publish_time')
                if isinstance(scheduled_time, str):
                    scheduled_time = datetime.fromisoformat(scheduled_time.replace('Z', '+00:00'))
                
                # Check if it's time to publish (with 1-minute tolerance)
                if scheduled_time and current_time >= scheduled_time - timedelta(minutes=1):
                    video_id = video_info.get('video_id')
                    if video_id:
                        try:
                            # Make the video public
                            if self.youtube_uploader.make_video_public(video_id):
                                video_info['status'] = 'published'
                                video_info['published_at'] = current_time
                                self.logger.info(f"✅ Published video: {video_info['title']} (ID: {video_id})")
                            else:
                                self.logger.error(f"Failed to publish video: {video_info['title']} (ID: {video_id})")
                        except Exception as e:
                            self.logger.error(f"Error publishing video {video_info['title']}: {e}")
        
        self.save_upload_queue()

    def move_processed_file(self, video_path: str):
        """Move successfully uploaded video to processed folder"""
        try:
            filename = os.path.basename(video_path)
            processed_path = os.path.join(self.config['files']['processed_folder'], filename)
            
            os.makedirs(os.path.dirname(processed_path), exist_ok=True)
            os.rename(video_path, processed_path)
            
            self.logger.info(f"Moved processed file to: {processed_path}")
            
        except Exception as e:
            self.logger.warning(f"Failed to move processed file: {e}")
    
    def cleanup_old_files(self, days_old: int = 7):
        """Clean up old files from downloads and processed folders"""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        for folder in [self.config['files']['download_folder'], 
                      self.config['files']['processed_folder']]:
            try:
                for root, dirs, files in os.walk(folder):
                    for file in files:
                        file_path = os.path.join(root, file)
                        file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                        
                        if file_time < cutoff_date:
                            os.remove(file_path)
                            self.logger.info(f"Cleaned up old file: {file_path}")
                            
            except Exception as e:
                self.logger.error(f"Error during cleanup: {e}")
    
    def run_scheduled_generation(self):
        """Run the scheduled video generation and upload"""
        self.logger.info("Running scheduled video generation and upload")
        
        try:
            # Clear any cached module to ensure we get the latest version
            if 'market_scripts' in sys.modules:
                del sys.modules['market_scripts']
            
            # Import fresh version
            import market_scripts
            
            # Get the script content
            if hasattr(market_scripts, 'MARKET_SCRIPT'):
                if isinstance(market_scripts.MARKET_SCRIPT, list):
                    sample_scripts = market_scripts.MARKET_SCRIPT
                else:
                    # If it's a single string, convert to list
                    sample_scripts = [market_scripts.MARKET_SCRIPT]
            else:
                raise AttributeError("MARKET_SCRIPT not found in market_scripts.py")
                
            self.logger.info(f"✅ Successfully loaded updated script from market_scripts.py ({len(sample_scripts)} scripts available)")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to load from market_scripts.py: {e}")
            self.logger.error("Please ensure market_scripts.py exists and contains MARKET_SCRIPT variable")
            return
        
        # Use the loaded script (rotate if multiple scripts available)
        script_index = len(self.upload_queue) % len(sample_scripts)
        script = sample_scripts[script_index]
        
        self.logger.info(f"Using script {script_index + 1} of {len(sample_scripts)}: {script[:100]}...")
        
        # Generate videos
        video_files = self.generate_videos_from_script(script)
        
        if video_files:
            self.logger.info(f"Generated {len(video_files)} videos, added to upload queue")
        else:
            self.logger.warning("No videos were generated")
        
        # Upload pending videos
        self.upload_pending_videos()
        
        # Cleanup old files
        self.cleanup_old_files()
    
    def start_scheduler(self):
        """Start the automation scheduler"""
        interval_hours = self.config['scheduling']['interval_hours']
        
        # Schedule the video generation job
        schedule.every(interval_hours).hours.do(self.run_scheduled_generation)
        
        # Schedule checks for videos ready to be published (every 30 minutes)
        schedule.every(30).minutes.do(self.check_and_publish_scheduled_videos)
        
        self.logger.info(f"Scheduler started - will generate videos every {interval_hours} hours")
        self.logger.info(f"Will check for videos to publish every 30 minutes")
        self.logger.info(f"Next generation run scheduled for: {schedule.next_run()}")
        
        # Run initial upload of any pending videos
        self.upload_pending_videos()
        
        # Start scheduler loop
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def run_manual_generation(self, script: str, voice: str = "onyx", speed: float = 1.2, custom_start_time: Optional[datetime] = None, video_type: str = "short"):
        """Manually trigger video generation with scheduled publishing"""
        self.logger.info(f"Manual video generation triggered for {video_type}")
        
        video_files = []
        
        if video_type == "short":
            # Generate YouTube Shorts using the existing API (multiple videos from script with pause markers)
            video_files = self.api_client.generate_and_download_videos(
                script=script,
                download_folder=self.config['files']['download_folder'],
                voice=voice,
                speed=speed
            )
        elif video_type == "post":
            # Generate YouTube Post using the new Regular Format Voiceover API (single landscape video)
            video_path = self.voiceover_client.generate_and_download_video(
                script=script,
                download_folder=self.config['files']['download_folder'],
                voice=voice,
                speed=speed
            )
            if video_path:
                video_files = [video_path]
        
        if video_files:
            # Add videos to upload queue with scheduled publication times
            script_info = {
                'script': script[:200] + '...' if len(script) > 200 else script,
                'voice': voice,
                'speed': speed,
                'generated_at': datetime.now()
            }
            self.add_videos_to_queue(video_files, script_info, custom_start_time, video_type)
            video_type_label = "YouTube Shorts" if video_type == "short" else "YouTube Posts"
            self.logger.info(f"Generated {len(video_files)} videos with scheduled publication times as {video_type_label}")
            
            # Upload the videos as private and schedule them
            self.upload_pending_videos()
        else:
            self.logger.warning("No videos were generated")

    def run_manual_generation_with_custom_time(self):
        """Manually trigger video generation with custom scheduling time"""
        print("\nScript Input Options:")
        print("1. Enter script manually")
        print("2. Load from market_scripts.py file")
        
        input_choice = input("Choose script input method (1-2): ").strip()
        
        if input_choice == '2':
            try:
                from market_scripts import MARKET_SCRIPT
                script = MARKET_SCRIPT
                print(f"✅ Loaded script from file ({len(script)} characters, {script.count('— pause —') + 1} videos)")
            except ImportError:
                print("❌ market_scripts.py file not found. Please create it first.")
                return
        else:
            script = input("Enter script (use — pause — to separate videos): ")
        
        voice = input("Enter voice (nova/alloy/echo/fable/onyx/shimmer) [onyx]: ") or "onyx"
        speed = float(input("Enter speed (0.25-4.0) [1.2]: ") or "1.2")
        
        # Get video type
        print("\nVideo Type Options:")
        print("1. YouTube Shorts (vertical videos with #Shorts)")
        print("2. YouTube Posts (regular videos without #Shorts)")
        
        video_type_choice = input("Choose video type (1-2) [1]: ").strip() or "1"
        video_type = "short" if video_type_choice == "1" else "post"
        video_type_label = "YouTube Shorts" if video_type == "short" else "YouTube Posts"
        print(f"✅ Selected: {video_type_label}")
        
        # Get custom start time
        print("\nScheduling Options:")
        print("1. Use automatic scheduling (based on last scheduled time)")
        print("2. Set custom start time")
        
        schedule_choice = input("Choose scheduling option (1-2): ").strip()
        
        custom_start_time = None
        if schedule_choice == '2':
            current_time = datetime.now()
            print(f"\nCurrent time: {current_time.strftime('%Y-%m-%d %H:%M')} ({current_time.strftime('%I:%M %p')} IST)")
            
            while True:
                try:
                    date_input = input("Enter start date (YYYY-MM-DD) [today]: ").strip()
                    if not date_input:
                        date_input = current_time.strftime('%Y-%m-%d')
                    
                    time_input = input("Enter start time (HH:MM in 24-hour format): ").strip()
                    if not time_input:
                        raise ValueError("Time is required")
                    
                    # Parse the custom time
                    custom_start_time = datetime.strptime(f"{date_input} {time_input}", '%Y-%m-%d %H:%M')
                    
                    # Validate that it's in the future
                    if custom_start_time <= current_time:
                        print("⚠️ Start time must be in the future. Please try again.")
                        continue
                    
                    print(f"✅ Videos will be scheduled starting from: {custom_start_time.strftime('%Y-%m-%d %H:%M')} ({custom_start_time.strftime('%I:%M %p')} IST)")
                    
                    # Show the schedule preview
                    interval_hours = self.config['scheduling']['interval_hours']
                    video_count = script.count('— pause —') + 1
                    print(f"📅 Schedule Preview for {video_count} {video_type_label}:")
                    for i in range(video_count):
                        video_time = custom_start_time + timedelta(hours=interval_hours * i)
                        print(f"   Video {i+1}: {video_time.strftime('%Y-%m-%d %H:%M')} ({video_time.strftime('%I:%M %p')} IST)")
                    
                    confirm = input("Proceed with this schedule? (y/N): ").strip().lower()
                    if confirm == 'y':
                        break
                    else:
                        print("Cancelled. Please enter new time.")
                        continue
                        
                except ValueError as e:
                    print(f"❌ Invalid date/time format. Please use YYYY-MM-DD and HH:MM")
                    continue
        
        # Generate videos with the specified scheduling
        self.run_manual_generation(script, voice, speed, custom_start_time, video_type)

    def get_status(self) -> Dict:
        """Get current status of the automation"""
        pending_count = len([v for v in self.upload_queue if v['status'] == 'pending'])
        uploaded_count = len([v for v in self.upload_queue if v['status'] == 'uploaded'])
        scheduled_count = len([v for v in self.upload_queue if v['status'] == 'scheduled'])
        published_count = len([v for v in self.upload_queue if v['status'] == 'published'])
        failed_count = len([v for v in self.upload_queue if v['status'] == 'failed'])
        
        # Find next scheduled publication
        next_publish_time = None
        scheduled_videos = [v for v in self.upload_queue if v['status'] == 'scheduled']
        if scheduled_videos:
            for video in scheduled_videos:
                scheduled_time = video.get('scheduled_publish_time')
                if isinstance(scheduled_time, str):
                    scheduled_time = datetime.fromisoformat(scheduled_time.replace('Z', '+00:00'))
                if not next_publish_time or (scheduled_time and scheduled_time < next_publish_time):
                    next_publish_time = scheduled_time
        
        return {
            'pending_uploads': pending_count,
            'scheduled_videos': scheduled_count,
            'published_videos': published_count,
            'uploaded_videos_old': uploaded_count,  # Old videos uploaded before scheduling system
            'failed_uploads': failed_count,
            'next_scheduled_run': str(schedule.next_run()) if schedule.jobs else 'Not scheduled',
            'next_video_publish': str(next_publish_time) if next_publish_time else 'No videos scheduled',
            'total_videos_processed': len(self.upload_queue)
        }

    def run_automation_iteration(self, script_sources: List[str] = None, custom_scripts: List[str] = None):
        """Run a complete automation iteration with enhanced monitoring"""
        iteration_start = datetime.now()
        self.logger.info(f"Starting automation iteration at {iteration_start}")
        
        try:
            iteration_results = {
                'start_time': iteration_start,
                'scripts_processed': 0,
                'videos_generated': 0,
                'videos_uploaded': 0,
                'errors': []
            }
            
            # Process custom scripts if provided
            if custom_scripts:
                for script in custom_scripts:
                    try:
                        self.logger.info(f"Processing custom script: {script[:50]}...")
                        
                        # Generate both shorts and posts
                        shorts = self.generate_videos_from_script(script)
                        posts = self.generate_youtube_posts_from_script(script)
                        
                        iteration_results['scripts_processed'] += 1
                        iteration_results['videos_generated'] += len(shorts) + len(posts)
                        
                    except Exception as e:
                        error_msg = f"Failed to process custom script: {e}"
                        self.logger.error(error_msg)
                        iteration_results['errors'].append(error_msg)
            
            # Upload all pending videos
            uploaded_count = self.upload_pending_videos()
            iteration_results['videos_uploaded'] = uploaded_count
            
            # Update stats
            self.iteration_stats['total_videos_generated'] += iteration_results['videos_generated']
            self.iteration_stats['successful_uploads'] += iteration_results['videos_uploaded']
            self.iteration_stats['last_iteration_time'] = iteration_start
            
            # Calculate performance metrics
            iteration_duration = datetime.now() - iteration_start
            performance_metric = {
                'timestamp': iteration_start,
                'duration_minutes': iteration_duration.total_seconds() / 60,
                'videos_per_minute': iteration_results['videos_generated'] / max(1, iteration_duration.total_seconds() / 60),
                'success_rate': iteration_results['videos_uploaded'] / max(1, iteration_results['videos_generated'])
            }
            self.iteration_stats['performance_metrics'].append(performance_metric)
            
            # Keep only last 50 metrics
            if len(self.iteration_stats['performance_metrics']) > 50:
                self.iteration_stats['performance_metrics'] = self.iteration_stats['performance_metrics'][-50:]
            
            self.logger.info(f"Iteration completed in {iteration_duration.total_seconds():.1f} seconds")
            self.logger.info(f"Generated {iteration_results['videos_generated']} videos, uploaded {iteration_results['videos_uploaded']}")
            
            return iteration_results
            
        except Exception as e:
            self.logger.error(f"Automation iteration failed: {e}")
            self.iteration_stats['failed_uploads'] += 1
            return None
    
    def get_automation_stats(self) -> Dict:
        """Get comprehensive automation statistics"""
        current_time = datetime.now()
        
        # Calculate queue statistics
        queue_stats = {
            'total_videos': len(self.upload_queue),
            'pending': len([v for v in self.upload_queue if v['status'] == 'pending']),
            'scheduled': len([v for v in self.upload_queue if v['status'] == 'scheduled']),
            'uploaded': len([v for v in self.upload_queue if v['status'] == 'uploaded']),
            'failed': len([v for v in self.upload_queue if v['status'] == 'failed'])
        }
        
        # Calculate performance averages
        recent_metrics = self.iteration_stats['performance_metrics'][-10:]  # Last 10 iterations
        avg_performance = {}
        if recent_metrics:
            avg_performance = {
                'avg_duration_minutes': sum(m['duration_minutes'] for m in recent_metrics) / len(recent_metrics),
                'avg_videos_per_minute': sum(m['videos_per_minute'] for m in recent_metrics) / len(recent_metrics),
                'avg_success_rate': sum(m['success_rate'] for m in recent_metrics) / len(recent_metrics)
            }
        
        return {
            'iteration_stats': self.iteration_stats,
            'queue_stats': queue_stats,
            'avg_performance': avg_performance,
            'last_updated': current_time.isoformat()
        }
    
    def cleanup_old_videos(self, days_old: int = 7):
        """Clean up old processed videos to save disk space"""
        try:
            processed_folder = Path(self.config['files']['processed_folder'])
            current_time = datetime.now()
            
            cleaned_count = 0
            for video_file in processed_folder.glob('*.mp4'):
                # Get file modification time
                file_time = datetime.fromtimestamp(video_file.stat().st_mtime)
                
                # Delete if older than specified days
                if (current_time - file_time).days > days_old:
                    video_file.unlink()
                    cleaned_count += 1
                    self.logger.info(f"Cleaned up old video: {video_file.name}")
            
            self.logger.info(f"Cleaned up {cleaned_count} old video files")
            return cleaned_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old videos: {e}")
            return 0
    
    def smart_retry_failed_uploads(self):
        """Intelligently retry failed uploads with exponential backoff"""
        failed_videos = [v for v in self.upload_queue if v['status'] == 'failed']
        
        if not failed_videos:
            self.logger.info("No failed uploads to retry")
            return 0
        
        retry_count = 0
        for video_info in failed_videos:
            try:
                attempts = video_info.get('upload_attempts', 0)
                
                # Check if we should retry based on attempt count and time
                if attempts < self.retry_config['max_retries']:
                    # Calculate delay based on attempt number
                    delay_minutes = self.retry_config['retry_delay_minutes'][min(attempts, len(self.retry_config['retry_delay_minutes']) - 1)]
                    
                    # Check if enough time has passed since last attempt
                    last_attempt = video_info.get('last_attempt_time')
                    if last_attempt:
                        last_attempt_dt = datetime.fromisoformat(last_attempt) if isinstance(last_attempt, str) else last_attempt
                        time_since_attempt = datetime.now() - last_attempt_dt
                        
                        if time_since_attempt.total_seconds() < delay_minutes * 60:
                            continue  # Not enough time has passed
                    
                    # Retry the upload
                    self.logger.info(f"Retrying upload for: {video_info['title']} (attempt {attempts + 1})")
                    
                    video_info['status'] = 'pending'  # Reset to pending for retry
                    video_info['last_attempt_time'] = datetime.now()
                    retry_count += 1
                
            except Exception as e:
                self.logger.error(f"Error during retry setup: {e}")
        
        # Save the updated queue
        self.save_upload_queue()
        
        self.logger.info(f"Set up {retry_count} videos for retry")
        return retry_count

def show_menu():
    """Display the main menu options"""
    print("\nYouTube Shorts Automation")
    print("=========================")
    print("1. Start automatic scheduler")
    print("2. Manual video generation")
    print("3. Manual video generation with custom scheduling")
    print("4. Upload pending videos")
    print("5. Show status")
    print("6. Exit")

def main():
    """Main entry point"""
    automation = YouTubeShortsAutomation()
    
    # Check if YouTube authentication works
    channel_info = automation.youtube_uploader.get_channel_info()
    if channel_info:
        automation.logger.info(f"Connected to YouTube channel: {channel_info['snippet']['title']}")
    else:
        automation.logger.error("Failed to authenticate with YouTube. Please check your credentials.")
        return
    
    # Show initial menu
    show_menu()
    
    while True:
        choice = input("\nEnter your choice (1-6): ").strip()
        
        if choice == '1':
            print("Starting automatic scheduler...")
            automation.start_scheduler()
            
        elif choice == '2':
            script = input("Enter script (use — pause — to separate videos): ")
            voice = input("Enter voice (nova/alloy/echo/fable/onyx/shimmer) [onyx]: ") or "onyx"
            speed = float(input("Enter speed (0.25-4.0) [1.2]: ") or "1.2")
            
            # Get video type
            print("\nVideo Type Options:")
            print("1. YouTube Shorts (vertical videos with #Shorts)")
            print("2. YouTube Posts (regular videos without #Shorts)")
            
            video_type_choice = input("Choose video type (1-2) [1]: ").strip() or "1"
            video_type = "short" if video_type_choice == "1" else "post"
            video_type_label = "YouTube Shorts" if video_type == "short" else "YouTube Posts"
            print(f"✅ Selected: {video_type_label}")
            
            automation.run_manual_generation(script, voice, speed, None, video_type)
            # Show menu again after task completion
            show_menu()
        
        elif choice == '3':
            automation.run_manual_generation_with_custom_time()
            # Show menu again after task completion
            show_menu()
            
        elif choice == '4':
            automation.upload_pending_videos()
            # Show menu again after task completion
            show_menu()
            
        elif choice == '5':
            status = automation.get_status()
            print("\nCurrent Status:")
            for key, value in status.items():
                print(f"  {key.replace('_', ' ').title()}: {value}")
            # Show menu again after task completion
            show_menu()
                
        elif choice == '6':
            print("Exiting...")
            break
            
        else:
            print("Invalid choice. Please enter 1-6.")
            # Show menu again for invalid choices
            show_menu()

if __name__ == "__main__":
    main()