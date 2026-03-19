"""
ET InvestorIQ — Video Engine Service
Background video generation with asyncio job management.
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from app.config import settings
from app.modules.video_engine.schemas import (
    VideoJob, VideoJobStatus, VideoRequest, VideoType
)
from app.services import claude_service, data_service

logger = logging.getLogger(__name__)

# In-memory job store (replace with DB for production)
_jobs: Dict[str, VideoJob] = {}
_jobs_lock = asyncio.Lock()


async def _update_job(job_id: str, **kwargs) -> None:
    """Update job fields safely."""
    async with _jobs_lock:
        if job_id in _jobs:
            job = _jobs[job_id]
            for k, v in kwargs.items():
                setattr(job, k, v)


async def create_video_job(request: VideoRequest) -> VideoJob:
    """
    Create a new video generation job and start background processing.

    Args:
        request: VideoRequest with type, symbols, duration, etc.

    Returns:
        VideoJob with job_id and QUEUED status.
    """
    job_id = str(uuid.uuid4())[:8]
    job = VideoJob(
        job_id=job_id,
        status=VideoJobStatus.QUEUED,
        video_type=request.video_type,
        created_at=datetime.now().isoformat(),
        request=request,
    )

    async with _jobs_lock:
        _jobs[job_id] = job

    # Fire and forget background generation
    asyncio.create_task(generate_video(job_id, request))
    return job


async def get_job_status(job_id: str) -> Optional[VideoJob]:
    """
    Get the current status of a video job.

    Args:
        job_id: Job identifier.

    Returns:
        VideoJob or None if not found.
    """
    return _jobs.get(job_id)


async def list_jobs(limit: int = 20) -> List[VideoJob]:
    """List recent video jobs, newest first."""
    jobs = list(_jobs.values())
    jobs.sort(key=lambda j: j.created_at, reverse=True)
    return jobs[:limit]


async def generate_video(job_id: str, request: VideoRequest) -> None:
    """
    Background async function that generates the complete video.

    Steps:
    1. Fetch market data
    2. Generate narration script via Claude
    3. Render animation via chart_renderer
    4. Update job status

    Args:
        job_id: Job identifier.
        request: VideoRequest parameters.
    """
    from app.modules.video_engine import chart_renderer

    try:
        await _update_job(job_id, status=VideoJobStatus.PROCESSING, progress_pct=5)

        # Prepare output path
        output_dir = settings.video_output_dir
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{job_id}.mp4")

        # ── Step 1: Fetch data ──────────────────────────────────────────────
        await _update_job(job_id, progress_pct=15)

        video_type = str(request.video_type)
        market_data = {}
        symbols = request.symbols or ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS",
                                        "INFY.NS", "ICICIBANK.NS"]

        if video_type == "MARKET_WRAP":
            market_data = await data_service.get_market_overview()
        elif video_type == "SECTOR_ROTATION":
            market_data = await data_service.get_sector_performance()
        elif video_type == "FII_DII_FLOW":
            market_data = await data_service.get_fii_dii_data(days=30)
        elif video_type == "RACE_CHART":
            market_data = {"symbols": symbols}
        elif video_type == "IPO_TRACKER":
            market_data = await data_service.get_ipo_data()
        elif video_type == "STOCK_DEEP_DIVE":
            sym = symbols[0] if symbols else "RELIANCE.NS"
            market_data = await data_service.get_fundamentals(sym)

        await _update_job(job_id, progress_pct=35)

        # ── Step 2: Generate narration script ──────────────────────────────
        narration = await claude_service.generate_video_narration(
            video_type=video_type,
            data=market_data if not isinstance(market_data, list) else {"items": market_data}
        )
        await _update_job(job_id, narration_script=narration, progress_pct=55)

        # ── Step 3: Render video in thread (matplotlib is not async) ────────
        loop = asyncio.get_event_loop()

        def _render():
            if video_type == "MARKET_WRAP":
                return chart_renderer.render_market_wrap(market_data, output_path)
            elif video_type == "SECTOR_ROTATION":
                return chart_renderer.render_sector_rotation(market_data, output_path)
            elif video_type == "FII_DII_FLOW":
                return chart_renderer.render_fii_dii_flow(
                    market_data if isinstance(market_data, list) else [], output_path
                )
            elif video_type == "RACE_CHART":
                return chart_renderer.render_race_chart({}, symbols, output_path)
            elif video_type == "IPO_TRACKER":
                return chart_renderer.render_ipo_tracker(
                    market_data if isinstance(market_data, list) else [], output_path
                )
            else:
                return chart_renderer.render_market_wrap(
                    {"nifty50": {"level": 22350, "change_pct": 0.5},
                     "top_gainers": [], "top_losers": [], "market_breadth": {},
                     "fii_net_today": 500, "vix": 15},
                    output_path
                )

        actual_path = await loop.run_in_executor(None, _render)
        await _update_job(job_id, progress_pct=90)

        # ── Step 4: Finalize ────────────────────────────────────────────────
        if actual_path and os.path.exists(actual_path):
            filename = os.path.basename(actual_path)
            output_url = f"/api/video/serve/{job_id}"
            await _update_job(
                job_id,
                status=VideoJobStatus.COMPLETE,
                progress_pct=100,
                output_url=output_url,
                completed_at=datetime.now().isoformat(),
            )
            # Store actual path for serving
            _jobs[job_id].__dict__["_actual_path"] = actual_path
            logger.info(f"Video job {job_id} complete: {actual_path}")
        else:
            await _update_job(
                job_id, status=VideoJobStatus.FAILED, progress_pct=0,
                error_message="Renderer returned no output path"
            )

    except Exception as e:
        logger.error(f"Video generation failed for job {job_id}: {e}", exc_info=True)
        await _update_job(
            job_id, status=VideoJobStatus.FAILED,
            error_message=str(e), progress_pct=0,
        )


def get_actual_video_path(job_id: str) -> Optional[str]:
    """Get the actual filesystem path for a completed video."""
    job = _jobs.get(job_id)
    if not job:
        return None
    # Check stored path
    actual = job.__dict__.get("_actual_path")
    if actual and os.path.exists(actual):
        return actual
    # Fallback: check expected paths
    for ext in [".mp4", ".gif", ".png"]:
        p = os.path.join(settings.video_output_dir, f"{job_id}{ext}")
        if os.path.exists(p):
            return p
    return None
