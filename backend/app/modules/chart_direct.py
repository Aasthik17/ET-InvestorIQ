"""
chart_direct.py — Standalone yfinance endpoint for Chart Intelligence.
No mock mode. No cache. No dependencies on other app modules.
If data cannot be fetched, returns an error — never fake data.
"""

import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# yfinance period strings accepted by this endpoint
VALID_PERIODS = {"1d","5d","1mo","3mo","6mo","1y","2y","5y"}

# Mapping from clean symbol to Yahoo Finance ticker
def to_yf_ticker(symbol: str) -> str:
    """Convert NSE symbol to Yahoo Finance format."""
    # A few symbols have different Yahoo tickers
    special = {
        "M&M":        "M&M.NS",
        "L&TFH":      "L&TFH.NS",
        "BAJAJ-AUTO": "BAJAJ-AUTO.NS",
    }
    s = symbol.upper().strip()
    return special.get(s, f"{s}.NS")


@router.get("/api/chart-data/{symbol}")
async def get_chart_data(symbol: str, period: str = "1y"):
    """
    Fetch real EOD OHLCV data for an NSE stock using yfinance.
    Returns actual data or a clear error — never mock/fallback data.

    symbol: NSE symbol without .NS suffix (e.g. RELIANCE, TCS)
    period: 1mo | 3mo | 6mo | 1y | 2y | 5y
    """
    if period not in VALID_PERIODS:
        raise HTTPException(status_code=400,
            detail=f"Invalid period '{period}'. Use one of: {VALID_PERIODS}")

    ticker_symbol = to_yf_ticker(symbol)
    logger.info(f"Fetching {ticker_symbol} period={period}")

    # 1. Import yfinance
    try:
        import yfinance as yf
    except ImportError:
        raise HTTPException(status_code=500,
            detail="yfinance not installed. Run: pip install yfinance")

    # 2. Fetch historical data
    try:
        ticker = yf.Ticker(ticker_symbol)
        hist   = ticker.history(
            period=period,
            interval="1d",
            auto_adjust=True,
            prepost=False,
            timeout=20,
        )
    except Exception as e:
        logger.error(f"yfinance fetch failed for {ticker_symbol}: {e}")
        raise HTTPException(status_code=502,
            detail=f"yfinance fetch failed: {str(e)}. "
                   f"Check internet connection and that '{ticker_symbol}' is valid.")

    # 3. Validate result
    if hist is None or hist.empty:
        raise HTTPException(status_code=404,
            detail=f"No data returned for '{ticker_symbol}'. "
                   f"Possible reasons: invalid symbol, market holiday, "
                   f"or Yahoo Finance is temporarily unavailable.")

    if len(hist) < 2:
        raise HTTPException(status_code=404,
            detail=f"Insufficient data for '{ticker_symbol}': "
                   f"only {len(hist)} rows returned.")

    # 4. Convert to JSON-serialisable list
    ohlcv = []
    for dt, row in hist.iterrows():
        try:
            ohlcv.append({
                "date":   dt.strftime("%Y-%m-%d"),
                "open":   round(float(row["Open"]),   2),
                "high":   round(float(row["High"]),   2),
                "low":    round(float(row["Low"]),    2),
                "close":  round(float(row["Close"]),  2),
                "volume": int(row["Volume"]),
            })
        except Exception:
            continue

    if not ohlcv:
        raise HTTPException(status_code=500,
            detail="Data conversion failed — all rows were malformed.")

    # 5. Compute last-day quote
    last = ohlcv[-1]
    prev = ohlcv[-2]
    change     = round(last["close"] - prev["close"], 2)
    change_pct = round((change / prev["close"]) * 100, 2)

    # 6. Fetch fundamentals (best-effort, never raises)
    fundamentals = {}
    try:
        info = ticker.info or {}
        fundamentals = {
            "company_name":  info.get("longName", symbol),
            "sector":        info.get("sector", ""),
            "market_cap_cr": round(info.get("marketCap", 0) / 1e7, 2),
            "pe_ratio":      info.get("trailingPE"),
            "pb_ratio":      info.get("priceToBook"),
            "52w_high":      info.get("fiftyTwoWeekHigh"),
            "52w_low":       info.get("fiftyTwoWeekLow"),
            "avg_volume":    info.get("averageVolume"),
            "dividend_yield": round((info.get("dividendYield") or 0) * 100, 2),
            "beta":          info.get("beta"),
        }
    except Exception as e:
        logger.warning(f"Fundamentals fetch failed for {symbol}: {e}")
        fundamentals = {"company_name": symbol}

    # 7. Return
    return JSONResponse(content={
        "symbol":       symbol.upper(),
        "ticker":       ticker_symbol,
        "period":       period,
        "data_points":  len(ohlcv),
        "ohlcv":        ohlcv,
        "quote": {
            "ltp":        last["close"],
            "open":       last["open"],
            "high":       last["high"],
            "low":        last["low"],
            "close":      last["close"],
            "volume":     last["volume"],
            "change":     change,
            "change_pct": change_pct,
            "prev_close": prev["close"],
        },
        "fundamentals":  fundamentals,
        "fetched_at":    datetime.utcnow().isoformat() + "Z",
        "data_source":   "Yahoo Finance via yfinance",
    })
