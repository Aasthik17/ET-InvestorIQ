"""
ET InvestorIQ — News Impact Scorer
Scenario 3 (Portfolio News Prioritisation): Quantifies the estimated ₹ P&L impact
of macro / sector news events on a user's specific portfolio holdings.

Uses pre-defined sector impact multipliers calibrated against historical Indian
market reactions to common event types (RBI rate decisions, sectoral regulations, etc.).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# ─── Sector affiliation map ────────────────────────────────────────────────────

SYMBOL_TO_SECTOR: dict[str, str] = {
    # Banking / NBFC
    "HDFCBANK": "Banking", "ICICIBANK": "Banking", "SBIN": "Banking",
    "AXISBANK": "Banking", "KOTAKBANK": "Banking", "BANDHANBNK": "Banking",
    "BAJFINANCE": "NBFC", "BAJAJFINSV": "NBFC", "MUTHOOTFIN": "NBFC",
    # IT
    "TCS": "IT", "INFY": "IT", "WIPRO": "IT", "HCLTECH": "IT",
    "TECHM": "IT", "LTIM": "IT",
    # Energy
    "RELIANCE": "Energy", "ONGC": "Energy", "BPCL": "Energy", "IOC": "Energy",
    "POWERGRID": "Power", "NTPC": "Power", "ADANIGREEN": "Power",
    # Pharma
    "SUNPHARMA": "Pharma", "DRREDDY": "Pharma", "CIPLA": "Pharma",
    "DIVISLAB": "Pharma", "AUROPHARMA": "Pharma",
    # Auto
    "MARUTI": "Auto", "TATAMOTORS": "Auto", "M&M": "Auto",
    "BAJAJ-AUTO": "Auto", "HEROMOOTO": "Auto",
    # FMCG
    "HINDUNILVR": "FMCG", "ITC": "FMCG", "NESTLEIND": "FMCG",
    "BRITANNIA": "FMCG", "DABUR": "FMCG", "MARICO": "FMCG",
    # Metals
    "TATASTEEL": "Metals", "JSWSTEEL": "Metals", "HINDALCO": "Metals",
    "COALINDIA": "Metals", "SAIL": "Metals",
    # Telecom
    "BHARTIARTL": "Telecom", "VODAFONE": "Telecom",
    # Infra / Realty
    "LT": "Infra", "DLF": "Realty", "GODREJPROP": "Realty",
}


# ─── Event type → sector impact map ───────────────────────────────────────────
# Values: estimated % move for each sector given the event.
# Positive = gain, Negative = loss. Calibrated on Indian market historical data.

EVENT_IMPACT_MAP: dict[str, dict[str, float]] = {
    "RBI_RATE_CUT": {
        "Banking": +1.8, "NBFC": +2.5, "Realty": +3.0, "Infra": +1.5,
        "Auto": +1.2, "FMCG": +0.8, "IT": +0.3, "Energy": +0.4,
        "Pharma": +0.2, "Metals": +0.6, "Telecom": +0.5, "Power": +1.0,
        "_default": +0.5,
    },
    "RBI_RATE_HIKE": {
        "Banking": -0.5, "NBFC": -2.0, "Realty": -3.5, "Infra": -1.8,
        "Auto": -1.5, "FMCG": -0.6, "IT": -0.2, "Energy": -0.3,
        "Pharma": -0.1, "Metals": -0.8, "Telecom": -0.7, "Power": -1.2,
        "_default": -0.6,
    },
    "RBI_RATE_HOLD": {
        "_default": 0.0,
        "Banking": +0.2, "NBFC": +0.3,
    },
    "SEBI_REGULATORY_TIGHTENING": {
        "_default": -0.8, "Banking": -1.0, "NBFC": -2.5, "Telecom": -0.5,
    },
    "SEBI_REGULATORY_EASING": {
        "_default": +0.5, "Banking": +0.8, "NBFC": +1.5,
    },
    "PHARMA_FMCG_PRICE_CAP": {
        "Pharma": -3.5, "FMCG": -2.0, "_default": 0.0,
    },
    "PHARMA_FDA_WARNING": {
        "Pharma": -4.0, "_default": 0.0,
    },
    "IMPORT_DUTY_INCREASE_METALS": {
        "Metals": +3.5, "_default": 0.0,
    },
    "IMPORT_DUTY_DECREASE_METALS": {
        "Metals": -2.5, "_default": 0.0,
    },
    "OIL_PRICE_SPIKE": {
        "Energy": +2.0, "Auto": -1.8, "FMCG": -0.5, "Pharma": -0.3, "_default": -0.3,
    },
    "OIL_PRICE_FALL": {
        "Energy": -1.5, "Auto": +1.5, "FMCG": +0.8, "Airlines": +3.0, "_default": +0.4,
    },
    "RUPEE_DEPRECIATION": {
        "IT": +2.5, "Pharma": +1.5, "Energy": -1.5, "FMCG": -0.5, "_default": -0.2,
    },
    "RUPEE_APPRECIATION": {
        "IT": -1.5, "Pharma": -1.0, "Energy": +0.8, "_default": +0.2,
    },
    "BUDGET_INFRA_PUSH": {
        "Infra": +4.0, "Metals": +2.5, "Power": +2.0, "_default": +0.5,
    },
    "GENERAL_MACRO_POSITIVE": {
        "_default": +1.0,
    },
    "GENERAL_MACRO_NEGATIVE": {
        "_default": -1.0,
    },
}


# ─── News event classifier ─────────────────────────────────────────────────────

def classify_news_event(headline: str, description: str = "") -> str:
    """
    Classify a news headline into an EVENT_IMPACT_MAP key using keyword matching.
    Returns an event type string.
    """
    text = (headline + " " + description).lower()

    if "rate cut" in text or "repo rate cut" in text or "eases" in text and "rate" in text:
        return "RBI_RATE_CUT"
    if "rate hike" in text or "rate increase" in text or "tightens" in text and "rate" in text:
        return "RBI_RATE_HIKE"
    if "rate unchanged" in text or "rates steady" in text or "hold" in text and "rate" in text:
        return "RBI_RATE_HOLD"
    if ("sebi" in text or "regulatory" in text) and (
        "tighten" in text or "restrict" in text or "curb" in text or "ban" in text
    ):
        return "SEBI_REGULATORY_TIGHTENING"
    if ("sebi" in text or "regulatory" in text) and (
        "ease" in text or "relax" in text or "allow" in text
    ):
        return "SEBI_REGULATORY_EASING"
    if "price cap" in text and ("pharma" in text or "medicine" in text or "drug" in text):
        return "PHARMA_FMCG_PRICE_CAP"
    if "fda warning" in text or "fda import alert" in text or "usfda" in text:
        return "PHARMA_FDA_WARNING"
    if "import duty" in text and "steel" in text or "metal" in text:
        if "increase" in text or "hike" in text or "raise" in text:
            return "IMPORT_DUTY_INCREASE_METALS"
        return "IMPORT_DUTY_DECREASE_METALS"
    if "crude" in text and ("spike" in text or "surge" in text or "rise" in text):
        return "OIL_PRICE_SPIKE"
    if "crude" in text and ("fall" in text or "drop" in text or "decline" in text):
        return "OIL_PRICE_FALL"
    if "rupee" in text and ("fall" in text or "weaken" in text or "depreciat" in text):
        return "RUPEE_DEPRECIATION"
    if "rupee" in text and ("rise" in text or "strengthen" in text or "appreciat" in text):
        return "RUPEE_APPRECIATION"
    if "infrastructure" in text or "capex" in text and "budget" in text:
        return "BUDGET_INFRA_PUSH"

    # Fallback
    if any(kw in text for kw in ["positive", "growth", "record", "boom", "surge", "approval"]):
        return "GENERAL_MACRO_POSITIVE"
    if any(kw in text for kw in ["negative", "slow", "concern", "risk", "probe", "penalty"]):
        return "GENERAL_MACRO_NEGATIVE"
    return "GENERAL_MACRO_POSITIVE"


def _get_sector(symbol: str, holding: dict) -> str:
    """Look up sector for a holding symbol."""
    sym = symbol.upper().replace(".NS", "")
    return SYMBOL_TO_SECTOR.get(sym, holding.get("sector", "Unknown"))


def score_news_impact(
    news_events: list[dict],
    holdings: list[dict],
) -> list[dict]:
    """
    Rank news events by their estimated financial impact on a portfolio.

    Args:
        news_events: List of dicts with keys: headline, description (optional),
                     event_type (optional — overrides classifier).
        holdings:    List of portfolio holding dicts with keys: symbol, quantity,
                     avg_cost (plus optionally ltp/current_price).

    Returns:
        Sorted list of event impact dicts (highest ₹ impact first), each containing:
          - event_type, headline, affected_sectors, total_pnl_impact_inr,
            per_holding_impact, priority_rank, materiality
    """
    if not news_events or not holdings:
        return []

    results: list[dict] = []

    for event in news_events:
        headline = str(event.get("headline", ""))
        description = str(event.get("description", ""))
        event_type = event.get("event_type") or classify_news_event(headline, description)

        sector_impacts = EVENT_IMPACT_MAP.get(event_type, EVENT_IMPACT_MAP["GENERAL_MACRO_POSITIVE"])
        default_impact = sector_impacts.get("_default", 0.0)

        affected_sectors: set[str] = set()
        per_holding: list[dict] = []
        total_inr_impact = 0.0

        for h in holdings:
            sym = str(h.get("symbol", "")).upper().replace(".NS", "")
            qty = int(float(h.get("quantity", 0) or 0))
            avg_cost = float(h.get("avg_cost", 0) or 0)
            ltp = float(h.get("ltp", h.get("current_price", avg_cost)) or avg_cost)
            current_value = qty * ltp if ltp else qty * avg_cost

            sector = _get_sector(sym, h)
            pct_impact = sector_impacts.get(sector, default_impact)

            inr_impact = round(current_value * pct_impact / 100, 0)
            total_inr_impact += inr_impact

            if pct_impact != 0:
                affected_sectors.add(sector)

            per_holding.append({
                "symbol": sym,
                "sector": sector,
                "current_value_inr": round(current_value, 0),
                "estimated_pct_impact": pct_impact,
                "estimated_inr_impact": inr_impact,
                "direction": "GAIN" if inr_impact > 0 else "LOSS" if inr_impact < 0 else "NEUTRAL",
            })

        # Sort per-holding by absolute impact
        per_holding.sort(key=lambda x: abs(x["estimated_inr_impact"]), reverse=True)

        results.append({
            "event_type": event_type,
            "headline": headline,
            "description": description,
            "affected_sectors": sorted(affected_sectors),
            "total_pnl_impact_inr": round(total_inr_impact, 0),
            "per_holding_impact": per_holding,
            "materiality": (
                "HIGH" if abs(total_inr_impact) > 10_000
                else "MEDIUM" if abs(total_inr_impact) > 2_000
                else "LOW"
            ),
            "direction": "GAIN" if total_inr_impact > 0 else "LOSS" if total_inr_impact < 0 else "NEUTRAL",
        })

    # Rank by absolute total impact (most financially material first)
    results.sort(key=lambda x: abs(x["total_pnl_impact_inr"]), reverse=True)
    for i, r in enumerate(results):
        r["priority_rank"] = i + 1

    return results
