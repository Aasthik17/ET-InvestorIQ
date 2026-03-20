"""
ET InvestorIQ — Chart Pattern Service
Business logic for chart pattern scanning and analysis.
"""

import asyncio
import logging
from datetime import datetime
from typing import List, Optional

from app.modules.chart_pattern.pattern_detector import detect_patterns
from app.modules.chart_pattern.schemas import (
    DetectedPattern, OHLCVData, PatternDirection,
    PatternScanResult, SupportResistanceLevels
)
from app.services import claude_service, data_service
from app.services.cache_service import cache

logger = logging.getLogger(__name__)

COMPANY_NAMES = {
    "RELIANCE.NS": "Reliance Industries", "TCS.NS": "Tata Consultancy Services",
    "HDFCBANK.NS": "HDFC Bank", "INFY.NS": "Infosys", "ICICIBANK.NS": "ICICI Bank",
    "KOTAKBANK.NS": "Kotak Mahindra Bank", "LT.NS": "Larsen & Toubro",
    "AXISBANK.NS": "Axis Bank", "BHARTIARTL.NS": "Bharti Airtel", "ITC.NS": "ITC Ltd",
    "SBIN.NS": "State Bank of India", "HINDUNILVR.NS": "Hindustan Unilever",
    "BAJFINANCE.NS": "Bajaj Finance", "WIPRO.NS": "Wipro", "TITAN.NS": "Titan Company",
    "MARUTI.NS": "Maruti Suzuki", "SUNPHARMA.NS": "Sun Pharma", "TATAMOTORS.NS": "Tata Motors",
    "ADANIENT.NS": "Adani Enterprises", "TATASTEEL.NS": "Tata Steel",
}


async def scan_stock(symbol: str, period: str = "1y") -> PatternScanResult:
    """
    Scan a single stock for all detectable chart patterns.

    Args:
        symbol: Yahoo Finance ticker (e.g., 'RELIANCE.NS').
        period: Historical data period for analysis.

    Returns:
        PatternScanResult with all detected patterns.
    """
    cache_key = f"pattern_scan:{symbol}"
    cached = cache.get(cache_key)
    if cached:
        return PatternScanResult(**cached)

    try:
        df = await data_service.get_stock_data(symbol, period=period)
        if df is None or df.empty:
            return PatternScanResult(symbol=symbol, scan_timestamp=datetime.now().isoformat())

        patterns = detect_patterns(df, symbol)

        current_price = float(df["Close"].iloc[-1])
        prev_price = float(df["Close"].iloc[-2]) if len(df) > 1 else current_price
        pct_change = round(((current_price - prev_price) / prev_price) * 100, 2)

        avg_vol = float(df["Volume"].rolling(20).mean().iloc[-1])
        today_vol = float(df["Volume"].iloc[-1])
        vol_ratio = round(today_vol / avg_vol, 2) if avg_vol > 0 else 1.0

        # Overall bias: count bullish vs bearish patterns
        bullish = sum(1 for p in patterns if p.direction == "BULLISH")
        bearish = sum(1 for p in patterns if p.direction == "BEARISH")
        bias = PatternDirection.NEUTRAL
        if bullish > bearish:
            bias = PatternDirection.BULLISH
        elif bearish > bullish:
            bias = PatternDirection.BEARISH

        # Get RSI if available
        rsi = 50.0
        if len(df) >= 14:
            try:
                import ta
                rsi_indicator = ta.momentum.RSIIndicator(close=df["Close"], window=14)
                rsi_series = rsi_indicator.rsi()
                rsi = round(float(rsi_series.iloc[-1]), 1)
            except Exception:
                pass

        result = PatternScanResult(
            symbol=symbol,
            company_name=COMPANY_NAMES.get(symbol, symbol.replace(".NS", "")),
            patterns=patterns,
            current_price=round(current_price, 2),
            price_change_1d_pct=pct_change,
            volume_ratio=vol_ratio,
            overall_bias=bias,
            rsi=rsi,
            scan_timestamp=datetime.now().isoformat(),
        )

        if patterns:
            cache.set(cache_key, result.model_dump(), ttl_seconds=900)  # 15 min cache

        return result
    except Exception as e:
        logger.error(f"Pattern scan failed for {symbol}: {e}")
        return PatternScanResult(symbol=symbol, scan_timestamp=datetime.now().isoformat())


async def scan_universe(symbols: Optional[List[str]] = None) -> List[PatternScanResult]:
    """
    Scan NSE Top 50 stocks for patterns — returns only stocks with patterns detected.

    Args:
        symbols: Optional list of symbols. Defaults to NSE Top 50.

    Returns:
        List of PatternScanResults with at least one pattern, sorted by confidence.
    """
    from app.config import settings
    if not symbols:
        symbols = settings.nse_top_50[:30]  # Scan top 30 for performance

    # Scan in batches of 5 to avoid overwhelming yfinance
    results = []
    batch_size = 5
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i + batch_size]
        batch_results = await asyncio.gather(
            *[scan_stock(sym) for sym in batch],
            return_exceptions=True,
        )
        for r in batch_results:
            if isinstance(r, PatternScanResult) and r.patterns:
                results.append(r)

    # Sort by average pattern confidence
    results.sort(
        key=lambda r: max((p.confidence for p in r.patterns), default=0),
        reverse=True
    )
    return results


async def get_pattern_explanation(pattern: DetectedPattern) -> str:
    """
    Get Claude-generated plain-English explanation for a pattern.

    Args:
        pattern: DetectedPattern object.

    Returns:
        Plain-English explanation string.
    """
    return await claude_service.explain_pattern(
        pattern_name=str(pattern.pattern_type),
        stock=pattern.symbol,
        pattern_data={
            "detected_at": pattern.detected_at,
            "confidence": pattern.confidence,
            "direction": pattern.direction,
            "key_levels": pattern.key_levels,
            "indicators": pattern.indicators,
        },
        backtest_stats=pattern.backtest_stats,
    )


async def get_support_resistance(symbol: str) -> SupportResistanceLevels:
    """
    Calculate key support and resistance levels for a stock.

    Args:
        symbol: Yahoo Finance ticker symbol.

    Returns:
        SupportResistanceLevels with zones, pivot points, and 52-week range.
    """
    try:
        df = await data_service.get_stock_data(symbol, period="6mo")
        if df is None or df.empty:
            raise ValueError("No data")

        current = float(df["Close"].iloc[-1])
        high = df["High"]
        low = df["Low"]
        close = df["Close"]

        # 52-week levels
        w52_high = float(df["High"].rolling(252).max().iloc[-1] if len(df) >= 252
                        else high.max())
        w52_low = float(df["Low"].rolling(252).min().iloc[-1] if len(df) >= 252
                       else low.min())

        # Pivot points (previous month high/low/close)
        prev_h = float(high.iloc[-22:].max())
        prev_l = float(low.iloc[-22:].min())
        prev_c = float(close.iloc[-22:].mean())
        pivot = (prev_h + prev_l + prev_c) / 3

        # Support zones: swing lows from 6 months
        n = len(close)
        swing_lows = []
        swing_highs = []
        for i in range(3, n - 3):
            if low.iloc[i] == low.iloc[i-3:i+4].min():
                swing_lows.append(float(low.iloc[i]))
            if high.iloc[i] == high.iloc[i-3:i+4].max():
                swing_highs.append(float(high.iloc[i]))

        # Cluster nearby levels (within 1%)
        import numpy as np

        def cluster_levels(levels, threshold=0.01):
            if not levels:
                return []
            levels = sorted(set(round(l, 0) for l in levels))
            clusters = []
            for level in levels:
                if not clusters or abs(level - clusters[-1]) / clusters[-1] > threshold:
                    clusters.append(level)
            return clusters[:4]

        support_zones = cluster_levels([l for l in swing_lows if l < current])
        resistance_zones = cluster_levels([h for h in swing_highs if h > current])

        return SupportResistanceLevels(
            symbol=symbol,
            current_price=round(current, 2),
            support_zones=[round(s, 2) for s in support_zones[-3:]],
            resistance_zones=[round(r, 2) for r in resistance_zones[:3]],
            pivot_point=round(pivot, 2),
            pivot_r1=round(2 * pivot - prev_l, 2),
            pivot_r2=round(pivot + (prev_h - prev_l), 2),
            pivot_s1=round(2 * pivot - prev_h, 2),
            pivot_s2=round(pivot - (prev_h - prev_l), 2),
            week_52_high=round(w52_high, 2),
            week_52_low=round(w52_low, 2),
        )
    except Exception as e:
        logger.error(f"Support/resistance calc failed for {symbol}: {e}")
        fund = await data_service.get_fundamentals(symbol)
        cp = fund.get("current_price", 1000)
        return SupportResistanceLevels(
            symbol=symbol, current_price=cp,
            support_zones=[round(cp * 0.92, 2), round(cp * 0.85, 2)],
            resistance_zones=[round(cp * 1.08, 2), round(cp * 1.15, 2)],
            week_52_high=fund.get("52w_high", cp * 1.25),
            week_52_low=fund.get("52w_low", cp * 0.78),
        )


async def get_ohlcv(symbol: str, period: str = "1y", interval: str = "1d") -> OHLCVData:
    """
    Fetch OHLCV data formatted for frontend chart rendering.

    Args:
        symbol: Yahoo Finance ticker.
        period: Data period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y).
        interval: Data interval (1d, 1wk, 1mo).

    Returns:
        OHLCVData with list of candle dicts.
    """
    try:
        if interval != "1d":
            # For non-daily, try direct yfinance download
            import yfinance as yf
            import asyncio
            loop = asyncio.get_event_loop()
            df = await loop.run_in_executor(
                None, lambda: yf.download(symbol, period=period, interval=interval, progress=False)
            )
        else:
            df = await data_service.get_stock_data(symbol, period=period)

        if df is None or df.empty:
            raise ValueError("No data")

        candles = []
        for idx, row in df.iterrows():
            date_str = idx.strftime("%Y-%m-%d") if hasattr(idx, "strftime") else str(idx)[:10]
            candles.append({
                "date": date_str,
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"]),
            })

        return OHLCVData(
            symbol=symbol,
            period=period,
            interval=interval,
            data=candles,
            current_price=round(float(df["Close"].iloc[-1]), 2),
            total_candles=len(candles),
        )
    except Exception as e:
        logger.error(f"OHLCV fetch failed for {symbol}: {e}")
        # Return mock OHLCV
        from app.demo_data import _ohlcv_series
        days_map = {"1mo": 22, "3mo": 66, "6mo": 132, "1y": 252, "2y": 504, "5y": 1260}
        mock_data = _ohlcv_series(start_price=1000.0, days=days_map.get(period, 252))
        candles = []
        for row in mock_data:
            candles.append({
                "date": row["date"],
                "open": row["open"],
                "high": row["high"],
                "low": row["low"],
                "close": row["close"],
                "volume": row["volume"],
            })
        return OHLCVData(
            symbol=symbol, period=period, interval=interval,
            data=candles, current_price=round(float(mock_df["Close"].iloc[-1]), 2),
            total_candles=len(candles),
        )
