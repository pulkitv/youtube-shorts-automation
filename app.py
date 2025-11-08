from flask import Flask, request, jsonify, send_file, send_from_directory, render_template_string
import uuid
import time
import os
import json
import threading
from datetime import datetime
from pathlib import Path
import logging
from werkzeug.utils import secure_filename

# Import the actual voiceover system used by the UI
from voiceover_system import VoiceoverSystem

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Create necessary directories
os.makedirs('voiceovers', exist_ok=True)
os.makedirs('temp', exist_ok=True)
os.makedirs('uploads', exist_ok=True)
os.makedirs('processed', exist_ok=True)

# Initialize the voiceover system (same as main UI)
voiceover_system = VoiceoverSystem()

# In-memory storage for session tracking
sessions = {}
session_lock = threading.Lock()

def generate_real_video(session_id, script, voice, speed, video_type="short"):
    """Generate real videos using the local voiceover system (same as main UI)"""
    try:
        with session_lock:
            sessions[session_id]["status"] = "processing"
            sessions[session_id]["progress"] = 10
            sessions[session_id]["message"] = "Starting video generation..."
        
        logger.info(f"Starting local video generation for session {session_id}")
        
        # Update progress
        with session_lock:
            sessions[session_id]["progress"] = 25
            sessions[session_id]["message"] = "Generating videos using local system..."
        
        # Use the same logic as the main UI - voiceover_system handles pause markers automatically
        if video_type == "short":
            # YouTube Shorts generation - voiceover_system will automatically split by pause markers
            result = voiceover_system.generate_speech(
                text=script,
                voice=voice,
                speed=speed,
                format='mp4',  # YouTube Shorts are always MP4
                session_id=session_id,
                background_image_path=None,  # Can be enhanced later to support background images
                generation_type='youtube_shorts'  # This enables pause marker splitting in voiceover_system
            )
        else:
            # Regular voiceover generation
            result = voiceover_system.generate_speech(
                text=script,
                voice=voice,
                speed=speed,
                format='mp4',
                session_id=session_id,
                background_image_path=None,
                generation_type='regular'
            )
        
        # Update progress
        with session_lock:
            sessions[session_id]["progress"] = 90
            sessions[session_id]["message"] = "Processing completed videos..."
        
        if result['success']:
            if video_type == "short":
                # For YouTube Shorts, the result contains a ZIP file with multiple videos
                # voiceover_system has already handled the pause marker splitting
                with session_lock:
                    sessions[session_id]["status"] = "completed"
                    sessions[session_id]["progress"] = 100
                    sessions[session_id]["message"] = "YouTube Shorts generated successfully!"
                    sessions[session_id]["zip_url"] = f"http://localhost:5000{result['file_url']}"
                    
                    # Get segment count from the result (voiceover_system provides this)
                    segments = result.get('segments', 1)
                    sessions[session_id]["count"] = segments
                    sessions[session_id]["videos"] = []
                    
                    # Create video array based on actual segments generated
                    for i in range(segments):
                        sessions[session_id]["videos"].append({
                            "index": i + 1,
                            "file_url": f"/download-voiceover/{session_id}_part_{i+1}.mp4",
                            "duration": result.get('duration', 8.5),
                            "format": "mp4",
                            "download_name": f"{session_id}_part_{i+1}.mp4"
                        })
            else:
                # Regular voiceover
                with session_lock:
                    sessions[session_id]["status"] = "completed"
                    sessions[session_id]["progress"] = 100
                    sessions[session_id]["message"] = "Voiceover generated successfully!"
                    sessions[session_id]["result"] = {
                        "file_url": f"http://localhost:5000{result['file_url']}",
                        "filename": result.get('filename', f'voiceover_{session_id}.mp4'),
                        "duration": result.get('duration', 0),
                        "format": "mp4"
                    }
            
            logger.info(f"Video generation completed successfully for session {session_id}")
        else:
            # Handle error
            error_message = result.get('error', 'Unknown error occurred')
            with session_lock:
                sessions[session_id]["status"] = "failed"
                sessions[session_id]["error"] = error_message
                sessions[session_id]["message"] = f"Video generation failed: {error_message}"
            
            logger.error(f"Video generation failed for session {session_id}: {error_message}")
        
    except Exception as e:
        logger.error(f"Error in real video generation: {e}")
        with session_lock:
            sessions[session_id]["status"] = "failed"
            sessions[session_id]["error"] = str(e)
            sessions[session_id]["message"] = f"Video generation failed: {str(e)}"

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
        
        voice = data.get('voice', 'onyx')
        speed = data.get('speed', 1.2)
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
            "voice": session.get("voice", "onyx"),
            "speed": session.get("speed", 1.2),
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

@app.route('/api/stats', methods=['GET'])
def get_automation_stats():
    """Get comprehensive automation statistics"""
    try:
        stats = automation.get_automation_stats()
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/iteration/run', methods=['POST'])
def run_iteration():
    """Manually trigger an automation iteration"""
    try:
        data = request.get_json() or {}
        custom_scripts = data.get('custom_scripts', [])
        script_sources = data.get('script_sources', [])
        
        logger.info(f"Manual iteration triggered with {len(custom_scripts)} custom scripts")
        
        # Run iteration in background
        results = automation.run_automation_iteration(
            script_sources=script_sources,
            custom_scripts=custom_scripts
        )
        
        return jsonify({
            'success': True,
            'message': 'Iteration completed',
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Manual iteration failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/retry-failed', methods=['POST'])
def retry_failed_uploads():
    """Retry failed uploads with smart backoff"""
    try:
        retry_count = automation.smart_retry_failed_uploads()
        
        return jsonify({
            'success': True,
            'message': f'Set up {retry_count} videos for retry',
            'retry_count': retry_count
        })
        
    except Exception as e:
        logger.error(f"Failed to retry uploads: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/cleanup', methods=['POST'])
def cleanup_old_files():
    """Clean up old processed videos"""
    try:
        data = request.get_json() or {}
        days_old = data.get('days_old', 7)
        
        cleaned_count = automation.cleanup_old_videos(days_old)
        
        return jsonify({
            'success': True,
            'message': f'Cleaned up {cleaned_count} old video files',
            'cleaned_count': cleaned_count
        })
        
    except Exception as e:
        logger.error(f"Cleanup failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/queue/status', methods=['GET'])
def get_queue_status():
    """Get current upload queue status with detailed breakdown"""
    try:
        queue_data = automation.load_upload_queue()
        
        # Organize by status
        status_breakdown = {}
        for video in queue_data:
            status = video.get('status', 'unknown')
            if status not in status_breakdown:
                status_breakdown[status] = []
            status_breakdown[status].append({
                'title': video.get('title', 'Unknown'),
                'scheduled_time': video.get('scheduled_time'),
                'file_path': video.get('file_path'),
                'upload_attempts': video.get('upload_attempts', 0),
                'last_attempt_time': video.get('last_attempt_time')
            })
        
        return jsonify({
            'success': True,
            'total_videos': len(queue_data),
            'status_breakdown': status_breakdown,
            'queue_health': {
                'pending_count': len(status_breakdown.get('pending', [])),
                'failed_count': len(status_breakdown.get('failed', [])),
                'success_rate': len(status_breakdown.get('uploaded', [])) / max(1, len(queue_data)) * 100
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get queue status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/schedule/optimize', methods=['POST'])
def optimize_schedule():
    """Optimize upload schedule based on performance data"""
    try:
        data = request.get_json() or {}
        target_uploads_per_day = data.get('target_uploads_per_day', 10)
        
        # Get current stats
        stats = automation.get_automation_stats()
        avg_performance = stats.get('avg_performance', {})
        
        # Calculate optimal scheduling
        if avg_performance.get('avg_videos_per_minute', 0) > 0:
            estimated_time_per_video = 1 / avg_performance['avg_videos_per_minute']
            optimal_interval_hours = (estimated_time_per_video * 60) / target_uploads_per_day * 24
            
            recommendation = {
                'optimal_interval_hours': round(optimal_interval_hours, 2),
                'estimated_daily_capacity': round(24 / optimal_interval_hours, 1),
                'current_success_rate': avg_performance.get('avg_success_rate', 0) * 100
            }
        else:
            recommendation = {
                'message': 'Insufficient performance data for optimization',
                'suggestion': 'Run a few iterations first to gather performance metrics'
            }
        
        return jsonify({
            'success': True,
            'optimization': recommendation,
            'current_stats': stats
        })
        
    except Exception as e:
        logger.error(f"Schedule optimization failed: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    print("🚀 Starting YouTube Video Generation API Server...")
    print("📍 Server will be available at: http://localhost:5000")
    print("📖 API Documentation: http://localhost:5000")
    print("❤️  Health Check: http://localhost:5000/health")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)