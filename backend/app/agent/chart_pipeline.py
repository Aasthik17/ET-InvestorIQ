"""
Chart Pipeline — 4-step autonomous chart analysis agent.
From raw OHLCV ingestion to actionable trade alert, zero human input.
"""

from __future__ import annotations

import asyncio
import logging

from .orchestrator import AgentContext, AgentOrchestrator, AgentStep

logger = logging.getLogger(__name__)


async def step_ingest_ohlcv(ctx: AgentContext) -> AgentContext:
    """
    Fetch one year of daily OHLCV data for ctx.metadata["symbol"].
    Also fetches fundamentals and the latest quote.
    """

    from app.services.data_service import get_fundamentals, get_ohlcv, get_stock_quote

    symbol = str(ctx.metadata.get("symbol", "RELIANCE")).upper().replace(".NS", "")
    ohlcv_task = asyncio.create_task(get_ohlcv(symbol, "1y", "1d"))
    fundamentals_task = asyncio.create_task(get_fundamentals(symbol))
    quote_task = asyncio.create_task(get_stock_quote(symbol))

    ohlcv, fundamentals, quote = await asyncio.gather(
        ohlcv_task,
        fundamentals_task,
        quote_task,
    )

    ctx.raw_data = {
        "symbol": symbol,
        "ohlcv": ohlcv if isinstance(ohlcv, list) else [],
        "fundamentals": fundamentals if isinstance(fundamentals, dict) else {},
        "quote": quote if isinstance(quote, dict) else {},
    }
    ctx.metadata["step_0_summary"] = (
        f"Ingested {len(ctx.raw_data['ohlcv'])} daily candles for {symbol}. "
        f"Current price: ₹{ctx.raw_data['quote'].get('ltp', '—')}. "
        f"52W range: ₹{ctx.raw_data['fundamentals'].get('52w_low', '—')} - "
        f"₹{ctx.raw_data['fundamentals'].get('52w_high', '—')}."
    )
    return ctx


async def step_detect_chart_patterns(ctx: AgentContext) -> AgentContext:
    """
    Run the technical pattern detector on OHLCV data and attach backtests.
    """

    import pandas as pd

    from app.modules.chart_pattern.pattern_detector import backtest_pattern, detect_patterns
    from app.modules.chart_pattern.schemas import PatternType

    ohlcv = ctx.raw_data.get("ohlcv", [])
    symbol = ctx.raw_data.get("symbol", "RELIANCE")

    if not ohlcv:
        ctx.signals = []
        ctx.metadata["step_1_summary"] = "No OHLCV data available; pattern detection skipped."
        return ctx

    df = pd.DataFrame(ohlcv)
    rename_map = {
        "open": "Open",
        "high": "High",
        "low": "Low",
        "close": "Close",
        "volume": "Volume",
    }
    df["date"] = pd.to_datetime(df["date"])
    df = df.rename(columns=rename_map).set_index("date")
    df = df[["Open", "High", "Low", "Close", "Volume"]]

    loop = asyncio.get_running_loop()
    patterns = await loop.run_in_executor(None, detect_patterns, df, symbol)

    enriched_patterns = []
    for pattern in patterns:
        pattern_type = getattr(pattern, "pattern_type", None)
        try:
            if isinstance(pattern_type, str):
                pattern_type = PatternType(pattern_type)
        except Exception:
            pass

        backtest = getattr(pattern, "backtest_stats", {}) or {}
        try:
            if pattern_type is not None:
                backtest = await loop.run_in_executor(None, backtest_pattern, df, pattern_type)
        except Exception as exc:
            logger.warning("Backtest failed for %s: %s", pattern_type, exc)

        if hasattr(pattern, "model_dump"):
            pattern_dict = pattern.model_dump()
        elif hasattr(pattern, "dict"):
            pattern_dict = pattern.dict()
        else:
            pattern_dict = vars(pattern)

        pattern_dict["backtest"] = backtest
        enriched_patterns.append(pattern_dict)

    enriched_patterns.sort(key=lambda item: float(item.get("confidence", 0) or 0), reverse=True)
    ctx.signals = enriched_patterns

    bullish = sum(1 for item in enriched_patterns if str(item.get("direction", "")).upper() == "BULLISH")
    strongest = enriched_patterns[0].get("pattern_type", "—") if enriched_patterns else "—"
    ctx.metadata["step_1_summary"] = (
        f"Detected {len(enriched_patterns)} patterns for {symbol}: "
        f"{bullish} bullish, {len(enriched_patterns) - bullish} bearish/neutral. "
        f"Strongest: {strongest}."
    )
    return ctx


async def step_explain_patterns(ctx: AgentContext) -> AgentContext:
    """
    Call Claude to produce a plain-English explanation for each detected pattern.
    """

    from app.services.claude_service import explain_pattern

    symbol = ctx.raw_data.get("symbol", "RELIANCE")
    fundamentals = ctx.raw_data.get("fundamentals", {})
    explained = []

    for pattern in ctx.signals[:4]:
        backtest = pattern.get("backtest", {}) or pattern.get("backtest_stats", {}) or {}
        try:
            explanation = await explain_pattern(
                pattern_name=str(pattern.get("pattern_type", "")),
                stock=symbol,
                pattern_data=pattern,
                backtest_stats=backtest,
            )
        except Exception as exc:
            logger.warning("Pattern explanation failed for %s: %s", pattern.get("pattern_type"), exc)
            explanation = "Analysis unavailable."

        explained.append({**pattern, "explanation": explanation, "backtest": backtest})

    ctx.enriched = explained
    ctx.metadata["step_2_summary"] = (
        f"Claude explained {len(explained)} patterns for {symbol}. "
        f"Company: {fundamentals.get('company_name', symbol)}, "
        f"sector: {fundamentals.get('sector', 'Unknown')}."
    )
    return ctx


async def step_generate_chart_alert(ctx: AgentContext) -> AgentContext:
    """
    For the highest-confidence patterns, generate trade alerts with levels.
    """

    symbol = ctx.raw_data.get("symbol", "RELIANCE")
    quote = ctx.raw_data.get("quote", {})
    price = float(quote.get("ltp", 0) or ctx.raw_data.get("fundamentals", {}).get("current_price", 0) or 0)
    holdings = ctx.portfolio.get("holdings", []) or []
    held_symbols = {str(holding.get("symbol", "")).upper() for holding in holdings}

    alerts = []
    for pattern in ctx.enriched[:2]:
        direction = str(pattern.get("direction", "NEUTRAL")).upper()
        levels = pattern.get("key_levels", {}) or {}
        backtest = pattern.get("backtest", {}) or {}

        if direction == "BULLISH":
            entry = levels.get("support") or (round(price * 0.99, 2) if price else None)
            target = levels.get("target") or (round(price * 1.08, 2) if price else None)
            stop_loss = levels.get("stop_loss") or (round(price * 0.95, 2) if price else None)
            action = "BUY"
        elif direction == "BEARISH":
            entry = levels.get("resistance") or (round(price * 1.01, 2) if price else None)
            target = levels.get("target") or (round(price * 0.93, 2) if price else None)
            stop_loss = levels.get("stop_loss") or (round(price * 1.04, 2) if price else None)
            action = "SELL"
        else:
            entry = target = stop_loss = None
            action = "WATCH"

        portfolio_note = (
            f"You hold {symbol} — this pattern directly impacts your position."
            if symbol.upper() in held_symbols
            else f"You have no {symbol} exposure — consider this a fresh opportunity."
        )

        alerts.append(
            {
                "symbol": symbol,
                "pattern": str(pattern.get("pattern_type", "")),
                "direction": direction,
                "action": action,
                "confidence": pattern.get("confidence", 0),
                "explanation": pattern.get("explanation", ""),
                "portfolio_note": portfolio_note,
                "trade_levels": {
                    "entry": entry,
                    "target": target,
                    "stop_loss": stop_loss,
                    "horizon": f"{backtest.get('avg_holding_days', '—')} days avg",
                },
                "backtest": {
                    "win_rate": backtest.get("win_rate"),
                    "avg_return_pct": backtest.get("avg_return_pct"),
                    "sample_size": backtest.get("sample_size"),
                },
            }
        )

    ctx.alerts = alerts
    ctx.metadata["step_3_summary"] = (
        f"Generated {len(alerts)} chart-based trade alert(s) for {symbol}. "
        f"Top action: {alerts[0]['action']} on {alerts[0]['pattern']}."
        if alerts
        else "No trade alerts generated."
    )
    return ctx


def create_chart_pipeline(symbol: str) -> AgentOrchestrator:
    """Return a configured Chart Intelligence pipeline."""

    return AgentOrchestrator(
        "Chart Intelligence",
        [
            AgentStep(
                "OHLCV Ingestion",
                f"Fetching 1 year of daily price data for {symbol}",
                step_ingest_ohlcv,
            ),
            AgentStep(
                "Pattern Detection",
                "Running technical analysis and historical backtests",
                step_detect_chart_patterns,
            ),
            AgentStep(
                "Claude Explanation",
                "Generating plain-English explanations for each pattern",
                step_explain_patterns,
            ),
            AgentStep(
                "Alert Generation",
                "Computing entry, target, and stop-loss levels",
                step_generate_chart_alert,
            ),
        ],
    )
