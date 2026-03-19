"""
ET InvestorIQ — Opportunity Radar Router
FastAPI router with REST endpoints and WebSocket for real-time signal streaming.
"""

import asyncio
import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse

from app.modules.opportunity_radar import service
from app.modules.opportunity_radar.schemas import (
    RadarResponse, Signal, SignalFilterRequest, SignalType, SignalDirection,
    InsiderSummary
)
from app.services import data_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/radar", tags=["Opportunity Radar"])

# Active WebSocket connections for real-time signal feed
_active_connections: List[WebSocket] = []


@router.get("/signals", response_model=RadarResponse)
async def get_signals(
    signal_types: Optional[str] = Query(None, description="Comma-separated signal types"),
    direction: Optional[str] = Query(None, description="BULLISH, BEARISH, or NEUTRAL"),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    symbols: Optional[str] = Query(None, description="Comma-separated NSE symbols"),
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD filter"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    Get paginated list of ranked market signals with optional filters.
    Signals are cached for 30 minutes for performance.
    """
    filters = SignalFilterRequest(
        signal_types=[SignalType(t.strip()) for t in signal_types.split(",") if t.strip()] if signal_types else None,
        direction=SignalDirection(direction) if direction else None,
        min_confidence=min_confidence,
        symbols=[s.strip().upper() for s in symbols.split(",") if s.strip()] if symbols else None,
        date_from=date_from,
        page=page,
        page_size=page_size,
    )
    return await service.get_signals(filters)


@router.get("/signals/refresh", response_model=RadarResponse)
async def refresh_signals():
    """Force refresh signals from live data sources, bypassing all caches."""
    return await service.refresh_signals()


@router.get("/signals/{signal_id}", response_model=Signal)
async def get_signal(signal_id: str):
    """Get a specific signal by its ID."""
    sig = await service.get_signal_by_id(signal_id)
    if not sig:
        raise HTTPException(status_code=404, detail=f"Signal {signal_id} not found")
    return sig


@router.get("/insider", response_model=list)
async def get_insider_trades(
    days: int = Query(30, ge=1, le=90),
    trade_type: Optional[str] = Query(None, description="Buy or Sell"),
):
    """Get recent insider trading disclosures from NSE."""
    trades = await data_service.get_insider_trades()
    if trade_type:
        trades = [t for t in trades if t.get("trade_type", "").lower() == trade_type.lower()]
    return trades[:50]


@router.get("/bulk-deals", response_model=list)
async def get_bulk_deals():
    """Get recent bulk and block deals from NSE/BSE."""
    return await data_service.get_bulk_block_deals()


@router.get("/filings", response_model=list)
async def get_filings(
    symbol: Optional[str] = Query(None, description="Filter by NSE symbol"),
):
    """Get recent corporate filings from BSE."""
    return await data_service.get_corporate_filings(symbol=symbol)


@router.get("/summary", response_model=InsiderSummary)
async def get_summary():
    """Get a market-wide insider trading activity summary."""
    return await service.get_insider_summary()


@router.get("/fii-dii")
async def get_fii_dii(days: int = Query(30, ge=5, le=90)):
    """Get FII and DII net investment flows."""
    return await data_service.get_fii_dii_data(days=days)


# ─── WebSocket: Real-time signal stream ──────────────────────────────────────

@router.websocket("/ws/signals")
async def websocket_signal_stream(websocket: WebSocket):
    """
    WebSocket endpoint that streams new signals every 60 seconds.
    Clients connect once and receive updates automatically.
    """
    await websocket.accept()
    _active_connections.append(websocket)
    logger.info(f"WebSocket connected. Active: {len(_active_connections)}")
    try:
        while True:
            # Send a ping every 60 seconds; real signals are broadcast externally
            await asyncio.sleep(60)
            try:
                # Fetch fresh signals and send top 5
                response = await service.refresh_signals()
                top_signals = [s.model_dump() for s in response.signals[:5]]
                message = {
                    "type": "signal_update",
                    "signals": top_signals,
                    "total": response.total_count,
                    "sentiment": response.market_sentiment,
                }
                await websocket.send_text(json.dumps(message, default=str))
            except Exception as e:
                logger.warning(f"Error sending WS update: {e}")
    except WebSocketDisconnect:
        _active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Active: {len(_active_connections)}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            _active_connections.remove(websocket)
        except ValueError:
            pass


async def broadcast_signal(signal: Signal):
    """Broadcast a new signal to all connected WebSocket clients."""
    if not _active_connections:
        return
    message = json.dumps({
        "type": "new_signal",
        "signal": signal.model_dump(),
    }, default=str)
    disconnected = []
    for ws in _active_connections:
        try:
            await ws.send_text(message)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        try:
            _active_connections.remove(ws)
        except ValueError:
            pass
