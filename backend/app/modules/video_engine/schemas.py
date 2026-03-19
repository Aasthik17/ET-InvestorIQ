"""
ET InvestorIQ — Video Engine Schemas
Pydantic v2 models for the AI Market Video Engine.
"""

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class VideoType(str, Enum):
    """Available video generation types."""
    MARKET_WRAP = "MARKET_WRAP"
    SECTOR_ROTATION = "SECTOR_ROTATION"
    FII_DII_FLOW = "FII_DII_FLOW"
    RACE_CHART = "RACE_CHART"
    IPO_TRACKER = "IPO_TRACKER"
    STOCK_DEEP_DIVE = "STOCK_DEEP_DIVE"


class VideoJobStatus(str, Enum):
    """Video generation job status."""
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class VideoRequest(BaseModel):
    """Request to generate a new market video."""
    video_type: VideoType
    symbols: List[str] = Field(default_factory=list)
    duration_seconds: int = Field(default=60, ge=15, le=120)
    date_range: str = Field(default="1M", description="1W, 1M, 3M, 6M, 1Y")
    custom_title: Optional[str] = None


class VideoJob(BaseModel):
    """A video generation job with status tracking."""
    job_id: str
    status: VideoJobStatus = VideoJobStatus.QUEUED
    video_type: VideoType
    progress_pct: int = Field(default=0, ge=0, le=100)
    output_url: Optional[str] = None
    narration_script: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    request: Optional[VideoRequest] = None

    class Config:
        use_enum_values = True


class VideoGenerationResponse(BaseModel):
    """Immediate response when a video job is created."""
    job_id: str
    estimated_seconds: int = 45
    status: VideoJobStatus = VideoJobStatus.QUEUED
    message: str = "Video generation started"

    class Config:
        use_enum_values = True


class VideoTypeInfo(BaseModel):
    """Metadata about an available video type."""
    video_type: str
    name: str
    description: str
    estimated_duration: str
    icon: str
