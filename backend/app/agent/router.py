"""
Agent Router — exposes all agent pipelines via HTTP.

POST /api/agent/radar/run     -> run Radar pipeline
POST /api/agent/radar/stream  -> SSE stream of Radar steps
POST /api/agent/chart/run     -> run Chart pipeline for a symbol
POST /api/agent/chart/stream  -> SSE stream of Chart steps
POST /api/agent/video/run     -> run Video pipeline
POST /api/agent/video/stream  -> SSE stream of Video steps
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional

from fastapi import APIRouter
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from .chart_pipeline import create_chart_pipeline
from .radar_pipeline import create_radar_pipeline
from .video_pipeline import create_video_pipeline

router = APIRouter(prefix="/api/agent", tags=["agent"])
logger = logging.getLogger(__name__)

_recent_runs: dict[str, dict[str, Any]] = {}


class PortfolioHolding(BaseModel):
    symbol: str
    quantity: int
    avg_cost: float


class Portfolio(BaseModel):
    holdings: list[PortfolioHolding] = Field(default_factory=list)
    risk_profile: str = "MODERATE"


class RadarRunRequest(BaseModel):
    portfolio: Optional[Portfolio] = None


class ChartRunRequest(BaseModel):
    symbol: str = "RELIANCE"
    portfolio: Optional[Portfolio] = None


class VideoRunRequest(BaseModel):
    video_type: str = "MARKET_WRAP"
    portfolio: Optional[Portfolio] = None


def _store_run(run: Any) -> dict[str, Any]:
    payload = jsonable_encoder(run)
    _recent_runs[run.run_id] = payload
    return payload


async def _stream_pipeline(pipeline, portfolio: dict, metadata: Optional[dict] = None):
    queue = pipeline.subscribe()

    async def event_generator():
        task = asyncio.create_task(pipeline.run(portfolio=portfolio, metadata=metadata))
        run_payload: Optional[dict[str, Any]] = None

        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=0.5)
                    yield f"data: {json.dumps(event)}\n\n"

                    if event.get("type") == "pipeline_complete":
                        run = await task
                        run_payload = _store_run(run)
                        if run_payload.get("context", {}).get("alerts"):
                            yield (
                                "data: "
                                + json.dumps(
                                    {
                                        "type": "alerts",
                                        "alerts": run_payload["context"]["alerts"],
                                        "steps": run_payload.get("steps", []),
                                    }
                                )
                                + "\n\n"
                            )
                        yield f"data: {json.dumps({'type': 'run_complete', 'run': run_payload})}\n\n"
                        break
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    if task.done():
                        run = await task
                        run_payload = _store_run(run)
                        yield f"data: {json.dumps({'type': 'run_complete', 'run': run_payload})}\n\n"
                        break
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Agent stream failed")
            yield f"data: {json.dumps({'type': 'error', 'error': str(exc)})}\n\n"
        finally:
            pipeline.unsubscribe(queue)
            if not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

    import contextlib

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/radar/run")
async def run_radar_agent(request: RadarRunRequest):
    """Trigger the 5-step Opportunity Radar pipeline."""

    pipeline = create_radar_pipeline()
    portfolio = request.portfolio.model_dump() if request.portfolio else {}
    run = await pipeline.run(portfolio=portfolio)
    payload = _store_run(run)

    result = {
        "run_id": payload["run_id"],
        "pipeline": payload["pipeline_name"],
        "status": payload["status"],
        "total_ms": payload["total_ms"],
        "completed_at": payload["completed_at"],
        "steps": payload["steps"],
        "alerts": payload["context"]["alerts"],
        "signal_count": len(payload["context"]["signals"]),
        "enriched_count": len(payload["context"]["enriched"]),
        "context": payload["context"],
    }
    return JSONResponse(content=result)


@router.post("/radar/stream")
async def stream_radar_agent(request: RadarRunRequest):
    """SSE stream for the Radar pipeline."""

    pipeline = create_radar_pipeline()
    portfolio = request.portfolio.model_dump() if request.portfolio else {}
    return await _stream_pipeline(pipeline, portfolio=portfolio)


@router.post("/chart/run")
async def run_chart_agent(request: ChartRunRequest):
    """Trigger the 4-step Chart Intelligence pipeline for a symbol."""

    symbol = request.symbol.upper().replace(".NS", "")
    pipeline = create_chart_pipeline(symbol)
    portfolio = request.portfolio.model_dump() if request.portfolio else {}
    run = await pipeline.run(portfolio=portfolio, metadata={"symbol": symbol})
    payload = _store_run(run)

    return JSONResponse(
        content={
            "run_id": payload["run_id"],
            "pipeline": payload["pipeline_name"],
            "status": payload["status"],
            "total_ms": payload["total_ms"],
            "completed_at": payload["completed_at"],
            "steps": payload["steps"],
            "alerts": payload["context"]["alerts"],
            "patterns": payload["context"]["signals"],
            "symbol": symbol,
            "context": payload["context"],
        }
    )


@router.post("/chart/stream")
async def stream_chart_agent(request: ChartRunRequest):
    """SSE stream for the Chart pipeline."""

    symbol = request.symbol.upper().replace(".NS", "")
    pipeline = create_chart_pipeline(symbol)
    portfolio = request.portfolio.model_dump() if request.portfolio else {}
    return await _stream_pipeline(pipeline, portfolio=portfolio, metadata={"symbol": symbol})


@router.post("/video/run")
async def run_video_agent(request: VideoRunRequest):
    """Trigger the 4-step Video Engine pipeline."""

    video_type = request.video_type.upper()
    pipeline = create_video_pipeline(video_type)
    portfolio = request.portfolio.model_dump() if request.portfolio else {}
    run = await pipeline.run(portfolio=portfolio, metadata={"video_type": video_type})
    payload = _store_run(run)

    return JSONResponse(
        content={
            "run_id": payload["run_id"],
            "pipeline": payload["pipeline_name"],
            "status": payload["status"],
            "total_ms": payload["total_ms"],
            "completed_at": payload["completed_at"],
            "steps": payload["steps"],
            "video_path": payload["context"]["video_path"],
            "narration": payload["context"]["narration"],
            "context": payload["context"],
        }
    )


@router.post("/video/stream")
async def stream_video_agent(request: VideoRunRequest):
    """SSE stream for the Video pipeline."""

    video_type = request.video_type.upper()
    pipeline = create_video_pipeline(video_type)
    portfolio = request.portfolio.model_dump() if request.portfolio else {}
    return await _stream_pipeline(pipeline, portfolio=portfolio, metadata={"video_type": video_type})
