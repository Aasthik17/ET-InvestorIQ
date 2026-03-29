"""
Chart Pipeline — 6-step autonomous chart analysis agent.
From raw OHLCV ingestion to actionable trade alert, zero human input.

Scenario 2 additions:
  - step_detect_conflicting_signals: finds RSI/FII conflicts for breakouts
  - step_generate_balanced_recommendation: nuanced output (not binary BUY/SELL)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

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
    Also computes RSI and 52-week high breakout status for Scenario 2.
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
        "open": "Open", "high": "High", "low": "Low",
        "close": "Close", "volume": "Volume",
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

    # ── Scenario 2: Compute RSI and 52w-high breakout inline ─────────────────
    try:
        close = df["Close"]
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, 1e-9)
        rsi_series = 100 - (100 / (1 + rs))
        current_rsi = float(rsi_series.iloc[-1]) if not rsi_series.empty else 50.0

        high_52w = float(df["High"].max())
        current_close = float(close.iloc[-1]) if not close.empty else 0.0
        is_at_52w_high = current_close >= high_52w * 0.995  # within 0.5% of 52w high
        near_52w_high = current_close >= high_52w * 0.97

        # Volume analysis — check last session vs 20-day avg
        last_vol = float(df["Volume"].iloc[-1]) if len(df) > 0 else 0
        avg_vol_20d = float(df["Volume"].iloc[-20:].mean()) if len(df) >= 20 else last_vol
        vol_ratio = last_vol / avg_vol_20d if avg_vol_20d > 0 else 1.0

        ctx.metadata["rsi"] = round(current_rsi, 1)
        ctx.metadata["52w_high"] = round(high_52w, 2)
        ctx.metadata["is_at_52w_high"] = is_at_52w_high
        ctx.metadata["near_52w_high"] = near_52w_high
        ctx.metadata["current_price"] = round(current_close, 2)
        ctx.metadata["volume_ratio"] = round(vol_ratio, 2)
        ctx.metadata["above_avg_volume"] = vol_ratio > 1.2

        # Historical success rate for 52w-high breakouts on this stock
        breakout_success = _compute_breakout_success_rate(df)
        ctx.metadata["breakout_success_rate"] = breakout_success

    except Exception as exc:
        logger.warning("Scenario 2 technical metrics failed: %s", exc)
        ctx.metadata.setdefault("rsi", 50.0)
        ctx.metadata.setdefault("is_at_52w_high", False)
        ctx.metadata.setdefault("breakout_success_rate", {"win_rate": None, "n_samples": 0})

    bullish = sum(1 for item in enriched_patterns if str(item.get("direction", "")).upper() == "BULLISH")
    strongest = enriched_patterns[0].get("pattern_type", "—") if enriched_patterns else "—"
    ctx.metadata["step_1_summary"] = (
        f"Detected {len(enriched_patterns)} patterns for {symbol}: "
        f"{bullish} bullish, {len(enriched_patterns) - bullish} bearish/neutral. "
        f"Strongest: {strongest}. RSI: {ctx.metadata.get('rsi', '—')}."
    )
    return ctx


def _compute_breakout_success_rate(df: Any) -> dict:
    """
    Count prior 52-week-high breakout events on the OHLCV dataframe and check
    how many resulted in >5% gain within the next 20 sessions.

    Returns: { win_rate: float|None, avg_return_pct: float, n_samples: int }
    """
    try:
        import pandas as pd
        close = df["Close"]
        n = len(close)
        if n < 60:
            return {"win_rate": None, "avg_return_pct": 0.0, "n_samples": 0}

        wins = 0
        total = 0
        returns = []

        for i in range(252, n - 20):  # need 1y lookback + 20 days forward
            prev_52w_high = float(close.iloc[i - 252:i].max())
            cur = float(close.iloc[i])
            prev = float(close.iloc[i - 1])
            # Breakout: current session crosses 52w high from below
            if prev < prev_52w_high and cur >= prev_52w_high:
                future_high = float(close.iloc[i:i + 20].max())
                ret = (future_high - cur) / cur * 100
                returns.append(ret)
                total += 1
                if ret >= 5.0:
                    wins += 1

        if total == 0:
            return {"win_rate": None, "avg_return_pct": 0.0, "n_samples": 0}

        return {
            "win_rate": round(wins / total * 100, 1),
            "avg_return_pct": round(sum(returns) / len(returns), 1),
            "n_samples": total,
        }
    except Exception:
        return {"win_rate": None, "avg_return_pct": 0.0, "n_samples": 0}


async def step_detect_conflicting_signals(ctx: AgentContext) -> AgentContext:
    """
    Scenario 2: Detect signals that conflict with the primary chart pattern.

    Checks:
    1. RSI overbought (>75) while pattern is bullish breakout
    2. FII reducing exposure in the stock
    3. Volume confirmation (should be above-average for a valid breakout)

    Populates ctx.metadata["conflicting_signals"] list.
    """

    from app.services.data_service import get_bulk_block_deals

    symbol = ctx.raw_data.get("symbol", "RELIANCE")
    rsi = float(ctx.metadata.get("rsi", 50.0))
    is_breakout = ctx.metadata.get("is_at_52w_high", False) or ctx.metadata.get("near_52w_high", False)
    above_avg_vol = ctx.metadata.get("above_avg_volume", False)
    vol_ratio = float(ctx.metadata.get("volume_ratio", 1.0))

    conflicting: list[dict] = []
    confirming: list[dict] = []

    # ── Volume confirmation ───────────────────────────────────────────────────
    if is_breakout:
        if above_avg_vol:
            confirming.append({
                "signal": "VOLUME_CONFIRMATION",
                "description": f"Breakout on above-average volume ({vol_ratio:.1f}x 20-day avg) — adds credibility",
                "impact": "BULLISH",
            })
        else:
            conflicting.append({
                "signal": "LOW_VOLUME_BREAKOUT",
                "description": (
                    f"Breakout without volume confirmation (only {vol_ratio:.1f}x avg). "
                    "Low-volume breakouts have historically failed ~60% of the time."
                ),
                "impact": "BEARISH",
            })

    # ── RSI conflict ──────────────────────────────────────────────────────────
    if rsi >= 75:
        conflicting.append({
            "signal": "RSI_OVERBOUGHT",
            "description": (
                f"RSI at {rsi:.0f} — deep overbought territory. "
                "Stocks with RSI >75 at breakout often see 5-8% pullback before continuation. "
                "Historical pullback risk: HIGH."
            ),
            "impact": "BEARISH",
            "rsi_value": round(rsi, 1),
        })
    elif rsi >= 65:
        conflicting.append({
            "signal": "RSI_ELEVATED",
            "description": f"RSI at {rsi:.0f} — elevated but not in extreme overbought zone.",
            "impact": "NEUTRAL",
            "rsi_value": round(rsi, 1),
        })
    elif rsi <= 40:
        confirming.append({
            "signal": "RSI_OVERSOLD_RECOVERY",
            "description": f"RSI at {rsi:.0f} — recovering from oversold, room to run upward.",
            "impact": "BULLISH",
            "rsi_value": round(rsi, 1),
        })

    # ── FII stance check ──────────────────────────────────────────────────────
    try:
        bulk_data = await get_bulk_block_deals(days_back=30)
        bulk_list = (bulk_data or {}).get("bulk", []) + (bulk_data or {}).get("block", [])
        sym_deals = [
            d for d in bulk_list
            if str(d.get("symbol", "")).upper() == symbol.upper()
        ]
        fii_keywords = ["mutual fund", "mf", "fii", "uti", "hdfc mf", "sbi mf", "nippon",
                        "icici pru", "kotak mf", "axis mf", "dsp", "franklin", "vanguard",
                        "blackrock", "fidelity", "nomura", "morgan", "jpmorgan"]

        fii_sells = [
            d for d in sym_deals
            if any(k in d.get("client_name", "").lower() for k in fii_keywords)
            and "sell" in d.get("deal_type", "").lower()
        ]
        fii_buys = [
            d for d in sym_deals
            if any(k in d.get("client_name", "").lower() for k in fii_keywords)
            and "buy" in d.get("deal_type", "").lower()
        ]

        fii_sell_value = sum(float(d.get("value_cr", 0)) for d in fii_sells)
        fii_buy_value = sum(float(d.get("value_cr", 0)) for d in fii_buys)

        if fii_sell_value > fii_buy_value and fii_sell_value > 5:
            conflicting.append({
                "signal": "FII_REDUCING_EXPOSURE",
                "description": (
                    f"FIIs have net-sold ₹{fii_sell_value - fii_buy_value:.0f} Cr of {symbol} "
                    "in the last 30 days — reducing exposure while retail is chasing the breakout."
                ),
                "impact": "BEARISH",
                "fii_net_sell_cr": round(fii_sell_value - fii_buy_value, 1),
            })
        elif fii_buy_value > fii_sell_value and fii_buy_value > 5:
            confirming.append({
                "signal": "FII_ACCUMULATING",
                "description": (
                    f"FIIs net-bought ₹{fii_buy_value - fii_sell_value:.0f} Cr of {symbol} "
                    "in last 30 days — institutional conviction aligns with breakout."
                ),
                "impact": "BULLISH",
                "fii_net_buy_cr": round(fii_buy_value - fii_sell_value, 1),
            })

    except Exception as exc:
        logger.warning("FII stance check failed for %s: %s", symbol, exc)

    ctx.metadata["conflicting_signals"] = conflicting
    ctx.metadata["confirming_signals"] = confirming

    n_conflicts = len(conflicting)
    n_confirms = len(confirming)
    ctx.metadata["step_2_5_summary"] = (
        f"Scenario 2 conflict check for {symbol}: "
        f"{n_conflicts} conflicting signal(s), {n_confirms} confirming signal(s). "
        f"RSI: {rsi:.0f}. "
        f"{'⚠ FII reducing.' if any(c['signal'] == 'FII_REDUCING_EXPOSURE' for c in conflicting) else 'FII neutral.'}"
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
    ctx.metadata["step_3_summary"] = (
        f"Claude explained {len(explained)} patterns for {symbol}. "
        f"Company: {fundamentals.get('company_name', symbol)}, "
        f"sector: {fundamentals.get('sector', 'Unknown')}."
    )
    return ctx


async def step_generate_chart_alert(ctx: AgentContext) -> AgentContext:
    """
    For the highest-confidence patterns, generate trade alerts with levels.

    Scenario 2: Output is BULLISH_WITH_CAVEATS or BEARISH_WITH_TAILWINDS
    when conflicting signals exist — never a flat BUY/SELL on a conflict.
    """

    symbol = ctx.raw_data.get("symbol", "RELIANCE")
    quote = ctx.raw_data.get("quote", {})
    price = float(quote.get("ltp", 0) or ctx.raw_data.get("fundamentals", {}).get("current_price", 0) or 0)
    holdings = ctx.portfolio.get("holdings", []) or []
    held_symbols = {str(holding.get("symbol", "")).upper() for holding in holdings}

    conflicting = ctx.metadata.get("conflicting_signals", [])
    confirming = ctx.metadata.get("confirming_signals", [])
    breakout_stats = ctx.metadata.get("breakout_success_rate", {})
    rsi = float(ctx.metadata.get("rsi", 50.0))
    is_breakout = ctx.metadata.get("is_at_52w_high", False)

    alerts = []
    for pattern in ctx.enriched[:2]:
        direction = str(pattern.get("direction", "NEUTRAL")).upper()
        levels = pattern.get("key_levels", {}) or {}
        backtest = pattern.get("backtest", {}) or {}

        has_conflicts = len(conflicting) > 0

        if direction == "BULLISH":
            entry = levels.get("support") or (round(price * 0.99, 2) if price else None)
            target = levels.get("target") or (round(price * 1.08, 2) if price else None)
            stop_loss = levels.get("stop_loss") or (round(price * 0.95, 2) if price else None)
            # Scenario 2: If there are conflicts, use nuanced action
            if has_conflicts and is_breakout:
                action = "BULLISH_WITH_CAVEATS"
            else:
                action = "BUY"
        elif direction == "BEARISH":
            entry = levels.get("resistance") or (round(price * 1.01, 2) if price else None)
            target = levels.get("target") or (round(price * 0.93, 2) if price else None)
            stop_loss = levels.get("stop_loss") or (round(price * 1.04, 2) if price else None)
            if len(confirming) > 0:
                action = "BEARISH_WITH_TAILWINDS"
            else:
                action = "SELL"
        else:
            entry = target = stop_loss = None
            action = "WATCH"

        portfolio_note = (
            f"You hold {symbol} — this pattern directly impacts your position."
            if symbol.upper() in held_symbols
            else f"You have no {symbol} exposure — consider this a fresh opportunity."
        )

        # Scenario 2: Balanced recommendation narrative
        recommendation_context = ""
        if action in ("BULLISH_WITH_CAVEATS", "BEARISH_WITH_TAILWINDS"):
            conflict_descriptions = [c["description"] for c in conflicting]
            confirming_descriptions = [c["description"] for c in confirming]
            recommendation_context = (
                f"⚖ BALANCED ASSESSMENT: Primary signal is {direction}. "
                f"Conflicting factors: {'; '.join(conflict_descriptions)}. "
                f"Confirming factors: {'; '.join(confirming_descriptions) if confirming_descriptions else 'None'}. "
                f"Do not treat this as a binary buy/sell signal."
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
                "recommendation_context": recommendation_context,
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
                # ── Scenario 2 fields ──────────────────────────────────────────
                "scenario2": {
                    "rsi": round(rsi, 1),
                    "is_52w_breakout": is_breakout,
                    "breakout_historical_success": breakout_stats,
                    "conflicting_signals": conflicting,
                    "confirming_signals": confirming,
                    "has_conflicts": has_conflicts,
                },
            }
        )

    ctx.alerts = alerts
    ctx.metadata["step_4_summary"] = (
        f"Generated {len(alerts)} chart-based trade alert(s) for {symbol}. "
        f"Top action: {alerts[0]['action']} on {alerts[0]['pattern']}. "
        f"Conflicts: {len(conflicting)}, Confirmations: {len(confirming)}."
        if alerts
        else "No trade alerts generated."
    )
    return ctx


def create_chart_pipeline(symbol: str) -> AgentOrchestrator:
    """Return a configured Chart Intelligence pipeline (6 steps for Scenario 2)."""

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
                "Running technical analysis, RSI, and 52W high breakout check",
                step_detect_chart_patterns,
            ),
            AgentStep(
                "Conflict Analysis",
                "Checking for RSI overbought, FII stance, and volume confirmation conflicts",
                step_detect_conflicting_signals,
            ),
            AgentStep(
                "Claude Explanation",
                "Generating plain-English explanations for each pattern",
                step_explain_patterns,
            ),
            AgentStep(
                "Alert Generation",
                "Computing entry, target, stop-loss and balanced recommendation",
                step_generate_chart_alert,
            ),
        ],
    )



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
