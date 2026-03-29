"""
Radar Pipeline — 5-step autonomous signal intelligence agent.

Step 1: Ingest raw data (NSE bulk deals, insider trades, filings)
Step 2: Detect signals (run signal_engine anomaly detection)
Step 3: Enrich with context (Claude analyses each signal's WHY)
Step 4: Personalise (boost signals relevant to user's portfolio)
Step 5: Generate actionable alerts (specific entry/target/stop)

Zero human input between steps. Each step reads from AgentContext
and writes back to it before passing to the next step.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from .orchestrator import AgentContext, AgentOrchestrator, AgentStep

logger = logging.getLogger(__name__)


def _normalise_date(value: Any) -> str:
    if not value:
        return datetime.now().strftime("%Y-%m-%d")

    raw = str(value).strip()
    for fmt in (
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d-%b-%Y",
        "%d %b %Y",
        "%Y%m%d",
    ):
        try:
            return datetime.strptime(raw[:19], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw[:10]


def _normalise_insider_trades(trades: list[dict]) -> list[dict]:
    normalised: list[dict] = []
    for trade in trades or []:
        quantity = int(float(trade.get("quantity", 0) or 0))
        value_cr = float(trade.get("value_cr", 0) or 0)
        explicit_price = float(trade.get("price_at_trade", trade.get("price", 0)) or 0)
        derived_price = round((value_cr * 1e7) / quantity, 2) if quantity and value_cr else 0.0
        normalised.append(
            {
                **trade,
                "symbol": str(trade.get("symbol", "")).upper().replace(".NS", ""),
                "person_name": trade.get("person_name", ""),
                "category": str(trade.get("category", "Promoter")).title(),
                "trade_type": str(trade.get("trade_type", "")).title(),
                "quantity": quantity,
                "value_cr": round(value_cr, 2),
                "date": _normalise_date(trade.get("date")),
                "price_at_trade": explicit_price or derived_price,
                "pre_transaction_holding_pct": float(
                    trade.get("pre_transaction_holding_pct", trade.get("pre_holding_pct", 0)) or 0
                ),
                "post_transaction_holding_pct": float(
                    trade.get("post_transaction_holding_pct", trade.get("post_holding_pct", 0)) or 0
                ),
            }
        )
    return normalised


def _normalise_deals(deals: list[dict], label: str) -> list[dict]:
    normalised: list[dict] = []
    for deal in deals or []:
        side = str(deal.get("buy_sell", "BUY")).upper()
        bucket = str(deal.get("deal_type", label)).upper()
        normalised.append(
            {
                **deal,
                "symbol": str(deal.get("symbol", "")).upper().replace(".NS", ""),
                "client_name": deal.get("client_name", ""),
                "buy_sell": side,
                "quantity": int(float(deal.get("quantity", 0) or 0)),
                "price": float(deal.get("price", 0) or 0),
                "value_cr": float(deal.get("value_cr", 0) or 0),
                "date": _normalise_date(deal.get("date")),
                # The signal engine currently infers side from deal_type.
                "deal_type": f"{bucket} {side}",
            }
        )
    return normalised


def _normalise_filings(filings: list[dict]) -> list[dict]:
    normalised: list[dict] = []
    for filing in filings or []:
        symbol = str(filing.get("symbol", "")).upper().replace(".NS", "")
        normalised.append(
            {
                **filing,
                "symbol": symbol,
                "company": filing.get("company", symbol),
                "subject": filing.get("subject") or filing.get("headline", ""),
                "headline": filing.get("headline") or filing.get("subject", ""),
                "category": filing.get("category", "General"),
                "date": _normalise_date(filing.get("date")),
                "source": filing.get("source", "BSE/NSE"),
            }
        )
    return normalised


async def step_ingest_data(ctx: AgentContext) -> AgentContext:
    """
    Pull fresh data from all sources: NSE bulk deals, insider trades,
    corporate filings, top movers, FII/DII flows.
    Populates ctx.raw_data.
    """

    from app.services.data_service import (
        get_bulk_block_deals,
        get_corporate_filings,
        get_fii_dii_data,
        get_index_quotes,
        get_insider_trades,
        get_top_movers,
    )

    deals_task = asyncio.create_task(get_bulk_block_deals(days_back=7))
    insider_task = asyncio.create_task(get_insider_trades(days_back=14))
    filings_task = asyncio.create_task(get_corporate_filings(days_back=3))
    fii_task = asyncio.create_task(get_fii_dii_data(days=10))
    movers_task = asyncio.create_task(get_top_movers())
    indices_task = asyncio.create_task(get_index_quotes())

    deals, insiders, filings, fii_dii, movers, indices = await asyncio.gather(
        deals_task,
        insider_task,
        filings_task,
        fii_task,
        movers_task,
        indices_task,
    )

    bulk_deals = _normalise_deals((deals or {}).get("bulk", []), "BULK")
    block_deals = _normalise_deals((deals or {}).get("block", []), "BLOCK")
    insider_trades = _normalise_insider_trades(insiders if isinstance(insiders, list) else [])
    corporate_filings = _normalise_filings(filings if isinstance(filings, list) else [])

    ctx.raw_data = {
        "bulk_deals": bulk_deals,
        "block_deals": block_deals,
        "insider_trades": insider_trades,
        "filings": corporate_filings,
        "fii_dii": fii_dii if isinstance(fii_dii, list) else [],
        "top_movers": movers if isinstance(movers, dict) else {"gainers": [], "losers": []},
        "indices": indices if isinstance(indices, dict) else {},
    }

    total_records = (
        len(bulk_deals)
        + len(block_deals)
        + len(insider_trades)
        + len(corporate_filings)
        + len(ctx.raw_data["fii_dii"])
    )

    ctx.metadata["step_0_summary"] = (
        f"Ingested {total_records} records: "
        f"{len(insider_trades)} insider trades, "
        f"{len(bulk_deals) + len(block_deals)} bulk/block deals, "
        f"{len(corporate_filings)} filings, "
        f"{len(ctx.raw_data['fii_dii'])} FII/DII sessions."
    )
    return ctx


async def step_detect_signals(ctx: AgentContext) -> AgentContext:
    """
    Run signal_engine anomaly detection on raw data.
    Produces a list of scored Signal objects.
    """

    from app.modules.opportunity_radar.signal_engine import (
        detect_bulk_deal_signals,
        detect_fii_accumulation,
        detect_filing_signals,
        detect_insider_signals,
        score_and_rank_signals,
    )

    loop = asyncio.get_running_loop()

    insider_task = loop.run_in_executor(None, detect_insider_signals, ctx.raw_data.get("insider_trades", []))
    bulk_task = loop.run_in_executor(
        None,
        detect_bulk_deal_signals,
        ctx.raw_data.get("bulk_deals", []) + ctx.raw_data.get("block_deals", []),
    )
    filing_task = loop.run_in_executor(None, detect_filing_signals, ctx.raw_data.get("filings", []))
    fii_task = loop.run_in_executor(None, detect_fii_accumulation, ctx.raw_data.get("fii_dii", []))

    insider_sigs, bulk_sigs, filing_sigs, fii_sigs = await asyncio.gather(
        insider_task,
        bulk_task,
        filing_task,
        fii_task,
    )

    all_signals = insider_sigs + bulk_sigs + filing_sigs + fii_sigs
    ctx.signals = await loop.run_in_executor(None, score_and_rank_signals, all_signals)

    bullish = sum(1 for signal in ctx.signals if str(signal.expected_impact).upper() == "BULLISH")
    bearish = sum(1 for signal in ctx.signals if str(signal.expected_impact).upper() == "BEARISH")
    top_signal = ctx.signals[0].headline if ctx.signals else "none"

    ctx.metadata["step_1_summary"] = (
        f"Detected {len(ctx.signals)} signals: {bullish} bullish, {bearish} bearish. "
        f"Top signal: {top_signal}."
    )
    return ctx


async def step_enrich_with_context(ctx: AgentContext) -> AgentContext:
    """
    For each top signal, call Claude to add context on why the signal matters.
    Enriches top 5 signals only for cost control.

    Scenario 1 (Hackathon): For BULK_DEAL promoter distress signals, also
    attaches the nearest corporate filing as a citation (using filing_matcher).
    """

    from app.services.claude_service import analyze_signal
    from app.services.data_service import get_fundamentals
    from app.services.filing_matcher import match_filing_to_deal

    indices = ctx.raw_data.get("indices", {})
    nifty_change = float(((indices.get("nifty50") or {}).get("change_pct")) or 0)
    market_mood = "bullish" if nifty_change > 0.5 else "bearish" if nifty_change < -0.5 else "flat"

    all_filings = ctx.raw_data.get("filings", [])
    enriched: list[dict] = []

    for signal in ctx.signals[:5]:
        fundamentals: dict[str, Any] = {}
        analysis = "Analysis unavailable."
        filing_citation = None

        try:
            fundamentals = await get_fundamentals(signal.symbol)
        except Exception as exc:
            logger.warning("Fundamentals fetch failed for %s: %s", signal.symbol, exc)

        # ── Scenario 1: Filing citation for promoter distress signals ─────────
        raw = signal.raw_data or {}
        deal_class = raw.get("deal_class", "")
        distress_prob = float(raw.get("distress_probability", 0.0))

        if str(signal.signal_type) in ("SignalType.BULK_DEAL", "BULK_DEAL") and distress_prob > 0.3:
            try:
                citation = match_filing_to_deal(
                    symbol=signal.symbol,
                    deal_date=signal.signal_date,
                    filings=all_filings,
                    window_days=3,
                )
                if citation:
                    filing_citation = citation
            except Exception as exc:
                logger.warning("Filing match failed for %s: %s", signal.symbol, exc)

        # ── Claude enrichment ─────────────────────────────────────────────────
        try:
            signal_payload: dict[str, Any] = {
                "symbol": signal.symbol,
                "signal_type": str(signal.signal_type),
                "headline": signal.headline,
                "detail": signal.detail,
                "confidence": signal.confidence_score,
                "expected_impact": str(signal.expected_impact),
                "market_mood": market_mood,
                "nifty_change_pct": nifty_change,
                "fundamentals": fundamentals,
                "signal_date": signal.signal_date,
            }
            # Inject distress data so Claude can produce filing-aware analysis
            if deal_class:
                signal_payload["deal_class"] = deal_class
                signal_payload["distress_probability"] = distress_prob
                signal_payload["distress_reasoning"] = raw.get("distress_reasoning", "")
            if filing_citation:
                signal_payload["filing_citation"] = filing_citation

            analysis = await analyze_signal(
                signal_data=signal_payload,
                signal_type=str(signal.signal_type),
            )
        except Exception as exc:
            logger.warning("Enrichment failed for %s: %s", signal.symbol, exc)

        enriched.append(
            {
                "signal": signal,
                "analysis": analysis,
                "fundamentals": fundamentals,
                "filing_citation": filing_citation,
                "deal_class": deal_class,
                "distress_probability": distress_prob,
                "market_context": {
                    "mood": market_mood,
                    "nifty_change": nifty_change,
                },
            }
        )

    ctx.enriched = enriched
    ctx.metadata["step_2_summary"] = (
        f"Enriched top {len(enriched)} signals with Claude market analysis. "
        f"Market mood: {market_mood}. "
        f"Nifty {'+' if nifty_change >= 0 else ''}{nifty_change:.2f}%."
    )
    return ctx


async def step_personalise(ctx: AgentContext) -> AgentContext:
    """
    Score each enriched signal against the user's portfolio.
    Direct holdings get the strongest boost, sector exposure gets a lighter one.
    """

    holdings = ctx.portfolio.get("holdings", []) or []
    held_symbols = {str(holding.get("symbol", "")).upper() for holding in holdings}
    risk_profile = str(ctx.portfolio.get("risk_profile", "MODERATE")).upper()

    sector_map = {
        "HDFCBANK": "Banking",
        "ICICIBANK": "Banking",
        "SBIN": "Banking",
        "AXISBANK": "Banking",
        "KOTAKBANK": "Banking",
        "BANDHANBNK": "Banking",
        "TCS": "IT",
        "INFY": "IT",
        "WIPRO": "IT",
        "HCLTECH": "IT",
        "TECHM": "IT",
        "RELIANCE": "Energy",
        "ONGC": "Energy",
        "BPCL": "Energy",
        "IOC": "Energy",
        "SUNPHARMA": "Pharma",
        "DRREDDY": "Pharma",
        "CIPLA": "Pharma",
        "DIVISLAB": "Pharma",
        "MARUTI": "Auto",
        "TATAMOTORS": "Auto",
        "M&M": "Auto",
        "BAJAJ-AUTO": "Auto",
        "HINDUNILVR": "FMCG",
        "ITC": "FMCG",
        "NESTLEIND": "FMCG",
        "BRITANNIA": "FMCG",
    }
    held_sectors = {sector_map.get(symbol, "Unknown") for symbol in held_symbols}

    personalised = []
    for item in ctx.enriched:
        signal = item["signal"]
        sym = signal.symbol.upper()
        fund = item.get("fundamentals", {})
        sector = fund.get("sector") or sector_map.get(sym, "Unknown")
        score = float(signal.confidence_score)

        if sym in held_symbols:
            score *= 2.0
            holding = next(
                (candidate for candidate in holdings if str(candidate.get("symbol", "")).upper() == sym),
                {},
            )
            qty = int(float(holding.get("quantity", 0) or 0))
            avg_cost = float(holding.get("avg_cost", 0) or 0)
            portfolio_note = (
                f"You hold {qty:,} shares at avg ₹{avg_cost:,.2f}. "
                f"This signal directly affects your position."
            )
            relevance = "DIRECT_HOLDING"
        elif sector in held_sectors and sector != "Unknown":
            score *= 1.3
            portfolio_note = (
                f"You have exposure to the {sector} sector. "
                f"This signal may affect your portfolio indirectly."
            )
            relevance = "SECTOR_EXPOSURE"
        else:
            portfolio_note = (
                "You have no current exposure to this stock. "
                f"This could be a new opportunity aligned with your {risk_profile.lower()} risk profile."
            )
            relevance = "NEW_OPPORTUNITY"

        if risk_profile == "CONSERVATIVE" and str(signal.expected_impact).upper() == "BULLISH":
            score *= 0.9
        elif risk_profile == "AGGRESSIVE" and score > 0.6:
            score *= 1.1

        personalised.append(
            {
                **item,
                "personalised_score": round(min(score, 1.0), 3),
                "portfolio_note": portfolio_note,
                "relevance": relevance,
                "sector": sector,
            }
        )

    ctx.personalised = sorted(
        personalised,
        key=lambda item: item.get("personalised_score", 0),
        reverse=True,
    )

    direct_count = sum(1 for item in ctx.personalised if item.get("relevance") == "DIRECT_HOLDING")
    ctx.metadata["step_3_summary"] = (
        f"Personalised {len(ctx.personalised)} signals for {len(held_symbols)} portfolio holdings. "
        f"{direct_count} signals directly affect your positions."
    )
    return ctx


async def step_generate_alerts(ctx: AgentContext) -> AgentContext:
    """
    For the top 3 personalised signals, generate a complete actionable alert.

    Scenario 1 (Hackathon): Alerts for PROMOTER_DISTRESS bulk deals include
    a filing_citation block and distress_probability so the frontend can
    display 'Alert cites the filing — not just a vague warning.'
    """

    alerts = []
    for rank, item in enumerate(ctx.personalised[:3], start=1):
        signal = item["signal"]
        score = float(item.get("personalised_score", signal.confidence_score))
        analysis = item.get("analysis") or getattr(signal, "ai_analysis", "") or "Analysis unavailable."
        fundamentals = item.get("fundamentals", {}) or {}
        note = item.get("portfolio_note", "")
        current_price = float(
            fundamentals.get("current_price")
            or getattr(signal, "stock_price_at_signal", 0)
            or 0
        )

        # Scenario 1 distress metadata
        filing_citation = item.get("filing_citation")
        deal_class = item.get("deal_class", "")
        distress_prob = float(item.get("distress_probability", 0.0))

        direction = str(signal.expected_impact).upper()
        if direction == "BULLISH":
            entry_low = round(current_price * 0.99, 2) if current_price else None
            entry_high = round(current_price * 1.01, 2) if current_price else None
            target = round(current_price * 1.08, 2) if current_price else None
            stop_loss = round(current_price * 0.95, 2) if current_price else None
            horizon = "2-4 weeks"
            action = "BUY"
        elif direction == "BEARISH":
            entry_low = round(current_price * 0.99, 2) if current_price else None
            entry_high = round(current_price * 1.01, 2) if current_price else None
            target = round(current_price * 0.93, 2) if current_price else None
            stop_loss = round(current_price * 1.04, 2) if current_price else None
            horizon = "1-3 weeks"
            action = "SELL"
        else:
            entry_low = entry_high = target = stop_loss = None
            horizon = "Monitor"
            action = "WATCH"

        conviction = "HIGH" if score >= 0.75 else "MEDIUM" if score >= 0.50 else "LOW"
        alert = {
            "rank": rank,
            "symbol": signal.symbol,
            "company_name": fundamentals.get("company_name", getattr(signal, "company_name", signal.symbol)),
            "action": action,
            "conviction": conviction,
            "signal_type": str(signal.signal_type),
            "headline": signal.headline,
            "reasoning": analysis,
            "portfolio_note": note,
            "relevance": item.get("relevance"),
            "trade_levels": {
                "entry_low": entry_low,
                "entry_high": entry_high,
                "target": target,
                "stop_loss": stop_loss,
                "horizon": horizon,
            },
            "scores": {
                "signal_confidence": round(float(signal.confidence_score), 2),
                "personalised_score": round(score, 2),
            },
            "data_sources": list(getattr(signal, "data_sources", [])),
            "detected_on": getattr(signal, "signal_date", ""),
            # ── Scenario 1: Filing citation & distress fields ─────────────────
            "filing_citation": filing_citation,
            "deal_class": deal_class or None,
            "distress_probability": distress_prob if distress_prob > 0 else None,
        }
        alerts.append(alert)

    ctx.alerts = alerts
    ctx.metadata["step_4_summary"] = (
        f"Generated {len(alerts)} actionable alerts. "
        f"Top alert: {alerts[0]['action']} {alerts[0]['symbol']} with {alerts[0]['conviction']} conviction."
        if alerts
        else "No alerts generated."
    )
    return ctx


def create_radar_pipeline() -> AgentOrchestrator:
    """Factory function that returns the configured 5-step Radar pipeline."""

    return AgentOrchestrator(
        "Opportunity Radar",
        [
            AgentStep(
                name="Data Ingestion",
                description="Pulling live NSE bulk deals, insider trades, and corporate filings",
                fn=step_ingest_data,
            ),
            AgentStep(
                name="Signal Detection",
                description="Running anomaly detection across all ingested records",
                fn=step_detect_signals,
            ),
            AgentStep(
                name="Context Enrichment",
                description="Asking Claude to explain why each signal matters in today's market",
                fn=step_enrich_with_context,
            ),
            AgentStep(
                name="Portfolio Personalisation",
                description="Scoring signals against your holdings and risk profile",
                fn=step_personalise,
            ),
            AgentStep(
                name="Alert Generation",
                description="Generating actionable alerts with entry, target, and stop-loss levels",
                fn=step_generate_alerts,
            ),
        ],
    )
