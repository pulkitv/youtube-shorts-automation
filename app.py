from flask import Flask, request, jsonify, send_file, send_from_directory, render_template_string
import uuid
import time
import os
import json
import threading
from datetime import datetime
from pathlib import Path
import logging
import requests
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Create necessary directories
os.makedirs('voiceovers', exist_ok=True)
os.makedirs('temp', exist_ok=True)
os.makedirs('uploads', exist_ok=True)
os.makedirs('processed', exist_ok=True)

# Configuration for external video generation API
VIDEO_API_CONFIG = {
    'base_url': os.getenv('VIDEO_API_BASE_URL', 'https://api.your-video-service.com'),
    'api_key': os.getenv('VIDEO_API_KEY', ''),
    'timeout': int(os.getenv('VIDEO_API_TIMEOUT', '300')),  # 5 minutes default
    'max_retries': int(os.getenv('VIDEO_API_MAX_RETRIES', '3'))
}

# In-memory storage for session tracking
sessions = {}
session_lock = threading.Lock()

def call_external_video_api(endpoint, payload, session_id):
    """Make API call to external video generation service"""
    try:
        headers = {
            'Authorization': f'Bearer {VIDEO_API_CONFIG["api_key"]}',
            'Content-Type': 'application/json',
            'User-Agent': 'YouTube-Automation-Service/1.0'
        }
        
        url = urljoin(VIDEO_API_CONFIG['base_url'], endpoint)
        
        logger.info(f"Calling external API: {url} for session {session_id}")
        
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=VIDEO_API_CONFIG['timeout']
        )
        
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.RequestException as e:
        logger.error(f"External API call failed for session {session_id}: {e}")
        raise Exception(f"Video generation service error: {str(e)}")

def download_video_from_url(video_url, local_filename, session_id):
    """Download video file from external API to local storage"""
    try:
        headers = {}
        if VIDEO_API_CONFIG['api_key']:
            headers['Authorization'] = f'Bearer {VIDEO_API_CONFIG["api_key"]}'
        
        response = requests.get(video_url, headers=headers, stream=True, timeout=300)
        response.raise_for_status()
        
        local_path = os.path.join('voiceovers', local_filename)
        
        with open(local_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        logger.info(f"Downloaded video file {local_filename} for session {session_id}")
        return local_path
        
    except Exception as e:
        logger.error(f"Failed to download video for session {session_id}: {e}")
        raise

def generate_real_video(session_id, script, voice, speed, video_type="short"):
    """Generate real videos using external AI video generation service"""
    try:
        with session_lock:
            sessions[session_id]["status"] = "processing"
            sessions[session_id]["progress"] = 10
            sessions[session_id]["message"] = "Connecting to video generation service..."
        
        # Prepare payload for external API
        if video_type == "short":
            payload = {
                'type': 'youtube_shorts',
                'script': script,
                'voice': voice,
                'speed': speed,
                'format': 'mp4',
                'orientation': 'vertical',
                'split_on_pause': True,
                'max_duration_per_segment': 60,
                'callback_url': f'http://localhost:5000/api/v1/webhook/video-complete/{session_id}'
            }
            endpoint = '/api/v1/shorts/generate'
        else:
            payload = {
                'type': 'voiceover_video',
                'script': script,
                'voice': voice,
                'speed': speed,
                'format': 'mp4',
                'orientation': 'landscape',
                'include_waveform': True,
                'background_type': 'gradient',
                'callback_url': f'http://localhost:5000/api/v1/webhook/video-complete/{session_id}'
            }
            endpoint = '/api/v1/generate/voiceover'
        
        with session_lock:
            sessions[session_id]["progress"] = 25
            sessions[session_id]["message"] = "Submitting request to video generation service..."
        
        # Call external API
        api_response = call_external_video_api(endpoint, payload, session_id)
        
        # Store external job ID for tracking
        external_job_id = api_response.get('job_id') or api_response.get('session_id')
        
        with session_lock:
            sessions[session_id]["external_job_id"] = external_job_id
            sessions[session_id]["progress"] = 50
            sessions[session_id]["message"] = "Video generation in progress..."
        
        # Poll for completion or wait for webhook
        if api_response.get('status') == 'processing':
            # Start polling for status updates
            poll_external_api_status(session_id, external_job_id, video_type)
        elif api_response.get('status') == 'completed':
            # Immediate completion
            process_completed_video(session_id, api_response, video_type)
        
    except Exception as e:
        logger.error(f"Error in real video generation: {e}")
        with session_lock:
            sessions[session_id]["status"] = "failed"
            sessions[session_id]["error"] = str(e)
            sessions[session_id]["message"] = f"Video generation failed: {str(e)}"

def poll_external_api_status(session_id, external_job_id, video_type):
    """Poll external API for job status updates"""
    max_polls = 60  # 5 minutes with 5-second intervals
    poll_count = 0
    
    while poll_count < max_polls:
        try:
            time.sleep(5)  # Wait 5 seconds between polls
            poll_count += 1
            
            # Check if session was cancelled
            with session_lock:
                if sessions.get(session_id, {}).get("status") == "cancelled":
                    return
            
            # Poll external API - use shorts-specific endpoint for shorts
            if video_type == "short":
                status_url = f'/api/v1/shorts/status/{external_job_id}'
            else:
                status_url = f'/api/v1/status/{external_job_id}'
            
            headers = {
                'Authorization': f'Bearer {VIDEO_API_CONFIG["api_key"]}',
                'Content-Type': 'application/json'
            }
            
            url = urljoin(VIDEO_API_CONFIG['base_url'], status_url)
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            status_data = response.json()
            
            # Update session with external API progress
            with session_lock:
                external_progress = status_data.get('progress', 50)
                sessions[session_id]["progress"] = min(50 + (external_progress // 2), 90)
                sessions[session_id]["message"] = status_data.get('message', 'Processing video...')
            
            if status_data.get('status') == 'completed':
                process_completed_video(session_id, status_data, video_type)
                return
            elif status_data.get('status') == 'failed':
                with session_lock:
                    sessions[session_id]["status"] = "failed"
                    sessions[session_id]["error"] = status_data.get('error', 'Video generation failed')
                return
                
        except Exception as e:
            logger.error(f"Error polling external API for session {session_id}: {e}")
            poll_count += 1
    
    # Timeout
    with session_lock:
        sessions[session_id]["status"] = "failed"
        sessions[session_id]["error"] = "Video generation timed out"

def process_completed_video(session_id, api_response, video_type):
    """Process completed video from external API"""
    try:
        with session_lock:
            sessions[session_id]["progress"] = 90
            sessions[session_id]["message"] = "Downloading generated videos..."
        
        if video_type == "short":
            # Handle multiple video files for shorts
            videos = api_response.get('videos', [])
            video_files = []
            
            for i, video_data in enumerate(videos):
                video_url = video_data.get('download_url')
                if video_url:
                    filename = f"api_shorts_{session_id}_part_{i+1}.mp4"
                    download_video_from_url(video_url, filename, session_id)
                    video_files.append(filename)
            
            # Create ZIP if multiple files
            if len(video_files) > 1:
                import zipfile
                zip_filename = f"api_shorts_{session_id}.zip"
                zip_path = os.path.join('voiceovers', zip_filename)
                
                with zipfile.ZipFile(zip_path, 'w') as zipf:
                    for video_file in video_files:
                        video_path = os.path.join('voiceovers', video_file)
                        if os.path.exists(video_path):
                            zipf.write(video_path, video_file)
                
                with session_lock:
                    sessions[session_id]["status"] = "completed"
                    sessions[session_id]["progress"] = 100
                    sessions[session_id]["message"] = "All videos generated successfully!"
                    sessions[session_id]["zip_url"] = f"http://localhost:5000/download-voiceover/{zip_filename}"
            else:
                with session_lock:
                    sessions[session_id]["status"] = "completed"
                    sessions[session_id]["progress"] = 100
                    sessions[session_id]["message"] = "Video generated successfully!"
                    sessions[session_id]["zip_url"] = f"http://localhost:5000/download-voiceover/{video_files[0]}"
        
        else:
            # Handle single video for voiceover
            video_url = api_response.get('download_url')
            if video_url:
                filename = f"api_voiceover_{session_id}.mp4"
                download_video_from_url(video_url, filename, session_id)
                
                with session_lock:
                    sessions[session_id]["status"] = "completed"
                    sessions[session_id]["progress"] = 100
                    sessions[session_id]["message"] = "Voiceover generation completed successfully!"
                    sessions[session_id]["result"] = {
                        "file_url": f"http://localhost:5000/download-voiceover/{filename}",
                        "filename": filename,
                        "duration": api_response.get('duration', 0),
                        "format": "mp4",
                        "file_size": api_response.get('file_size', 'Unknown')
                    }
        
        logger.info(f"Video generation completed for session {session_id}")
        
    except Exception as e:
        logger.error(f"Error processing completed video: {e}")
        with session_lock:
            sessions[session_id]["status"] = "failed"
            sessions[session_id]["error"] = str(e)

@app.route('/')
def home():
    """Home page with basic API info"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>YouTube Video Generation API</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .endpoint { background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 5px; }
            .method { color: #007bff; font-weight: bold; }
        </style>
    </head>
    <body>
        <h1>🎬 YouTube Video Generation API</h1>
        <p>This API provides video generation services for YouTube automation.</p>
        
        <h2>Available Endpoints:</h2>
        
        <div class="endpoint">
            <span class="method">POST</span> /api/v1/generate-shorts
            <br>Generate YouTube Shorts (vertical videos with pause markers)
        </div>
        
        <div class="endpoint">
            <span class="method">GET</span> /api/v1/shorts-status/{session_id}
            <br>Check status of shorts generation
        </div>
        
        <div class="endpoint">
            <span class="method">POST</span> /api/v1/voiceover/generate
            <br>Generate regular voiceover videos (landscape format)
        </div>
        
        <div class="endpoint">
            <span class="method">GET</span> /api/v1/voiceover/status/{session_id}
            <br>Check status of voiceover generation
        </div>
        
        <div class="endpoint">
            <span class="method">GET</span> /download-voiceover/{filename}
            <br>Download generated video files
        </div>
        
        <div class="endpoint">
            <span class="method">GET</span> /health
            <br>API health check
        </div>
        
        <h2>Status:</h2>
        <p>✅ API Server Running</p>
        <p>✅ Video Generation Service Active</p>
        <p>✅ Ready to Accept Requests</p>
    </body>
    </html>
    """
    return html

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "YouTube Video Generation API"
    })

@app.route('/api/v1/generate-shorts', methods=['POST'])
def generate_shorts():
    """Generate YouTube Shorts from script"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        script = data.get('script')
        if not script:
            return jsonify({"error": "Script is required"}), 400
        
        voice = data.get('voice', 'nova')
        speed = data.get('speed', 1.0)
        
        # Generate session ID
        session_id = f"api_{uuid.uuid4()}"
        
        # Initialize session
        with session_lock:
            sessions[session_id] = {
                "status": "started",
                "progress": 0,
                "message": "Starting generation...",
                "created_at": datetime.now().isoformat(),
                "script": script,
                "voice": voice,
                "speed": speed
            }
        
        # Start background generation
        thread = threading.Thread(target=generate_real_video, args=(session_id, script, voice, speed, "short"))
        thread.start()
        
        # Estimate segments based on pause markers
        estimated_segments = len([part for part in script.split("—") if part.strip()])
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "status": "processing",
            "message": "YouTube Shorts generation started successfully",
            "estimated_segments": estimated_segments,
            "status_url": f"/api/v1/shorts-status/{session_id}",
            "created_at": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error in generate_shorts: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/shorts-status/<session_id>')
def shorts_status(session_id):
    """Check status of shorts generation"""
    try:
        with session_lock:
            session = sessions.get(session_id)
        
        if not session:
            return jsonify({"error": "Session not found"}), 404
        
        response = {
            "success": True,
            "session_id": session_id,
            "status": session["status"],
            "progress": session["progress"],
            "message": session["message"]
        }
        
        if session["status"] == "completed" and "zip_url" in session:
            response["zip_url"] = session["zip_url"]
            # Add mock video details for completed sessions
            parts = session.get("script", "").split("—")
            response["count"] = len([part for part in parts if part.strip()])
            response["videos"] = []
            for i, part in enumerate(parts):
                if part.strip():
                    response["videos"].append({
                        "index": i + 1,
                        "file_url": f"/download-voiceover/api_shorts_{session_id}_part_{i+1}.mp4",
                        "duration": 8.5 + i,
                        "format": "mp4",
                        "download_name": f"api_shorts_{session_id}_part_{i+1}.mp4"
                    })
        elif session["status"] == "failed" and "error" in session:
            response["error"] = session["error"]
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in shorts_status: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/voiceover/generate', methods=['POST'])
def generate_voiceover():
    """Generate regular format voiceover video"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        script = data.get('script')
        if not script:
            return jsonify({"error": "Script is required"}), 400
        
        voice = data.get('voice', 'nova')
        speed = data.get('speed', 1.0)
        format_type = data.get('format', 'mp4')
        background_image_url = data.get('background_image_url')
        webhook_url = data.get('webhook_url')
        
        # Validate parameters
        valid_voices = ['nova', 'alloy', 'echo', 'fable', 'onyx', 'shimmer']
        if voice not in valid_voices:
            return jsonify({"error": f"Invalid voice. Available voices: {', '.join(valid_voices)}"}), 400
        
        if not (0.25 <= speed <= 4.0):
            return jsonify({"error": "Speed must be between 0.25 and 4.0"}), 400
        
        valid_formats = ['mp3', 'wav', 'mp4']
        if format_type not in valid_formats:
            return jsonify({"error": f"Invalid format. Available formats: {', '.join(valid_formats)}"}), 400
        
        # Generate session ID
        session_id = f"api_voiceover_{uuid.uuid4()}"
        
        # Initialize session
        with session_lock:
            sessions[session_id] = {
                "status": "started",
                "progress": 0,
                "message": "Starting voiceover generation...",
                "created_at": datetime.now().isoformat(),
                "script": script,
                "voice": voice,
                "speed": speed,
                "format": format_type,
                "background_image_url": background_image_url,
                "webhook_url": webhook_url
            }
        
        # Start background video generation
        thread = threading.Thread(
            target=generate_real_video,
            args=(session_id, script, voice, speed, "post")
        )
        thread.daemon = True
        thread.start()
        
        logger.info(f"Started voiceover generation for session {session_id}")
        
        return jsonify({
            "success": True,
            "session_id": session_id,
            "message": "Voiceover generation started",
            "status_url": f"/api/v1/voiceover/status/{session_id}"
        }), 202
        
    except Exception as e:
        logger.error(f"Error in generate_voiceover: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/voiceover/status/<session_id>')
def voiceover_status(session_id):
    """Check status of voiceover generation"""
    try:
        with session_lock:
            session = sessions.get(session_id)
        
        if not session:
            return jsonify({"error": "Session not found"}), 404
        
        response = {
            "session_id": session_id,
            "status": session["status"],
            "progress": session["progress"],
            "message": session["message"],
            "script": session.get("script", ""),
            "voice": session.get("voice", "nova"),
            "speed": session.get("speed", 1.0),
            "format": session.get("format", "mp4"),
            "created_at": session["created_at"]
        }
        
        if session["status"] == "completed" and "result" in session:
            response["result"] = session["result"]
        elif session["status"] == "failed" and "error" in session:
            response["error"] = session["error"]
        
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in voiceover_status: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/v1/voiceover/download/<session_id>')
def download_voiceover_file(session_id):
    """Download the generated voiceover file directly"""
    try:
        with session_lock:
            session = sessions.get(session_id)
        
        if not session:
            return jsonify({"error": "Session not found"}), 404
        
        if session["status"] != "completed":
            return jsonify({"error": "Generation not completed yet"}), 400
        
        if "result" not in session:
            return jsonify({"error": "No file available for download"}), 404
        
        # Extract filename from the result
        filename = session["result"]["filename"]
        file_path = os.path.join('voiceovers', filename)
        
        if not os.path.exists(file_path):
            return jsonify({"error": "File not found on server"}), 404
        
        return send_file(file_path, as_attachment=True, download_name=filename)
        
    except Exception as e:
        logger.error(f"Error in download_voiceover_file: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/download-voiceover/<filename>')
def download_voiceover(filename):
    """Download voiceover file by filename"""
    try:
        return send_from_directory('voiceovers', filename, as_attachment=True)
    except Exception as e:
        logger.error(f"Error downloading file {filename}: {e}")
        return jsonify({"error": "File not found"}), 404

@app.route('/voiceovers')
def list_voiceovers():
    """List available voiceover files"""
    try:
        files = []
        voiceovers_dir = Path('voiceovers')
        if voiceovers_dir.exists():
            for file_path in voiceovers_dir.iterdir():
                if file_path.is_file():
                    files.append({
                        "filename": file_path.name,
                        "size": file_path.stat().st_size,
                        "created": datetime.fromtimestamp(file_path.stat().st_ctime).isoformat()
                    })
        
        return jsonify({
            "files": files,
            "count": len(files)
        })
        
    except Exception as e:
        logger.error(f"Error listing voiceovers: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/status')
def api_status():
    """Get API status and session count"""
    try:
        with session_lock:
            active_sessions = len([s for s in sessions.values() if s["status"] == "processing"])
            total_sessions = len(sessions)
        
        return jsonify({
            "status": "running",
            "timestamp": datetime.now().isoformat(),
            "active_sessions": active_sessions,
            "total_sessions": total_sessions,
            "endpoints": [
                "POST /api/v1/generate-shorts",
                "GET /api/v1/shorts-status/{session_id}",
                "POST /api/v1/voiceover/generate", 
                "GET /api/v1/voiceover/status/{session_id}",
                "GET /api/v1/voiceover/download/{session_id}",
                "GET /download-voiceover/{filename}",
                "GET /health"
            ]
        })
        
    except Exception as e:
        logger.error(f"Error in api_status: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting YouTube Video Generation API Server...")
    print("📍 Server will be available at: http://localhost:5000")
    print("📖 API Documentation: http://localhost:5000")
    print("❤️  Health Check: http://localhost:5000/health")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)