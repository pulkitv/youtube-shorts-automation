# 🚀 YouTube Shorts Automation API

A RESTful API for automated YouTube Shorts generation, scheduling, and social media distribution. Generate professional video content from text scripts with automated YouTube uploads and Twitter integration via Make.com webhooks.

---

## 📋 Table of Contents

- [Features](#-features)
- [Quick Start](#-quick-start)
- [API Endpoints](#-api-endpoints)
- [Authentication](#-authentication)
- [Request Examples](#-request-examples)
- [Response Formats](#-response-formats)
- [Error Handling](#-error-handling)
- [Rate Limits](#-rate-limits)
- [Workflow](#-workflow)
- [Best Practices](#-best-practices)

---

## ✨ Features

- 🎬 **Automated Video Generation**: Convert text scripts to professional videos with AI voiceover
- 📅 **Scheduled Publishing**: Set future publish times for YouTube videos
- 🐦 **Twitter Integration**: Automatic tweet scheduling via Make.com webhooks
- 🔄 **Background Processing**: Non-blocking async job processing
- 📊 **Job Tracking**: Real-time status monitoring and progress updates
- 🔐 **Secure Authentication**: API key-based authentication
- 📈 **Rate Limiting**: Built-in protection against API abuse
- 🎨 **Multiple Formats**: Support for YouTube Shorts (9:16) and regular videos (16:9)
- 🗣️ **Voice Options**: 6 different AI voices (OpenAI TTS)
- ⚡ **Fast Processing**: Optimized video generation pipeline

---

## 🚀 Quick Start

### Base URL
```
http://your-server:8000
```

### Authentication
All endpoints require an API key in the request header:
```
X-API-Key: your-api-key-here
```

### Basic Request Example
```bash
curl -X POST http://your-server:8000/api/videos/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{
    "market_script": "Tesla stock surged today.\n— pause —\nRevenue up 30%.",
    "voice": "onyx",
    "speed": 1.2,
    "video_type": "short",
    "scheduled_datetime": "2025-12-20T15:30:00"
  }'
```

---

## 📡 API Endpoints

### 1. Generate Videos

**Endpoint:** `POST /api/videos/generate`

**Description:** Create a video generation job. Videos are generated immediately and uploaded to YouTube with scheduled publish times. Twitter posts are scheduled via Make.com webhook.

**Headers:**
```
Content-Type: application/json
X-API-Key: your-api-key-here
```

**Request Body:**
```json
{
  "market_script": "Your video script here.\n— pause —\nNext video segment.",
  "voice": "onyx",
  "speed": 1.2,
  "video_type": "short",
  "scheduled_datetime": "2025-12-20T15:30:00"
}
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `market_script` | string | Yes | Video script. Use `— pause —` to separate multiple videos (for shorts only) |
| `voice` | string | No | AI voice: `alloy`, `echo`, `fable`, `onyx`, `nova`, `shimmer` (default: `onyx`) |
| `speed` | float | No | Speech speed: 0.5 to 2.0 (default: 1.2) |
| `video_type` | string | Yes | `short` (9:16 vertical) or `regular` (16:9 landscape) |
| `scheduled_datetime` | string | Yes | ISO 8601 datetime: `YYYY-MM-DDTHH:MM:SS` |

**Response:**
```json
{
  "success": true,
  "job_id": "job_1765896140_ef13ym0t",
  "message": "Video generation started",
  "status": "queued",
  "estimated_videos": 2,
  "check_status_url": "/api/jobs/job_1765896140_ef13ym0t"
}
```

---

### 2. Check Job Status

**Endpoint:** `GET /api/jobs/{job_id}`

**Description:** Get real-time status of a video generation job.

**Headers:**
```
X-API-Key: your-api-key-here
```

**Response:**
```json
{
  "job_id": "job_1765896140_ef13ym0t",
  "status": "processing",
  "progress": 75,
  "message": "Uploading video 2 of 2...",
  "created_at": "2025-12-16T20:12:20.123456",
  "completed_at": null,
  "videos_generated": 2,
  "videos_uploaded": 1,
  "error": null
}
```

**Status Values:**
- `queued` - Job waiting to be processed
- `processing` - Currently generating/uploading videos
- `completed` - All videos generated and uploaded successfully
- `failed` - Job failed (check `error` field)
- `cancelled` - Job was cancelled

---

### 3. List Jobs

**Endpoint:** `GET /api/jobs`

**Description:** List all jobs for your API key.

**Headers:**
```
X-API-Key: your-api-key-here
```

**Query Parameters:**
- `status` (optional): Filter by status (`queued`, `processing`, `completed`, `failed`)
- `limit` (optional): Maximum number of jobs to return (default: 50, max: 100)

**Response:**
```json
{
  "success": true,
  "count": 2,
  "jobs": [
    {
      "job_id": "job_1765896140_ef13ym0t",
      "status": "completed",
      "progress": 100,
      "video_type": "short",
      "created_at": "2025-12-16T20:12:20",
      "completed_at": "2025-12-16T20:15:44",
      "videos_generated": 2,
      "videos_uploaded": 2
    }
  ]
}
```

---

### 4. Health Check

**Endpoint:** `GET /health`

**Description:** Check API health and database status.

**Authentication:** Not required

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-16T20:19:00.362140",
  "database": {
    "connected": true,
    "total_jobs": 15,
    "processing_jobs": 2
  },
  "version": "1.0.0"
}
```

---

### 5. API Documentation

**Endpoint:** `GET /`

**Description:** Interactive Swagger UI with all endpoints and schemas.

**Authentication:** Not required

**URL:** `http://your-server:8000/`

---

## 🔐 Authentication

All endpoints (except `/health` and `/`) require API key authentication.

**How to authenticate:**

Add the API key to your request headers:
```
X-API-Key: your-api-key-here
```

**Example with curl:**
```bash
curl -H "X-API-Key: your-api-key-here" \
  http://your-server:8000/api/jobs
```

**Example with Python requests:**
```python
import requests

headers = {
    'X-API-Key': 'your-api-key-here',
    'Content-Type': 'application/json'
}

response = requests.post(
    'http://your-server:8000/api/videos/generate',
    headers=headers,
    json={...}
)
```

**Authentication Errors:**
```json
{
  "success": false,
  "error": "Missing API key in X-API-Key header"
}
```

---

## 📝 Request Examples

### Example 1: Generate YouTube Shorts (Multiple Videos)

```bash
curl -X POST http://your-server:8000/api/videos/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{
    "market_script": "Tesla stock surged 15% today after impressive Q4 earnings.\n— pause —\nRevenue increased by 30% year-over-year, beating analyst expectations.\n— pause —\nAnalysts remain optimistic about future growth in electric vehicle market.",
    "voice": "nova",
    "speed": 1.0,
    "video_type": "short",
    "scheduled_datetime": "2025-12-20T10:00:00"
  }'
```

**Result:** 3 separate short videos scheduled to publish at:
- Video 1: 2025-12-20 10:00:00
- Video 2: 2025-12-20 12:30:00
- Video 3: 2025-12-20 15:00:00

---

### Example 2: Generate Single Regular Video

```bash
curl -X POST http://your-server:8000/api/videos/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{
    "market_script": "Comprehensive market analysis for December 2024. Major indices showed strong performance with the S&P 500 reaching new highs. Technology sector led gains while energy stocks faced headwinds from falling oil prices.",
    "voice": "onyx",
    "speed": 1.2,
    "video_type": "regular",
    "scheduled_datetime": "2025-12-20T14:00:00"
  }'
```

**Result:** 1 regular-format video (16:9) scheduled to publish at 2025-12-20 14:00:00

---

### Example 3: Python Integration

```python
import requests
from datetime import datetime, timedelta

API_URL = "http://your-server:8000"
API_KEY = "your-api-key-here"

def generate_video(script, scheduled_time):
    """Generate and schedule a video"""
    
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "market_script": script,
        "voice": "onyx",
        "speed": 1.2,
        "video_type": "short",
        "scheduled_datetime": scheduled_time.isoformat()
    }
    
    response = requests.post(
        f"{API_URL}/api/videos/generate",
        headers=headers,
        json=payload
    )
    
    return response.json()

# Schedule a video for tomorrow at 10 AM
scheduled_time = datetime.now() + timedelta(days=1, hours=10)
script = "Market update.\n— pause —\nKey insights."

result = generate_video(script, scheduled_time)
print(f"Job created: {result['job_id']}")

# Check job status
def check_status(job_id):
    response = requests.get(
        f"{API_URL}/api/jobs/{job_id}",
        headers={"X-API-Key": API_KEY}
    )
    return response.json()

status = check_status(result['job_id'])
print(f"Status: {status['status']}, Progress: {status['progress']}%")
```

---

### Example 4: JavaScript/Node.js Integration

```javascript
const axios = require('axios');

const API_URL = 'http://your-server:8000';
const API_KEY = 'your-api-key-here';

async function generateVideo(script, scheduledTime) {
    try {
        const response = await axios.post(
            `${API_URL}/api/videos/generate`,
            {
                market_script: script,
                voice: 'onyx',
                speed: 1.2,
                video_type: 'short',
                scheduled_datetime: scheduledTime
            },
            {
                headers: {
                    'X-API-Key': API_KEY,
                    'Content-Type': 'application/json'
                }
            }
        );
        
        console.log('Job created:', response.data.job_id);
        return response.data;
        
    } catch (error) {
        console.error('Error:', error.response.data);
    }
}

// Schedule a video
const scheduledTime = new Date();
scheduledTime.setHours(scheduledTime.getHours() + 2);

generateVideo(
    'Market update.\n— pause —\nKey insights.',
    scheduledTime.toISOString()
);
```

---

## 📤 Response Formats

### Success Response

```json
{
  "success": true,
  "job_id": "job_1765896140_ef13ym0t",
  "message": "Video generation started",
  "status": "queued",
  "estimated_videos": 2,
  "check_status_url": "/api/jobs/job_1765896140_ef13ym0t"
}
```

### Error Response

```json
{
  "success": false,
  "error": "Validation failed",
  "details": "scheduled_datetime cannot be more than 1 day in the past"
}
```

### Job Status Response

```json
{
  "job_id": "job_1765896140_ef13ym0t",
  "status": "completed",
  "progress": 100,
  "message": "Successfully generated 2 video(s), uploaded 2",
  "created_at": "2025-12-16T20:12:20.123456",
  "completed_at": "2025-12-16T20:15:44.789012",
  "videos_generated": 2,
  "videos_uploaded": 2,
  "error": null
}
```

---

## ⚠️ Error Handling

### Common Error Codes

| HTTP Code | Error | Description |
|-----------|-------|-------------|
| 400 | Bad Request | Invalid request body or parameters |
| 401 | Unauthorized | Missing or invalid API key |
| 404 | Not Found | Job ID not found |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server-side error |

### Error Response Examples

**1. Missing API Key**
```json
{
  "success": false,
  "error": "Missing API key in X-API-Key header"
}
```

**2. Invalid Request**
```json
{
  "success": false,
  "error": "Validation failed",
  "details": "1 validation error for VideoGenerationRequest\nvoice\n  Input should be 'alloy', 'echo', 'fable', 'onyx', 'nova' or 'shimmer'"
}
```

**3. Rate Limit Exceeded**
```json
{
  "success": false,
  "error": "Rate limit exceeded. Maximum 10 requests per minute"
}
```

**4. Job Failed**
```json
{
  "job_id": "job_123",
  "status": "failed",
  "error": "Video generation API timeout",
  "progress": 45
}
```

---

## ⚡ Rate Limits

To ensure fair usage and system stability:

- **Requests per minute:** 10 per API key
- **Concurrent jobs:** 3 active jobs per API key
- **Script length:** Maximum 50,000 characters
- **Job timeout:** 60 minutes per job

**Rate Limit Headers:**
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1734325678
```

---

## 🔄 Workflow

### Complete Video Generation Flow

```
1. Client sends POST /api/videos/generate
   ↓
2. API validates request and creates job
   ↓
3. Job stored in database with status 'queued'
   ↓
4. Background worker picks up job
   ↓
5. Videos generated via AI pipeline
   ↓
6. Videos uploaded to YouTube immediately
   ↓
7. YouTube scheduled to publish at specified time
   ↓
8. Make.com webhook called with scheduled time
   ↓
9. Job marked as 'completed'
   ↓
10. Twitter posts published at scheduled times
```

### Timing Example

**Request:** Schedule video for 2025-12-20 10:00:00 with 3 shorts

**What happens:**
1. **Immediately:** Videos generate (takes ~30 seconds)
2. **Immediately:** Videos upload to YouTube as PRIVATE
3. **Immediately:** YouTube scheduled to go public at specific times
4. **Immediately:** Make.com webhook receives scheduling data
5. **2025-12-20 10:00:** First short becomes public on YouTube
6. **2025-12-20 10:00:** First tweet posted via Make.com
7. **2025-12-20 12:30:** Second short becomes public (2.5 hour interval)
8. **2025-12-20 12:30:** Second tweet posted
9. **2025-12-20 15:00:** Third short becomes public
10. **2025-12-20 15:00:** Third tweet posted

**Interval between videos:** 2.5 hours (configurable)

---

## 📌 Best Practices

### 1. Script Formatting

**For YouTube Shorts (multiple videos):**
```
First video content here.
— pause —
Second video content here.
— pause —
Third video content here.
```

**For Regular Videos (single video):**
```
Full video content without pause separators.
Can be as long as needed.
```

### 2. Scheduling

- ✅ **Do:** Schedule at least 1 hour in the future
- ✅ **Do:** Use ISO 8601 format: `2025-12-20T10:00:00`
- ❌ **Don't:** Schedule more than 1 day in the past
- ❌ **Don't:** Schedule too many videos at once (respect rate limits)

### 3. Voice Selection

| Voice | Characteristics | Best For |
|-------|----------------|----------|
| `alloy` | Neutral, balanced | General content |
| `echo` | Male, clear | Professional content |
| `fable` | British, expressive | Storytelling |
| `onyx` | Male, deep | News, market updates |
| `nova` | Female, energetic | Shorts, quick updates |
| `shimmer` | Female, soft | Calm content |

### 4. Speed Settings

- `0.5-0.8`: Slower, educational content
- `1.0-1.2`: Normal, conversational (recommended)
- `1.3-1.5`: Faster, dynamic shorts
- `1.6-2.0`: Very fast, highlights only

### 5. Error Handling in Your Application

```python
import requests
import time

def generate_with_retry(script, scheduled_time, max_retries=3):
    """Generate video with automatic retry on failure"""
    
    for attempt in range(max_retries):
        try:
            response = requests.post(
                f"{API_URL}/api/videos/generate",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 429:
                # Rate limit - wait and retry
                time.sleep(60)
                continue
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(5)
    
    return None
```

### 6. Monitoring Jobs

Poll job status until completion:

```python
def wait_for_completion(job_id, timeout=600):
    """Wait for job to complete with timeout"""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        status = check_status(job_id)
        
        if status['status'] == 'completed':
            return True
        elif status['status'] == 'failed':
            raise Exception(f"Job failed: {status['error']}")
        
        time.sleep(10)  # Check every 10 seconds
    
    raise TimeoutError(f"Job {job_id} did not complete in {timeout} seconds")
```

---

## 🎯 Use Cases

### 1. Automated Market Updates
Schedule daily market analysis videos at specific times

### 2. Social Media Content Calendar
Bulk generate and schedule a week's worth of content

### 3. Event Coverage
Generate recap videos immediately after events with future publish times

### 4. Multi-Platform Distribution
Automatically post to YouTube and Twitter simultaneously

### 5. A/B Testing
Generate multiple versions with different voices/speeds

---

## 🔧 Integration Tips

### Webhook Integration (Make.com)

The API automatically sends data to Make.com webhooks with this structure:

```json
{
  "video_url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "scheduled_time": "2025-12-20T10:00:00",
  "full_content": "Video title"
}
```

**Make.com Scenario Setup:**
1. Create a webhook trigger
2. Parse incoming JSON
3. Schedule Twitter post using `scheduled_time`
4. Use `video_url` and `full_content` in tweet

### Database Integration

Store job IDs in your database for tracking:

```sql
CREATE TABLE video_generations (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(50) NOT NULL,
    script TEXT NOT NULL,
    scheduled_time TIMESTAMP NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Monitoring Dashboard

Build a status dashboard by polling `/api/jobs`:

```javascript
async function updateDashboard() {
    const response = await fetch('/api/jobs?status=processing', {
        headers: {'X-API-Key': API_KEY}
    });
    
    const data = await response.json();
    
    data.jobs.forEach(job => {
        updateJobCard(job.job_id, job.progress, job.message);
    });
}

setInterval(updateDashboard, 5000); // Update every 5 seconds
```

---

## 📞 Support

### Health Check
```bash
curl http://your-server:8000/health
```

### API Documentation
Open in browser: `http://your-server:8000/`

### Contact
For API access and support, contact your administrator.

---

## 🔒 Security Notes

- 🔐 Keep API keys secret - never commit to version control
- 🔄 Rotate API keys regularly
- 🚫 Don't share API keys between applications
- 📝 Log all API usage for auditing
- 🛡️ Use HTTPS in production environments

---

## 📊 API Status

- **Version:** 1.0.0
- **Status:** Production Ready
- **Uptime SLA:** 99.9%
- **Support:** Business hours (9 AM - 6 PM EST)

---

**Last Updated:** December 2024

**API Version:** 1.0.0
