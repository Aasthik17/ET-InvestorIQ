"""
ET InvestorIQ — Opportunity Radar Schemas
Pydantic v2 models for signal detection and radar responses.
"""

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class SignalType(str, Enum):
    """Types of market signals detected by the Opportunity Radar."""
    INSIDER_TRADE = "INSIDER_TRADE"
    BULK_DEAL = "BULK_DEAL"
    FILING = "FILING"
    EARNINGS_SURPRISE = "EARNINGS_SURPRISE"
    PROMOTER_PLEDGE_CHANGE = "PROMOTER_PLEDGE_CHANGE"
    FII_ACCUMULATION = "FII_ACCUMULATION"
    TECHNICAL_BREAKOUT = "TECHNICAL_BREAKOUT"
    MANAGEMENT_CHANGE = "MANAGEMENT_CHANGE"
    DIVIDEND_SURPRISE = "DIVIDEND_SURPRISE"
    CORPORATE_ACTION = "CORPORATE_ACTION"


class SignalDirection(str, Enum):
    """Expected market impact direction of a signal."""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class MarketSentiment(str, Enum):
    """Overall market sentiment."""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class Signal(BaseModel):
    """
    A single market signal detected by the Opportunity Radar.
    Represents an anomaly or pattern worth investor attention.
    """
    id: str = Field(..., description="Unique signal identifier")
    symbol: str = Field(..., description="NSE stock symbol (without .NS suffix)")
    company_name: str = Field(default="", description="Full company name")
    signal_type: SignalType = Field(..., description="Category of signal")
    headline: str = Field(..., description="One-line summary of the signal")
    detail: str = Field(..., description="Detailed description with specific numbers")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="AI confidence 0-1")
    signal_date: str = Field(..., description="Date signal was detected (YYYY-MM-DD)")
    stock_price_at_signal: float = Field(default=0.0, description="Stock price when signal fired")
    expected_impact: SignalDirection = Field(default=SignalDirection.NEUTRAL)
    ai_analysis: str = Field(default="", description="Claude-generated analysis paragraph")
    data_sources: List[str] = Field(default_factory=list, description="Sources used")
    tags: List[str] = Field(default_factory=list, description="Searchable tags")
    raw_data: Optional[dict] = Field(default=None, description="Raw signal data for debugging")

    class Config:
        use_enum_values = True


class RadarResponse(BaseModel):
    """Full Opportunity Radar response with signals and market context."""
    signals: List[Signal] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    total_count: int = Field(default=0)
    bullish_count: int = Field(default=0)
    bearish_count: int = Field(default=0)
    market_sentiment: MarketSentiment = Field(default=MarketSentiment.NEUTRAL)
    top_opportunities: List[str] = Field(
        default_factory=list,
        description="Top stock symbols with highest-confidence bullish signals"
    )
    scan_metadata: dict = Field(
        default_factory=dict,
        description="Scan statistics: stocks scanned, time taken, data sources used"
    )


class InsiderSummary(BaseModel):
    """Summary of insider trading activity."""
    total_buys: int = 0
    total_sells: int = 0
    total_buy_value_cr: float = 0.0
    total_sell_value_cr: float = 0.0
    promoter_buys: int = 0
    net_sentiment: SignalDirection = SignalDirection.NEUTRAL
    top_signals: List[Signal] = Field(default_factory=list)
    notable_names: List[str] = Field(default_factory=list)


class SignalFilterRequest(BaseModel):
    """Filter parameters for signal queries."""
    signal_types: Optional[List[SignalType]] = None
    direction: Optional[SignalDirection] = None
    min_confidence: float = 0.0
    symbols: Optional[List[str]] = None
    date_from: Optional[str] = None
    page: int = 1
    page_size: int = 20
