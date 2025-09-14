import os
import json
import logging
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from typing import Optional, Dict, List

class YouTubeUploader:
    """Handle YouTube video uploads using the YouTube Data API v3"""
    
    def __init__(self, client_id: str, client_secret: str, refresh_token: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.youtube = None
        self.logger = logging.getLogger(__name__)
        
    def authenticate(self) -> bool:
        """Authenticate with YouTube API using refresh token"""
        try:
            credentials = Credentials(
                token=None,
                refresh_token=self.refresh_token,
                client_id=self.client_id,
                client_secret=self.client_secret,
                token_uri='https://oauth2.googleapis.com/token'
            )
            
            self.youtube = build('youtube', 'v3', credentials=credentials)
            self.logger.info("Successfully authenticated with YouTube API")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to authenticate with YouTube API: {e}")
            return False
    
    def upload_video(self, 
                    video_path: str, 
                    title: str, 
                    description: str,
                    tags: List[str] = None,
                    category_id: str = "22",  # People & Blogs
                    privacy_status: str = "public",
                    video_type: str = "short") -> Optional[str]:
        """
        Upload a video to YouTube
        
        Args:
            video_path: Path to the video file
            title: Video title
            description: Video description
            tags: List of tags for the video
            category_id: YouTube category ID (22 = People & Blogs)
            privacy_status: public, private, or unlisted
            video_type: "short" for YouTube Shorts, "post" for regular videos
            
        Returns:
            Video ID if successful, None if failed
        """
        if not self.youtube:
            if not self.authenticate():
                return None
        
        if not os.path.exists(video_path):
            self.logger.error(f"Video file not found: {video_path}")
            return None
        
        try:
            # Adjust title and tags based on video type
            if video_type == "short":
                # For Shorts, add #Shorts tag if not already present
                final_tags = tags or []
                if "Shorts" not in final_tags and "shorts" not in final_tags:
                    final_tags.append("Shorts")
                # Add #Shorts to description if not present
                if "#Shorts" not in description and "#shorts" not in description:
                    description = f"{description}\n\n#Shorts"
                self.logger.info(f"Uploading as YouTube Short: {title}")
            else:
                # For regular posts, use tags as-is
                final_tags = tags or []
                self.logger.info(f"Uploading as YouTube Post: {title}")
            
            # Prepare video metadata
            body = {
                'snippet': {
                    'title': title,
                    'description': description,
                    'tags': final_tags,
                    'categoryId': category_id
                },
                'status': {
                    'privacyStatus': privacy_status,
                    'selfDeclaredMadeForKids': False
                }
            }
            
            # Create media upload object
            media = MediaFileUpload(
                video_path,
                chunksize=-1,
                resumable=True,
                mimetype='video/mp4'
            )
            
            # Execute upload
            self.logger.info(f"Starting upload for: {title}")
            insert_request = self.youtube.videos().insert(
                part=','.join(body.keys()),
                body=body,
                media_body=media
            )
            
            video_id = self._resumable_upload(insert_request)
            
            if video_id:
                video_type_label = "YouTube Short" if video_type == "short" else "YouTube Post"
                self.logger.info(f"Successfully uploaded {video_type_label}: {title} (ID: {video_id})")
                return video_id
            else:
                self.logger.error(f"Failed to upload video: {title}")
                return None
                
        except HttpError as e:
            self.logger.error(f"HTTP error during upload: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error during upload: {e}")
            return None
    
    def _resumable_upload(self, insert_request):
        """Handle resumable upload with retry logic"""
        response = None
        error = None
        retry = 0
        
        while response is None:
            try:
                status, response = insert_request.next_chunk()
                if response is not None:
                    if 'id' in response:
                        return response['id']
                    else:
                        raise Exception(f"Upload failed with unexpected response: {response}")
                        
            except HttpError as e:
                if e.resp.status in [500, 502, 503, 504]:
                    error = f"HTTP error {e.resp.status}: {e.content}"
                    retry += 1
                    if retry > 3:
                        self.logger.error(f"Max retries exceeded: {error}")
                        break
                    self.logger.warning(f"Retrying upload (attempt {retry}): {error}")
                else:
                    raise e
            except Exception as e:
                error = str(e)
                break
        
        return None
    
    def get_channel_info(self) -> Optional[Dict]:
        """Get information about the authenticated channel"""
        if not self.youtube:
            if not self.authenticate():
                return None
        
        try:
            response = self.youtube.channels().list(
                part='snippet,statistics',
                mine=True
            ).execute()
            
            if response['items']:
                return response['items'][0]
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get channel info: {e}")
            return None
    
    def schedule_video(self, video_id: str, publish_time: datetime) -> bool:
        """Schedule a video to be published at a specific time"""
        if not self.youtube:
            if not self.authenticate():
                return False
        
        try:
            # Convert local time to UTC for YouTube API
            import pytz
            
            # Assume the input time is in local timezone (IST)
            local_tz = pytz.timezone('Asia/Kolkata')  # IST timezone
            utc_tz = pytz.UTC
            
            # If the datetime is naive (no timezone info), assume it's IST
            if publish_time.tzinfo is None:
                # Localize to IST first
                publish_time_ist = local_tz.localize(publish_time)
            else:
                publish_time_ist = publish_time
            
            # Convert to UTC
            publish_time_utc = publish_time_ist.astimezone(utc_tz)
            
            # Format for YouTube API
            publish_time_str = publish_time_utc.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            
            self.logger.info(f"Converting schedule time: {publish_time} IST → {publish_time_utc} UTC")
            
            self.youtube.videos().update(
                part='status',
                body={
                    'id': video_id,
                    'status': {
                        'privacyStatus': 'private',
                        'publishAt': publish_time_str
                    }
                }
            ).execute()
            
            self.logger.info(f"Scheduled video {video_id} for {publish_time_utc} UTC ({publish_time} IST)")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to schedule video: {e}")
            return False

    def make_video_public(self, video_id: str) -> bool:
        """Make a private video public"""
        if not self.youtube:
            if not self.authenticate():
                return False
        
        try:
            self.youtube.videos().update(
                part='status',
                body={
                    'id': video_id,
                    'status': {
                        'privacyStatus': 'public'
                    }
                }
            ).execute()
            
            self.logger.info(f"Made video {video_id} public")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to make video public: {e}")
            return False