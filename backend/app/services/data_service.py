"""
ET InvestorIQ — Data Service
The primary data fetching layer. All external data calls go through here.
Every function has a realistic mock fallback for demo reliability.

Set MOCK_MODE = True for pure offline operation.
"""

import asyncio
import random
import logging
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# MOCK MODE toggle — flip to True for offline demo
# ─────────────────────────────────────────────────────────────────────────────
MOCK_MODE: bool = settings.mock_mode

# ─────────────────────────────────────────────────────────────────────────────
# Sentiment keywords for news scoring
# ─────────────────────────────────────────────────────────────────────────────
POSITIVE_KEYWORDS = [
    "profit", "growth", "record", "beat", "upgrade", "buy", "positive",
    "strong", "bullish", "expansion", "acquisition", "order", "win",
    "outperform", "surge", "rally", "gain", "increase", "beat estimates",
    "buyback", "bonus", "dividend", "deal", "partnership"
]
NEGATIVE_KEYWORDS = [
    "loss", "decline", "miss", "downgrade", "sell", "negative",
    "bearish", "slowdown", "quarterly loss", "fraud", "probe",
    "underperform", "slump", "fall", "decrease", "miss estimates",
    "penalty", "scam", "default", "impairment", "write-off"
]


def _sentiment_score(text: str) -> str:
    """Simple keyword-based sentiment scorer for news headlines."""
    text_lower = text.lower()
    pos = sum(1 for kw in POSITIVE_KEYWORDS if kw in text_lower)
    neg = sum(1 for kw in NEGATIVE_KEYWORDS if kw in text_lower)
    if pos > neg:
        return "positive"
    elif neg > pos:
        return "negative"
    return "neutral"


# ─────────────────────────────────────────────────────────────────────────────
# MOCK DATA GENERATORS
# ─────────────────────────────────────────────────────────────────────────────

def _mock_ohlcv(symbol: str, days: int = 365) -> pd.DataFrame:
    """Generate realistic mock OHLCV data for an Indian stock."""
    base_prices = {
        "RELIANCE.NS": 2900, "TCS.NS": 4100, "HDFCBANK.NS": 1650,
        "INFY.NS": 1780, "ICICIBANK.NS": 1180, "KOTAKBANK.NS": 1800,
        "LT.NS": 3700, "AXISBANK.NS": 1150, "BHARTIARTL.NS": 1390,
        "ITC.NS": 470, "SBIN.NS": 820, "HINDUNILVR.NS": 2650,
        "BAJFINANCE.NS": 7200, "WIPRO.NS": 540, "ULTRACEMCO.NS": 10500,
        "TITAN.NS": 3600, "NESTLEIND.NS": 24000, "MARUTI.NS": 12800,
        "SUNPHARMA.NS": 1780, "TATAMOTORS.NS": 960,
        "^NSEI": 22300,
    }
    base = base_prices.get(symbol, 1000 + random.uniform(-200, 500))
    dates = pd.date_range(end=datetime.now(), periods=days, freq="B")
    np.random.seed(hash(symbol) % (2**31))
    returns = np.random.normal(0.0005, 0.015, days)
    prices = base * np.cumprod(1 + returns)
    highs = prices * (1 + np.abs(np.random.normal(0, 0.008, days)))
    lows = prices * (1 - np.abs(np.random.normal(0, 0.008, days)))
    opens = np.roll(prices, 1)
    opens[0] = prices[0]
    volumes = np.random.randint(500_000, 5_000_000, days).astype(float)

    df = pd.DataFrame({
        "Open": opens, "High": highs, "Low": lows,
        "Close": prices, "Volume": volumes
    }, index=dates)
    df.index.name = "Date"
    return df


def _mock_fundamentals(symbol: str) -> dict:
    """Generate realistic fundamental data for Indian stocks."""
    base_data = {
        "RELIANCE.NS": {"market_cap": 19_50_000, "pe_ratio": 28.5, "pb_ratio": 2.4,
                        "roe": 12.3, "debt_to_equity": 0.45, "current_price": 2920,
                        "52w_high": 3024, "52w_low": 2220, "promoter_holding": 50.3},
        "TCS.NS": {"market_cap": 15_10_000, "pe_ratio": 33.2, "pb_ratio": 12.8,
                   "roe": 52.4, "debt_to_equity": 0.0, "current_price": 4112,
                   "52w_high": 4592, "52w_low": 3311, "promoter_holding": 71.9},
        "HDFCBANK.NS": {"market_cap": 12_20_000, "pe_ratio": 19.8, "pb_ratio": 2.8,
                        "roe": 16.5, "debt_to_equity": 7.2, "current_price": 1648,
                        "52w_high": 1880, "52w_low": 1363, "promoter_holding": 0.0},
        "INFY.NS": {"market_cap": 7_40_000, "pe_ratio": 24.6, "pb_ratio": 7.2,
                    "roe": 32.8, "debt_to_equity": 0.0, "current_price": 1782,
                    "52w_high": 1950, "52w_low": 1351, "promoter_holding": 14.7},
        "ICICIBANK.NS": {"market_cap": 8_30_000, "pe_ratio": 17.2, "pb_ratio": 2.5,
                         "roe": 18.9, "debt_to_equity": 5.8, "current_price": 1185,
                         "52w_high": 1322, "52w_low": 908, "promoter_holding": 0.0},
    }
    default = {
        "market_cap": random.randint(10_000, 5_00_000),
        "pe_ratio": round(random.uniform(12, 40), 1),
        "pb_ratio": round(random.uniform(1, 8), 1),
        "roe": round(random.uniform(8, 35), 1),
        "debt_to_equity": round(random.uniform(0, 2), 2),
        "current_price": round(random.uniform(200, 3000), 2),
        "52w_high": 0, "52w_low": 0,
        "promoter_holding": round(random.uniform(25, 75), 1),
    }
    data = base_data.get(symbol, default)
    cp = data["current_price"]
    if not data.get("52w_high"):
        data["52w_high"] = round(cp * random.uniform(1.05, 1.35), 2)
        data["52w_low"] = round(cp * random.uniform(0.65, 0.95), 2)

    data.update({
        "symbol": symbol,
        "revenue_growth": round(random.uniform(-5, 25), 1),
        "profit_growth": round(random.uniform(-10, 35), 1),
        "fii_holding": round(random.uniform(10, 45), 1),
        "volume": random.randint(500_000, 10_000_000),
        "avg_volume": random.randint(500_000, 8_000_000),
    })
    return data


def _mock_bulk_deals() -> list:
    """Generate realistic bulk deal mock data."""
    companies = [
        ("RELIANCE", "Reliance Industries"), ("TCS", "Tata Consultancy"),
        ("HDFCBANK", "HDFC Bank"), ("INFY", "Infosys"),
        ("ICICIBANK", "ICICI Bank"), ("AXISBANK", "Axis Bank"),
        ("TATAMOTORS", "Tata Motors"), ("WIPRO", "Wipro"),
        ("SUNPHARMA", "Sun Pharma"), ("BAJFINANCE", "Bajaj Finance"),
    ]
    buyers = [
        "Mirae Asset MF", "SBI Mutual Fund", "HDFC MF", "Nippon India MF",
        "ICICI Pru MF", "Kotak Mahindra MF", "Axis MF", "DSP MF",
        "Government Pension Fund Norway", "Vanguard Funds",
    ]
    deals = []
    for i in range(12):
        sym, name = random.choice(companies)
        qty = random.randint(100_000, 2_000_000)
        price = round(random.uniform(200, 3000), 2)
        deals.append({
            "symbol": sym, "company": name,
            "client_name": random.choice(buyers),
            "deal_type": random.choice(["Buy", "Buy", "Buy", "Sell"]),
            "quantity": qty,
            "price": price,
            "value_cr": round(qty * price / 1e7, 2),
            "date": (datetime.now() - timedelta(days=random.randint(0, 5))).strftime("%Y-%m-%d"),
            "exchange": random.choice(["NSE", "BSE"]),
        })
    return deals


def _mock_insider_trades() -> list:
    """Generate realistic insider trading mock data."""
    insiders = [
        ("RELIANCE", "Mukesh Ambani", "Promoter", 2920),
        ("TCS", "N Chandrasekaran", "Director", 4112),
        ("HDFCBANK", "Sashidhar Jagdishan", "MD & CEO", 1648),
        ("INFY", "Salil Parekh", "MD & CEO", 1782),
        ("ICICIBANK", "Sandeep Bakhshi", "MD & CEO", 1185),
        ("BAJFINANCE", "Rajeev Jain", "MD & CEO", 7215),
        ("TITAN", "C K Venkataraman", "MD", 3610),
        ("ADANIENT", "Gautam Adani", "Promoter", 3150),
    ]
    trades = []
    for sym, person, category, price in insiders:
        qty = random.randint(5_000, 200_000)
        trade_type = random.choice(["Buy", "Buy", "Sell"])
        pre_holding = round(random.uniform(1, 72), 2)
        change = round(random.uniform(0.1, 2.5) * (1 if trade_type == "Buy" else -1), 2)
        trades.append({
            "symbol": sym, "person_name": person, "category": category,
            "trade_type": trade_type, "quantity": qty,
            "value_cr": round(qty * price / 1e7, 2),
            "date": (datetime.now() - timedelta(days=random.randint(0, 10))).strftime("%Y-%m-%d"),
            "pre_transaction_holding_pct": pre_holding,
            "post_transaction_holding_pct": round(pre_holding + change, 2),
            "price_at_trade": price,
        })
    return trades


def _mock_corporate_filings() -> list:
    """Generate realistic corporate filing mock data."""
    filings_data = [
        ("RELIANCE", "Capacity expansion: Jamnagar Refinery Phase 3", "Expansion", "BULLISH"),
        ("TCS", "New order win: $1.2B deal with European retailer", "Order Win", "BULLISH"),
        ("HDFCBANK", "Q4 FY25 Financial Results - Record NII of ₹29,000 Cr", "Results", "BULLISH"),
        ("INFY", "Acquisition of German AI company for €210 million", "Acquisition", "BULLISH"),
        ("ADANIENT", "Promoter pledge reduced by 18% — 8.2 Cr shares freed", "Pledge Reduction", "BULLISH"),
        ("BAJFINANCE", "Bonus issue 1:1 approved by Board", "Bonus Issue", "BULLISH"),
        ("ZOMATO", "Change in Top Management: New CFO appointed", "Mgmt Change", "NEUTRAL"),
        ("COALINDIA", "Auditor concerns on inventory valuation noted", "Auditor Note", "BEARISH"),
        ("TATAMOTORS", "EV sales cross 1 lakh units — ahead of target", "Milestone", "BULLISH"),
        ("SUNPHARMA", "USFDA inspection completed, EIR received", "Regulatory", "BULLISH"),
        ("ITC", "Board approves ₹18,000 Cr share buyback at ₹530", "Buyback", "BULLISH"),
        ("POWERGRID", "New transmission project worth ₹4,800 Cr approved", "New Project", "BULLISH"),
    ]
    results = []
    for i, (sym, subject, category, direction) in enumerate(filings_data):
        results.append({
            "symbol": sym, "subject": subject, "category": category,
            "direction": direction,
            "date": (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d"),
            "headline": subject,
            "source": "BSE",
        })
    return results


def _mock_fii_dii_data(days: int = 30) -> list:
    """Generate realistic FII/DII net flow data."""
    data = []
    base_date = datetime.now() - timedelta(days=days)
    fii_trend = random.choice([1, -1])
    for i in range(days):
        date = base_date + timedelta(days=i)
        if date.weekday() >= 5:
            continue
        fii_net = round(fii_trend * random.uniform(200, 3500) * random.choice([1, 1, 1, -1]), 2)
        dii_net = round(-fii_net * random.uniform(0.6, 1.2) + random.uniform(-300, 300), 2)
        fii_buy = round(abs(fii_net) + random.uniform(1000, 5000), 2)
        fii_sell = round(fii_buy - fii_net, 2)
        dii_buy = round(abs(dii_net) + random.uniform(800, 4000), 2)
        dii_sell = round(dii_buy - dii_net, 2)
        data.append({
            "date": date.strftime("%Y-%m-%d"),
            "fii_buy": fii_buy, "fii_sell": fii_sell, "fii_net": fii_net,
            "dii_buy": dii_buy, "dii_sell": dii_sell, "dii_net": dii_net,
        })
    return data


def _mock_ipo_data() -> list:
    """Generate realistic IPO data."""
    return [
        {"company": "Hyundai Motor India", "open_date": "2026-03-20", "close_date": "2026-03-22",
         "issue_price": 1960, "lot_size": 7, "subscription_times": 0, "listing_gain_pct": None,
         "status": "Upcoming", "issue_size_cr": 27870, "gmp": 120},
        {"company": "Swiggy", "open_date": "2026-03-25", "close_date": "2026-03-27",
         "issue_price": 390, "lot_size": 38, "subscription_times": 0, "listing_gain_pct": None,
         "status": "Upcoming", "issue_size_cr": 11327, "gmp": 45},
        {"company": "NTPC Green Energy", "open_date": "2026-02-22", "close_date": "2026-02-26",
         "issue_price": 108, "lot_size": 138, "subscription_times": 2.55, "listing_gain_pct": 3.5,
         "status": "Listed", "issue_size_cr": 10000, "gmp": 0},
        {"company": "Bajaj Housing Finance", "open_date": "2026-01-09", "close_date": "2026-01-11",
         "issue_price": 70, "lot_size": 214, "subscription_times": 64.0, "listing_gain_pct": 114.3,
         "status": "Listed", "issue_size_cr": 6560, "gmp": 0},
        {"company": "Ola Electric", "open_date": "2025-08-02", "close_date": "2025-08-06",
         "issue_price": 76, "lot_size": 195, "subscription_times": 4.3, "listing_gain_pct": -2.9,
         "status": "Listed", "issue_size_cr": 6145, "gmp": 0},
    ]


def _mock_sector_performance() -> list:
    """Generate realistic sector performance data."""
    sectors = [
        ("IT", ["TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS"]),
        ("Banking", ["HDFCBANK.NS", "ICICIBANK.NS", "KOTAKBANK.NS", "AXISBANK.NS", "SBIN.NS"]),
        ("Pharma", ["SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS"]),
        ("Auto", ["MARUTI.NS", "TATAMOTORS.NS", "BAJAJ-AUTO.NS", "EICHERMOT.NS", "HEROMOTOCO.NS"]),
        ("FMCG", ["HINDUNILVR.NS", "ITC.NS", "NESTLEIND.NS", "BRITANNIA.NS", "DABUR.NS"]),
        ("Energy", ["RELIANCE.NS", "ONGC.NS", "BPCL.NS", "IOC.NS", "NTPC.NS"]),
        ("Metals", ["TATASTEEL.NS", "JSWSTEEL.NS", "HINDALCO.NS", "COALINDIA.NS"]),
        ("Infra", ["LT.NS", "POWERGRID.NS", "ULTRACEMCO.NS", "GRASIM.NS"]),
        ("Realty", ["DLF.NS", "GODREJPROP.NS", "OBEROIRLTY.NS"]),
    ]
    results = []
    for sector, _ in sectors:
        results.append({
            "sector": sector,
            "return_1d_pct": round(random.uniform(-2.5, 2.5), 2),
            "return_1w_pct": round(random.uniform(-5, 5), 2),
            "return_1m_pct": round(random.uniform(-12, 15), 2),
            "top_gainer": random.choice(["TATASTEEL", "INFY", "HDFCBANK", "MARUTI", "SUNPHARMA"]),
            "market_cap_cr": random.randint(50_000, 5_00_000),
        })
    return results


def _mock_news(symbol: str) -> list:
    """Generate realistic news for a stock symbol."""
    sym_clean = symbol.replace(".NS", "").replace(".BO", "")
    templates = [
        f"{sym_clean} Q4 results beat Street estimates; profit up 18% YoY",
        f"Analysts upgrade {sym_clean} to 'Buy'; target price raised to ₹{random.randint(500, 5000)}",
        f"{sym_clean} announces ₹{random.randint(500, 5000)} Cr capex plan for FY26",
        f"FII increases stake in {sym_clean} by {round(random.uniform(0.5, 3), 1)}%",
        f"{sym_clean} signs major deal worth ${random.randint(100, 2000)} million",
        f"Promoter buys ₹{round(random.uniform(50, 500), 1)} Cr worth of {sym_clean} shares",
    ]
    publishers = ["Economic Times", "Business Standard", "Mint", "CNBC TV18", "MoneyControl"]
    news = []
    for i, tmpl in enumerate(random.sample(templates, min(5, len(templates)))):
        news.append({
            "title": tmpl, "publisher": random.choice(publishers),
            "link": f"https://economictimes.com/news/{sym_clean.lower()}-{i}",
            "providerPublishTime": int((datetime.now() - timedelta(hours=i * 4)).timestamp()),
            "sentiment": _sentiment_score(tmpl),
        })
    return news


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC API FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

async def get_stock_data(symbol: str, period: str = "1y") -> pd.DataFrame:
    """
    Fetch OHLCV price data for a stock symbol.

    Args:
        symbol: Yahoo Finance ticker symbol (e.g. 'RELIANCE.NS')
        period: yfinance period string (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y)

    Returns:
        DataFrame with columns: Open, High, Low, Close, Volume
    """
    if MOCK_MODE:
        days_map = {"1d": 1, "5d": 5, "1mo": 22, "3mo": 66, "6mo": 132,
                    "1y": 252, "2y": 504, "5y": 1260}
        return _mock_ohlcv(symbol, days_map.get(period, 252))

    try:
        import yfinance as yf
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(None, lambda: yf.Ticker(symbol).history(period=period))
        if df.empty:
            raise ValueError(f"No data returned for {symbol}")
        return df
    except Exception as e:
        logger.warning(f"yfinance fetch failed for {symbol}: {e}. Using mock data.")
        days_map = {"1d": 1, "5d": 5, "1mo": 22, "3mo": 66, "6mo": 132,
                    "1y": 252, "2y": 504, "5y": 1260}
        return _mock_ohlcv(symbol, days_map.get(period, 252))


async def get_fundamentals(symbol: str) -> dict:
    """
    Fetch fundamental data for a stock.

    Args:
        symbol: Yahoo Finance ticker symbol.

    Returns:
        dict with market_cap, pe_ratio, pb_ratio, roe, debt_to_equity,
        revenue_growth, profit_growth, promoter_holding, fii_holding,
        52w_high, 52w_low, current_price, volume, avg_volume.
    """
    if MOCK_MODE:
        return _mock_fundamentals(symbol)

    try:
        import yfinance as yf
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, lambda: yf.Ticker(symbol).info)
        if not info or "regularMarketPrice" not in info:
            raise ValueError("Empty info returned")

        return {
            "symbol": symbol,
            "market_cap": info.get("marketCap", 0) // 1_00_00_000,  # Convert to Cr
            "pe_ratio": round(info.get("trailingPE", 0) or 0, 2),
            "pb_ratio": round(info.get("priceToBook", 0) or 0, 2),
            "roe": round((info.get("returnOnEquity", 0) or 0) * 100, 2),
            "debt_to_equity": round(info.get("debtToEquity", 0) or 0, 2),
            "revenue_growth": round((info.get("revenueGrowth", 0) or 0) * 100, 2),
            "profit_growth": round((info.get("earningsGrowth", 0) or 0) * 100, 2),
            "promoter_holding": round(info.get("heldPercentInsiders", 0) * 100, 2),
            "fii_holding": round(info.get("heldPercentInstitutions", 0) * 100, 2),
            "52w_high": info.get("fiftyTwoWeekHigh", 0),
            "52w_low": info.get("fiftyTwoWeekLow", 0),
            "current_price": info.get("regularMarketPrice", info.get("currentPrice", 0)),
            "volume": info.get("regularMarketVolume", 0),
            "avg_volume": info.get("averageVolume", 0),
            "company_name": info.get("longName", symbol),
            "sector": info.get("sector", "Unknown"),
        }
    except Exception as e:
        logger.warning(f"Fundamentals fetch failed for {symbol}: {e}. Using mock.")
        return _mock_fundamentals(symbol)


async def get_news(symbol: str) -> list:
    """
    Fetch recent news for a stock with sentiment scoring.

    Args:
        symbol: Yahoo Finance ticker symbol.

    Returns:
        list of dicts with title, publisher, link, providerPublishTime, sentiment.
    """
    if MOCK_MODE:
        return _mock_news(symbol)

    try:
        import yfinance as yf
        loop = asyncio.get_event_loop()
        ticker = yf.Ticker(symbol)
        news_raw = await loop.run_in_executor(None, lambda: ticker.news)
        if not news_raw:
            return _mock_news(symbol)

        results = []
        for item in news_raw[:10]:
            title = item.get("title", "")
            results.append({
                "title": title,
                "publisher": item.get("publisher", "Unknown"),
                "link": item.get("link", ""),
                "providerPublishTime": item.get("providerPublishTime", 0),
                "sentiment": _sentiment_score(title),
            })
        return results
    except Exception as e:
        logger.warning(f"News fetch failed for {symbol}: {e}. Using mock.")
        return _mock_news(symbol)


async def get_bulk_block_deals() -> list:
    """
    Fetch bulk and block deals from NSE.

    Returns:
        list of dicts with symbol, client_name, deal_type, quantity,
        price, value_cr, date, exchange.
    """
    if MOCK_MODE:
        return _mock_bulk_deals()

    try:
        from nsepython import get_bulkdeals_data, get_blockdeals_data
        loop = asyncio.get_event_loop()
        bulk = await loop.run_in_executor(None, get_bulkdeals_data)
        block = await loop.run_in_executor(None, get_blockdeals_data)

        results = []
        for df_raw, deal_type in [(bulk, "Bulk"), (block, "Block")]:
            if df_raw is None:
                continue
            if isinstance(df_raw, pd.DataFrame):
                for _, row in df_raw.iterrows():
                    try:
                        qty = int(str(row.get("QUANTITY TRADED", "0")).replace(",", ""))
                        price = float(str(row.get("TRADE PRICE/ WTED AVG PRICE", "0")).replace(",", ""))
                        results.append({
                            "symbol": str(row.get("SYMBOL", "")),
                            "client_name": str(row.get("CLIENT NAME", "")),
                            "deal_type": deal_type,
                            "quantity": qty,
                            "price": price,
                            "value_cr": round(qty * price / 1e7, 2),
                            "date": str(row.get("DATE", datetime.now().strftime("%Y-%m-%d"))),
                            "exchange": "NSE",
                        })
                    except Exception:
                        continue
        return results if results else _mock_bulk_deals()
    except Exception as e:
        logger.warning(f"Bulk/block deals fetch failed: {e}. Using mock.")
        return _mock_bulk_deals()


async def get_insider_trades() -> list:
    """
    Fetch insider trading data from NSE.

    Returns:
        list of dicts with symbol, person_name, category, trade_type,
        quantity, value_cr, date, pre/post holding percentages.
    """
    if MOCK_MODE:
        return _mock_insider_trades()

    try:
        import httpx
        url = "https://www.nseindia.com/api/corporates-pit?index=equities&from_date={}&to_date={}"
        from_date = (datetime.now() - timedelta(days=30)).strftime("%d-%m-%Y")
        to_date = datetime.now().strftime("%d-%m-%Y")
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Referer": "https://www.nseindia.com/",
        }
        async with httpx.AsyncClient(headers=headers, timeout=10) as client:
            resp = await client.get(url.format(from_date, to_date))
            data = resp.json()

        trades = []
        for item in data.get("data", [])[:15]:
            qty = int(str(item.get("noOfSecuritiesAcquiredOrDisposed", "0")).replace(",", "") or "0")
            price = float(str(item.get("valueOfSecuritiesAcquiredOrDisposed", "0")).replace(",", "") or "0")
            trades.append({
                "symbol": item.get("symbol", ""),
                "person_name": item.get("name", ""),
                "category": item.get("category", "Director"),
                "trade_type": "Buy" if item.get("typeOfTransaction", "").lower() == "buy" else "Sell",
                "quantity": qty,
                "value_cr": round(qty * price / 1e7, 2) if price > 100 else round(price / 1e7, 2),
                "date": item.get("date", datetime.now().strftime("%Y-%m-%d")),
                "pre_transaction_holding_pct": float(item.get("beforeAcqPercetage", 0) or 0),
                "post_transaction_holding_pct": float(item.get("afterAcqPercentage", 0) or 0),
            })
        return trades if trades else _mock_insider_trades()
    except Exception as e:
        logger.warning(f"Insider trades fetch failed: {e}. Using mock.")
        return _mock_insider_trades()


async def get_corporate_filings(symbol: str = None) -> list:
    """
    Fetch recent corporate filings from BSE.

    Args:
        symbol: Optional BSE scrip code or symbol to filter.

    Returns:
        list of dicts with symbol, subject, date, category, headline.
    """
    if MOCK_MODE:
        filings = _mock_corporate_filings()
        if symbol:
            sym_clean = symbol.replace(".NS", "").replace(".BO", "")
            filings = [f for f in filings if f["symbol"] == sym_clean] or filings
        return filings

    try:
        import httpx
        from datetime import datetime
        to_date = datetime.now().strftime("%Y%m%d")
        from_date = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
        url = (f"https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w"
               f"?strCat=-1&strPrevDate={from_date}&strScrip=&strSearch=P"
               f"&strToDate={to_date}&strType=C")
        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.bseindia.com/"}
        async with httpx.AsyncClient(headers=headers, timeout=10) as client:
            resp = await client.get(url)
            data = resp.json()

        filings = []
        for item in data.get("Table", [])[:20]:
            filings.append({
                "symbol": item.get("SLONGNAME", "").strip(),
                "subject": item.get("NEWSSUB", ""),
                "date": item.get("NEWS_DT", "")[:10],
                "category": item.get("CATEGORYNAME", ""),
                "headline": item.get("HEADLINE", item.get("NEWSSUB", "")),
                "source": "BSE",
            })
        return filings if filings else _mock_corporate_filings()
    except Exception as e:
        logger.warning(f"Corporate filings fetch failed: {e}. Using mock.")
        filings = _mock_corporate_filings()
        if symbol:
            sym_clean = symbol.replace(".NS", "").replace(".BO", "")
            filings = [f for f in filings if f["symbol"] == sym_clean] or filings
        return filings


async def get_fii_dii_data(days: int = 30) -> list:
    """
    Fetch FII/DII net investment data.

    Args:
        days: Number of trading days to fetch.

    Returns:
        list of dicts with date, fii_buy, fii_sell, fii_net, dii_buy, dii_sell, dii_net.
    """
    if MOCK_MODE:
        return _mock_fii_dii_data(days)

    try:
        import httpx
        url = "https://www.nseindia.com/api/fiidiiTradeReact"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Referer": "https://www.nseindia.com/",
        }
        async with httpx.AsyncClient(headers=headers, timeout=10) as client:
            resp = await client.get(url)
            data = resp.json()

        results = []
        for item in data[:days]:
            try:
                results.append({
                    "date": item.get("date", ""),
                    "fii_buy": float(str(item.get("fiiBuy", "0")).replace(",", "") or 0),
                    "fii_sell": float(str(item.get("fiiSell", "0")).replace(",", "") or 0),
                    "fii_net": float(str(item.get("fiiNet", "0")).replace(",", "") or 0),
                    "dii_buy": float(str(item.get("diiBuy", "0")).replace(",", "") or 0),
                    "dii_sell": float(str(item.get("diiSell", "0")).replace(",", "") or 0),
                    "dii_net": float(str(item.get("diiNet", "0")).replace(",", "") or 0),
                })
            except Exception:
                continue
        return results if results else _mock_fii_dii_data(days)
    except Exception as e:
        logger.warning(f"FII/DII data fetch failed: {e}. Using mock.")
        return _mock_fii_dii_data(days)


async def get_ipo_data() -> list:
    """
    Fetch upcoming and recent IPO data.

    Returns:
        list of IPO dicts with company, open_date, close_date, issue_price,
        lot_size, subscription_times, listing_gain_pct, status.
    """
    # IPO data requires paid APIs; use mock data
    return _mock_ipo_data()


async def get_sector_performance() -> list:
    """
    Calculate sector performance by averaging representative stock returns.

    Returns:
        list of sector dicts with return_1d_pct, return_1w_pct, return_1m_pct.
    """
    if MOCK_MODE:
        return _mock_sector_performance()

    try:
        import yfinance as yf
        sector_stocks = {
            "IT": ["TCS.NS", "INFY.NS", "WIPRO.NS"],
            "Banking": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS"],
            "Pharma": ["SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS"],
            "Auto": ["MARUTI.NS", "TATAMOTORS.NS", "BAJAJ-AUTO.NS"],
            "FMCG": ["HINDUNILVR.NS", "ITC.NS", "NESTLEIND.NS"],
            "Energy": ["RELIANCE.NS", "ONGC.NS", "BPCL.NS"],
            "Metals": ["TATASTEEL.NS", "JSWSTEEL.NS", "HINDALCO.NS"],
            "Infra": ["LT.NS", "POWERGRID.NS", "ULTRACEMCO.NS"],
            "Realty": ["DLF.NS", "GODREJPROP.NS"],
        }
        results = []
        loop = asyncio.get_event_loop()

        for sector, symbols in sector_stocks.items():
            try:
                data = await loop.run_in_executor(
                    None, lambda syms=symbols: yf.download(syms, period="1mo", progress=False)["Close"]
                )
                if data.empty:
                    raise ValueError("Empty data")
                r1d = data.pct_change(1).iloc[-1].mean() * 100
                r1w = data.pct_change(5).iloc[-1].mean() * 100
                r1m = data.pct_change(22).iloc[-1].mean() * 100
                results.append({
                    "sector": sector,
                    "return_1d_pct": round(r1d, 2),
                    "return_1w_pct": round(r1w, 2),
                    "return_1m_pct": round(r1m, 2),
                })
            except Exception:
                results.append({
                    "sector": sector,
                    "return_1d_pct": round(random.uniform(-2, 2), 2),
                    "return_1w_pct": round(random.uniform(-5, 5), 2),
                    "return_1m_pct": round(random.uniform(-10, 12), 2),
                })
        return results
    except Exception as e:
        logger.warning(f"Sector performance fetch failed: {e}. Using mock.")
        return _mock_sector_performance()


async def get_market_overview() -> dict:
    """
    Fetch a combined market snapshot for the Dashboard.

    Returns:
        dict with nifty50, sensex, top_gainers, top_losers, market_breadth,
        fii_net_today, vix, sentiment.
    """
    if MOCK_MODE:
        nifty = round(22350 + random.uniform(-200, 200), 2)
        sensex = round(73800 + random.uniform(-600, 600), 2)
        nifty_chg = round(random.uniform(-1.5, 1.5), 2)
        sensex_chg = round(random.uniform(-1.5, 1.5), 2)
    else:
        try:
            import yfinance as yf
            loop = asyncio.get_event_loop()
            nifty_data = await loop.run_in_executor(
                None, lambda: yf.Ticker("^NSEI").history(period="2d"))
            sensex_data = await loop.run_in_executor(
                None, lambda: yf.Ticker("^BSESN").history(period="2d"))
            nifty = round(nifty_data["Close"].iloc[-1], 2)
            sensex = round(sensex_data["Close"].iloc[-1], 2)
            nifty_chg = round(((nifty - nifty_data["Close"].iloc[-2]) / nifty_data["Close"].iloc[-2]) * 100, 2)
            sensex_chg = round(((sensex - sensex_data["Close"].iloc[-2]) / sensex_data["Close"].iloc[-2]) * 100, 2)
        except Exception:
            nifty = round(22350 + random.uniform(-200, 200), 2)
            sensex = round(73800 + random.uniform(-600, 600), 2)
            nifty_chg = round(random.uniform(-1.5, 1.5), 2)
            sensex_chg = round(random.uniform(-1.5, 1.5), 2)

    gainers = [
        {"symbol": "TATAMOTORS", "change_pct": round(random.uniform(2, 6), 2), "price": 962},
        {"symbol": "ADANIENT", "change_pct": round(random.uniform(2, 5), 2), "price": 3151},
        {"symbol": "JSWSTEEL", "change_pct": round(random.uniform(1.5, 4), 2), "price": 985},
        {"symbol": "COALINDIA", "change_pct": round(random.uniform(1, 3), 2), "price": 485},
        {"symbol": "HINDALCO", "change_pct": round(random.uniform(1, 3), 2), "price": 698},
    ]
    losers = [
        {"symbol": "NESTLEIND", "change_pct": round(random.uniform(-4, -1.5), 2), "price": 24012},
        {"symbol": "BRITANNIA", "change_pct": round(random.uniform(-3, -1), 2), "price": 4892},
        {"symbol": "HDFCBANK", "change_pct": round(random.uniform(-2, -0.5), 2), "price": 1648},
        {"symbol": "INFY", "change_pct": round(random.uniform(-2, -0.5), 2), "price": 1782},
        {"symbol": "WIPRO", "change_pct": round(random.uniform(-2, -0.5), 2), "price": 541},
    ]

    advances = random.randint(1100, 1600)
    declines = random.randint(700, 1200)
    unchanged = 2500 - advances - declines

    return {
        "nifty50": {"level": nifty, "change_pct": nifty_chg},
        "sensex": {"level": sensex, "change_pct": sensex_chg},
        "top_gainers": gainers,
        "top_losers": losers,
        "market_breadth": {"advances": advances, "declines": declines, "unchanged": unchanged},
        "fii_net_today": round(random.uniform(-3000, 3000), 2),
        "vix": round(random.uniform(12, 22), 2),
        "sentiment": "BULLISH" if nifty_chg > 0.2 else ("BEARISH" if nifty_chg < -0.2 else "NEUTRAL"),
        "timestamp": datetime.now().isoformat(),
    }
