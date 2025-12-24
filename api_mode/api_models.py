"""
API Models - Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, Literal, Dict, Any
from datetime import datetime


class VideoGenerationRequest(BaseModel):
    """Request model for video generation endpoint"""
    
    market_script: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        description="Market analysis script. Use '— pause —' to separate videos for shorts."
    )
    
    voice: Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"] = Field(
        default="onyx",
        description="OpenAI TTS voice to use for voiceover"
    )
    
    speed: float = Field(
        default=1.2,
        ge=0.5,
        le=2.0,
        description="Speech speed (0.5 to 2.0)"
    )
    
    video_type: Literal["short", "regular"] = Field(
        ...,
        description="Video format: 'short' for vertical 9:16, 'regular' for landscape 16:9"
    )
    
    scheduled_datetime: str = Field(
        ...,
        description="ISO format datetime for upload scheduling (e.g., 2025-12-20T10:30:00)"
    )
    
    @validator('scheduled_datetime')
    def validate_datetime(cls, v):
        """Ensure scheduled_datetime is valid ISO format and in the future"""
        try:
            dt = datetime.fromisoformat(v.replace('Z', '+00:00'))
            
            # Check if datetime is in the future
            if dt <= datetime.now():
                raise ValueError("scheduled_datetime must be in the future")
            
            return v
        except ValueError as e:
            if "future" in str(e):
                raise ValueError("scheduled_datetime must be in the future")
            raise ValueError(f"Invalid datetime format. Use ISO format (e.g., 2025-12-20T10:30:00)")
    
    @validator('market_script')
    def validate_script(cls, v):
        """Validate script content"""
        if not v.strip():
            raise ValueError("market_script cannot be empty")
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "market_script": "HDFC Bank as on 15 Dec 2024\n\nMarket analysis content here...\n\n— pause —\n\nNext company analysis...",
                "voice": "onyx",
                "speed": 1.2,
                "video_type": "short",
                "scheduled_datetime": "2025-12-20T10:30:00"
            }
        }


class VideoGenerationResponse(BaseModel):
    """Response model for successful video generation request"""
    
    success: bool = True
    job_id: str = Field(..., description="Unique job identifier")
    message: str = Field(default="Video generation started")
    status: str = Field(default="queued", description="Current job status")
    estimated_videos: int = Field(..., description="Estimated number of videos to be generated")
    check_status_url: str = Field(..., description="URL to check job status")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "job_id": "job_1734325678_abc123",
                "message": "Video generation started",
                "status": "queued",
                "estimated_videos": 3,
                "check_status_url": "/api/jobs/job_1734325678_abc123"
            }
        }


class JobStatusResponse(BaseModel):
    """Response model for job status endpoint"""
    
    job_id: str
    status: Literal["queued", "processing", "completed", "failed", "cancelled"]
    progress: int = Field(ge=0, le=100, description="Progress percentage (0-100)")
    message: str = Field(default="", description="Current status message")
    created_at: str
    completed_at: Optional[str] = None
    videos_generated: int = Field(default=0, description="Number of videos generated")
    videos_uploaded: int = Field(default=0, description="Number of videos uploaded to YouTube")
    error: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "job_1734325678_abc123",
                "status": "processing",
                "progress": 66,
                "message": "Generating video 2 of 3...",
                "created_at": "2025-12-16T10:00:00",
                "completed_at": None,
                "videos_generated": 2,
                "videos_uploaded": 1,
                "error": None
            }
        }


class JobListResponse(BaseModel):
    """Response model for listing jobs"""
    
    jobs: list[JobStatusResponse]
    total: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "jobs": [
                    {
                        "job_id": "job_1734325678_abc123",
                        "status": "completed",
                        "progress": 100,
                        "message": "All videos uploaded successfully",
                        "created_at": "2025-12-16T10:00:00",
                        "completed_at": "2025-12-16T10:15:00",
                        "videos_generated": 3,
                        "videos_uploaded": 3,
                        "error": None
                    }
                ],
                "total": 1
            }
        }


class ErrorResponse(BaseModel):
    """Response model for errors"""
    
    success: bool = False
    error: str
    details: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "Invalid API key",
                "details": "The provided API key is not valid"
            }
        }


class HealthResponse(BaseModel):
    """Response model for health check"""
    
    status: str = "healthy"
    timestamp: str
    version: str = "1.0.0"
    uptime_seconds: float
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2025-12-16T10:00:00",
                "version": "1.0.0",
                "uptime_seconds": 3600.5
            }
        }


def validate_video_generation_request(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate video generation request data
    
    Args:
        data: Request data dictionary
        
    Returns:
        Dictionary with 'valid' (bool) and 'error' (str) keys
    """
    try:
        # Use Pydantic model for validation
        request = VideoGenerationRequest(**data)
        return {
            'valid': True,
            'error': None,
            'data': request.model_dump()
        }
    except Exception as e:
        return {
            'valid': False,
            'error': str(e),
            'data': None
        }
