"""
ET InvestorIQ — Video Engine Router
FastAPI router for video generation and serving.
"""

import logging
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from app.modules.video_engine import service
from app.modules.video_engine.schemas import (
    VideoGenerationResponse, VideoJob, VideoRequest, VideoTypeInfo
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/video", tags=["AI Market Video Engine"])

VIDEO_TYPE_CATALOG = [
    VideoTypeInfo(
        video_type="MARKET_WRAP",
        name="Market Wrap",
        description="Daily NSE/BSE market summary: index levels, top movers, breadth, FII",
        estimated_duration="60 seconds",
        icon="📊",
    ),
    VideoTypeInfo(
        video_type="SECTOR_ROTATION",
        name="Sector Rotation Heatmap",
        description="Animated heatmap showing sector performance (1D, 1W, 1M returns)",
        estimated_duration="45 seconds",
        icon="🗺️",
    ),
    VideoTypeInfo(
        video_type="FII_DII_FLOW",
        name="FII/DII Flow Analysis",
        description="30-day stacked bar chart of Foreign and Domestic institutional flows",
        estimated_duration="60 seconds",
        icon="💰",
    ),
    VideoTypeInfo(
        video_type="RACE_CHART",
        name="Stock Return Race",
        description="Animated bar race: see which stocks gained most over a period",
        estimated_duration="30 seconds",
        icon="🏁",
    ),
    VideoTypeInfo(
        video_type="IPO_TRACKER",
        name="IPO Tracker",
        description="Upcoming IPOs timeline + recent listing gains animated chart",
        estimated_duration="45 seconds",
        icon="🚀",
    ),
    VideoTypeInfo(
        video_type="STOCK_DEEP_DIVE",
        name="Stock Deep Dive",
        description="Technical + fundamental breakdown for a single stock",
        estimated_duration="90 seconds",
        icon="🔍",
    ),
]


@router.get("/types")
async def list_video_types():
    """List all available video types with descriptions and estimated duration."""
    return [v.model_dump() for v in VIDEO_TYPE_CATALOG]


@router.post("/generate", response_model=VideoGenerationResponse)
async def generate_video(request: VideoRequest):
    """
    Create a new video generation job. Returns immediately with a job_id.
    Poll /job/{job_id} to check progress.
    """
    job = await service.create_video_job(request)
    return VideoGenerationResponse(
        job_id=job.job_id,
        estimated_seconds=45,
        status=job.status,
        message=f"{request.video_type} video generation queued.",
    )


@router.get("/job/{job_id}", response_model=VideoJob)
async def get_job_status(job_id: str):
    """Poll the status and progress of a video generation job."""
    job = await service.get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job


@router.get("/jobs")
async def list_jobs(limit: int = 20):
    """List recent video jobs with their status."""
    jobs = await service.list_jobs(limit=limit)
    return [j.model_dump() for j in jobs]


@router.get("/serve/{job_id}")
async def serve_video(job_id: str):
    """Stream the generated video file for a completed job."""
    actual_path = service.get_actual_video_path(job_id)
    if not actual_path:
        raise HTTPException(status_code=404, detail=f"Video file not found for job {job_id}")

    ext = os.path.splitext(actual_path)[1].lower()
    media_types = {
        ".mp4": "video/mp4",
        ".gif": "image/gif",
        ".png": "image/png",
    }
    media_type = media_types.get(ext, "application/octet-stream")

    return FileResponse(
        path=actual_path,
        media_type=media_type,
        filename=f"investoriq_{job_id}{ext}",
    )
