#!/usr/bin/env python3
"""
Simplified YouTube API Credential Setup

This script helps you set up YouTube API credentials by manually entering them
or by using the OAuth flow if you have client_secrets.json.
"""

import os
import json
from dotenv import load_dotenv

def manual_credential_setup():
    """Manually enter YouTube API credentials"""
    print("Manual YouTube API Credential Setup")
    print("=" * 50)
    print()
    print("First, you need to create YouTube API credentials:")
    print("1. Go to https://console.cloud.google.com")
    print("2. Create a new project or select existing one")
    print("3. Enable YouTube Data API v3")
    print("4. Go to 'Credentials' → 'Create Credentials' → 'OAuth 2.0 Client IDs'")
    print("5. Choose 'Desktop application'")
    print("6. Copy the Client ID and Client Secret")
    print()
    
    client_id = input("Enter your YouTube Client ID: ").strip()
    if not client_id:
        print("❌ Client ID is required!")
        return False
    
    client_secret = input("Enter your YouTube Client Secret: ").strip()
    if not client_secret:
        print("❌ Client Secret is required!")
        return False
    
    print()
    print("⚠️  For the Refresh Token, you'll need to complete the OAuth flow.")
    print("   You can:")
    print("   A) Download the OAuth JSON file and use youtube_auth_helper.py")
    print("   B) Or enter a refresh token if you already have one")
    print()
    
    choice = input("Do you have a refresh token already? (y/n): ").strip().lower()
    
    if choice == 'y':
        refresh_token = input("Enter your Refresh Token: ").strip()
        if not refresh_token:
            print("❌ Refresh Token is required!")
            return False
    else:
        print()
        print("📋 To get your refresh token:")
        print("1. Download the OAuth 2.0 Client JSON file from Google Cloud Console")
        print("2. Rename it to 'client_secrets.json' and place it in this directory")
        print("3. Run: python youtube_auth_helper.py")
        print()
        refresh_token = input("Enter refresh token (or press Enter to skip for now): ").strip()
    
    # Update .env file
    update_env_file(client_id, client_secret, refresh_token)
    
    return True

def update_env_file(client_id, client_secret, refresh_token):
    """Update the .env file with credentials"""
    
    # Read current .env file
    env_content = []
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            env_content = f.readlines()
    
    # Update or add credentials
    credentials = {
        'YOUTUBE_CLIENT_ID': client_id,
        'YOUTUBE_CLIENT_SECRET': client_secret,
        'YOUTUBE_REFRESH_TOKEN': refresh_token
    }
    
    updated_content = []
    updated_keys = set()
    
    for line in env_content:
        line = line.strip()
        if '=' in line:
            key = line.split('=')[0].strip()
            if key in credentials:
                updated_content.append(f"{key}={credentials[key]}\n")
                updated_keys.add(key)
            else:
                updated_content.append(line + '\n')
        else:
            updated_content.append(line + '\n')
    
    # Add any missing credentials
    for key, value in credentials.items():
        if key not in updated_keys and value:
            updated_content.append(f"{key}={value}\n")
    
    # Write back to .env file
    with open('.env', 'w') as f:
        f.writelines(updated_content)
    
    print()
    print("✅ Updated .env file with your credentials!")
    print()
    
    if refresh_token:
        print("🎉 Setup complete! You can now run:")
        print("   python automation_scheduler.py")
    else:
        print("⚠️  Setup incomplete - missing refresh token.")
        print("   Complete the OAuth flow and then run the automation.")
    
    print()
    print("📝 Your .env file now contains:")
    for key, value in credentials.items():
        if value:
            display_value = value[:10] + "..." if len(value) > 10 else value
            print(f"   {key}={display_value}")
        else:
            print(f"   {key}=<not set>")

def check_current_setup():
    """Check what credentials are already configured"""
    load_dotenv()
    
    client_id = os.getenv('YOUTUBE_CLIENT_ID')
    client_secret = os.getenv('YOUTUBE_CLIENT_SECRET')
    refresh_token = os.getenv('YOUTUBE_REFRESH_TOKEN')
    
    print("Current YouTube API Setup:")
    print("=" * 30)
    print(f"Client ID: {'✅ Set' if client_id else '❌ Not set'}")
    print(f"Client Secret: {'✅ Set' if client_secret else '❌ Not set'}")
    print(f"Refresh Token: {'✅ Set' if refresh_token else '❌ Not set'}")
    print()
    
    if client_id and client_secret and refresh_token:
        print("🎉 All credentials are configured!")
        return True
    else:
        print("⚠️  Some credentials are missing.")
        return False

def main():
    print("🔐 YouTube API Credential Setup")
    print("=" * 40)
    print()
    
    # Check current setup
    if check_current_setup():
        choice = input("Credentials are already set. Do you want to update them? (y/n): ").strip().lower()
        if choice != 'y':
            print("✅ Using existing credentials.")
            return
    
    print()
    print("Setup Options:")
    print("1. Manual credential entry")
    print("2. Check if client_secrets.json exists for OAuth flow")
    print("3. Show Google Cloud Console setup instructions")
    print("4. Exit")
    
    while True:
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == '1':
            manual_credential_setup()
            break
        elif choice == '2':
            if os.path.exists('client_secrets.json'):
                print("✅ client_secrets.json found!")
                print("Run: python youtube_auth_helper.py")
            else:
                print("❌ client_secrets.json not found.")
                print("Download it from Google Cloud Console first.")
            break
        elif choice == '3':
            show_google_cloud_instructions()
        elif choice == '4':
            print("👋 Goodbye!")
            break
        else:
            print("Invalid choice. Please enter 1-4.")

def show_google_cloud_instructions():
    """Show detailed Google Cloud Console setup instructions"""
    print()
    print("📋 Google Cloud Console Setup Instructions")
    print("=" * 50)
    print()
    print("1. Go to https://console.cloud.google.com")
    print("2. Create a new project:")
    print("   - Click 'Select a project' → 'New Project'")
    print("   - Enter project name (e.g., 'YouTube Shorts Automation')")
    print("   - Click 'Create'")
    print()
    print("3. Enable YouTube Data API v3:")
    print("   - Go to 'APIs & Services' → 'Library'")
    print("   - Search for 'YouTube Data API v3'")
    print("   - Click on it and press 'Enable'")
    print()
    print("4. Create OAuth 2.0 Credentials:")
    print("   - Go to 'APIs & Services' → 'Credentials'")
    print("   - Click '+ Create Credentials' → 'OAuth 2.0 Client IDs'")
    print("   - If prompted, configure OAuth consent screen first:")
    print("     * Choose 'External' user type")
    print("     * Fill in app name, user support email, developer email")
    print("     * Add your email to test users")
    print("   - For Application type, choose 'Desktop application'")
    print("   - Enter name (e.g., 'YouTube Shorts Uploader')")
    print("   - Click 'Create'")
    print()
    print("5. Download Credentials:")
    print("   - Click 'Download JSON' for your new OAuth client")
    print("   - Rename the file to 'client_secrets.json'")
    print("   - Place it in this project directory")
    print()
    print("6. Run OAuth Flow:")
    print("   - python youtube_auth_helper.py")
    print("   - Follow browser prompts to authorize")
    print()

if __name__ == "__main__":
    main()