#!/bin/bash

# YouTube Shorts Automation Setup Script

echo "🚀 Setting up YouTube Shorts Automation..."

# Create virtual environment
echo "📦 Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install dependencies
echo "📥 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p downloads
mkdir -p processed
mkdir -p logs

# Copy environment template
echo "⚙️ Setting up environment configuration..."
cp .env.template .env

echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Edit .env file with your API credentials:"
echo "   - YouTube API credentials (client_id, client_secret, refresh_token)"
echo "   - PDF API base URL (if different from localhost:5000)"
echo "   - Channel configuration"
echo ""
echo "2. To get YouTube API credentials:"
echo "   - Go to Google Cloud Console (console.cloud.google.com)"
echo "   - Create a new project or select existing one"
echo "   - Enable YouTube Data API v3"
echo "   - Create OAuth 2.0 credentials"
echo "   - Use youtube_auth_helper.py to get refresh token"
echo ""
echo "3. Start the automation:"
echo "   source venv/bin/activate"
echo "   python automation_scheduler.py"
echo ""
echo "🎬 Ready to automate your YouTube Shorts!"