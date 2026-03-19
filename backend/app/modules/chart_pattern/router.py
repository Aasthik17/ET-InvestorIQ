"""
ET InvestorIQ — Chart Pattern Router
FastAPI router for chart intelligence endpoints.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Query, HTTPException

from app.modules.chart_pattern import service
from app.modules.chart_pattern.schemas import (
    OHLCVData, PatternScanResult, SupportResistanceLevels
)
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/charts", tags=["Chart Pattern Intelligence"])


@router.get("/scan/{symbol}", response_model=PatternScanResult)
async def scan_stock(
    symbol: str,
    period: str = Query("1y", description="1mo, 3mo, 6mo, 1y, 2y"),
):
    """Scan a single stock for all detectable chart patterns with AI analysis."""
    symbol_clean = symbol.upper()
    if "." not in symbol_clean:
        symbol_clean += ".NS"  # Default to NSE
    return await service.scan_stock(symbol_clean, period=period)


@router.get("/scan/universe/all", response_model=List[PatternScanResult])
async def scan_universe(
    symbols: Optional[str] = Query(None, description="Comma-separated symbols"),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    direction: Optional[str] = Query(None, description="BULLISH, BEARISH, NEUTRAL"),
):
    """Scan NSE Top 50 stocks for patterns. Returns only stocks with detected patterns."""
    sym_list = None
    if symbols:
        sym_list = [s.strip().upper() for s in symbols.split(",")]
        sym_list = [s if "." in s else s + ".NS" for s in sym_list]

    results = await service.scan_universe(sym_list)

    # Apply filters
    if min_confidence > 0:
        results = [r for r in results if any(p.confidence >= min_confidence for p in r.patterns)]
    if direction:
        results = [r for r in results if r.overall_bias == direction]

    return results


@router.get("/patterns", response_model=List[PatternScanResult])
async def list_patterns(
    pattern_type: Optional[str] = Query(None),
    direction: Optional[str] = Query(None, description="BULLISH or BEARISH"),
    min_confidence: float = Query(0.5),
    limit: int = Query(20, ge=1, le=100),
):
    """List recently detected patterns across the market with filters."""
    results = await service.scan_universe()
    if direction:
        results = [r for r in results if any(
            p.direction == direction for p in r.patterns
        )]
    if pattern_type:
        results = [r for r in results if any(
            str(p.pattern_type) == pattern_type for p in r.patterns
        )]
    if min_confidence > 0:
        results = [r for r in results if any(
            p.confidence >= min_confidence for p in r.patterns
        )]
    return results[:limit]


@router.get("/levels/{symbol}", response_model=SupportResistanceLevels)
async def get_support_resistance(symbol: str):
    """Get key support and resistance levels, pivot points, and 52-week range."""
    symbol_clean = symbol.upper()
    if "." not in symbol_clean:
        symbol_clean += ".NS"
    return await service.get_support_resistance(symbol_clean)


@router.get("/ohlcv/{symbol}", response_model=OHLCVData)
async def get_ohlcv(
    symbol: str,
    period: str = Query("1y", description="1mo, 3mo, 6mo, 1y, 2y, 5y"),
    interval: str = Query("1d", description="1d, 1wk, 1mo"),
):
    """Fetch OHLCV candlestick data formatted for the frontend chart component."""
    symbol_clean = symbol.upper()
    if "." not in symbol_clean:
        symbol_clean += ".NS"
    return await service.get_ohlcv(symbol_clean, period=period, interval=interval)


@router.post("/explain")
async def explain_pattern(pattern_data: dict):
    """Get Claude AI explanation for a specific detected pattern."""
    from app.modules.chart_pattern.schemas import DetectedPattern, PatternType, PatternDirection
    try:
        pattern = DetectedPattern(**pattern_data)
        explanation = await service.get_pattern_explanation(pattern)
        return {"explanation": explanation}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
