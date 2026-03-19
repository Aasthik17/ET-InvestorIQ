"""
ET InvestorIQ — Chart Pattern Schemas
Pydantic v2 models for chart pattern detection and analysis.
"""

from __future__ import annotations
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class PatternType(str, Enum):
    """All detectable chart/technical patterns."""
    HEAD_AND_SHOULDERS = "HEAD_AND_SHOULDERS"
    INVERSE_HEAD_AND_SHOULDERS = "INVERSE_HEAD_AND_SHOULDERS"
    DOUBLE_TOP = "DOUBLE_TOP"
    DOUBLE_BOTTOM = "DOUBLE_BOTTOM"
    TRIPLE_TOP = "TRIPLE_TOP"
    TRIPLE_BOTTOM = "TRIPLE_BOTTOM"
    CUP_AND_HANDLE = "CUP_AND_HANDLE"
    BULL_FLAG = "BULL_FLAG"
    BEAR_FLAG = "BEAR_FLAG"
    ASCENDING_TRIANGLE = "ASCENDING_TRIANGLE"
    DESCENDING_TRIANGLE = "DESCENDING_TRIANGLE"
    SYMMETRICAL_TRIANGLE = "SYMMETRICAL_TRIANGLE"
    BULLISH_ENGULFING = "BULLISH_ENGULFING"
    BEARISH_ENGULFING = "BEARISH_ENGULFING"
    DOJI = "DOJI"
    HAMMER = "HAMMER"
    SHOOTING_STAR = "SHOOTING_STAR"
    MORNING_STAR = "MORNING_STAR"
    EVENING_STAR = "EVENING_STAR"
    RSI_DIVERGENCE = "RSI_DIVERGENCE"
    MACD_CROSSOVER = "MACD_CROSSOVER"
    GOLDEN_CROSS = "GOLDEN_CROSS"
    DEATH_CROSS = "DEATH_CROSS"
    BREAKOUT = "BREAKOUT"
    BREAKDOWN = "BREAKDOWN"
    SUPPORT_BOUNCE = "SUPPORT_BOUNCE"
    RESISTANCE_REJECTION = "RESISTANCE_REJECTION"
    BB_SQUEEZE = "BB_SQUEEZE"
    RSI_OVERSOLD = "RSI_OVERSOLD"
    RSI_OVERBOUGHT = "RSI_OVERBOUGHT"


class PatternDirection(str, Enum):
    """Expected price movement direction."""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class DetectedPattern(BaseModel):
    """A single detected chart pattern on a stock."""
    symbol: str
    pattern_type: PatternType
    detected_at: str = Field(..., description="Date pattern was confirmed (YYYY-MM-DD)")
    confidence: float = Field(..., ge=0.0, le=1.0)
    direction: PatternDirection
    key_levels: Dict[str, float] = Field(
        default_factory=dict,
        description="Support, resistance, target, stop_loss levels"
    )
    indicators: Dict[str, float] = Field(
        default_factory=dict,
        description="RSI, MACD, BB_width, volume_ratio, ADX values at detection"
    )
    ai_explanation: str = Field(default="", description="Claude-generated plain-English explanation")
    backtest_stats: Dict = Field(
        default_factory=dict,
        description="Historical win_rate, avg_return_pct, avg_holding_days, sample_size"
    )
    pattern_label: str = Field(default="", description="Human-readable pattern name")

    class Config:
        use_enum_values = True


class PatternScanResult(BaseModel):
    """Scan result for a single stock — contains all detected patterns."""
    symbol: str
    company_name: str = ""
    patterns: List[DetectedPattern] = Field(default_factory=list)
    current_price: float = 0.0
    price_change_1d_pct: float = 0.0
    volume_ratio: float = 1.0  # Today's volume / 20-day avg volume
    overall_bias: PatternDirection = PatternDirection.NEUTRAL
    rsi: float = 50.0
    scan_timestamp: str = ""

    class Config:
        use_enum_values = True


class SupportResistanceLevels(BaseModel):
    """Key price levels for a stock."""
    symbol: str
    current_price: float
    support_zones: List[float] = Field(default_factory=list)
    resistance_zones: List[float] = Field(default_factory=list)
    pivot_point: float = 0.0
    pivot_r1: float = 0.0
    pivot_r2: float = 0.0
    pivot_s1: float = 0.0
    pivot_s2: float = 0.0
    trend_direction: PatternDirection = PatternDirection.NEUTRAL
    week_52_high: float = 0.0
    week_52_low: float = 0.0


class OHLCVData(BaseModel):
    """OHLCV candlestick data for chart rendering."""
    symbol: str
    period: str
    interval: str
    data: List[Dict] = Field(default_factory=list)  # [{date, open, high, low, close, volume}]
    current_price: float = 0.0
    total_candles: int = 0
