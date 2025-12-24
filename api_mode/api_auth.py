"""
API Authentication - API key validation and rate limiting
"""
import logging
import yaml
import time
from functools import wraps
from typing import Optional, Dict, List
from pathlib import Path
from flask import request, jsonify
from collections import defaultdict
from datetime import datetime, timedelta


class APIAuth:
    """Handles API key authentication and rate limiting"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize authentication system
        
        Args:
            config_path: Path to configuration file
        """
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config(config_path)
        self.api_keys = self._load_api_keys()
        
        # Rate limiting tracking
        self.request_counts = defaultdict(list)  # api_key -> [timestamps]
        self.max_requests_per_minute = self.config['limits']['max_requests_per_minute']
        
        self.logger.info(f"✅ Auth initialized with {len(self.api_keys)} API keys")
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                return config
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            # Return default config
            return {
                'api': {
                    'api_keys': []
                },
                'limits': {
                    'max_requests_per_minute': 10,
                    'max_concurrent_jobs': 3
                }
            }
    
    def _load_api_keys(self) -> Dict[str, Dict]:
        """
        Load API keys from config
        
        Returns:
            Dict mapping API key to metadata
        """
        api_keys = {}
        
        for key_config in self.config['api']['api_keys']:
            key = key_config['key']
            api_keys[key] = {
                'name': key_config.get('name', 'Unknown'),
                'description': key_config.get('description', '')
            }
        
        return api_keys
    
    def validate_api_key(self, api_key: Optional[str]) -> tuple[bool, Optional[str]]:
        """
        Validate API key
        
        Args:
            api_key: API key to validate
            
        Returns:
            (is_valid, error_message)
        """
        if not api_key:
            return False, "API key is required. Provide it in X-API-Key header"
        
        if api_key not in self.api_keys:
            return False, "Invalid API key"
        
        return True, None
    
    def check_rate_limit(self, api_key: str) -> tuple[bool, Optional[str]]:
        """
        Check if API key has exceeded rate limit
        
        Args:
            api_key: API key to check
            
        Returns:
            (is_allowed, error_message)
        """
        now = time.time()
        cutoff = now - 60  # 1 minute ago
        
        # Remove old timestamps
        self.request_counts[api_key] = [
            ts for ts in self.request_counts[api_key] 
            if ts > cutoff
        ]
        
        # Check if limit exceeded
        current_count = len(self.request_counts[api_key])
        
        if current_count >= self.max_requests_per_minute:
            return False, f"Rate limit exceeded. Maximum {self.max_requests_per_minute} requests per minute"
        
        # Add current request
        self.request_counts[api_key].append(now)
        
        return True, None
    
    def get_api_key_info(self, api_key: str) -> Optional[Dict]:
        """
        Get API key metadata
        
        Args:
            api_key: API key
            
        Returns:
            Metadata dict or None
        """
        return self.api_keys.get(api_key)


# Flask decorator for API key authentication
def require_api_key(f):
    """Decorator to require and validate API key"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        logger = logging.getLogger(__name__)
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            # Return tuple instead of Response object
            return {'error': 'Missing API key', 'message': 'Please provide X-API-Key header'}, 401
        
        # Load valid API keys from config
        config_path = Path(__file__).parent / 'config.yaml'
        try:
            with open(config_path, 'r') as config_file:
                config = yaml.safe_load(config_file)
                
                # Handle different config structures
                valid_keys = []
                
                # Try to get api_keys from nested structure
                if isinstance(config, dict):
                    api_section = config.get('api', {})
                    if isinstance(api_section, dict):
                        api_keys_list = api_section.get('api_keys', [])
                        
                        # If api_keys is a list of dicts with 'key' field
                        if isinstance(api_keys_list, list):
                            for key_config in api_keys_list:
                                if isinstance(key_config, dict):
                                    valid_keys.append(key_config.get('key'))
                                elif isinstance(key_config, str):
                                    valid_keys.append(key_config)
                        # If api_keys is a simple list of strings
                        elif isinstance(api_keys_list, str):
                            valid_keys.append(api_keys_list)
                    
                    # Also check for direct api_keys field at root level
                    if 'api_keys' in config:
                        root_keys = config['api_keys']
                        if isinstance(root_keys, list):
                            for key in root_keys:
                                if isinstance(key, str):
                                    valid_keys.append(key)
                                elif isinstance(key, dict):
                                    valid_keys.append(key.get('key'))
                
                # Remove None values
                valid_keys = [k for k in valid_keys if k]
                
                if not valid_keys:
                    logger.error("No valid API keys found in config")
                    return {'error': 'Server configuration error'}, 500
                    
        except FileNotFoundError:
            logger.error(f"Config file not found: {config_path}")
            return {'error': 'Server configuration error'}, 500
        except Exception as e:
            logger.error(f"Failed to load API config: {e}")
            return {'error': 'Server configuration error'}, 500
        
        # Validate API key
        if api_key not in valid_keys:
            logger.warning(f"Invalid API key attempt: {api_key[:10]}...")
            return {'error': 'Invalid API key', 'message': 'The provided API key is not valid'}, 401
        
        # Check rate limit
        if not check_rate_limit(api_key):
            return {'error': 'Rate limit exceeded', 'message': 'Too many requests. Please try again later.'}, 429
        
        # API key is valid, continue
        return f(*args, **kwargs)
    
    return decorated_function


# Utility functions
def get_client_ip() -> str:
    """Get client IP address from request"""
    if request.environ.get('HTTP_X_FORWARDED_FOR'):
        return request.environ['HTTP_X_FORWARDED_FOR'].split(',')[0]
    return request.environ.get('REMOTE_ADDR', 'unknown')


def log_request(api_key: str, endpoint: str, method: str):
    """Log API request for monitoring"""
    logger = logging.getLogger(__name__)
    logger.info(f"API Request: {method} {endpoint} | API Key: {api_key[:10]}... | IP: {get_client_ip()}")


# Global variables for standalone functions
_rate_limit_tracker = defaultdict(list)
_config = None


def _load_global_config():
    """Load config for standalone functions"""
    global _config
    if _config is None:
        import os
        config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
        try:
            with open(config_path, 'r') as f:
                _config = yaml.safe_load(f)
        except Exception:
            _config = {
                'limits': {
                    'max_requests_per_minute': 10,
                    'max_concurrent_jobs': 3
                }
            }
    return _config


def check_rate_limit(api_key: str) -> bool:
    """
    Standalone function to check rate limit for an API key
    
    Args:
        api_key: API key to check
        
    Returns:
        True if allowed, False if rate limit exceeded
    """
    config = _load_global_config()
    now = time.time()
    cutoff = now - 60  # 1 minute ago
    
    # Remove old timestamps
    _rate_limit_tracker[api_key] = [
        ts for ts in _rate_limit_tracker[api_key] 
        if ts > cutoff
    ]
    
    # Check if limit exceeded
    current_count = len(_rate_limit_tracker[api_key])
    max_requests = config['limits']['max_requests_per_minute']
    
    if current_count >= max_requests:
        return False
    
    # Add current request
    _rate_limit_tracker[api_key].append(now)
    return True


def check_concurrent_jobs(api_key: str, current_jobs_count: int) -> bool:
    """
    Standalone function to check if API key has exceeded concurrent jobs limit
    
    Args:
        api_key: API key to check
        current_jobs_count: Number of currently active jobs for this API key
        
    Returns:
        True if allowed, False if limit exceeded
    """
    config = _load_global_config()
    max_concurrent = config['limits']['max_concurrent_jobs']
    return current_jobs_count < max_concurrent
