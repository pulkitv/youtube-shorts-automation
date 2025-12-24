"""
Simple script to test the API with a real call
"""
import requests
import json
from datetime import datetime, timedelta

# API Configuration
API_URL = "http://localhost:8000"  # Changed from 5000 to 8000
API_KEY = "demo-api-key-replace-with-secure-key"  # Update this with your actual API key

def test_health_check():
    """Test the health check endpoint"""
    print("🔍 Testing health check...")
    # Try different possible paths based on common flask-restx patterns
    paths = [
        "/health",
        "/api/health", 
        "/health/",
    ]
    
    for path in paths:
        try:
            response = requests.get(f"{API_URL}{path}")
            print(f"Trying {path}: Status {response.status_code}")
            if response.status_code == 200:
                print(f"✅ Found health endpoint at: {path}")
                print(f"Response: {json.dumps(response.json(), indent=2)}")
                print()
                return path
        except Exception as e:
            print(f"  Error: {e}")
            continue
    
    print("❌ Could not find health endpoint")
    print()
    return None

def test_video_generation():
    """Test video generation endpoint"""
    print("🎬 Testing video generation...")
    
    # Schedule video for 2 hours from now
    scheduled_time = (datetime.now() + timedelta(hours=2)).isoformat()
    
    payload = {
        "market_script": """Tesla stock surged today after strong earnings report.
— pause —
Revenue increased by 30% year-over-year.
— pause —
Analysts are optimistic about future growth.""",
        "voice": "onyx",
        "speed": 1.2,
        "video_type": "short",
        "scheduled_datetime": scheduled_time
    }
    
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    
    # Try different endpoint paths
    endpoints = [
        "/api/videos/generate",
        "/videos/generate",
        "/generate",
    ]
    
    for endpoint in endpoints:
        print(f"Trying endpoint: {endpoint}")
        response = requests.post(
            f"{API_URL}{endpoint}",
            json=payload,
            headers=headers
        )
        
        print(f"  Status: {response.status_code}")
        
        if response.status_code in [200, 201]:
            try:
                resp_json = response.json()
                print(f"  Response: {json.dumps(resp_json, indent=2)}")
                job_id = resp_json.get('job_id')
                print(f"\n✅ Job created successfully: {job_id}")
                return job_id
            except Exception as e:
                print(f"  Error parsing response: {e}")
        elif response.status_code != 404:
            # Not a 404, so we found the endpoint but there's another issue
            print(f"  Response text: {response.text}")
    
    print(f"\n❌ Failed to create job - endpoint not found")
    return None

def test_job_status(job_id):
    """Test job status endpoint"""
    if not job_id:
        return
    
    print(f"\n🔍 Checking job status for: {job_id}")
    
    headers = {
        "X-API-Key": API_KEY
    }
    
    endpoints = [
        f"/api/jobs/{job_id}",
        f"/jobs/{job_id}",
    ]
    
    for endpoint in endpoints:
        response = requests.get(f"{API_URL}{endpoint}", headers=headers)
        print(f"Trying {endpoint}: Status {response.status_code}")
        
        if response.status_code == 200:
            try:
                print(f"Response: {json.dumps(response.json(), indent=2)}")
                return
            except:
                print(f"Response text: {response.text}")
                return

def test_list_jobs():
    """Test list jobs endpoint"""
    print("\n📋 Listing all jobs...")
    
    headers = {
        "X-API-Key": API_KEY
    }
    
    endpoints = [
        "/api/jobs",
        "/jobs",
    ]
    
    for endpoint in endpoints:
        response = requests.get(f"{API_URL}{endpoint}", headers=headers)
        print(f"Trying {endpoint}: Status {response.status_code}")
        
        if response.status_code == 200:
            try:
                print(f"Response: {json.dumps(response.json(), indent=2)}")
                return
            except:
                print(f"Response text: {response.text}")
                return

def test_api_docs():
    """Test if Swagger docs are available"""
    print("📚 Checking API documentation...")
    response = requests.get(f"{API_URL}/")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print("✅ Swagger UI available at: http://localhost:8000/")
        print("   Open this URL in your browser to see all available endpoints")
    print()

if __name__ == "__main__":
    print("=" * 60)
    print("YouTube Shorts API Test")
    print("=" * 60)
    print()
    
    try:
        # Test API docs
        test_api_docs()
        
        # Test health check
        test_health_check()
        
        # Test video generation
        job_id = test_video_generation()
        
        # Test job status
        if job_id:
            test_job_status(job_id)
        
        # Test list jobs
        test_list_jobs()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("=" * 60)
        print("\n💡 Tip: Open http://localhost:8000/ in your browser")
        print("   to see the interactive API documentation (Swagger UI)")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to API server")
        print("Make sure the API server is running on http://localhost:8000")
        print("\nTo start the server, run:")
        print("  cd api_mode")
        print("  python api_server.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()