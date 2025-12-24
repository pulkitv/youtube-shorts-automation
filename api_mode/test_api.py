"""
Comprehensive test suite for YouTube Shorts Automation API
Run with: pytest test_api.py -v
"""

import pytest
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api_server import app, db
from api_models import validate_video_generation_request
from api_database import JobDatabase

@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def valid_api_key():
    """Return a valid API key from config"""
    return "demo-api-key-replace-with-secure-key"

@pytest.fixture
def sample_script():
    """Return a sample market script"""
    return """Company ABC reported strong quarterly results.
— pause —
Revenue increased by 25% year-over-year.
— pause —
The stock price surged 10% in after-hours trading."""

@pytest.fixture
def valid_video_request(sample_script):
    """Return a valid video generation request"""
    scheduled_time = (datetime.now() + timedelta(hours=2)).isoformat()
    return {
        'market_script': sample_script,
        'voice': 'onyx',
        'speed': 1.2,
        'video_type': 'short',
        'scheduled_datetime': scheduled_time
    }

@pytest.fixture
def valid_regular_video_request():
    """Return a valid regular video generation request"""
    scheduled_time = (datetime.now() + timedelta(hours=2)).isoformat()
    return {
        'market_script': 'This is a longer market analysis script without pause markers.',
        'voice': 'nova',
        'speed': 1.0,
        'video_type': 'regular',
        'scheduled_datetime': scheduled_time
    }

# ==================== HEALTH CHECK TESTS ====================

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    
    data = response.get_json()
    assert data['status'] == 'healthy'
    assert 'timestamp' in data
    assert 'database' in data

# ==================== AUTHENTICATION TESTS ====================

def test_missing_api_key(client, valid_video_request):
    """Test request without API key"""
    response = client.post('/api/videos/generate', 
                          json=valid_video_request)
    assert response.status_code == 401
    
    data = response.get_json()
    assert 'message' in data or 'error' in data

def test_invalid_api_key(client, valid_video_request):
    """Test request with invalid API key"""
    response = client.post('/api/videos/generate',
                          json=valid_video_request,
                          headers={'X-API-Key': 'invalid-key'})
    assert response.status_code == 401
    
    data = response.get_json()
    assert 'message' in data or 'error' in data

# ==================== REQUEST VALIDATION TESTS ====================

def test_validate_valid_request(valid_video_request):
    """Test validation of valid request"""
    result = validate_video_generation_request(valid_video_request)
    assert result['valid'] == True
    assert result['error'] is None

def test_validate_missing_required_fields():
    """Test validation with missing required fields"""
    # Missing market_script
    result = validate_video_generation_request({
        'video_type': 'short',
        'scheduled_datetime': datetime.now().isoformat()
    })
    assert result['valid'] == False
    assert 'market_script' in result['error']
    
    # Missing video_type
    result = validate_video_generation_request({
        'market_script': 'Test script',
        'scheduled_datetime': datetime.now().isoformat()
    })
    assert result['valid'] == False
    assert 'video_type' in result['error']

def test_validate_invalid_video_type(sample_script):
    """Test validation with invalid video type"""
    result = validate_video_generation_request({
        'market_script': sample_script,
        'video_type': 'invalid_type',
        'scheduled_datetime': (datetime.now() + timedelta(hours=2)).isoformat()
    })
    assert result['valid'] == False
    assert 'video_type' in result['error']

def test_validate_invalid_datetime(sample_script):
    """Test validation with invalid datetime format"""
    result = validate_video_generation_request({
        'market_script': sample_script,
        'video_type': 'short',
        'scheduled_datetime': 'invalid-datetime'
    })
    assert result['valid'] == False

def test_validate_past_datetime(sample_script):
    """Test validation with past datetime"""
    past_time = (datetime.now() - timedelta(hours=1)).isoformat()
    result = validate_video_generation_request({
        'market_script': sample_script,
        'video_type': 'short',
        'scheduled_datetime': past_time
    })
    assert result['valid'] == False
    assert 'future' in result['error'].lower() or 'past' in result['error'].lower()
