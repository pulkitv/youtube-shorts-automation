#!/usr/bin/env python3
"""
Test the scheduling calculation logic
"""

from datetime import datetime, timedelta

def test_scheduling_logic():
    print("🕐 Testing Video Scheduling Logic")
    print("=" * 40)
    
    # Simulate current time
    current_time = datetime(2025, 9, 13, 17, 13)  # 5:13 PM IST
    print(f"Current time (IST): {current_time.strftime('%Y-%m-%d %H:%M')} ({current_time.strftime('%I:%M %p')})")
    
    # Calculate first video schedule (2.5 hours from now)
    interval_hours = 2.5
    first_video_time = current_time + timedelta(hours=interval_hours * 1)
    second_video_time = current_time + timedelta(hours=interval_hours * 2)
    
    print(f"\nScheduled times:")
    print(f"First video:  {first_video_time.strftime('%Y-%m-%d %H:%M')} ({first_video_time.strftime('%I:%M %p')} IST)")
    print(f"Second video: {second_video_time.strftime('%Y-%m-%d %H:%M')} ({second_video_time.strftime('%I:%M %p')} IST)")
    
    print(f"\nTime differences from now:")
    print(f"First video:  {(first_video_time - current_time).total_seconds() / 3600} hours")
    print(f"Second video: {(second_video_time - current_time).total_seconds() / 3600} hours")
    
    print(f"\nExpected results:")
    print(f"✅ First video should be scheduled for: 7:43 PM IST today")
    print(f"✅ Second video should be scheduled for: 10:13 PM IST today")

if __name__ == "__main__":
    test_scheduling_logic()