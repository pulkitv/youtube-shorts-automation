#!/usr/bin/env python3
"""
Diagnostic script to find the correct download URL pattern for your PDF processing API
"""

import requests
import json
from datetime import datetime

def check_api_endpoints(session_id):
    """Check various endpoint patterns to find where the ZIP file might be"""
    
    base_url = "http://localhost:5000"
    
    # Comprehensive list of possible download URL patterns
    url_patterns = [
        # Common Flask patterns
        f"/download-voiceover/{session_id}.zip",
        f"/download-voiceover/api_shorts_{session_id.replace('api_', '')}.zip",
        f"/download-voiceover/shorts_{session_id}.zip",
        f"/download-voiceover/api_shorts_{session_id}.zip",
        
        # Alternative patterns
        f"/api/v1/download/{session_id}",
        f"/api/v1/download/{session_id}.zip",
        f"/download/{session_id}.zip",
        f"/downloads/{session_id}.zip",
        f"/voiceovers/{session_id}.zip",
        f"/static/voiceovers/{session_id}.zip",
        f"/files/{session_id}.zip",
        f"/generated/{session_id}.zip",
        
        # With different naming conventions
        f"/download-voiceover/{session_id}_shorts.zip",
        f"/download-voiceover/output_{session_id}.zip",
        f"/download-voiceover/result_{session_id}.zip",
        
        # Direct file access patterns
        f"/{session_id}.zip",
        f"/shorts_{session_id}.zip",
        f"/output_{session_id}.zip"
    ]
    
    print(f"🔍 Testing download URLs for session: {session_id}")
    print("=" * 60)
    
    found_urls = []
    
    for pattern in url_patterns:
        url = base_url + pattern
        try:
            # Try HEAD request first
            response = requests.head(url, timeout=3)
            status = response.status_code
            content_type = response.headers.get('content-type', 'unknown')
            content_length = response.headers.get('content-length', 'unknown')
            
            if status == 200:
                print(f"✅ FOUND: {url}")
                print(f"   Content-Type: {content_type}")
                print(f"   Content-Length: {content_length}")
                found_urls.append(url)
            elif status == 404:
                print(f"❌ Not found: {pattern}")
            else:
                print(f"⚠️  Status {status}: {pattern}")
                
        except requests.exceptions.RequestException as e:
            print(f"🔗 Connection error: {pattern} ({str(e)[:50]}...)")
    
    if not found_urls:
        print("\n🔄 HEAD requests failed, trying GET requests...")
        
        # Try GET requests for most likely patterns
        priority_patterns = url_patterns[:8]  # First 8 patterns
        
        for pattern in priority_patterns:
            url = base_url + pattern
            try:
                response = requests.get(url, timeout=3, stream=True)
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '')
                    if 'zip' in content_type or 'application/octet-stream' in content_type:
                        print(f"✅ FOUND (GET): {url}")
                        print(f"   Content-Type: {content_type}")
                        found_urls.append(url)
                        break
            except:
                continue
    
    return found_urls

def check_api_directory_listing():
    """Check if the API has any directory listing or file listing endpoints"""
    
    base_url = "http://localhost:5000"
    endpoints_to_check = [
        "/",
        "/files",
        "/downloads", 
        "/voiceovers",
        "/download-voiceover",
        "/static",
        "/api/v1/files",
        "/api/v1/status"
    ]
    
    print("\n🗂️  Checking for directory listings...")
    print("=" * 40)
    
    for endpoint in endpoints_to_check:
        try:
            response = requests.get(base_url + endpoint, timeout=3)
            if response.status_code == 200:
                content = response.text
                if 'zip' in content.lower() or 'api_' in content:
                    print(f"📁 Found potential files at {endpoint}:")
                    # Extract potential filenames
                    lines = content.split('\n')
                    for line in lines:
                        if 'api_' in line and '.zip' in line:
                            print(f"   📄 {line.strip()[:100]}")
        except:
            continue

def suggest_manual_check(session_id):
    """Suggest manual checks the user can do"""
    
    print(f"\n🛠️  Manual Investigation Suggestions")
    print("=" * 40)
    print(f"Session ID: {session_id}")
    print()
    print("1. Check your PDF processing API logs for:")
    print("   - Where the ZIP file is actually saved")
    print("   - What the download endpoint returns")
    print()
    print("2. Try these manual curl commands:")
    print(f"   curl -I http://localhost:5000/download-voiceover/{session_id}.zip")
    print(f"   curl -I http://localhost:5000/api/v1/download/{session_id}")
    print()
    print("3. Check your Flask app routes:")
    print("   - Look for @app.route decorators with 'download' in the path")
    print("   - Check what the actual download endpoint is called")
    print()
    print("4. Check the file system:")
    print("   - Look in your Flask app's static/voiceovers folder")
    print("   - Search for files containing the session ID")
    print()
    print("5. Test the status endpoint response:")
    print(f"   curl http://localhost:5000/api/v1/shorts-status/{session_id}")

def main():
    print("🔍 PDF API Download URL Diagnostics")
    print("=" * 40)
    print()
    
    # Use the session ID from your logs
    session_id = "api_6700dfb3-38d9-456e-b4c2-61d6d3027427"
    
    # Check various URL patterns
    found_urls = check_api_endpoints(session_id)
    
    # Check for directory listings
    check_api_directory_listing()
    
    # Show results
    print(f"\n📊 Results Summary")
    print("=" * 20)
    
    if found_urls:
        print(f"✅ Found {len(found_urls)} working download URLs:")
        for url in found_urls:
            print(f"   {url}")
        print()
        print("🔧 Add this pattern to pdf_api_client.py:")
        # Extract the pattern from the first working URL
        pattern = found_urls[0].replace("http://localhost:5000", "").replace(session_id, "{session_id}")
        print(f'   f"{{self.base_url}}{pattern}"')
    else:
        print("❌ No working download URLs found")
        suggest_manual_check(session_id)

if __name__ == "__main__":
    main()