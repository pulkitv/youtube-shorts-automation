#!/usr/bin/env python3
"""
YouTube API Authentication Helper

This script helps you obtain the refresh token needed for YouTube API authentication.
Run this script once to get your refresh token, then add it to your .env file.
"""

import os
from google_auth_oauthlib.flow import InstalledAppFlow
import json

# YouTube API scopes
SCOPES = ['https://www.googleapis.com/auth/youtube.upload', 
          'https://www.googleapis.com/auth/youtube']

def get_youtube_credentials():
    """
    Get YouTube API credentials and refresh token
    """
    print("YouTube API Authentication Helper")
    print("="*40)
    print()
    
    # Check if client_secrets.json exists
    if not os.path.exists('client_secrets.json'):
        print("❌ client_secrets.json not found!")
        print()
        print("Please follow these steps:")
        print("1. Go to https://console.cloud.google.com")
        print("2. Create a new project or select existing one")
        print("3. Enable YouTube Data API v3")
        print("4. Go to 'Credentials' → 'Create Credentials' → 'OAuth 2.0 Client IDs'")
        print("5. Choose 'Desktop application'")
        print("6. Download the JSON file and rename it to 'client_secrets.json'")
        print("7. Place it in the same directory as this script")
        return None
    
    try:
        # Run OAuth flow
        flow = InstalledAppFlow.from_client_secrets_file(
            'client_secrets.json', SCOPES)
        
        print("🔐 Starting OAuth flow...")
        print("Your browser will open automatically.")
        print("Please authorize the application and grant permissions.")
        
        credentials = flow.run_local_server(port=8080)
        
        print()
        print("✅ Authentication successful!")
        print()
        print("Your credentials:")
        print(f"Client ID: {credentials.client_id}")
        print(f"Client Secret: {credentials.client_secret}")
        print(f"Refresh Token: {credentials.refresh_token}")
        print()
        
        # Save to a file for easy copying
        creds_data = {
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'refresh_token': credentials.refresh_token
        }
        
        with open('youtube_credentials.json', 'w') as f:
            json.dump(creds_data, f, indent=2)
        
        print("💾 Credentials saved to 'youtube_credentials.json'")
        print()
        print("📝 Add these to your .env file:")
        print(f"YOUTUBE_CLIENT_ID={credentials.client_id}")
        print(f"YOUTUBE_CLIENT_SECRET={credentials.client_secret}")
        print(f"YOUTUBE_REFRESH_TOKEN={credentials.refresh_token}")
        
        return creds_data
        
    except Exception as e:
        print(f"❌ Error during authentication: {e}")
        return None

if __name__ == "__main__":
    get_youtube_credentials()