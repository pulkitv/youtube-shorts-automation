import requests
import logging
from datetime import datetime, timedelta
import pytz
from typing import Optional
import time
import os
from dotenv import load_dotenv


class MakeWebhookClient:
    """Client for sending tweet data to Make.com webhook"""
    
    def __init__(self, webhook_url: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize the Make.com webhook client
        
        Args:
            webhook_url: Make.com webhook URL to send data to (optional, will load from env if not provided)
            api_key: Make.com API key for authentication (optional, will load from env if not provided)
        """
        # Load environment variables
        load_dotenv()
        
        # Use provided URL or load from environment
        self.webhook_url = webhook_url or os.getenv('MAKE_WEBHOOK_URL')
        self.api_key = api_key or os.getenv('MAKE_API_KEY')
        
        if not self.webhook_url:
            raise ValueError("MAKE_WEBHOOK_URL not provided and not found in environment variables")
        
        if not self.api_key:
            raise ValueError("MAKE_API_KEY not provided and not found in environment variables")
        
        self.logger = logging.getLogger(__name__)
        self.tweet_counter = 0  # Simple counter, resets each video generation batch
        
        self.logger.info(f"Make.com webhook client initialized with authentication")
    
    def reset_counter(self):
        """Reset tweet counter to 0 for new video generation batch"""
        self.tweet_counter = 0
        self.logger.info("Tweet counter reset to 0")
    
    def send_tweet_data(self, full_content: str, video_url: str, 
                       scheduled_time: datetime) -> bool:
        """
        Send tweet data to Make.com webhook
        
        Args:
            full_content: Complete script text for the short
            video_url: YouTube Shorts URL (empty string if upload failed)
            scheduled_time: When the video is scheduled to be published
            
        Returns:
            True if successful, False otherwise
        """
        # Debug: Log the length and preview of full_content
        self.logger.info(f"📝 Full content length: {len(full_content)} characters")
        self.logger.debug(f"📝 Full content preview: {full_content[:200]}...")


        # Increment counter
        self.tweet_counter += 1
        tweet_id = str(self.tweet_counter).zfill(2)  # 01, 02, 03, etc.
        
        # Generate tweet text (first 200 chars + "...")
        tweet_text = self._generate_tweet_text(full_content)
        
        # Calculate tweet date (15 minutes after scheduled time, in IST)
        tweet_datetime = self._calculate_tweet_time(scheduled_time)
        
        # Prepare payload
        payload = {
            "Tweet_ID": tweet_id,
            "Full_Content": full_content,
            "Tweet_Text": tweet_text,
            "Video_ID": video_url,
            "Tweet_date": tweet_datetime
        }
        
        # Log the data being sent
        self.logger.info(f"Preparing to send tweet data:")
        self.logger.info(f"  Tweet_ID: {tweet_id}")
        self.logger.info(f"  Tweet_Text: {tweet_text[:50]}...")
        self.logger.info(f"  Full_Content length: {len(payload['Full_Content'])} chars")
        self.logger.info(f"  Video_ID: {video_url if video_url else '(empty - upload failed)'}")
        self.logger.info(f"  Tweet_date: {tweet_datetime}")
        
        # Send to webhook with retry logic
        return self._send_with_retry(payload)
    
    def _generate_tweet_text(self, full_content: str) -> str:
        """
        Generate tweet text from full content
        
        Args:
            full_content: Complete script text
            
        Returns:
            First 200 characters + "..."
        """
        # Clean the content (remove extra whitespace)
        cleaned_content = ' '.join(full_content.split())
        
        # Take first 200 characters
        if len(cleaned_content) <= 200:
            return cleaned_content
        
        tweet_text = cleaned_content[:200].strip() + "..."
        return tweet_text
    
    def _calculate_tweet_time(self, scheduled_time: datetime) -> str:
        """
        Add 15 minutes to scheduled time and convert to IST
        
        Args:
            scheduled_time: Video publish time
            
        Returns:
            Formatted string: "dd-mm-yyyy hh:mm A"
        """
        # Add 15 minutes
        tweet_time = scheduled_time + timedelta(minutes=15)
        
        # Convert to IST
        ist = pytz.timezone('Asia/Kolkata')
        
        # Handle timezone conversion
        if tweet_time.tzinfo is None:
            # If no timezone info, assume it's in local timezone
            # Get local timezone and localize
            local_tz = datetime.now().astimezone().tzinfo
            tweet_time = tweet_time.replace(tzinfo=local_tz)
        
        # Convert to IST
        tweet_time_ist = tweet_time.astimezone(ist)
        
        # Format: "17-11-2025 02:30 PM"
        formatted_time = tweet_time_ist.strftime('%d-%m-%Y %I:%M %p')
        
        return formatted_time
    
    def _send_with_retry(self, payload: dict, max_retries: int = 3) -> bool:
        """
        Send POST request to webhook with retry logic
        
        Args:
            payload: Data to send
            max_retries: Number of retry attempts
            
        Returns:
            True if successful, False otherwise
        """
        for attempt in range(max_retries):
            try:
                self.logger.info(f"Sending tweet data to Make.com webhook (attempt {attempt + 1}/{max_retries})")
                self.logger.debug(f"Payload: {payload}")
                
                # Include API key in headers
                headers = {
                    'Content-Type': 'application/json',
                    'x-make-apikey': self.api_key
                }
                
                response = requests.post(
                    self.webhook_url,
                    json=payload,
                    timeout=30,
                    headers=headers
                )
                
                # Check response
                if response.status_code == 200:
                    self.logger.info(f"✅ Tweet data sent successfully (Tweet_ID: {payload['Tweet_ID']})")
                    self.logger.debug(f"Response: {response.text}")
                    return True
                else:
                    self.logger.warning(f"⚠️ Webhook returned status {response.status_code}: {response.text}")
                    
            except requests.exceptions.Timeout:
                self.logger.error(f"❌ Webhook request timeout (attempt {attempt + 1})")
            except requests.exceptions.RequestException as e:
                self.logger.error(f"❌ Webhook request failed (attempt {attempt + 1}): {e}")
            except Exception as e:
                self.logger.error(f"❌ Unexpected error (attempt {attempt + 1}): {e}")
            
            # Wait before retry (exponential backoff)
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                self.logger.info(f"⏳ Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
        
        self.logger.error(f"❌ Failed to send tweet data after {max_retries} attempts")
        return False
