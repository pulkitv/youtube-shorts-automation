import requests
import time
import zipfile
import os
import logging
from typing import Optional, Dict, List
from pathlib import Path

class PDFAPIClient:
    """Client for interacting with the PDF processing API to generate YouTube Shorts"""
    
    def __init__(self, base_url: str, endpoint: str):
        self.base_url = base_url.rstrip('/')
        self.endpoint = endpoint
        self.logger = logging.getLogger(__name__)
        # Add flag for testing mode
        self.testing_mode = os.getenv('API_TESTING_MODE', 'false').lower() == 'true'
    
    def generate_shorts(self, 
                       script: str,
                       voice: str = "nova",
                       speed: float = 1.0,
                       background_image_url: Optional[str] = None,
                       webhook_url: Optional[str] = None) -> Optional[Dict]:
        """
        Generate YouTube Shorts from a script
        
        Args:
            script: Text script with — pause — markers to create separate videos
            voice: Voice type (alloy, echo, fable, onyx, nova, shimmer)
            speed: Speech speed between 0.25 and 4.0
            background_image_url: Optional background image URL
            webhook_url: Optional webhook URL for progress notifications
            
        Returns:
            Response dict with session_id and status, None if failed
        """
        # Initialize session tracking
        if not hasattr(self, '_session_start_times'):
            self._session_start_times = {}
        
        # Testing mode - simulate successful API response
        if self.testing_mode:
            import uuid
            session_id = f"mock_{uuid.uuid4()}"
            self._session_start_times[session_id] = time.time()
            self.logger.info(f"🧪 Testing mode: Simulating API call for session {session_id}")
            return {
                "success": True,
                "session_id": session_id,
                "status": "processing"
            }
        
        url = f"{self.base_url}{self.endpoint}"
        
        payload = {
            "script": script,
            "voice": voice,
            "speed": speed
        }
        
        if background_image_url:
            payload["background_image_url"] = background_image_url
        if webhook_url:
            payload["webhook_url"] = webhook_url
        
        try:
            self.logger.info(f"Requesting shorts generation for script: {script[:100]}...")
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 202:
                data = response.json()
                session_id = data.get('session_id')
                if session_id:
                    self._session_start_times[session_id] = time.time()
                self.logger.info(f"Shorts generation started. Session ID: {session_id}")
                return data
            else:
                self.logger.error(f"API request failed: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to connect to API: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            return None
    
    def check_status(self, session_id: str) -> Optional[Dict]:
        """
        Check the status of a shorts generation request
        
        Args:
            session_id: Session ID from the generation request
            
        Returns:
            Status dict with progress info, None if failed
        """
        # Testing mode - simulate status progression
        if self.testing_mode and session_id.startswith("mock_"):
            # Simulate different stages based on time
            import uuid
            current_time = time.time()
            # Use a more reliable timestamp extraction
            try:
                session_start = current_time - 30  # Assume started 30 seconds ago for testing
                elapsed = current_time - session_start
                
                if elapsed < 5:
                    return {
                        "success": True,
                        "session_id": session_id,
                        "status": "processing",
                        "progress": 25,
                        "message": "Generating video 1 of 3..."
                    }
                elif elapsed < 10:
                    return {
                        "success": True,
                        "session_id": session_id,
                        "status": "processing", 
                        "progress": 75,
                        "message": "Generating video 3 of 3..."
                    }
                else:
                    return {
                        "success": True,
                        "session_id": session_id,
                        "status": "completed",
                        "progress": 100,
                        "message": "All videos generated successfully!",
                        "zip_url": f"http://localhost:5000/mock-download/{session_id}.zip"
                    }
            except:
                # Fallback to completed status
                return {
                    "success": True,
                    "session_id": session_id,
                    "status": "completed",
                    "progress": 100,
                    "message": "All videos generated successfully!",
                    "zip_url": f"http://localhost:5000/mock-download/{session_id}.zip"
                }
        
        url = f"{self.base_url}/api/v1/shorts-status/{session_id}"
        
        try:
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                status_data = response.json()
                
                # WORKAROUND: If API is stuck at 0% but we know it's working,
                # check if enough time has passed and assume completion
                if (status_data.get('progress', 0) == 0 and 
                    'Starting generation' in status_data.get('message', '') and
                    hasattr(self, '_session_start_times')):
                    
                    session_start = self._session_start_times.get(session_id, time.time())
                    elapsed = time.time() - session_start
                    
                    # If more than 30 seconds have passed, try to find download URL
                    if elapsed > 30:
                        self.logger.warning(f"API stuck at 0% for {elapsed:.0f}s, checking for completed files...")
                        zip_url = self._try_find_download_url(session_id)
                        if zip_url:
                            self.logger.info(f"Found download URL despite stuck status: {zip_url}")
                            return {
                                "success": True,
                                "session_id": session_id,
                                "status": "completed",
                                "progress": 100,
                                "message": "Generation completed (auto-detected)",
                                "zip_url": zip_url
                            }
                        else:
                            self.logger.warning(f"No download URL found after {elapsed:.0f}s")
                
                return status_data
            else:
                self.logger.error(f"Status check failed: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to check status: {e}")
            return None

    def _try_find_download_url(self, session_id: str) -> Optional[str]:
        """Try to find the download URL for a completed session"""
        try:
            # First, try to get the file listing from /voiceovers endpoint
            try:
                response = requests.get(f"{self.base_url}/voiceovers", timeout=10)
                if response.status_code == 200:
                    content = response.text
                    # Look for files matching our session ID
                    if session_id in content and '.zip' in content:
                        # Extract the filename from the JSON response
                        import re
                        # Look for the pattern: "filename": "api_shorts_api_SESSION_ID_UUID.zip"
                        pattern = rf'"filename":\s*"(api_shorts_{re.escape(session_id)}_[^"]+\.zip)"'
                        match = re.search(pattern, content)
                        if match:
                            filename = match.group(1)
                            # Try different download URL patterns with this filename
                            possible_urls = [
                                f"{self.base_url}/download-voiceover/{filename}",
                                f"{self.base_url}/voiceovers/{filename}",
                                f"{self.base_url}/static/voiceovers/{filename}",
                                f"{self.base_url}/files/{filename}",
                                f"{self.base_url}/download/{filename}"
                            ]
                            
                            for url in possible_urls:
                                try:
                                    self.logger.info(f"Testing filename-based URL: {url}")
                                    test_response = requests.head(url, timeout=5)
                                    if test_response.status_code == 200:
                                        self.logger.info(f"✅ Found working URL with filename: {url}")
                                        return url
                                except:
                                    continue
            except Exception as e:
                self.logger.debug(f"Failed to get file listing: {e}")
            
            # Fallback: try original patterns
            possible_urls = [
                f"{self.base_url}/download-voiceover/api_shorts_{session_id.replace('api_', '')}.zip",
                f"{self.base_url}/download-voiceover/{session_id}.zip", 
                f"{self.base_url}/download-voiceover/shorts_{session_id}.zip",
                f"{self.base_url}/api/v1/download/{session_id}",
                f"{self.base_url}/download/{session_id}.zip",
                f"{self.base_url}/voiceovers/{session_id}.zip"
            ]
            
            for url in possible_urls:
                try:
                    self.logger.info(f"Checking download URL: {url}")
                    response = requests.head(url, timeout=5)
                    if response.status_code == 200:
                        self.logger.info(f"✅ Found working download URL: {url}")
                        return url
                    elif response.status_code == 404:
                        self.logger.debug(f"❌ URL not found: {url}")
                    else:
                        self.logger.debug(f"⚠️  URL returned {response.status_code}: {url}")
                except requests.exceptions.RequestException as e:
                    self.logger.debug(f"❌ Connection error for {url}: {e}")
                    continue
                    
            # If HEAD requests don't work, try GET requests (some servers don't support HEAD)
            self.logger.info("HEAD requests failed, trying GET requests...")
            for url in possible_urls[:3]:  # Only try the most likely URLs with GET
                try:
                    response = requests.get(url, timeout=5, stream=True)
                    if response.status_code == 200:
                        # Check if it's actually a ZIP file
                        content_type = response.headers.get('content-type', '')
                        if 'zip' in content_type or 'application/octet-stream' in content_type:
                            self.logger.info(f"✅ Found working download URL (GET): {url}")
                            return url
                except requests.exceptions.RequestException:
                    continue
                    
            return None
        except Exception as e:
            self.logger.error(f"Error finding download URL: {e}")
            return None
    
    def wait_for_completion(self, session_id: str, max_wait_time: int = 600, poll_interval: int = 10) -> Optional[Dict]:
        """
        Wait for shorts generation to complete
        
        Args:
            session_id: Session ID to monitor
            max_wait_time: Maximum time to wait in seconds (default: 10 minutes)
            poll_interval: How often to check status in seconds (default: 10 seconds)
            
        Returns:
            Final status dict with zip_url, None if failed or timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            status = self.check_status(session_id)
            
            if not status:
                return None
            
            current_status = status.get('status')
            progress = status.get('progress', 0)
            message = status.get('message', '')
            
            self.logger.info(f"Progress: {progress}% - {message}")
            
            if current_status == 'completed':
                self.logger.info("Shorts generation completed successfully!")
                return status
            elif current_status == 'failed':
                error = status.get('error', 'Unknown error')
                self.logger.error(f"Shorts generation failed: {error}")
                return None
            
            time.sleep(poll_interval)
        
        self.logger.error(f"Timeout waiting for completion after {max_wait_time} seconds")
        return None

    def create_mock_videos(self, session_id: str, download_folder: str) -> List[str]:
        """Create mock video files for testing"""
        self.logger.info("🎬 Creating mock video files for testing...")
        
        # Create mock MP4 files
        video_files = []
        extract_folder = os.path.join(download_folder, f"extracted_mock_{int(time.time())}")
        os.makedirs(extract_folder, exist_ok=True)
        
        for i in range(3):  # Create 3 mock videos
            filename = f"short_video_{i+1}.mp4"
            video_path = os.path.join(extract_folder, filename)
            
            # Create a minimal MP4 file (this won't actually play, but will test the upload logic)
            with open(video_path, 'wb') as f:
                # Write minimal MP4 header bytes
                f.write(b'\x00\x00\x00\x20ftypmp41\x00\x00\x00\x00mp41isom')
                f.write(b'\x00' * 1024)  # Pad to make it a reasonable size
            
            video_files.append(video_path)
            self.logger.info(f"Created mock video: {filename}")
        
        return video_files

    def download_zip(self, zip_url: str, download_path: str) -> bool:
        """
        Download the generated shorts ZIP file
        
        Args:
            zip_url: URL to download the ZIP file
            download_path: Local path to save the ZIP file
            
        Returns:
            True if successful, False otherwise
        """
        # Testing mode - simulate download
        if self.testing_mode and "mock-download" in zip_url:
            self.logger.info("🧪 Testing mode: Simulating ZIP download...")
            os.makedirs(os.path.dirname(download_path), exist_ok=True)
            
            # Create a mock ZIP file
            with open(download_path, 'wb') as f:
                f.write(b'PK\x03\x04')  # ZIP file signature
                f.write(b'\x00' * 100)  # Minimal ZIP content
            
            return True
        
        try:
            self.logger.info(f"Downloading ZIP file from: {zip_url}")
            
            # Ensure download directory exists
            os.makedirs(os.path.dirname(download_path), exist_ok=True)
            
            response = requests.get(zip_url, stream=True, timeout=60)
            response.raise_for_status()
            
            with open(download_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            self.logger.info(f"ZIP file downloaded successfully: {download_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to download ZIP file: {e}")
            return False
    
    def extract_videos(self, zip_path: str, extract_to: str) -> List[str]:
        """
        Extract video files from the downloaded ZIP
        
        Args:
            zip_path: Path to the ZIP file
            extract_to: Directory to extract videos to
            
        Returns:
            List of extracted video file paths
        """
        # Testing mode - return mock videos instead of extracting
        if self.testing_mode and os.path.basename(zip_path).startswith("shorts_mock_"):
            session_id = os.path.basename(zip_path).replace("shorts_", "").replace(".zip", "")
            return self.create_mock_videos(session_id, os.path.dirname(extract_to))
        
        video_files = []
        
        try:
            self.logger.info(f"Extracting videos from: {zip_path}")
            
            # Ensure extraction directory exists
            os.makedirs(extract_to, exist_ok=True)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                for file_info in zip_ref.filelist:
                    filename = file_info.filename
                    
                    # Only extract video files (mp4)
                    if filename.lower().endswith('.mp4'):
                        zip_ref.extract(file_info, extract_to)
                        video_path = os.path.join(extract_to, filename)
                        video_files.append(video_path)
                        self.logger.info(f"Extracted video: {filename}")
            
            self.logger.info(f"Extracted {len(video_files)} video files")
            return sorted(video_files)  # Sort for consistent ordering
            
        except Exception as e:
            self.logger.error(f"Failed to extract videos: {e}")
            return []
    
    def generate_and_download_videos(self, 
                                   script: str,
                                   download_folder: str,
                                   voice: str = "nova",
                                   speed: float = 1.0,
                                   background_image_url: Optional[str] = None) -> List[str]:
        """
        Complete workflow: generate shorts, wait for completion, download and extract videos
        
        Args:
            script: Text script with pause markers
            download_folder: Folder to download and extract videos
            voice: Voice type
            speed: Speech speed
            background_image_url: Optional background image
            
        Returns:
            List of extracted video file paths
        """
        # Start generation
        response = self.generate_shorts(script, voice, speed, background_image_url)
        if not response:
            return []
        
        session_id = response.get('session_id')
        if not session_id:
            return []
        
        # Wait for completion
        final_status = self.wait_for_completion(session_id)
        if not final_status:
            return []
        
        zip_url = final_status.get('zip_url')
        if not zip_url:
            self.logger.error("No ZIP URL in completed response")
            return []
        
        # Download ZIP file
        timestamp = int(time.time())
        zip_filename = f"shorts_{session_id}_{timestamp}.zip"
        zip_path = os.path.join(download_folder, zip_filename)
        
        if not self.download_zip(zip_url, zip_path):
            return []
        
        # Extract videos
        extract_folder = os.path.join(download_folder, f"extracted_{timestamp}")
        video_files = self.extract_videos(zip_path, extract_folder)
        
        # Clean up ZIP file after extraction
        try:
            os.remove(zip_path)
            self.logger.info(f"Cleaned up ZIP file: {zip_path}")
        except Exception as e:
            self.logger.warning(f"Failed to clean up ZIP file: {e}")
        
        return video_files