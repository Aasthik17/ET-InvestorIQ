"""
ET InvestorIQ — Signal Engine
Core intelligence for Opportunity Radar. Detects anomalies and patterns
across insider trades, bulk deals, corporate filings, and FII flow data.
"""

import hashlib
import json
import logging
import re
from datetime import datetime, timedelta
from typing import List

from app.modules.opportunity_radar.schemas import (
    Signal, SignalType, SignalDirection, RadarResponse, MarketSentiment
)

logger = logging.getLogger(__name__)

# ─── Company name lookup (NSE symbol → full name) ─────────────────────────────
COMPANY_NAMES = {
    "RELIANCE": "Reliance Industries Ltd",
    "TCS": "Tata Consultancy Services",
    "HDFCBANK": "HDFC Bank Ltd",
    "INFY": "Infosys Ltd",
    "ICICIBANK": "ICICI Bank Ltd",
    "KOTAKBANK": "Kotak Mahindra Bank",
    "LT": "Larsen & Toubro Ltd",
    "AXISBANK": "Axis Bank Ltd",
    "BHARTIARTL": "Bharti Airtel Ltd",
    "ITC": "ITC Ltd",
    "SBIN": "State Bank of India",
    "HINDUNILVR": "Hindustan Unilever Ltd",
    "BAJFINANCE": "Bajaj Finance Ltd",
    "WIPRO": "Wipro Ltd",
    "TITAN": "Titan Company Ltd",
    "MARUTI": "Maruti Suzuki India Ltd",
    "SUNPHARMA": "Sun Pharmaceutical Industries",
    "TATAMOTORS": "Tata Motors Ltd",
    "ADANIENT": "Adani Enterprises Ltd",
    "TATASTEEL": "Tata Steel Ltd",
    "JSWSTEEL": "JSW Steel Ltd",
    "COALINDIA": "Coal India Ltd",
    "POWERGRID": "Power Grid Corporation of India",
    "NTPC": "NTPC Ltd",
    "ZOMATO": "Zomato Ltd",
}

KNOWN_INSTITUTIONAL_BUYERS = [
    "mirae", "sbi mf", "hdfc mf", "nippon", "icici pru", "kotak mf",
    "axis mf", "dsp", "franklin", "birla", "uti", "invesco", "tata mf",
    "government pension fund", "vanguard", "blackrock", "fidelity",
    "aberdeen", "nomura", "morgan stanley", "jpmorgan", "goldman",
]

BULLISH_FILING_KEYWORDS = [
    "capacity expansion", "new order", "acquisition", "buyback", "bonus issue",
    "split", "dividend", "deal won", "partnership", "order win", "record",
    "milestone", "eir received", "nod", "approval", "capex", "ipo",
    "stake sale", "divestment at premium", "joint venture",
]
BEARISH_FILING_KEYWORDS = [
    "auditor resignation", "change in auditor", "probe", "investigation",
    "fraud", "sebi notice", "cbi", "ed raid", "write-off", "impairment",
    "default", "npa", "downgrade", "recall", "fda warning", "show cause",
    "penalty imposed",
]


def _make_signal_id(symbol: str, signal_type: str, date: str, extra: str = "") -> str:
    """Generate a deterministic unique ID for a signal."""
    raw = f"{symbol}:{signal_type}:{date}:{extra}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def _days_ago(date_str: str) -> int:
    """Return number of days from today for a YYYY-MM-DD date string."""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        return (datetime.now() - d).days
    except Exception:
        return 999


def detect_insider_signals(insider_trades: List[dict]) -> List[Signal]:
    """
    Detect high-value insider trading signals.

    Flags:
    - Large buy > ₹1 Cr by promoters/directors
    - Cluster buying: 3+ different insiders buying within 10 days
    - Buy at or near 52-week low

    Args:
        insider_trades: List of insider trade dicts from data_service.

    Returns:
        List of Signal objects for notable trades.
    """
    signals = []
    recent_buys_by_symbol: dict = {}

    for trade in insider_trades:
        symbol = trade.get("symbol", "")
        person = trade.get("person_name", "")
        category = trade.get("category", "")
        trade_type = trade.get("trade_type", "")
        value_cr = float(trade.get("value_cr", 0))
        qty = int(trade.get("quantity", 0))
        date_str = trade.get("date", datetime.now().strftime("%Y-%m-%d"))
        price = float(trade.get("price_at_trade", 0))

        if trade_type != "Buy":
            continue

        # Track cluster buys
        if symbol not in recent_buys_by_symbol:
            recent_buys_by_symbol[symbol] = []
        recent_buys_by_symbol[symbol].append(trade)

        # Signal: large buy > ₹1 Cr
        if value_cr >= 1.0:
            confidence = 0.55
            if category == "Promoter":
                confidence += 0.20
            if category in ("Director", "KMP"):
                confidence += 0.10
            if value_cr >= 5:
                confidence += 0.10
            if value_cr >= 20:
                confidence += 0.05
            confidence = min(0.95, confidence)

            category_weight = {
                "Promoter": "Promoter", "Director": "Director",
                "KMP": "Key Managerial Person", "Others": "Institutional"
            }.get(category, category)

            signals.append(Signal(
                id=_make_signal_id(symbol, "INSIDER_TRADE", date_str, person),
                symbol=symbol,
                company_name=COMPANY_NAMES.get(symbol, symbol),
                signal_type=SignalType.INSIDER_TRADE,
                headline=f"{category_weight} {person} bought ₹{value_cr:.1f} Cr of {symbol}",
                detail=(f"{person} ({category}) purchased {qty:,} shares of {symbol} "
                        f"at approx ₹{price:.0f} per share (total ₹{value_cr:.2f} Cr) on {date_str}. "
                        f"Post-transaction holding: {trade.get('post_transaction_holding_pct', 0):.2f}%."),
                confidence_score=round(confidence, 2),
                signal_date=date_str,
                stock_price_at_signal=price,
                expected_impact=SignalDirection.BULLISH,
                data_sources=["NSE Insider Trading Disclosure"],
                tags=["insider", "buy", category.lower(), symbol.lower()],
                raw_data=trade,
            ))

    # Cluster buying: 3+ insiders buying same stock within 10 days
    for symbol, trades in recent_buys_by_symbol.items():
        if len(trades) >= 3:
            total_value = sum(float(t.get("value_cr", 0)) for t in trades)
            latest_date = max(t.get("date", "") for t in trades)
            signals.append(Signal(
                id=_make_signal_id(symbol, "INSIDER_CLUSTER", latest_date, "cluster"),
                symbol=symbol,
                company_name=COMPANY_NAMES.get(symbol, symbol),
                signal_type=SignalType.INSIDER_TRADE,
                headline=f"CLUSTER BUY: {len(trades)} insiders bought {symbol} — total ₹{total_value:.1f} Cr",
                detail=(f"{len(trades)} different insiders (including {trades[0].get('person_name', '')}) "
                        f"have purchased shares of {symbol} in the last 10 days. "
                        f"Combined purchase value: ₹{total_value:.2f} Cr. "
                        f"Cluster buying by multiple insiders is historically one of the strongest bullish signals."),
                confidence_score=0.82,
                signal_date=latest_date,
                stock_price_at_signal=float(trades[0].get("price_at_trade", 0)),
                expected_impact=SignalDirection.BULLISH,
                data_sources=["NSE Insider Trading Disclosure"],
                tags=["insider", "cluster", "buy", symbol.lower(), "high-conviction"],
                raw_data={"trades": trades},
            ))

    return signals


def detect_bulk_deal_signals(bulk_deals: List[dict]) -> List[Signal]:
    """
    Detect meaningful bulk/block deal signals.

    Scenario 1 (Hackathon): Classifies each deal as PROMOTER_DISTRESS,
    PROMOTER_ROUTINE_SALE, INSTITUTIONAL_EXIT, or INSTITUTIONAL_ACCUMULATION
    using filing_matcher.classify_bulk_deal().

    Flags:
    - Promoter selling with >3% discount → distress signal (BEARISH, high confidence)
    - Large deals by known institutional buyers (MFs, FIIs)
    - Repeated bulk buys in same stock within 5 days

    Args:
        bulk_deals: List of bulk/block deal dicts.

    Returns:
        List of Signal objects with deal_class and distress_probability in raw_data.
    """
    from app.services.filing_matcher import classify_bulk_deal

    signals = []
    deals_by_symbol: dict = {}

    for deal in bulk_deals:
        symbol = deal.get("symbol", "")
        client = deal.get("client_name", "")
        deal_type = deal.get("deal_type", "")
        value_cr = float(deal.get("value_cr", 0))
        qty = int(deal.get("quantity", 0))
        price = float(deal.get("price", 0))
        date_str = deal.get("date", datetime.now().strftime("%Y-%m-%d"))

        if symbol not in deals_by_symbol:
            deals_by_symbol[symbol] = []
        deals_by_symbol[symbol].append(deal)

        client_lower = client.lower()
        is_institutional = any(inst in client_lower for inst in KNOWN_INSTITUTIONAL_BUYERS)
        is_buy = "buy" in deal_type.lower()
        is_sell = not is_buy

        # ── Scenario 1: Promoter Distress Classification ──────────────────────
        classification = classify_bulk_deal(deal)
        deal_class = classification["deal_class"]
        distress_prob = classification["distress_probability"]
        distress_reasoning = classification["reasoning"]
        is_promoter_seller = classification["is_promoter_seller"]

        if is_promoter_seller and is_sell:
            if deal_class == "PROMOTER_DISTRESS":
                confidence = 0.55 + distress_prob * 0.35
                direction = SignalDirection.BEARISH
                headline = (
                    f"⚠ PROMOTER DISTRESS SELL: {client} sold ₹{value_cr:.1f} Cr "
                    f"({distress_prob*100:.0f}% distress score) — {symbol}"
                )
                detail = (
                    f"**Promoter Distress Signal** — {client} sold {qty:,} shares of {symbol} "
                    f"at ₹{price:.2f} (₹{value_cr:.2f} Cr total) on {date_str}. "
                    f"Distress indicators: {distress_reasoning}. "
                    f"Distress probability: {distress_prob*100:.0f}%. "
                    f"Cross-reference against recent management commentary and earnings trajectory before acting."
                )
                tags = ["bulk_deal", "promoter_distress", "bearish", symbol.lower(), "scenario1"]
            else:
                # Routine promoter sale
                confidence = 0.45
                direction = SignalDirection.NEUTRAL
                headline = f"Promoter sale: {client} sold ₹{value_cr:.1f} Cr of {symbol} (routine)"
                detail = (
                    f"{client} sold {qty:,} shares of {symbol} at ₹{price:.2f} on {date_str}. "
                    f"Classification: Routine promoter divestment (distress score: {distress_prob*100:.0f}%). "
                    f"{distress_reasoning}."
                )
                tags = ["bulk_deal", "promoter_sale", symbol.lower()]

            enriched_raw = {
                **deal,
                "deal_class": deal_class,
                "distress_probability": distress_prob,
                "distress_reasoning": distress_reasoning,
                "seller_category": "Promoter",
            }

            signals.append(Signal(
                id=_make_signal_id(symbol, "BULK_DEAL_PROMOTER", date_str, client),
                symbol=symbol,
                company_name=COMPANY_NAMES.get(symbol, symbol),
                signal_type=SignalType.BULK_DEAL,
                headline=headline,
                detail=detail,
                confidence_score=round(min(0.92, confidence), 2),
                signal_date=date_str,
                stock_price_at_signal=price,
                expected_impact=direction,
                data_sources=["NSE Bulk Deals", "BSE Block Deals"],
                tags=tags,
                raw_data=enriched_raw,
            ))
            continue

        # ── Institutional accumulation signals ────────────────────────────────
        if value_cr >= 5 and is_institutional and is_buy:
            confidence = 0.60 + min(0.20, value_cr / 200)
            signals.append(Signal(
                id=_make_signal_id(symbol, "BULK_DEAL", date_str, client),
                symbol=symbol,
                company_name=COMPANY_NAMES.get(symbol, symbol),
                signal_type=SignalType.BULK_DEAL,
                headline=f"Institutional bulk buy: {client} acquired ₹{value_cr:.1f} Cr of {symbol}",
                detail=(f"{client} executed a bulk buy of {qty:,} shares of {symbol} at ₹{price:.2f} "
                        f"(total: ₹{value_cr:.2f} Cr) on {date_str}. "
                        f"Institutional accumulation at these levels suggests conviction in the stock's outlook."),
                confidence_score=round(min(0.90, confidence), 2),
                signal_date=date_str,
                stock_price_at_signal=price,
                expected_impact=SignalDirection.BULLISH,
                data_sources=["NSE Bulk Deals", "BSE Block Deals"],
                tags=["bulk_deal", "institutional", symbol.lower(), "buy"],
                raw_data={**deal, "deal_class": "INSTITUTIONAL_ACCUMULATION", "distress_probability": 0.0},
            ))

    # ── Repeat accumulation pattern ───────────────────────────────────────────
    for symbol, deals in deals_by_symbol.items():
        buy_deals = [d for d in deals if "buy" in d.get("deal_type", "").lower()]
        if len(buy_deals) >= 2:
            total_val = sum(float(d.get("value_cr", 0)) for d in buy_deals)
            latest = max(d.get("date", "") for d in buy_deals)
            signals.append(Signal(
                id=_make_signal_id(symbol, "BULK_REPEAT", latest, "repeat"),
                symbol=symbol,
                company_name=COMPANY_NAMES.get(symbol, symbol),
                signal_type=SignalType.BULK_DEAL,
                headline=f"Repeat accumulation: {len(buy_deals)} bulk buys in {symbol} — ₹{total_val:.1f} Cr total",
                detail=(f"Multiple buyers executed bulk purchases in {symbol} within the past 5 trading days. "
                        f"Total accumulated: ₹{total_val:.2f} Cr. "
                        f"Repeat institutional buying suggests pre-event accumulation."),
                confidence_score=0.72,
                signal_date=latest,
                stock_price_at_signal=float(buy_deals[0].get("price", 0)),
                expected_impact=SignalDirection.BULLISH,
                data_sources=["NSE Bulk Deals"],
                tags=["bulk_deal", "accumulation", symbol.lower(), "repeat"],
                raw_data={"deals": buy_deals, "deal_class": "REPEAT_ACCUMULATION", "distress_probability": 0.0},
            ))

    return signals


def detect_filing_signals(filings: List[dict]) -> List[Signal]:
    """
    Parse corporate filings for keyword-based signal detection.

    Bullish keywords: capacity expansion, new order, buyback, bonus, etc.
    Bearish keywords: auditor resignation, probe, fraud, write-off, etc.

    Args:
        filings: List of corporate filing dicts.

    Returns:
        List of Signal objects.
    """
    signals = []

    for filing in filings:
        symbol = filing.get("symbol", "")
        subject = (filing.get("subject", "") or "").lower()
        headline = filing.get("headline", filing.get("subject", ""))
        date_str = filing.get("date", datetime.now().strftime("%Y-%m-%d"))
        direction_hint = filing.get("direction", "")

        bullish_score = sum(1 for kw in BULLISH_FILING_KEYWORDS if kw in subject)
        bearish_score = sum(1 for kw in BEARISH_FILING_KEYWORDS if kw in subject)

        if bullish_score == 0 and bearish_score == 0 and not direction_hint:
            continue

        if direction_hint == "BULLISH" or bullish_score > bearish_score:
            direction = SignalDirection.BULLISH
            confidence = 0.50 + min(0.30, bullish_score * 0.10)
            signal_type = SignalType.FILING
        elif direction_hint == "BEARISH" or bearish_score > bullish_score:
            direction = SignalDirection.BEARISH
            confidence = 0.55 + min(0.25, bearish_score * 0.10)
            signal_type = SignalType.FILING
        else:
            direction = SignalDirection.NEUTRAL
            confidence = 0.40
            signal_type = SignalType.FILING

        # Special high-confidence cases
        if "buyback" in subject or "bonus" in subject:
            confidence = max(confidence, 0.78)
            signal_type = SignalType.CORPORATE_ACTION
        elif "auditor resignation" in subject or "fraud" in subject:
            confidence = max(confidence, 0.80)
        elif "capacity expansion" in subject or "new order" in subject:
            confidence = max(confidence, 0.65)
        elif "management change" in subject.lower() or "change in management" in subject:
            signal_type = SignalType.MANAGEMENT_CHANGE

        signals.append(Signal(
            id=_make_signal_id(symbol, signal_type, date_str, headline[:20]),
            symbol=symbol,
            company_name=COMPANY_NAMES.get(symbol, symbol),
            signal_type=signal_type,
            headline=headline,
            detail=(f"Filing category: {filing.get('category', 'General')}. "
                    f"Source: {filing.get('source', 'BSE')}. "
                    f"Filed on: {date_str}. "
                    f"{'Bullish keywords detected: ' + ', '.join([kw for kw in BULLISH_FILING_KEYWORDS if kw in subject]) if bullish_score > 0 else ''}"
                    f"{'Bearish keywords detected: ' + ', '.join([kw for kw in BEARISH_FILING_KEYWORDS if kw in subject]) if bearish_score > 0 else ''}"),
            confidence_score=round(min(0.92, confidence), 2),
            signal_date=date_str,
            stock_price_at_signal=0.0,
            expected_impact=direction,
            data_sources=["BSE Corporate Filings", "NSE Announcements"],
            tags=["filing", direction.lower() if isinstance(direction, str) else direction.value.lower(), symbol.lower()],
            raw_data=filing,
        ))

    return signals


def detect_fii_accumulation(fii_data: List[dict]) -> List[Signal]:
    """
    Detect FII accumulation or distribution patterns from flow data.

    Flags:
    - 5+ consecutive days of FII net buying (> ₹1000 Cr/day average)
    - Large single-day FII inflow (> ₹3000 Cr)
    - Sudden reversal from persistent FII selling

    Args:
        fii_data: List of FII/DII flow dicts sorted by date (oldest first).

    Returns:
        List of Signal objects.
    """
    signals = []
    if not fii_data:
        return signals

    sorted_data = sorted(fii_data, key=lambda x: x.get("date", ""))
    recent = sorted_data[-10:]  # Last 10 trading days

    # Check for consecutive buying streak
    streak = 0
    streak_total = 0.0
    for day in recent:
        net = float(day.get("fii_net", 0))
        if net > 0:
            streak += 1
            streak_total += net
        else:
            streak = 0
            streak_total = 0.0

    if streak >= 5:
        daily_avg = streak_total / streak
        signals.append(Signal(
            id=_make_signal_id("NIFTY", "FII_STREAK", recent[-1].get("date", ""), str(streak)),
            symbol="NIFTY",
            company_name="NSE Nifty 50 Index",
            signal_type=SignalType.FII_ACCUMULATION,
            headline=f"FII buying streak: {streak} consecutive days, ₹{streak_total/100:.0f} Cr net inflow",
            detail=(f"Foreign Institutional Investors (FIIs) have been net buyers for {streak} "
                    f"consecutive trading days with a cumulative net inflow of ₹{streak_total:.0f} Cr "
                    f"(₹{daily_avg:.0f} Cr/day average). "
                    f"Sustained FII buying of this magnitude typically precedes an index rally of 3-7% "
                    f"within the next 3-4 weeks."),
            confidence_score=min(0.80, 0.55 + streak * 0.04),
            signal_date=recent[-1].get("date", datetime.now().strftime("%Y-%m-%d")),
            stock_price_at_signal=0.0,
            expected_impact=SignalDirection.BULLISH,
            data_sources=["NSE FII/DII Data"],
            tags=["fii", "accumulation", "streak", "macro", "bullish"],
            raw_data={"streak_days": streak, "total_inflow_cr": streak_total},
        ))

    # Single-day large inflow
    if recent:
        last_day = recent[-1]
        fii_net = float(last_day.get("fii_net", 0))
        if abs(fii_net) >= 3000:
            direction = SignalDirection.BULLISH if fii_net > 0 else SignalDirection.BEARISH
            action = "bought" if fii_net > 0 else "sold"
            signals.append(Signal(
                id=_make_signal_id("NIFTY", "FII_LARGE_DAY", last_day.get("date", ""), str(fii_net)),
                symbol="NIFTY",
                company_name="NSE Nifty 50 Index",
                signal_type=SignalType.FII_ACCUMULATION,
                headline=f"FIIs {action} ₹{abs(fii_net)/100:.0f} Cr net in single session",
                detail=(f"FIIs were significant {'buyers' if fii_net > 0 else 'sellers'} in today's session, "
                        f"with a net {action} value of ₹{abs(fii_net):.0f} Cr. "
                        f"Meanwhile, DIIs {'bought' if last_day.get('dii_net', 0) > 0 else 'sold'} "
                        f"₹{abs(float(last_day.get('dii_net', 0))):.0f} Cr. "
                        f"Large FII flows in a single session often indicate positioning ahead of expected catalysts."),
                confidence_score=0.65,
                signal_date=last_day.get("date", datetime.now().strftime("%Y-%m-%d")),
                stock_price_at_signal=0.0,
                expected_impact=direction,
                data_sources=["NSE FII/DII Data"],
                tags=["fii", "large_flow", "macro", direction.value.lower()],
                raw_data=last_day,
            ))

    return signals


def score_and_rank_signals(signals: List[Signal]) -> List[Signal]:
    """
    Apply composite scoring and sort signals by relevance.

    Scoring weights:
    - Base confidence_score
    - Recency: < 2 days = 1.3x, < 5 days = 1.1x
    - Category: Promoter insider = 1.5x, Institutional bulk = 1.2x, Filing = 1.0x
    - Direction: BULLISH = slight preference in ranking

    Args:
        signals: Unranked list of Signal objects.

    Returns:
        Signals sorted by composite score, highest first.
    """
    def composite_score(sig: Signal) -> float:
        score = sig.confidence_score

        # Recency weight
        days = _days_ago(sig.signal_date)
        if days <= 2:
            score *= 1.3
        elif days <= 5:
            score *= 1.1

        # Category/type weight
        if sig.signal_type == SignalType.INSIDER_TRADE:
            score *= 1.4
            if "cluster" in sig.headline.lower():
                score *= 1.2
        elif sig.signal_type == SignalType.BULK_DEAL:
            score *= 1.2
        elif sig.signal_type == SignalType.FII_ACCUMULATION:
            score *= 1.15
        elif sig.signal_type == SignalType.CORPORATE_ACTION:
            score *= 1.1

        # Slight boost for bullish signals (user preference)
        if sig.expected_impact == SignalDirection.BULLISH:
            score *= 1.05

        return score

    return sorted(signals, key=composite_score, reverse=True)


async def run_radar(use_cache: bool = True) -> RadarResponse:
    """
    Orchestrate the full Opportunity Radar scan.

    1. Fetch all data sources (insider trades, bulk deals, filings, FII data)
    2. Run all signal detection algorithms
    3. Score and rank all signals
    4. Enrich top 10 with Claude AI analysis
    5. Return complete RadarResponse

    Args:
        use_cache: Whether to use cached data (True) or force fresh fetch.

    Returns:
        RadarResponse with all detected signals.
    """
    import time
    from app.services import data_service, claude_service
    from app.services.cache_service import cache

    start_time = time.time()

    # Try cache first
    if use_cache:
        cached = cache.get_signals()
        if cached:
            logger.info("Returning cached radar signals")
            return RadarResponse(**cached)

    logger.info("Running full Opportunity Radar scan...")

    # Fetch all data concurrently
    import asyncio
    insider_trades, bulk_deals, filings, fii_data = await asyncio.gather(
        data_service.get_insider_trades(),
        data_service.get_bulk_block_deals(),
        data_service.get_corporate_filings(),
        data_service.get_fii_dii_data(days=15),
        return_exceptions=True,
    )

    # Handle exceptions from gather
    insider_trades = insider_trades if isinstance(insider_trades, list) else []
    bulk_deals = bulk_deals if isinstance(bulk_deals, list) else []
    filings = filings if isinstance(filings, list) else []
    fii_data = fii_data if isinstance(fii_data, list) else []

    # Run signal detection
    all_signals = []
    all_signals.extend(detect_insider_signals(insider_trades))
    all_signals.extend(detect_bulk_deal_signals(bulk_deals))
    all_signals.extend(detect_filing_signals(filings))
    all_signals.extend(detect_fii_accumulation(fii_data))

    # Score and rank
    ranked_signals = score_and_rank_signals(all_signals)

    # Enrich top 10 with Claude analysis (async)
    top_signals = ranked_signals[:10]
    enrichment_tasks = []
    for sig in top_signals:
        enrichment_tasks.append(
            claude_service.analyze_signal(
                signal_data={
                    "symbol": sig.symbol,
                    "signal_type": sig.signal_type,
                    "headline": sig.headline,
                    "detail": sig.detail,
                    "confidence_score": sig.confidence_score,
                    **(sig.raw_data or {}),
                },
                signal_type=str(sig.signal_type),
            )
        )

    try:
        analyses = await asyncio.gather(*enrichment_tasks, return_exceptions=True)
        for sig, analysis in zip(top_signals, analyses):
            if isinstance(analysis, str):
                sig.ai_analysis = analysis
    except Exception as e:
        logger.warning(f"Signal enrichment partial failure: {e}")

    # Compute summary stats
    bullish_count = sum(1 for s in ranked_signals if s.expected_impact == SignalDirection.BULLISH)
    bearish_count = sum(1 for s in ranked_signals if s.expected_impact == SignalDirection.BEARISH)

    sentiment = MarketSentiment.NEUTRAL
    if bullish_count > bearish_count * 1.5:
        sentiment = MarketSentiment.BULLISH
    elif bearish_count > bullish_count * 1.5:
        sentiment = MarketSentiment.BEARISH

    # Top opportunities: unique symbols from top bullish signals
    top_opps = list(dict.fromkeys(
        s.symbol for s in ranked_signals
        if s.expected_impact == SignalDirection.BULLISH and s.symbol != "NIFTY"
    ))[:5]

    elapsed = round(time.time() - start_time, 2)
    response = RadarResponse(
        signals=ranked_signals,
        generated_at=datetime.now().isoformat(),
        total_count=len(ranked_signals),
        bullish_count=bullish_count,
        bearish_count=bearish_count,
        market_sentiment=sentiment,
        top_opportunities=top_opps,
        scan_metadata={
            "scan_time_seconds": elapsed,
            "insider_trades_analyzed": len(insider_trades),
            "bulk_deals_analyzed": len(bulk_deals),
            "filings_analyzed": len(filings),
            "fii_days_analyzed": len(fii_data),
            "signals_detected": len(ranked_signals),
        },
    )

    # Cache the result
    try:
        cache.cache_signals(response.model_dump())
    except Exception as e:
        logger.warning(f"Failed to cache signals: {e}")

    logger.info(f"Radar scan complete: {len(ranked_signals)} signals in {elapsed}s")
    return response
