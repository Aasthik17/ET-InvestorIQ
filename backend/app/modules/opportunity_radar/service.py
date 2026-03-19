"""
ET InvestorIQ — Opportunity Radar Service
Business logic layer between the router and the signal engine.
"""

import logging
from typing import Optional

from app.modules.opportunity_radar.schemas import (
    RadarResponse, Signal, SignalFilterRequest, InsiderSummary, SignalDirection
)
from app.modules.opportunity_radar.signal_engine import run_radar
from app.services import data_service
from app.services.cache_service import cache

logger = logging.getLogger(__name__)


async def get_signals(filters: Optional[SignalFilterRequest] = None) -> RadarResponse:
    """
    Get radar signals with optional filtering.

    Args:
        filters: Optional filter parameters (signal type, direction, confidence, etc.)

    Returns:
        Filtered RadarResponse.
    """
    response = await run_radar(use_cache=True)

    if not filters:
        return response

    filtered_signals = response.signals

    # Apply filters
    if filters.signal_types:
        filtered_signals = [s for s in filtered_signals if s.signal_type in filters.signal_types]
    if filters.direction:
        filtered_signals = [s for s in filtered_signals if s.expected_impact == filters.direction]
    if filters.min_confidence > 0:
        filtered_signals = [s for s in filtered_signals if s.confidence_score >= filters.min_confidence]
    if filters.symbols:
        syms = [s.upper() for s in filters.symbols]
        filtered_signals = [s for s in filtered_signals if s.symbol.upper() in syms]
    if filters.date_from:
        filtered_signals = [s for s in filtered_signals if s.signal_date >= filters.date_from]

    # Pagination
    start = (filters.page - 1) * filters.page_size
    end = start + filters.page_size
    paginated = filtered_signals[start:end]

    response.signals = paginated
    response.total_count = len(filtered_signals)
    return response


async def get_signal_by_id(signal_id: str) -> Optional[Signal]:
    """
    Fetch a single signal by ID from the current radar scan.

    Args:
        signal_id: Signal unique identifier.

    Returns:
        Signal if found, None otherwise.
    """
    response = await run_radar(use_cache=True)
    for sig in response.signals:
        if sig.id == signal_id:
            return sig
    return None


async def refresh_signals() -> RadarResponse:
    """
    Force a fresh scan bypassing all caches.

    Returns:
        Fresh RadarResponse from live data.
    """
    cache.delete("signals:latest")
    return await run_radar(use_cache=False)


async def get_insider_summary() -> InsiderSummary:
    """
    Get a summary of insider trading activity with key stats.

    Returns:
        InsiderSummary with aggregate statistics and top signals.
    """
    trades = await data_service.get_insider_trades()
    response = await run_radar(use_cache=True)

    insider_signals = [s for s in response.signals
                       if s.signal_type == "INSIDER_TRADE"]

    total_buys = sum(1 for t in trades if t.get("trade_type") == "Buy")
    total_sells = sum(1 for t in trades if t.get("trade_type") == "Sell")
    buy_value = sum(float(t.get("value_cr", 0)) for t in trades if t.get("trade_type") == "Buy")
    sell_value = sum(float(t.get("value_cr", 0)) for t in trades if t.get("trade_type") == "Sell")
    promoter_buys = sum(1 for t in trades
                        if t.get("trade_type") == "Buy" and t.get("category") == "Promoter")

    net_sentiment = SignalDirection.NEUTRAL
    if buy_value > sell_value * 1.5:
        net_sentiment = SignalDirection.BULLISH
    elif sell_value > buy_value * 1.5:
        net_sentiment = SignalDirection.BEARISH

    notable = list(set(t.get("person_name", "") for t in trades if t.get("category") == "Promoter"))[:5]

    return InsiderSummary(
        total_buys=total_buys,
        total_sells=total_sells,
        total_buy_value_cr=round(buy_value, 2),
        total_sell_value_cr=round(sell_value, 2),
        promoter_buys=promoter_buys,
        net_sentiment=net_sentiment,
        top_signals=insider_signals[:5],
        notable_names=notable,
    )
