#!/usr/bin/env python3
"""
Test timezone conversion for YouTube scheduling
"""

from datetime import datetime
import pytz

def test_timezone_conversion():
    print("🕐 Testing Timezone Conversion for YouTube Scheduling")
    print("=" * 55)
    
    # Simulate the current issue
    local_time = datetime(2025, 9, 13, 19, 43, 24)  # 7:43 PM IST
    
    print(f"Original scheduled time (IST): {local_time}")
    
    # Convert using our new logic
    local_tz = pytz.timezone('Asia/Kolkata')  # IST timezone
    utc_tz = pytz.UTC
    
    # Localize to IST first
    local_time_ist = local_tz.localize(local_time)
    print(f"Localized to IST: {local_time_ist}")
    
    # Convert to UTC
    utc_time = local_time_ist.astimezone(utc_tz)
    print(f"Converted to UTC: {utc_time}")
    
    # Format for YouTube API
    youtube_format = utc_time.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    print(f"YouTube API format: {youtube_format}")
    
    print("\n📊 Results:")
    print(f"IST Time: {local_time.strftime('%I:%M %p on %B %d, %Y')}")
    print(f"UTC Time: {utc_time.strftime('%I:%M %p on %B %d, %Y')}")
    print(f"Time difference: {(utc_time - local_time_ist).total_seconds() / 3600} hours")
    
    # Show what YouTube should display
    print(f"\n✅ YouTube should show: {utc_time.strftime('%B %d, %Y at %I:%M %p')} UTC")
    print(f"   Which converts back to: {local_time.strftime('%I:%M %p on %B %d, %Y')} IST")

if __name__ == "__main__":
    test_timezone_conversion()