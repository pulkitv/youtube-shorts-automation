#!/usr/bin/env python3
"""
Test script to diagnose PDF API issues and test the YouTube Shorts automation
"""

import requests
import json
import time
from dotenv import load_dotenv
import os

def test_pdf_api_direct():
    """Test the PDF API directly to diagnose issues"""
    print("🔍 Testing PDF Processing API...")
    
    # Test basic connectivity
    try:
        response = requests.get("http://localhost:5000", timeout=5)
        print(f"✅ API is reachable (Status: {response.status_code})")
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot reach API: {e}")
        return False
    
    # Test the shorts generation endpoint
    test_script = "Test news update today. — pause — Market shows positive trends. — pause — Economic outlook remains stable."
    
    payload = {
        "script": test_script,
        "voice": "nova",
        "speed": 1.0
    }
    
    try:
        print("📤 Sending test request to /api/v1/generate-shorts...")
        response = requests.post(
            "http://localhost:5000/api/v1/generate-shorts",
            json=payload,
            timeout=30
        )
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 202:
            data = response.json()
            print(f"✅ Request accepted! Session ID: {data.get('session_id')}")
            
            # Test status endpoint
            session_id = data.get('session_id')
            if session_id:
                print(f"🔄 Testing status endpoint...")
                status_response = requests.get(f"http://localhost:5000/api/v1/shorts-status/{session_id}")
                print(f"Status Response: {status_response.status_code}")
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    print(f"Status Data: {json.dumps(status_data, indent=2)}")
                else:
                    print(f"Status Error: {status_response.text}")
            
            return True
        else:
            print(f"❌ Request failed: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def test_with_curl():
    """Generate curl commands for manual testing"""
    print("\n🛠️  Manual Testing Commands:")
    print("=" * 40)
    
    curl_cmd = '''curl -X POST http://localhost:5000/api/v1/generate-shorts \\
  -H "Content-Type: application/json" \\
  -d '{
    "script": "Test market update. — pause — Stocks are performing well. — pause — Economic indicators positive.",
    "voice": "nova",
    "speed": 1.0
  }'
'''
    
    print("Test with curl:")
    print(curl_cmd)
    
    print("\nCheck status with curl (replace SESSION_ID):")
    print("curl http://localhost:5000/api/v1/shorts-status/SESSION_ID")

def check_api_endpoints():
    """Check what endpoints are available on the API"""
    print("\n🔍 Checking Available API Endpoints...")
    
    endpoints_to_test = [
        "/",
        "/api/v1/generate-shorts",
        "/health",
        "/status"
    ]
    
    for endpoint in endpoints_to_test:
        try:
            response = requests.get(f"http://localhost:5000{endpoint}", timeout=5)
            print(f"✅ {endpoint}: {response.status_code}")
        except:
            print(f"❌ {endpoint}: Not reachable")

def suggest_api_fixes():
    """Suggest fixes for the Flask context issue"""
    print("\n🔧 Suggested Fixes for Your PDF Processing API:")
    print("=" * 50)
    print()
    print("The 'Working outside of request context' error suggests your Flask app")
    print("is trying to access request-specific data in a background task.")
    print()
    print("Potential fixes:")
    print("1. Use Flask's app.app_context() for background tasks:")
    print("   ```python")
    print("   with app.app_context():")
    print("       # Your video generation code here")
    print("   ```")
    print()
    print("2. Or use Flask's test_request_context():")
    print("   ```python") 
    print("   with app.test_request_context():")
    print("       # Your video generation code here")
    print("   ```")
    print()
    print("3. Make sure session handling doesn't rely on Flask's session object")
    print("   in background tasks")
    print()
    print("4. Consider using Celery or similar for background processing")

def main():
    print("🧪 YouTube Shorts API Test Suite")
    print("=" * 40)
    
    # Test API connectivity and endpoints
    check_api_endpoints()
    
    # Test the shorts generation endpoint
    api_working = test_pdf_api_direct()
    
    if not api_working:
        print("\n❌ API tests failed!")
        suggest_api_fixes()
        test_with_curl()
    else:
        print("\n✅ API tests passed! The automation should work.")
    
    print("\n📋 Next Steps:")
    print("1. If API tests failed, fix the Flask context issue in your PDF processing API")
    print("2. If API tests passed, try the YouTube Shorts automation again")
    print("3. Use the manual curl commands above to test your API directly")

if __name__ == "__main__":
    main()