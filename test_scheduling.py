#!/usr/bin/env python3
"""
Test script to verify the scheduling system is working properly
"""

import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

def reset_upload_queue():
    """Reset the upload queue to test new scheduling system"""
    load_dotenv()
    
    print("🔄 Resetting upload queue for testing...")
    
    # Backup existing queue
    if os.path.exists('upload_queue.json'):
        backup_name = f"upload_queue_backup_{int(datetime.now().timestamp())}.json"
        os.rename('upload_queue.json', backup_name)
        print(f"📋 Backed up existing queue to: {backup_name}")
    
    # Create empty queue
    with open('upload_queue.json', 'w') as f:
        json.dump([], f, indent=2)
    
    print("✅ Upload queue reset. Ready for testing scheduled publishing.")
    print("\nNext steps:")
    print("1. Run: python automation_scheduler.py")
    print("2. Choose option 2: Manual video generation")
    print("3. Enter a test script")
    print("4. Check that videos are uploaded as 'scheduled' instead of 'uploaded'")
    print("5. Use option 4 to check status and see scheduled publication times")

def show_current_queue_status():
    """Show current queue status with detailed scheduling info"""
    if not os.path.exists('upload_queue.json'):
        print("❌ No upload queue found")
        return
    
    with open('upload_queue.json', 'r') as f:
        queue = json.load(f)
    
    if not queue:
        print("📭 Upload queue is empty")
        return
    
    print("📊 Current Upload Queue Status:")
    print("=" * 50)
    
    status_counts = {}
    for video in queue:
        status = video.get('status', 'unknown')
        status_counts[status] = status_counts.get(status, 0) + 1
    
    for status, count in status_counts.items():
        print(f"  {status.title()}: {count} videos")
    
    print("\n📅 Scheduled Videos:")
    scheduled_videos = [v for v in queue if v.get('status') == 'scheduled']
    
    if scheduled_videos:
        for video in scheduled_videos:
            scheduled_time = video.get('scheduled_publish_time')
            if scheduled_time:
                print(f"  • {video.get('title', 'Unknown')} → {scheduled_time}")
    else:
        print("  No videos currently scheduled")
    
    print(f"\n📈 Total videos: {len(queue)}")

def main():
    print("🧪 YouTube Shorts Scheduling Test Tool")
    print("=" * 40)
    
    print("\nChoose an option:")
    print("1. Show current queue status")
    print("2. Reset upload queue (for testing)")
    print("3. Exit")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == '1':
        show_current_queue_status()
    elif choice == '2':
        confirm = input("⚠️  This will backup and reset your upload queue. Continue? (y/N): ")
        if confirm.lower() == 'y':
            reset_upload_queue()
        else:
            print("❌ Cancelled")
    elif choice == '3':
        print("👋 Goodbye!")
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    main()