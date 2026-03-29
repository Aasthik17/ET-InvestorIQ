"""
ET InvestorIQ — Filing Matcher Service
Scenario 1 (Bulk Deal Distress): Links NSE/BSE corporate filings to bulk deal events
by matching symbol + deal date, returning a structured filing citation for alerts.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


def _parse_date(value: str) -> Optional[datetime]:
    """Parse a YYYY-MM-DD string to datetime, silently return None on failure."""
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d")
    except Exception:
        return None


def match_filing_to_deal(
    symbol: str,
    deal_date: str,
    filings: list[dict],
    window_days: int = 3,
) -> Optional[dict]:
    """
    Find the closest corporate filing for the given symbol within ±window_days of
    the bulk deal date.

    Args:
        symbol:      NSE ticker (e.g. 'HINDULEVR').
        deal_date:   YYYY-MM-DD string of the bulk deal.
        filings:     List of filing dicts from data_service.get_corporate_filings().
        window_days: Maximum number of days either side of deal_date to search.

    Returns:
        A citation dict with filing metadata, or None if no match found.
    """
    sym = symbol.upper().replace(".NS", "")
    deal_dt = _parse_date(deal_date)
    if deal_dt is None:
        return None

    window = timedelta(days=window_days)
    best: Optional[dict] = None
    best_delta: Optional[int] = None

    for filing in filings or []:
        filing_sym = str(filing.get("symbol", "")).upper().replace(".NS", "")
        if filing_sym != sym:
            continue
        filing_dt = _parse_date(filing.get("date", ""))
        if filing_dt is None:
            continue

        delta = abs((filing_dt - deal_dt).days)
        if delta > window_days:
            continue

        if best_delta is None or delta < best_delta:
            best_delta = delta
            best = filing

    if best is None:
        return None

    return {
        "exchange": best.get("source", "BSE/NSE"),
        "filing_date": best.get("date", deal_date),
        "category": best.get("category", "General"),
        "subject": best.get("subject") or best.get("headline", "Corporate disclosure"),
        "headline": best.get("headline") or best.get("subject", ""),
        "delta_days": best_delta,
        "citation": (
            f"[{best.get('source', 'BSE/NSE')}] {best.get('category', 'Disclosure')} · "
            f"Filed {best.get('date', deal_date)} — "
            f"\"{(best.get('headline') or best.get('subject', ''))[:100]}\""
        ),
    }


def classify_bulk_deal(deal: dict) -> dict:
    """
    Classify a bulk deal as PROMOTER_DISTRESS, ROUTINE_BLOCK, or INSTITUTIONAL_ACCUMULATION.

    Distress indicators:
      - Seller category is Promoter/Promoter Group
      - Sale at > 3% discount to closing price (price_discount_pct)
      - Stake sold > 1% of total shareholding

    Returns a dict with: deal_class, distress_probability, reasoning
    """
    client = str(deal.get("client_name", "")).lower()
    side = str(deal.get("buy_sell", "")).upper()
    value_cr = float(deal.get("value_cr", 0) or 0)
    qty = int(deal.get("quantity", 0) or 0)
    price = float(deal.get("price", 0) or 0)
    deal_type = str(deal.get("deal_type", "")).upper()

    # Promoter keywords
    promoter_keywords = ["promoter", "promoter group", "founder", "managing director", "chairman"]
    is_promoter = any(kw in client for kw in promoter_keywords)

    is_sell = side == "SELL" or "SELL" in deal_type

    # Stake approximation from deal value — large value = large stake
    # Heuristic: >₹50 Cr bulk sell by promoter at discount = distress
    stake_proxy = value_cr  # ₹ Cr sold
    price_discount_pct = float(deal.get("price_discount_pct", 0) or 0)

    distress_score = 0.0
    reasons: list[str] = []

    if is_promoter and is_sell:
        distress_score += 0.45
        reasons.append("Promoter is the seller")
    if price_discount_pct >= 3.0:
        distress_score += 0.25
        reasons.append(f"Sale at {price_discount_pct:.1f}% discount to market price")
    elif price_discount_pct >= 1.5:
        distress_score += 0.12
        reasons.append(f"Sale at {price_discount_pct:.1f}% discount")
    if stake_proxy >= 50:
        distress_score += 0.20
        reasons.append(f"Large sale: ₹{stake_proxy:.0f} Cr")
    elif stake_proxy >= 20:
        distress_score += 0.10

    distress_score = round(min(distress_score, 0.95), 2)

    if distress_score >= 0.60:
        deal_class = "PROMOTER_DISTRESS"
    elif is_promoter and is_sell:
        deal_class = "PROMOTER_ROUTINE_SALE"
    elif is_sell:
        deal_class = "INSTITUTIONAL_EXIT"
    else:
        deal_class = "INSTITUTIONAL_ACCUMULATION"

    return {
        "deal_class": deal_class,
        "distress_probability": distress_score,
        "is_promoter_seller": is_promoter and is_sell,
        "reasoning": "; ".join(reasons) if reasons else "Standard institutional transaction",
    }
