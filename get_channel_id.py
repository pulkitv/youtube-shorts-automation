#!/usr/bin/env python3
"""
Get YouTube Channel ID for your authenticated account
"""

import os
from dotenv import load_dotenv
from youtube_uploader import YouTubeUploader

def get_channel_id():
    load_dotenv()
    
    uploader = YouTubeUploader(
        client_id=os.getenv('YOUTUBE_CLIENT_ID'),
        client_secret=os.getenv('YOUTUBE_CLIENT_SECRET'),
        refresh_token=os.getenv('YOUTUBE_REFRESH_TOKEN')
    )
    
    channel_info = uploader.get_channel_info()
    if channel_info:
        channel_id = channel_info['id']
        channel_title = channel_info['snippet']['title']
        
        print(f"✅ YouTube Channel Information:")
        print(f"   Channel Name: {channel_title}")
        print(f"   Channel ID: {channel_id}")
        print()
        print(f"📝 Add this to your .env file:")
        print(f"CHANNEL_ID={channel_id}")
        
        return channel_id
    else:
        print("❌ Failed to get channel information")
        return None

if __name__ == "__main__":
    get_channel_id()