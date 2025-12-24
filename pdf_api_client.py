import os
import requests
import time
import zipfile
import logging
from typing import Optional, Dict, List
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class PDFAPIClient:
    """Client for interacting with the PDF processing API to generate YouTube Shorts"""
    
    def __init__(self, base_url: str, endpoint: str):
        """
        Initialize the PDF API client
        
        Args:
            base_url: Base URL of the API
            endpoint: Endpoint for shorts generation
        """
        self.base_url = base_url.rstrip('/')
        self.endpoint = endpoint
        self.logger = logging.getLogger(__name__)
        
        # Load timeout values from environment variables
        self.request_timeout = int(os.getenv('API_REQUEST_TIMEOUT', '900'))  # 15 minutes default
        self.status_timeout = int(os.getenv('API_STATUS_TIMEOUT', '30'))     # 30 seconds default
        self.download_timeout = int(os.getenv('API_DOWNLOAD_TIMEOUT', '1200'))  # 20 minutes default
        
        # Maximum time to wait for video generation to complete
        self.max_wait_time = self.request_timeout  # Use same as request timeout
        
        # Add flag for testing mode
        self.testing_mode = os.getenv('API_TESTING_MODE', 'false').lower() == 'true'
        
        # Initialize mock session tracking
        if self.testing_mode:
            self.mock_sessions = {}
            
        self.logger.info(f"PDF API Client initialized with timeouts: request={self.request_timeout}s, status={self.status_timeout}s, download={self.download_timeout}s, max_wait={self.max_wait_time}s")

    def _count_script_segments(self, script: str) -> int:
        """Count the number of video segments in the script"""
        if not script.strip():
            return 0
        # Count segments by splitting on "— pause —" and adding 1
        return len(script.split("— pause —"))
    
    def _split_script_into_segments(self, script: str) -> List[str]:
        """Split script into individual segments"""
        if not script.strip():
            return []
        segments = [segment.strip() for segment in script.split("— pause —")]
        return [seg for seg in segments if seg]  # Remove empty segments
    
    def _extract_company_name(self, segment: str) -> str:
        """Extract company name from a script segment"""
        # Look for the pattern "Company Name as on Date"
        lines = segment.split('\n')
        if lines:
            first_line = lines[0].strip()
            # Extract text before " as on "
            if " as on " in first_line:
                company_name = first_line.split(" as on ")[0].strip()
                return company_name
            # Fallback: use first few words
            words = first_line.split()[:3]
            return "_".join(words)
        return f"Company_{len(segment)}"

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
        
        # Store script for testing mode
        self._current_script = script
        
        # Testing mode - simulate successful API response
        if self.testing_mode:
            import uuid
            session_id = f"mock_{uuid.uuid4()}"
            self._session_start_times[session_id] = time.time()
            video_count = self._count_script_segments(script)
            self.logger.info(f"🧪 Testing mode: Simulating API call for session {session_id} with {video_count} videos")
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
        
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            self.logger.info(f"Requesting shorts generation for script: {script[:100]}...")
            
            response = requests.post(
                url, 
                json=payload, 
                headers=headers,
                timeout=self.request_timeout  # ✅ Use configured timeout
            )
            response.raise_for_status()
            
            result = response.json()
            session_id = result.get('session_id')
            
            if not session_id:
                self.logger.error("No session_id in API response")
                return None
            
            self.logger.info(f"Shorts generation started. Session ID: {session_id}")
            
            # Wait for completion with configured timeout
            completion_status = self._wait_for_completion(session_id)
            
            if not completion_status:
                self.logger.error("Failed to complete video generation")
                return None
            
            # Return the completion status but ensure session_id is included
            # The status response should include session_id, but let's make sure
            if 'session_id' not in completion_status:
                completion_status['session_id'] = session_id
            
            return completion_status
            
        except requests.exceptions.Timeout:
            self.logger.error(f"Request timeout after {self.request_timeout} seconds")
            return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {e}")
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
            # Get the actual script and count segments
            script = self._current_script
            video_count = self._count_script_segments(script) if script else 3
            
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
                        "message": f"Generating video 1 of {video_count}..."
                    }
                elif elapsed < 10:
                    return {
                        "success": True,
                        "session_id": session_id,
                        "status": "processing", 
                        "progress": 75,
                        "message": f"Generating video {video_count} of {video_count}..."
                    }
                else:
                    return {
                        "success": True,
                        "session_id": session_id,
                        "status": "completed",
                        "progress": 100,
                        "message": f"All {video_count} videos generated successfully!",
                        "zip_url": f"http://localhost:5000/mock-download/{session_id}.zip"
                    }
            except:
                # Fallback to completed status
                return {
                    "success": True,
                    "session_id": session_id,
                    "status": "completed",
                    "progress": 100,
                    "message": f"All {video_count} videos generated successfully!",
                    "zip_url": f"http://localhost:5000/mock-download/{session_id}.zip"
                }
        
        # Real API mode
        url = f"{self.base_url}/api/v1/shorts/status/{session_id}"
        headers = {'Content-Type': 'application/json'}
        
        try:
            response = requests.get(
                url, 
                headers=headers,
                timeout=self.status_timeout  # ✅ Use configured status timeout (30s)
            )
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.Timeout:
            self.logger.error(f"Status check timeout after {self.status_timeout} seconds")
            return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Status check failed: {e}")
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
    
    def _wait_for_completion(self, session_id: str, status_url: Optional[str] = None, poll_interval: int = 5) -> Optional[Dict]:
        """
        Poll the API until video generation is complete or timeout
        
        Args:
            session_id: Session ID to check
            status_url: Optional status URL (not used for PDFAPIClient, kept for compatibility)
            poll_interval: Seconds between status checks (default: 5)
            
        Returns:
            Final status dict with download_url or None if failed/timeout
        """
        start_time = time.time()
        
        self.logger.info(f"Waiting for completion (max {self.max_wait_time}s)...")
        
        while True:
            elapsed = time.time() - start_time
            
            # Check if we've exceeded max wait time
            if elapsed > self.max_wait_time:
                self.logger.error(f"Timeout waiting for completion after {self.max_wait_time} seconds")
                return None
            
            # Check status - PDFAPIClient.check_status() only takes session_id
            status = self.check_status(session_id)
            
            if not status:
                self.logger.error("Failed to check status")
                return None
            
            # Log progress
            progress = status.get('progress', 0)
            message = status.get('message', 'Processing...')
            self.logger.info(f"Progress: {progress}% - {message} (elapsed: {int(elapsed)}s / {self.max_wait_time}s)")
            
            # Check if completed
            if status.get('status') == 'completed':
                self.logger.info("Video generation completed successfully!")
                self.logger.info(f"Full status response keys: {list(status.keys())}")
                
                # Extract data from nested 'result' object if present
                result_data = status.get('result', {})
                if result_data:
                    self.logger.info(f"Result data keys: {list(result_data.keys())}")
                
                # Get download URL - try multiple possible locations
                download_url = (
                    status.get('zip_url') or
                    status.get('download_url') or 
                    result_data.get('download_url') or
                    result_data.get('zip_url') or
                    result_data.get('file_url') or
                    status.get('file_url')
                )
                
                if not download_url:
                    self.logger.info("No direct download_url in status, attempting to find it...")
                    download_url = self._try_find_download_url(session_id)
                
                if not download_url:
                    self.logger.error("No download_url in completion status")
                    self.logger.error(f"Status keys: {list(status.keys())}")
                    self.logger.error(f"Result keys: {list(result_data.keys())}")
                    return None
                
                # Make URL absolute if it's relative
                if download_url.startswith('/'):
                    download_url = f"{self.base_url}{download_url}"
                
                # Build the final result dict with flattened data
                final_result = {
                    'status': 'completed',
                    'zip_url': download_url,
                    'download_url': download_url,  # Add both for compatibility
                    'session_id': session_id
                }
                
                # Copy other useful fields from result_data
                if result_data:
                    for key in ['duration', 'format', 'file_path', 'file_url', 'video_count']:
                        if key in result_data:
                            final_result[key] = result_data[key]
                
                self.logger.info(f"✅ Completion data extracted:")
                self.logger.info(f"   Download URL: {download_url}")
                self.logger.info(f"   Session ID: {session_id}")
                
                return final_result
            
            # Check if failed
            if status.get('status') == 'failed':
                error = status.get('error', 'Unknown error')
                self.logger.error(f"Video generation failed: {error}")
                return None
            
            # Wait before next poll
            time.sleep(poll_interval)

    def create_mock_videos(self, script: str, output_dir: str) -> List[str]:
        """Create mock video files for testing"""
        video_files = []
        segments = self._split_script_into_segments(script)
        
        for i, segment in enumerate(segments):
            company_name = self._extract_company_name(segment)
            filename = f"api_{company_name.replace(' ', '_')}.mp4"
            filepath = os.path.join(output_dir, filename)
            
            # Create a dummy video file
            with open(filepath, 'wb') as f:
                f.write(b'fake video content for testing')
            
            video_files.append(filepath)
            print(f"✅ Created mock video {i+1}/{len(segments)}: {filename}")
        
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
            
            response = requests.get(zip_url, stream=True, timeout=self.download_timeout)  # ✅ Use download timeout from environment
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
            self.logger.error("Failed to start video generation")
            return []
        
        session_id = response.get('session_id')
        if not session_id:
            self.logger.error("No session_id in response")
            return []
        
        self.logger.info(f"Video generation completed for session: {session_id}")
        
        # Try to get zip_url from response, if not present, try to find it
        zip_url = response.get('zip_url')
        if not zip_url:
            self.logger.info("No zip_url in response, attempting to find download URL...")
            zip_url = self._try_find_download_url(session_id)
            
            if not zip_url:
                self.logger.error("Failed to find download URL for completed session")
                self.logger.error("This might mean:")
                self.logger.error("  1. The API completed but files aren't ready yet")
                self.logger.error("  2. The download URL pattern has changed")
                self.logger.error("  3. The files were deleted or moved")
                return []
        
        self.logger.info(f"Found download URL: {zip_url}")
        
        # Download ZIP file
        timestamp = int(time.time())
        zip_filename = f"shorts_{session_id}_{timestamp}.zip"
        zip_path = os.path.join(download_folder, zip_filename)
        
        if not self.download_zip(zip_url, zip_path):
            self.logger.error("Failed to download ZIP file")
            return []
        
        # Extract videos
        extract_folder = os.path.join(download_folder, f"extracted_{timestamp}")
        video_files = self.extract_videos(zip_path, extract_folder)
        
        if not video_files:
            self.logger.error("No videos extracted from ZIP file")
            return []
        
        self.logger.info(f"Successfully extracted {len(video_files)} videos")
        
        # Clean up ZIP file after extraction
        try:
            os.remove(zip_path)
            self.logger.info(f"Cleaned up ZIP file: {zip_path}")
        except Exception as e:
            self.logger.warning(f"Failed to clean up ZIP file: {e}")
        
        return video_files

    def download_video(self, download_url: str, output_path: str) -> bool:
        """
        Download a video file from the API
        
        Args:
            download_url: URL to download the video from
            output_path: Local path to save the video
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Downloading video from: {download_url}")
            
            headers = {'Content-Type': 'application/json'}
            
            # Use tuple timeout: (connection timeout, read timeout)
            # Connection: 30s, Read: configured download timeout
            response = requests.get(
                download_url, 
                headers=headers, 
                stream=True,
                timeout=(30, self.download_timeout)  # ✅ Use configured download timeout
            )
            response.raise_for_status()
            
            # Download with progress tracking
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Log progress for large files
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            if int(progress) % 10 == 0:  # Log every 10%
                                self.logger.info(f"Download progress: {progress:.1f}%")
            
            self.logger.info(f"Video downloaded successfully to: {output_path}")
            return True
            
        except requests.exceptions.Timeout:
            self.logger.error(f"Download timeout after {self.download_timeout} seconds")
            return False
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Download failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error during download: {e}")
            return False

class RegularVoiceoverAPIClient:
    """Client for generating regular format voiceover videos (landscape)"""
    
    def __init__(self, base_url: str):
        """
        Initialize the Regular Format Voiceover API client
        
        Args:
            base_url: Base URL of the API
        """
        self.base_url = base_url.rstrip('/')
        self.endpoint = '/api/v1/voiceover/generate'
        self.logger = logging.getLogger(__name__)
        
        # Load timeout values from environment variables
        self.request_timeout = int(os.getenv('API_REQUEST_TIMEOUT', '900'))
        self.status_timeout = int(os.getenv('API_STATUS_TIMEOUT', '30'))
        self.download_timeout = int(os.getenv('API_DOWNLOAD_TIMEOUT', '1200'))
        self.max_wait_time = self.request_timeout
        
        # Add flag for testing mode
        self.testing_mode = os.getenv('API_TESTING_MODE', 'false').lower() == 'true'
        
        self.logger.info(f"Voiceover API Client initialized with timeouts: request={self.request_timeout}s, status={self.status_timeout}s, download={self.download_timeout}s")
    
    def generate_voiceover(self, 
                          script: str,
                          voice: str = "onyx",
                          speed: float = 1.2) -> Optional[Dict]:
        """
        Generate a regular format voiceover video (landscape)
        
        Args:
            script: Text script for the voiceover (no pause markers needed)
            voice: Voice type (alloy, echo, fable, onyx, nova, shimmer)
            speed: Speech speed between 0.25 and 4.0
            
        Returns:
            Response dict with session_id and status, None if failed
        """
        url = f"{self.base_url}{self.endpoint}"
        
        payload = {
            "script": script,
            "voice": voice,
            "speed": speed
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        try:
            self.logger.info(f"Requesting voiceover generation for script: {script[:100]}...")
            
            response = requests.post(
                url, 
                json=payload, 
                headers=headers,
                timeout=self.request_timeout
            )
            response.raise_for_status()
            
            result = response.json()
            
            if not result.get('success'):
                self.logger.error(f"Voiceover generation failed: {result.get('error', 'Unknown error')}")
                return None
            
            session_id = result.get('session_id')
            status_url = result.get('status_url')
            
            if not session_id:
                self.logger.error("No session_id in API response")
                return None
            
            self.logger.info(f"Voiceover generation started. Session ID: {session_id}")
            
            # Wait for completion
            completion_status = self._wait_for_completion(session_id, status_url)
            
            if not completion_status:
                self.logger.error("Failed to complete video generation")
                return None
            
            return completion_status
            
        except requests.exceptions.Timeout:
            self.logger.error(f"Request timeout after {self.request_timeout} seconds")
            return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            return None
    
    def check_status(self, session_id: str, status_url: Optional[str] = None) -> Optional[Dict]:
        """
        Check the status of a voiceover generation request
        
        Args:
            session_id: Session ID from the generation request
            status_url: Optional status URL (if not provided, will construct from session_id)
            
        Returns:
            Status dict with progress info, None if failed
        """
        if status_url:
            url = status_url if status_url.startswith('http') else f"{self.base_url}{status_url}"
        else:
            url = f"{self.base_url}/api/v1/voiceover/status/{session_id}"
        
        try:
            response = requests.get(url, timeout=self.status_timeout)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.Timeout:
            self.logger.error(f"Status check timeout after {self.status_timeout} seconds")
            return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Status check failed: {e}")
            return None
    
    def _wait_for_completion(self, session_id: str, status_url: Optional[str] = None, poll_interval: int = 5) -> Optional[Dict]:
        """
        Poll the API until video generation is complete or timeout
        
        Args:
            session_id: Session ID to check
            status_url: Optional status URL
            poll_interval: Seconds between status checks (default: 5)
            
        Returns:
            Final status dict with download_url or None if failed/timeout
        """
        start_time = time.time()
        
        self.logger.info(f"Waiting for completion (max {self.max_wait_time}s)...")
        
        while True:
            elapsed = time.time() - start_time
            
            # Check if we've exceeded max wait time
            if elapsed > self.max_wait_time:
                self.logger.error(f"Timeout waiting for completion after {self.max_wait_time} seconds")
                return None
            
            # Check status
            status = self.check_status(session_id, status_url)
            
            if not status:
                self.logger.error("Failed to check status")
                return None
            
            # Log progress
            progress = status.get('progress', 0)
            message = status.get('message', 'Processing...')
            self.logger.info(f"Progress: {progress}% - {message} (elapsed: {int(elapsed)}s / {self.max_wait_time}s)")
            
            # Check if completed
            if status.get('status') == 'completed':
                self.logger.info("Video generation completed successfully!")
                self.logger.info(f"Full status response keys: {list(status.keys())}")
                
                # Extract data from nested 'result' object if present
                result_data = status.get('result', {})
                if result_data:
                    self.logger.info(f"Result data keys: {list(result_data.keys())}")
                
                # Get download URL - try multiple possible locations
                download_url = (
                    status.get('download_url') or 
                    result_data.get('download_url') or
                    result_data.get('file_url') or
                    result_data.get('full_file_url') or
                    status.get('file_url')
                )
                
                if not download_url:
                    self.logger.error("No download_url in completion status")
                    self.logger.error(f"Status keys: {list(status.keys())}")
                    self.logger.error(f"Result keys: {list(result_data.keys())}")
                    return None
                
                # Make URL absolute if it's relative
                if download_url.startswith('/'):
                    download_url = f"{self.base_url}{download_url}"
                
                # Get filename - CHECK RESULT FIRST, then status
                filename = (
                    result_data.get('filename') or
                    status.get('filename') or
                    result_data.get('file_name') or
                    status.get('file_name')
                )
                
                self.logger.info(f"Extracted filename from result: {filename}")
                
                # If still no filename, try to extract from file_path
                if not filename:
                    file_path = result_data.get('file_path') or status.get('file_path')
                    if file_path:
                        filename = os.path.basename(file_path)
                        self.logger.info(f"Extracted filename from file_path: {filename}")
                
                # Build the final result dict with flattened data
                final_result = {
                    'status': 'completed',
                    'download_url': download_url,
                    'filename': filename,
                    'session_id': session_id
                }
                
                # Copy other useful fields from result_data
                if result_data:
                    for key in ['duration', 'format', 'file_path', 'file_url']:
                        if key in result_data:
                            final_result[key] = result_data[key]
                
                self.logger.info(f"✅ Completion data extracted:")
                self.logger.info(f"   Download URL: {download_url}")
                self.logger.info(f"   Filename: {filename}")
                self.logger.info(f"   File path: {final_result.get('file_path', 'N/A')}")
                
                return final_result
            
            # Check if failed
            if status.get('status') == 'failed':
                error = status.get('error', 'Unknown error')
                self.logger.error(f"Video generation failed: {error}")
                return None
            
            # Wait before next poll
            time.sleep(poll_interval)
    
    def generate_and_download_video(self, 
                                    script: str,
                                    download_folder: str = "downloads",
                                    voice: str = "onyx",
                                    speed: float = 1.2) -> Optional[str]:
        """
        Generate and download a regular format video
        
        Args:
            script: Text script for the voiceover
            download_folder: Folder to save downloaded videos
            voice: Voice type
            speed: Speech speed
            
        Returns:
            Path to downloaded video file, None if failed
        """
        try:
            self.logger.info("Starting regular video generation and download")
            
            # Step 1: Generate voiceover and wait for completion
            result = self.generate_voiceover(script, voice, speed)
            
            if not result:
                self.logger.error("Failed to generate voiceover")
                return None
            
            # Step 2: Get download URL
            download_url = result.get('download_url')
            
            if not download_url:
                self.logger.error("No download URL in response")
                self.logger.error(f"Response keys: {list(result.keys())}")
                return None
            
            # Step 3: Get the original filename from API response
            filename = result.get('filename')
            
            if not filename:
                # Fallback: extract from download URL or file_url
                file_url = result.get('file_url', '')
                if file_url:
                    # Extract filename from URL like /download-voiceover/voiceover_api_voiceover_xxx.mp4
                    filename = file_url.split('/')[-1]
                    self.logger.info(f"Extracted filename from file_url: {filename}")
                else:
                    # Last resort fallback
                    filename = f'voiceover_{datetime.now().strftime("%Y%m%d_%H%M%S")}.mp4'
                    self.logger.warning(f"No filename in API response, using fallback: {filename}")
            
            output_path = os.path.join(download_folder, filename)
            
            # Ensure download directory exists
            os.makedirs(download_folder, exist_ok=True)
            
            # Step 4: Download the video
            self.logger.info(f"Downloading video from: {download_url}")
            self.logger.info(f"Saving to: {output_path}")
            self.logger.info(f"Original filename: {filename}")
            
            response = requests.get(download_url, timeout=300, stream=True)
            response.raise_for_status()
            
            # Download with progress tracking
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        # Log progress every 20%
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            if downloaded == len(chunk) or int(progress) % 20 == 0:
                                self.logger.info(f"Download progress: {progress:.1f}%")
            
            # Verify file exists and has content
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                file_size_mb = os.path.getsize(output_path) / (1024*1024)
                self.logger.info(f"✅ Video downloaded successfully: {output_path}")
                self.logger.info(f"   Original filename preserved: {filename}")
                self.logger.info(f"   File size: {file_size_mb:.2f} MB")
                return output_path
            else:
                self.logger.error("Downloaded file is empty or doesn't exist")
                return None
            
        except requests.exceptions.Timeout:
            self.logger.error("Download timeout")
            return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Download failed: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error during video download: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None
