"""
ET InvestorIQ — Data Service
Central data access layer. All market data fetches go through here.
Sources: NSE Unofficial API (nse_session.py), yfinance, BSE India API
Important: cache_service.get/set are SYNCHRONOUS — do not await them.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

import pytz

logger = logging.getLogger(__name__)
IST = pytz.timezone("Asia/Kolkata")


def _get_settings():
    from app.config import settings
    return settings


def _get_mock_mode():
    return _get_settings().mock_mode


# ─────────────────────────────────────────────────────────────────────────────
# MARKET STATUS
# ─────────────────────────────────────────────────────────────────────────────

def is_market_open() -> bool:
    """NSE is open Mon–Fri 9:15 AM – 3:30 PM IST excluding holidays."""
    now = datetime.now(IST)
    if now.weekday() >= 5:
        return False
    market_open  = now.replace(hour=9,  minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return market_open <= now <= market_close


async def get_market_status() -> dict:
    """Return NSE market open/close status."""
    from app.services.nse_session import nse

    if not _get_mock_mode():
        try:
            data = await nse.get("market_status")
            if data:
                state = data.get("marketState", [{}])[0]
                return {
                    "is_open": state.get("marketStatus") == "Open",
                    "status_text": state.get("marketStatus", "Unknown"),
                    "as_of": datetime.now(IST).isoformat(),
                }
        except Exception as e:
            logger.warning(f"NSE market status failed: {e}")

    open_now = is_market_open()
    return {
        "is_open":     open_now,
        "status_text": "Open" if open_now else "Closed",
        "as_of":       datetime.now(IST).isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# INDEX QUOTES
# ─────────────────────────────────────────────────────────────────────────────

async def get_index_quotes() -> dict:
    """
    Fetch live Nifty 50, Sensex, Bank Nifty, India VIX values with sparklines.
    Cache: 30 seconds.
    """
    from app.services.cache_service import cache
    from app.demo_data import MOCK_DATA

    cached = cache.get("index_quotes")
    if cached:
        return cached

    result = {}

    if not _get_mock_mode():
        from app.services.nse_session import nse

        # Nifty 50
        try:
            nifty_data = await nse.get("nifty50")
            for item in nifty_data.get("data", []):
                if item.get("index") == "NIFTY 50":
                    result["nifty50"] = {
                        "name":       "NIFTY 50",
                        "value":      float(item.get("last", 0)),
                        "change":     float(item.get("variation", 0)),
                        "change_pct": float(item.get("percentChange", 0)),
                        "high":       float(item.get("high", 0)),
                        "low":        float(item.get("low", 0)),
                        "sparkline":  [],
                    }
                    break
        except Exception as e:
            logger.warning(f"NSE Nifty50 failed: {e}")

        # Bank Nifty
        try:
            bnk_data = await nse.get("banknifty")
            for item in bnk_data.get("data", []):
                if item.get("index") == "NIFTY BANK":
                    result["banknifty"] = {
                        "name":       "BANK NIFTY",
                        "value":      float(item.get("last", 0)),
                        "change":     float(item.get("variation", 0)),
                        "change_pct": float(item.get("percentChange", 0)),
                        "high":       float(item.get("high", 0)),
                        "low":        float(item.get("low", 0)),
                        "sparkline":  [],
                    }
                    break
        except Exception as e:
            logger.warning(f"NSE BankNifty failed: {e}")

        # Sensex + VIX via yfinance
        try:
            import yfinance as yf
            loop = asyncio.get_event_loop()
            hist = await loop.run_in_executor(
                None,
                lambda: yf.download(
                    ["^BSESN", "^INDIAVIX", "^NSEI", "^NSEBANK"],
                    period="5d", interval="1d",
                    progress=False, threads=False,
                    group_by="ticker",
                )
            )
            if not hist.empty:
                def _extract(sym, name, disp_name):
                    try:
                        closes = hist[sym]["Close"].dropna()
                        if len(closes) < 2:
                            return None
                        curr = float(closes.iloc[-1])
                        prev = float(closes.iloc[-2])
                        chg  = curr - prev
                        return {
                            "name":       disp_name,
                            "value":      round(curr, 2),
                            "change":     round(chg, 2),
                            "change_pct": round((chg / prev) * 100, 2) if prev else 0,
                            "high":       float(hist[sym]["High"].iloc[-1]),
                            "low":        float(hist[sym]["Low"].iloc[-1]),
                            "sparkline":  [],
                        }
                    except Exception:
                        return None

                if "sensex" not in result:
                    s = _extract("^BSESN", "^BSESN", "SENSEX")
                    if s:
                        result["sensex"] = s
                if "vix" not in result:
                    v = _extract("^INDIAVIX", "^INDIAVIX", "INDIA VIX")
                    if v:
                        result["vix"] = v
                if "nifty50" not in result:
                    n = _extract("^NSEI", "^NSEI", "NIFTY 50")
                    if n:
                        result["nifty50"] = n
                if "banknifty" not in result:
                    b = _extract("^NSEBANK", "^NSEBANK", "BANK NIFTY")
                    if b:
                        result["banknifty"] = b
        except Exception as e:
            logger.warning(f"yfinance index fetch failed: {e}")

        # Add sparklines
        try:
            result = await _add_sparklines(result)
        except Exception as e:
            logger.warning(f"Sparkline generation failed: {e}")

    # Fill missing with mock
    mock = MOCK_DATA["index_quotes"]
    for k in ["nifty50", "sensex", "banknifty", "vix"]:
        if k not in result:
            result[k] = mock[k]

    cache.set("index_quotes", result, ttl_seconds=30)
    return result


async def _add_sparklines(indices: dict) -> dict:
    """Add 20-point intraday sparkline arrays (% change from open)."""
    import yfinance as yf

    symbol_map = {
        "nifty50":   "^NSEI",
        "sensex":    "^BSESN",
        "banknifty": "^NSEBANK",
        "vix":       "^INDIAVIX",
    }
    loop = asyncio.get_event_loop()

    for key, yf_sym in symbol_map.items():
        if key not in indices:
            continue
        try:
            hist = await loop.run_in_executor(
                None,
                lambda s=yf_sym: yf.Ticker(s).history(period="1d", interval="5m")
            )
            if not hist.empty:
                closes = hist["Close"].dropna().tolist()
                if closes:
                    base = closes[0] or 1
                    sparkline = [round(((c - base) / base) * 100, 3) for c in closes[-20:]]
                    indices[key]["sparkline"] = sparkline
        except Exception:
            indices[key]["sparkline"] = []

    return indices


# ─────────────────────────────────────────────────────────────────────────────
# SINGLE STOCK QUOTE
# ─────────────────────────────────────────────────────────────────────────────

async def get_stock_quote(symbol: str) -> dict:
    """
    Fetch live quote for a single NSE stock (symbol WITHOUT .NS suffix).
    Cache: 10 seconds.
    """
    from app.services.cache_service import cache
    from app.demo_data import MOCK_DATA

    cache_key = f"quote:{symbol}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    if not _get_mock_mode():
        from app.services.nse_session import nse

        # Try NSE API first
        try:
            data = await nse.get("quote", symbol=symbol)
            if data:
                price_info = data.get("priceInfo", {})
                meta       = data.get("metadata", {})
                quote = {
                    "symbol":       symbol,
                    "company_name": meta.get("companyName", symbol),
                    "ltp":          float(price_info.get("lastPrice", 0)),
                    "open":         float(price_info.get("open", 0)),
                    "high":         float(price_info.get("intraDayHighLow", {}).get("max", 0)),
                    "low":          float(price_info.get("intraDayHighLow", {}).get("min", 0)),
                    "prev_close":   float(price_info.get("previousClose", 0)),
                    "change":       float(price_info.get("change", 0)),
                    "change_pct":   float(price_info.get("pChange", 0)),
                    "volume":       int(data.get("marketDeptOrderBook", {}).get("tradeInfo", {}).get("totalTradedVolume", 0)),
                    "52w_high":     float(price_info.get("weekHighLow", {}).get("max", 0)),
                    "52w_low":      float(price_info.get("weekHighLow", {}).get("min", 0)),
                    "timestamp":    datetime.now(IST).isoformat(),
                }
                cache.set(cache_key, quote, ttl_seconds=10)
                return quote
        except Exception as e:
            logger.warning(f"NSE quote for {symbol} failed: {e}")

        # Fallback: yfinance
        try:
            import yfinance as yf
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None, lambda: yf.Ticker(f"{symbol}.NS").fast_info
            )
            ltp  = float(info.last_price or 0)
            prev = float(info.previous_close or ltp)
            quote = {
                "symbol":       symbol,
                "company_name": symbol,
                "ltp":          round(ltp, 2),
                "change":       round(ltp - prev, 2),
                "change_pct":   round(((ltp - prev) / prev) * 100, 2) if prev else 0,
                "52w_high":     float(info.year_high or 0),
                "52w_low":      float(info.year_low  or 0),
                "market_cap":   int(info.market_cap or 0),
                "timestamp":    datetime.now(IST).isoformat(),
            }
            cache.set(cache_key, quote, ttl_seconds=15)
            return quote
        except Exception as e:
            logger.warning(f"yfinance quote for {symbol} failed: {e}")

    # Final fallback: mock
    mock = MOCK_DATA["stock_quotes"].get(symbol, MOCK_DATA["stock_quotes"]["RELIANCE"])
    mock = dict(mock)
    mock["symbol"] = symbol
    return mock


# ─────────────────────────────────────────────────────────────────────────────
# MULTIPLE STOCK QUOTES (batch)
# ─────────────────────────────────────────────────────────────────────────────

async def get_multiple_quotes(symbols: list) -> list:
    """Batch-fetch quotes for multiple symbols using yfinance download."""
    from app.services.cache_service import cache
    from app.demo_data import MOCK_DATA

    key = f"quotes:{'_'.join(sorted(s.upper() for s in symbols[:10]))}"
    cached = cache.get(key)
    if cached:
        return cached

    results = []

    if not _get_mock_mode():
        try:
            import yfinance as yf
            yf_symbols = [f"{s.upper()}.NS" for s in symbols]
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None,
                lambda: yf.download(
                    yf_symbols, period="2d", interval="1d",
                    progress=False, threads=False, group_by="ticker",
                )
            )
            for sym in symbols:
                yf_sym = f"{sym.upper()}.NS"
                try:
                    closes = data[yf_sym]["Close"].dropna()
                    if len(closes) >= 2:
                        curr = float(closes.iloc[-1])
                        prev = float(closes.iloc[-2])
                        chg  = curr - prev
                        results.append({
                            "symbol":     sym.upper(),
                            "ltp":        round(curr, 2),
                            "change":     round(chg, 2),
                            "change_pct": round((chg / prev) * 100, 2) if prev else 0,
                            "volume":     int(data[yf_sym]["Volume"].iloc[-1]),
                            "high":       float(data[yf_sym]["High"].iloc[-1]),
                            "low":        float(data[yf_sym]["Low"].iloc[-1]),
                            "timestamp":  datetime.now(IST).isoformat(),
                        })
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Batch quotes failed: {e}")

    if not results:
        results = MOCK_DATA["multiple_quotes"]

    cache.set(key, results, ttl_seconds=30)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# TOP GAINERS / LOSERS
# ─────────────────────────────────────────────────────────────────────────────

async def get_top_movers() -> dict:
    """Fetch top 10 gainers and losers from NSE. Cache: 60s."""
    from app.services.cache_service import cache
    from app.demo_data import MOCK_DATA

    cached = cache.get("top_movers")
    if cached:
        return cached

    gainers, losers = [], []

    if not _get_mock_mode():
        from app.services.nse_session import nse
        try:
            g_data = await nse.get("top_gainers")
            for item in g_data.get("data", [])[:10]:
                gainers.append({
                    "symbol":     item.get("symbol", ""),
                    "company":    item.get("companyName", item.get("symbol", "")),
                    "ltp":        float(item.get("ltp", 0)),
                    "change_pct": float(item.get("netPrice", 0)),
                    "volume":     int(item.get("tradedQuantity", 0)),
                })
        except Exception as e:
            logger.warning(f"NSE top gainers failed: {e}")

        try:
            l_data = await nse.get("top_losers")
            for item in l_data.get("data", [])[:10]:
                losers.append({
                    "symbol":     item.get("symbol", ""),
                    "company":    item.get("companyName", item.get("symbol", "")),
                    "ltp":        float(item.get("ltp", 0)),
                    "change_pct": float(item.get("netPrice", 0)),
                    "volume":     int(item.get("tradedQuantity", 0)),
                })
        except Exception as e:
            logger.warning(f"NSE top losers failed: {e}")

    if not gainers:
        gainers = MOCK_DATA["top_movers"]["gainers"]
    if not losers:
        losers  = MOCK_DATA["top_movers"]["losers"]

    result = {"gainers": gainers, "losers": losers}
    cache.set("top_movers", result, ttl_seconds=60)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# FII / DII DATA
# ─────────────────────────────────────────────────────────────────────────────

async def get_fii_dii_data(days: int = 30) -> list:
    """
    Fetch FII/DII net buy-sell data (₹ Crore) from NSE.
    Cache: 1 hour.
    """
    from app.services.cache_service import cache
    from app.demo_data import MOCK_DATA

    cache_key = f"fii_dii:{days}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    if not _get_mock_mode():
        from app.services.nse_session import nse
        try:
            data = await nse.get("fii_dii")
            if data:
                rows = []
                for item in data[:days]:
                    fii_buy  = float(item.get("buyValue",  0) or 0)
                    fii_sell = float(item.get("sellValue", 0) or 0)
                    # DII fields vary by NSE API version
                    dii_buy  = float(item.get("dii_buy",   item.get("buyValue2",  0)) or 0)
                    dii_sell = float(item.get("dii_sell",  item.get("sellValue2", 0)) or 0)
                    rows.append({
                        "date":     item.get("date", ""),
                        "fii_buy":  fii_buy,
                        "fii_sell": fii_sell,
                        "fii_net":  round(fii_buy - fii_sell, 2),
                        "dii_buy":  dii_buy,
                        "dii_sell": dii_sell,
                        "dii_net":  round(dii_buy - dii_sell, 2),
                    })
                if rows:
                    cache.set(cache_key, rows, ttl_seconds=3600)
                    return rows
        except Exception as e:
            logger.warning(f"NSE FII/DII failed: {e}")

    result = MOCK_DATA["fii_dii_data"][:days]
    cache.set(cache_key, result, ttl_seconds=3600)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# BULK AND BLOCK DEALS
# ─────────────────────────────────────────────────────────────────────────────

async def get_bulk_block_deals(days_back: int = 7) -> dict:
    """
    Fetch bulk and block deals from NSE.
    Cache: 30 minutes.
    """
    from app.services.cache_service import cache
    from app.demo_data import MOCK_DATA

    cache_key = f"deals:{days_back}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    to_date   = datetime.now(IST).strftime("%d-%m-%Y")
    from_date = (datetime.now(IST) - timedelta(days=days_back)).strftime("%d-%m-%Y")
    bulk_deals, block_deals = [], []

    if not _get_mock_mode():
        from app.services.nse_session import nse
        try:
            data = await nse.get("bulk_deals", from_date=from_date, to_date=to_date)
            for item in data.get("data", []):
                qty   = float(item.get("quantity", 0) or 0)
                price = float(item.get("tradePrice", item.get("avg_price", 0)) or 0)
                bulk_deals.append({
                    "symbol":      item.get("symbol", ""),
                    "client_name": item.get("clientName", item.get("client", "")),
                    "buy_sell":    item.get("buySell", "BUY"),
                    "quantity":    int(qty),
                    "price":       price,
                    "value_cr":    round((qty * price) / 1e7, 2),
                    "date":        item.get("tradeDate", item.get("date", "")),
                    "deal_type":   "BULK",
                })
        except Exception as e:
            logger.warning(f"NSE bulk deals failed: {e}")

        try:
            data = await nse.get("block_deals", from_date=from_date, to_date=to_date)
            for item in data.get("data", []):
                qty   = float(item.get("quantity", 0) or 0)
                price = float(item.get("tradePrice", item.get("avg_price", 0)) or 0)
                block_deals.append({
                    "symbol":      item.get("symbol", ""),
                    "client_name": item.get("clientName", item.get("client", "")),
                    "buy_sell":    item.get("buySell", "BUY"),
                    "quantity":    int(qty),
                    "price":       price,
                    "value_cr":    round((qty * price) / 1e7, 2),
                    "date":        item.get("tradeDate", item.get("date", "")),
                    "deal_type":   "BLOCK",
                })
        except Exception as e:
            logger.warning(f"NSE block deals failed: {e}")

    if not bulk_deals:
        bulk_deals  = MOCK_DATA["bulk_deals"]
    if not block_deals:
        block_deals = MOCK_DATA["block_deals"]

    result = {"bulk": bulk_deals, "block": block_deals}
    cache.set(cache_key, result, ttl_seconds=1800)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# INSIDER TRADES
# ─────────────────────────────────────────────────────────────────────────────

async def get_insider_trades(days_back: int = 14) -> list:
    """
    Fetch SEBI insider trading disclosures from NSE.
    Cache: 30 minutes.
    """
    from app.services.cache_service import cache
    from app.demo_data import MOCK_DATA

    cache_key = f"insider:{days_back}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    to_date   = datetime.now(IST).strftime("%d-%m-%Y")
    from_date = (datetime.now(IST) - timedelta(days=days_back)).strftime("%d-%m-%Y")
    trades = []

    if not _get_mock_mode():
        from app.services.nse_session import nse
        try:
            data = await nse.get("insider_trades", from_date=from_date, to_date=to_date)
            for item in data.get("data", []):
                qty   = float(item.get("secAcq", item.get("noSecuritiesBought", 0)) or 0)
                price = float(item.get("secVal", item.get("price", 0)) or 0)
                value_cr = round((qty * price) / 1e7, 2) if price > 0 else round(
                    float(item.get("value", 0) or 0) / 1e7, 2
                )
                trades.append({
                    "symbol":            item.get("symbol", ""),
                    "person_name":       item.get("acqName", item.get("name", "")),
                    "category":          item.get("personCategory", "Promoter"),
                    "trade_type":        "BUY" if float(item.get("secAcq", 0) or 0) > 0 else "SELL",
                    "quantity":          int(qty),
                    "value_cr":          value_cr,
                    "date":              item.get("date", item.get("acqfromDt", "")),
                    "pre_holding_pct":   float(item.get("befAcqSharesPerc", 0) or 0),
                    "post_holding_pct":  float(item.get("afterAcqSharesPerc", 0) or 0),
                    "mode":              item.get("modeOfAcq", "Market Purchase"),
                })
            if trades:
                cache.set(cache_key, trades, ttl_seconds=1800)
                return trades
        except Exception as e:
            logger.warning(f"NSE insider trades failed: {e}")

    result = MOCK_DATA["insider_trades"]
    cache.set(cache_key, result, ttl_seconds=1800)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# CORPORATE FILINGS  (BSE India primary source)
# ─────────────────────────────────────────────────────────────────────────────

async def get_corporate_filings(days_back: int = 3, symbol: Optional[str] = None) -> list:
    """
    Fetch recent corporate filings/announcements from BSE India API.
    Cache: 15 minutes.
    """
    from app.services.cache_service import cache
    from app.demo_data import MOCK_DATA

    cache_key = f"filings:{days_back}:{symbol or 'all'}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    filings = []

    if not _get_mock_mode():
        try:
            import httpx
            to_date   = datetime.now(IST).strftime("%Y%m%d")
            from_date = (datetime.now(IST) - timedelta(days=days_back)).strftime("%Y%m%d")
            url = (
                f"https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w"
                f"?strCat=-1&strPrevDate={from_date}&strScrip=&strSearch=P"
                f"&strToDate={to_date}&strType=C&subcategory=-1"
            )
            async with httpx.AsyncClient(
                headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.bseindia.com"},
                timeout=15.0,
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
            await asyncio.sleep(3)  # BSE rate limit

            for item in data.get("Table", [])[:60]:
                f = {
                    "symbol":   item.get("SCRIP_CD", ""),
                    "company":  item.get("SLONGNAME", ""),
                    "subject":  item.get("NEWSSUB", ""),
                    "category": item.get("CATEGORYNAME", ""),
                    "date":     item.get("NEWS_DT", ""),
                    "headline": item.get("HEADLINE", item.get("NEWSSUB", "")),
                }
                if symbol and str(f["symbol"]) != str(symbol):
                    continue
                filings.append(f)

            if filings:
                cache.set(cache_key, filings, ttl_seconds=900)
                return filings
        except Exception as e:
            logger.warning(f"BSE filings failed: {e}")

        # Fallback: NSE announcements
        try:
            from app.services.nse_session import nse
            to_date_nse   = datetime.now(IST).strftime("%d-%m-%Y")
            from_date_nse = (datetime.now(IST) - timedelta(days=days_back)).strftime("%d-%m-%Y")
            data = await nse.get("corporate_filings",
                                  from_date=from_date_nse, to_date=to_date_nse)
            for item in data[:60]:
                f = {
                    "symbol":   item.get("symbol", ""),
                    "company":  item.get("comp", ""),
                    "subject":  item.get("subject", ""),
                    "category": item.get("sub_cat", item.get("category", "")),
                    "date":     item.get("an_dt", ""),
                    "headline": item.get("desc", item.get("subject", "")),
                }
                if symbol and f["symbol"] != symbol:
                    continue
                filings.append(f)
            if filings:
                cache.set(cache_key, filings, ttl_seconds=900)
                return filings
        except Exception as e:
            logger.warning(f"NSE announcements failed: {e}")

    result = MOCK_DATA["corporate_filings"]
    if symbol:
        result = [f for f in result if str(f.get("symbol", "")) == str(symbol)]
    cache.set(cache_key, result, ttl_seconds=900)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# OHLCV HISTORY  (yfinance)
# ─────────────────────────────────────────────────────────────────────────────

async def get_ohlcv(symbol: str, period: str = "1y", interval: str = "1d") -> list:
    """
    Fetch OHLCV data for charting.
    symbol: NSE symbol WITHOUT .NS suffix.
    period: 1mo, 3mo, 6mo, 1y, 2y, 5y  |  interval: 5m, 15m, 1h, 1d, 1wk
    Cache: 1 hour for daily; 60s for intraday.
    """
    from app.services.cache_service import cache
    from app.demo_data import MOCK_DATA

    cache_key = f"ohlcv:{symbol}:{period}:{interval}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    if not _get_mock_mode():
        try:
            import yfinance as yf
            loop = asyncio.get_event_loop()
            hist = await loop.run_in_executor(
                None,
                lambda: yf.Ticker(f"{symbol}.NS").history(
                    period=period.replace("1w", "5d"),
                    interval=interval,
                    auto_adjust=True,
                    prepost=False,
                )
            )
            if not hist.empty:
                rows = []
                for dt, row in hist.iterrows():
                    rows.append({
                        "date":   str(dt)[:19],
                        "open":   round(float(row["Open"]),   2),
                        "high":   round(float(row["High"]),   2),
                        "low":    round(float(row["Low"]),    2),
                        "close":  round(float(row["Close"]),  2),
                        "volume": int(row["Volume"]),
                    })
                ttl = 60 if interval in ("1m", "5m", "15m", "30m") else 3600
                cache.set(cache_key, rows, ttl_seconds=ttl)
                return rows
        except Exception as e:
            logger.warning(f"yfinance OHLCV for {symbol} failed: {e}")

    sym_key = symbol.upper().replace(".NS", "")
    result = MOCK_DATA["ohlcv"].get(sym_key, MOCK_DATA["ohlcv"]["RELIANCE"])
    return result


# ─────────────────────────────────────────────────────────────────────────────
# FUNDAMENTALS
# ─────────────────────────────────────────────────────────────────────────────

async def get_fundamentals(symbol: str) -> dict:
    """
    Fetch company fundamentals via yfinance.
    symbol may include .NS suffix — will be normalised.
    Cache: 1 hour.
    """
    from app.services.cache_service import cache
    from app.demo_data import MOCK_DATA

    sym_clean = symbol.upper().replace(".NS", "")
    cache_key = f"fundamentals:{sym_clean}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    if not _get_mock_mode():
        try:
            import yfinance as yf
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(
                None,
                lambda: yf.Ticker(f"{sym_clean}.NS").info
            )
            result = {
                "symbol":          sym_clean,
                "company_name":    info.get("longName", sym_clean),
                "sector":          info.get("sector", ""),
                "industry":        info.get("industry", ""),
                "market_cap_cr":   round((info.get("marketCap", 0) or 0) / 1e7, 2),
                "current_price":   info.get("currentPrice", info.get("regularMarketPrice", 0)),
                "pe_ratio":        info.get("trailingPE", info.get("forwardPE")),
                "pb_ratio":        info.get("priceToBook"),
                "roe_pct":         round((info.get("returnOnEquity", 0) or 0) * 100, 2),
                "debt_equity":     info.get("debtToEquity"),
                "revenue_growth":  round((info.get("revenueGrowth",  0) or 0) * 100, 2),
                "earnings_growth": round((info.get("earningsGrowth", 0) or 0) * 100, 2),
                "52w_high":        info.get("fiftyTwoWeekHigh", 0),
                "52w_low":         info.get("fiftyTwoWeekLow",  0),
                "avg_volume":      info.get("averageVolume", 0),
                "dividend_yield":  round((info.get("dividendYield", 0) or 0) * 100, 2),
                "beta":            info.get("beta"),
                "description":     (info.get("longBusinessSummary", "") or "")[:300],
            }
            cache.set(cache_key, result, ttl_seconds=3600)
            return result
        except Exception as e:
            logger.warning(f"yfinance fundamentals for {sym_clean} failed: {e}")

    return MOCK_DATA["fundamentals"].get(sym_clean, MOCK_DATA["fundamentals"]["RELIANCE"])


# ─────────────────────────────────────────────────────────────────────────────
# IPO DATA
# ─────────────────────────────────────────────────────────────────────────────

async def get_ipo_data() -> dict:
    """Fetch current, upcoming, and listed IPOs from NSE. Cache: 1 hour."""
    from app.services.cache_service import cache
    from app.demo_data import MOCK_DATA

    cached = cache.get("ipo_data")
    if cached:
        return cached

    result = {"current": [], "upcoming": [], "listed": []}

    if not _get_mock_mode():
        from app.services.nse_session import nse
        for status in ["current", "upcoming", "listed"]:
            try:
                data = await nse.get(f"ipo_{status}")
                ipos = []
                items = data if isinstance(data, list) else data.get("data", [])
                for item in items[:8]:
                    ipos.append({
                        "company":            item.get("companyName", ""),
                        "symbol":             item.get("symbol", ""),
                        "open_date":          item.get("bidStartDt",    item.get("openDate", "")),
                        "close_date":         item.get("bidEndDt",      item.get("closeDate", "")),
                        "issue_price":        item.get("issuePrice",    item.get("cutOffPrice", "")),
                        "lot_size":           item.get("lotSize", 0),
                        "issue_size_cr":      item.get("issueSize", 0),
                        "listing_date":       item.get("listingDate", ""),
                        "listing_price":      item.get("listingPrice", None),
                        "listing_gain_pct":   item.get("listingGain",  None),
                        "subscription_times": item.get("totalSubscriptionTimes", None),
                        "status":             status.upper(),
                    })
                result[status] = ipos
            except Exception as e:
                logger.warning(f"NSE IPO {status} failed: {e}")

    if not any(result.values()):
        result = MOCK_DATA["ipo_data"]

    cache.set("ipo_data", result, ttl_seconds=3600)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# SECTOR PERFORMANCE
# ─────────────────────────────────────────────────────────────────────────────

async def get_sector_performance() -> list:
    """
    Calculate sector returns by averaging representative NSE stocks.
    Cache: 1 hour.
    """
    from app.services.cache_service import cache
    from app.demo_data import MOCK_DATA

    cached = cache.get("sector_performance")
    if cached:
        return cached

    SECTOR_STOCKS = {
        "IT":      ["TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS"],
        "Banking": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "AXISBANK.NS", "KOTAKBANK.NS"],
        "Pharma":  ["SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS", "APOLLOHOSP.NS"],
        "Auto":    ["MARUTI.NS", "TATAMOTORS.NS", "BAJAJ-AUTO.NS", "EICHERMOT.NS", "HEROMOTOCO.NS"],
        "FMCG":    ["HINDUNILVR.NS", "ITC.NS", "NESTLEIND.NS", "BRITANNIA.NS", "DABUR.NS"],
        "Energy":  ["RELIANCE.NS", "ONGC.NS", "BPCL.NS", "IOC.NS", "POWERGRID.NS"],
        "Metals":  ["TATASTEEL.NS", "JSWSTEEL.NS", "HINDALCO.NS", "COALINDIA.NS", "VEDL.NS"],
        "Realty":  ["DLF.NS", "GODREJPROP.NS", "PRESTIGE.NS", "OBEROIRLTY.NS"],
        "Infra":   ["LT.NS", "ADANIPORTS.NS", "ADANIENT.NS", "SIEMENS.NS"],
    }

    if not _get_mock_mode():
        try:
            import yfinance as yf
            all_syms = list({s for stocks in SECTOR_STOCKS.values() for s in stocks})
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(
                None,
                lambda: yf.download(
                    all_syms, period="1mo", interval="1d",
                    progress=False, threads=False, group_by="ticker",
                )
            )
            sectors = []
            for sector, syms in SECTOR_STOCKS.items():
                r1d, r1w, r1m = [], [], []
                for sym in syms:
                    try:
                        closes = data[sym]["Close"].dropna()
                        if len(closes) >= 2:
                            r1d.append((closes.iloc[-1] - closes.iloc[-2]) / closes.iloc[-2] * 100)
                        if len(closes) >= 6:
                            r1w.append((closes.iloc[-1] - closes.iloc[-6]) / closes.iloc[-6] * 100)
                        if len(closes) >= 21:
                            r1m.append((closes.iloc[-1] - closes.iloc[-21]) / closes.iloc[-21] * 100)
                    except Exception:
                        pass
                sectors.append({
                    "sector":        sector,
                    "return_1d_pct": round(sum(r1d) / len(r1d), 2) if r1d else 0,
                    "return_1w_pct": round(sum(r1w) / len(r1w), 2) if r1w else 0,
                    "return_1m_pct": round(sum(r1m) / len(r1m), 2) if r1m else 0,
                    "top_stock":     syms[0].replace(".NS", ""),
                })
            if sectors:
                cache.set("sector_performance", sectors, ttl_seconds=3600)
                return sectors
        except Exception as e:
            logger.warning(f"Sector performance failed: {e}")

    result = MOCK_DATA["sector_performance"]
    cache.set("sector_performance", result, ttl_seconds=3600)
    return result


# ─────────────────────────────────────────────────────────────────────────────
# MARKET OVERVIEW  (aggregated for /api/market/overview)
# ─────────────────────────────────────────────────────────────────────────────

async def get_market_overview() -> dict:
    """
    Aggregated market snapshot — calls all sub-functions, merges results.
    All data is pre-warmed by APScheduler so this is typically cache-only.
    """
    indices, movers, fii_dii, sectors, ipos, status = await asyncio.gather(
        get_index_quotes(),
        get_top_movers(),
        get_fii_dii_data(days=7),
        get_sector_performance(),
        get_ipo_data(),
        get_market_status(),
        return_exceptions=True,
    )

    def safe(val, default):
        return default if isinstance(val, Exception) else val

    indices = safe(indices, {})
    movers  = safe(movers,  {"gainers": [], "losers": []})
    fii_dii = safe(fii_dii, [])
    sectors = safe(sectors, [])
    ipos    = safe(ipos,    {"current": [], "upcoming": [], "listed": []})
    status  = safe(status,  {"is_open": False, "status_text": "Unknown"})

    gainers  = movers.get("gainers", [])
    losers   = movers.get("losers",  [])
    advances = sum(1 for s in gainers if float(s.get("change_pct", 0) or 0) > 0)
    declines = sum(1 for s in losers  if float(s.get("change_pct", 0) or 0) < 0)

    return {
        "indices":            indices,
        "top_gainers":        gainers[:5],
        "top_losers":         losers[:5],
        "fii_dii_7d":         fii_dii,
        "sector_performance": sorted(sectors, key=lambda x: x.get("return_1d_pct", 0), reverse=True),
        "ipo_pipeline": {
            "current":  ipos.get("current",  [])[:3],
            "upcoming": ipos.get("upcoming", [])[:3],
            "listed":   ipos.get("listed",   [])[:5],
        },
        "market_status": status,
        "breadth": {
            "advances":  advances,
            "declines":  declines,
            "unchanged": max(0, 50 - advances - declines),
        },
        "generated_at": datetime.now(IST).isoformat(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# NEWS  (kept for backward compat with existing endpoints)
# ─────────────────────────────────────────────────────────────────────────────

async def get_news(symbol: str) -> list:
    """Fetch recent news for a stock. Falls back to mock headlines."""
    from app.demo_data import MOCK_DATA
    # Try corporate filings
    sym_clean = symbol.upper().replace(".NS", "")
    filings = await get_corporate_filings(days_back=7, symbol=sym_clean)
    if filings:
        return [{"title": f.get("headline", ""), "source": "BSE/NSE", "date": f.get("date", "")} for f in filings[:5]]
    return [
        {"title": f"Latest news for {sym_clean} unavailable in demo mode", "source": "ET Markets", "date": datetime.now(IST).strftime("%Y-%m-%d")},
    ]
