"""
ET InvestorIQ — Market Chat Service
Portfolio-aware, tool-augmented AI chat powered by Claude.
Supports multi-step analysis, live data tools, and portfolio context injection.
"""

import asyncio
import json
import logging
from typing import AsyncGenerator, Dict, List, Optional

from app.modules.market_chat.schemas import (
    ChatMessage, ChatRequest, ChatResponse, Portfolio,
    PortfolioAnalysisResponse, Source, SuggestedQuestion, ToolCallRecord
)
from app.services import claude_service, data_service

logger = logging.getLogger(__name__)

# ─── Tool Definitions for Claude ─────────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "name": "get_stock_quote",
        "description": "Get real-time stock quote and key metrics for an Indian stock.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "NSE stock symbol e.g. 'RELIANCE', 'HDFCBANK', 'TCS'"
                }
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "compare_stocks",
        "description": "Compare multiple stocks on fundamental and technical metrics side by side.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbols": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of NSE symbols to compare"
                },
                "metrics": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of metrics: pe_ratio, pb_ratio, roe, market_cap, current_price etc."
                }
            },
            "required": ["symbols"]
        }
    },
    {
        "name": "get_portfolio_analysis",
        "description": "Analyze a user's stock portfolio for risk, concentration, and performance.",
        "input_schema": {
            "type": "object",
            "properties": {
                "portfolio": {
                    "type": "object",
                    "description": "Portfolio dict with holdings list"
                }
            },
            "required": ["portfolio"]
        }
    },
    {
        "name": "get_technical_levels",
        "description": "Get technical analysis levels for a stock: support, resistance, RSI, MACD.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "NSE stock symbol"
                }
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "search_news",
        "description": "Search recent news for a stock or market topic with sentiment analysis.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query or topic"
                },
                "symbols": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of stock symbols to narrow search"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_sector_outlook",
        "description": "Get sector performance data, top stocks, and FII stance for a market sector.",
        "input_schema": {
            "type": "object",
            "properties": {
                "sector": {
                    "type": "string",
                    "description": "Sector name: IT, Banking, Pharma, Auto, FMCG, Energy, Metals, Infra"
                }
            },
            "required": ["sector"]
        }
    },
    {
        "name": "prioritise_news_for_portfolio",
        "description": (
            "Scenario 3: Given two or more simultaneous news events (e.g., an RBI rate cut AND "
            "a sector-specific regulatory change), rank each event by how financially material it is "
            "to the user's specific portfolio. Returns estimated ₹ P&L impact for each holding and "
            "a priority ranking of the events."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "news_events": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "headline": {"type": "string"},
                            "description": {"type": "string"},
                            "event_type": {
                                "type": "string",
                                "description": (
                                    "Optional: one of RBI_RATE_CUT, RBI_RATE_HIKE, "
                                    "SEBI_REGULATORY_TIGHTENING, PHARMA_FMCG_PRICE_CAP, "
                                    "OIL_PRICE_SPIKE, RUPEE_DEPRECIATION, BUDGET_INFRA_PUSH, etc."
                                )
                            }
                        },
                        "required": ["headline"]
                    },
                    "description": "List of simultaneous news events to rank"
                }
            },
            "required": ["news_events"]
        }
    },
]


async def _execute_tool(tool_name: str, tool_input: dict, portfolio: dict | None = None) -> dict:
    """
    Execute a tool call from Claude and return the result.

    Args:
        tool_name: Name of the tool to execute.
        tool_input: Input parameters for the tool.
        portfolio: Optional portfolio dict for portfolio-aware tools.

    Returns:
        Tool result as a dict.
    """
    try:
        if tool_name == "get_stock_quote":
            symbol = tool_input.get("symbol", "").upper()
            if "." not in symbol:
                symbol += ".NS"
            fundamentals = await data_service.get_fundamentals(symbol)
            return {
                "symbol": symbol,
                "current_price": fundamentals.get("current_price", 0),
                "pe_ratio": fundamentals.get("pe_ratio", 0),
                "market_cap_cr": fundamentals.get("market_cap", 0),
                "52w_high": fundamentals.get("52w_high", 0),
                "52w_low": fundamentals.get("52w_low", 0),
                "volume": fundamentals.get("volume", 0),
                "roe": fundamentals.get("roe", 0),
                "source": "Yahoo Finance / NSE"
            }

        elif tool_name == "compare_stocks":
            symbols = tool_input.get("symbols", [])
            metrics = tool_input.get("metrics", ["pe_ratio", "market_cap", "roe", "current_price"])
            comparison = {}
            for sym in symbols[:5]:  # Cap at 5 stocks
                s = sym.upper()
                if "." not in s:
                    s += ".NS"
                fund = await data_service.get_fundamentals(s)
                comparison[sym] = {m: fund.get(m, "N/A") for m in metrics}
            return {"comparison": comparison, "metrics": metrics, "source": "Yahoo Finance"}

        elif tool_name == "get_portfolio_analysis":
            portfolio = tool_input.get("portfolio", {})
            holdings = portfolio.get("holdings", [])
            total_invested = sum(
                h.get("quantity", 0) * h.get("avg_cost", 0) for h in holdings
            )
            total_current = 0
            for h in holdings:
                sym = h.get("symbol", "").upper()
                if "." not in sym:
                    sym += ".NS"
                try:
                    fund = await data_service.get_fundamentals(sym)
                    current_val = h.get("quantity", 0) * fund.get("current_price", h.get("avg_cost", 0))
                    total_current += current_val
                    h["current_value"] = round(current_val, 0)
                    h["gain_pct"] = round(((current_val - h.get("quantity", 0) * h.get("avg_cost", 0))
                                           / max(1, h.get("quantity", 0) * h.get("avg_cost", 0))) * 100, 2)
                except Exception:
                    total_current += h.get("quantity", 0) * h.get("avg_cost", 0)
            gain_pct = round(((total_current - total_invested) / max(1, total_invested)) * 100, 2)
            return {
                "total_invested": round(total_invested, 0),
                "total_current_value": round(total_current, 0),
                "overall_gain_pct": gain_pct,
                "holdings_enriched": holdings,
                "source": "Yahoo Finance"
            }

        elif tool_name == "get_technical_levels":
            symbol = tool_input.get("symbol", "").upper()
            if "." not in symbol:
                symbol += ".NS"
            from app.modules.chart_pattern.service import get_support_resistance, scan_stock
            levels = await get_support_resistance(symbol)
            scan = await scan_stock(symbol)
            return {
                "symbol": symbol,
                "support_zones": levels.support_zones,
                "resistance_zones": levels.resistance_zones,
                "rsi": scan.rsi,
                "overall_bias": scan.overall_bias,
                "patterns_count": len(scan.patterns),
                "top_pattern": scan.patterns[0].pattern_label if scan.patterns else "None detected",
                "source": "NSE / Technical Analysis"
            }

        elif tool_name == "search_news":
            symbols = tool_input.get("symbols", [])
            symbol = (symbols[0].upper() if symbols else "NIFTY") + ".NS"
            news = await data_service.get_news(symbol)
            return {
                "news": news[:5],
                "query": tool_input.get("query", ""),
                "source": "Yahoo Finance News"
            }

        elif tool_name == "get_sector_outlook":
            sector = tool_input.get("sector", "")
            sectors = await data_service.get_sector_performance()
            sector_data = next((s for s in sectors if s.get("sector", "").lower() == sector.lower()),
                               sectors[0] if sectors else {})
            return {
                "sector": sector,
                "return_1d": sector_data.get("return_1d_pct", 0),
                "return_1w": sector_data.get("return_1w_pct", 0),
                "return_1m": sector_data.get("return_1m_pct", 0),
                "top_gainer": sector_data.get("top_gainer", "N/A"),
                "source": "NSE Sector Data"
            }

        elif tool_name == "prioritise_news_for_portfolio":
            # ── Scenario 3: Portfolio-aware news prioritisation ────────────────
            from app.services.news_impact_scorer import score_news_impact

            news_events = tool_input.get("news_events", [])
            holdings = tool_input.get("holdings", [])
            if not holdings and portfolio:
                holdings = portfolio.get("holdings", [])

            ranked = score_news_impact(news_events=news_events, holdings=holdings)

            if not ranked:
                return {
                    "error": "No news events or portfolio holdings provided",
                    "ranked_events": [],
                }

            # Format for Claude to explain clearly
            summary_lines = []
            for r in ranked:
                direction_symbol = "▲" if r["direction"] == "GAIN" else "▼" if r["direction"] == "LOSS" else "—"
                impact_inr = r["total_pnl_impact_inr"]
                summary_lines.append(
                    f"#{r['priority_rank']} [{r['materiality']}] {r['headline']}: "
                    f"Estimated P&L impact {direction_symbol}₹{abs(impact_inr):,.0f} "
                    f"(affects sectors: {', '.join(r['affected_sectors']) or 'General market'})"
                )

            return {
                "ranked_events": ranked,
                "priority_summary": summary_lines,
                "most_material_event": ranked[0]["headline"] if ranked else "N/A",
                "most_material_pnl_inr": ranked[0]["total_pnl_impact_inr"] if ranked else 0,
                "source": "ET InvestorIQ News Impact Scorer (Sector Beta Model)",
            }

        else:
            return {"error": f"Unknown tool: {tool_name}"}
    except Exception as e:
        logger.error(f"Tool execution failed ({tool_name}): {e}")
        return {"error": str(e), "tool": tool_name}


async def chat(request: ChatRequest) -> ChatResponse:
    """
    Process a chat message with full tool orchestration.

    1. Build system prompt with portfolio context
    2. Call Claude with tool definitions
    3. Execute any tool calls
    4. Continue until final response
    5. Generate follow-up suggestions

    Args:
        request: ChatRequest with conversation history and portfolio.

    Returns:
        ChatResponse with answer, sources, tool calls, and suggestions.
    """
    messages = [{"role": m.role, "content": m.content} for m in request.messages]
    portfolio_dict = request.portfolio.model_dump() if request.portfolio else None

    # Wrap _execute_tool to inject portfolio context (needed for Scenario 3)
    async def _tool_executor(tool_name: str, tool_input: dict) -> dict:
        return await _execute_tool(tool_name, tool_input, portfolio=portfolio_dict)

    # Full tool-augmented chat
    result = await claude_service.chat_with_tools(
        messages=messages,
        tool_definitions=TOOL_DEFINITIONS,
        tool_executor=_tool_executor,
        portfolio=portfolio_dict,
    )

    # Generate follow-up suggestions
    follow_ups = []
    try:
        follow_ups = await claude_service.generate_follow_up_suggestions(
            result.get("response", "")[:300]
        )
    except Exception:
        follow_ups = [
            "What are the key risks for this investment?",
            "How does this compare to sector peers?",
            "What's the analyst consensus target price?"
        ]

    # Build source objects from tool calls
    sources = [
        Source(name=tc.get("name", ""), type="tool")
        for tc in result.get("tool_calls", [])
    ]
    tool_call_records = [
        ToolCallRecord(
            name=tc.get("name", ""),
            input=tc.get("input", {}),
        )
        for tc in result.get("tool_calls", [])
    ]

    return ChatResponse(
        response=result.get("response", ""),
        sources=sources,
        tool_calls=tool_call_records,
        follow_up_suggestions=follow_ups,
        session_id=request.session_id,
    )


async def stream_chat(request: ChatRequest) -> AsyncGenerator[str, None]:
    """
    Stream a chat response using Server-Sent Events.
    Falls back to a chunked non-streaming response if streaming unavailable.

    Args:
        request: ChatRequest.

    Yields:
        SSE-formatted string chunks.
    """
    try:
        import anthropic
        from app.config import settings
        import time

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        portfolio_dict = request.portfolio.model_dump() if request.portfolio else None
        portfolio_json = json.dumps(portfolio_dict, indent=2, default=str) if portfolio_dict else "No portfolio."

        system_prompt = f"""You are ET InvestorIQ, an expert Indian stock market AI assistant.
Always cite your data sources. Use ₹ for Rupees, Cr for Crores.
User portfolio: {portfolio_json}
Today: {time.strftime('%B %d, %Y')}"""

        messages = [{"role": m.role, "content": m.content} for m in request.messages]

        loop = asyncio.get_event_loop()

        def _stream_call():
            return client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                temperature=0.7,
                system=system_prompt,
                messages=messages,
                stream=True,
            )

        stream = await loop.run_in_executor(None, _stream_call)

        for event in stream:
            if hasattr(event, "type"):
                if event.type == "content_block_delta":
                    if hasattr(event, "delta") and hasattr(event.delta, "text"):
                        yield f"data: {json.dumps({'type': 'text', 'content': event.delta.text})}\n\n"
                elif event.type == "message_stop":
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"

    except Exception as e:
        logger.error(f"Streaming chat failed: {e}")
        # Fallback: non-streaming
        result = await chat(request)
        # Simulate streaming by chunking response
        words = result.response.split(" ")
        for i, word in enumerate(words):
            yield f"data: {json.dumps({'type': 'text', 'content': word + ' '})}\n\n"
            if i % 10 == 0:
                await asyncio.sleep(0.05)
        yield f"data: {json.dumps({'type': 'done'})}\n\n"


async def analyze_portfolio(portfolio: Portfolio) -> PortfolioAnalysisResponse:
    """
    Perform a standalone portfolio analysis without chat context.

    Args:
        portfolio: Portfolio with holdings.

    Returns:
        PortfolioAnalysisResponse with detailed analysis.
    """
    tool_result = await _execute_tool("get_portfolio_analysis", {"portfolio": portfolio.model_dump()})

    # Build a portfolio analysis prompt
    analysis_prompt = f"""Analyze this Indian stock portfolio:
{json.dumps(tool_result, indent=2, default=str)}

Risk Profile: {portfolio.risk_profile}
Investment Horizon: {portfolio.investment_horizon}

Provide:
1. Overall portfolio health assessment
2. Sector concentration risk
3. Identify the strongest and weakest holding
4. 3 specific actionable recommendations
5. Risk rating: 1-10

Be specific with numbers."""

    try:
        from app.services.claude_service import _get_client, _call_with_retry, MODEL
        client = _get_client()

        def _call():
            return client.messages.create(
                model=MODEL, max_tokens=1024, temperature=0.3,
                messages=[{"role": "user", "content": analysis_prompt}]
            )

        response = await _call_with_retry(_call)
        analysis_text = response.content[0].text
    except Exception as e:
        logger.error(f"Portfolio analysis failed: {e}")
        analysis_text = (f"Portfolio contains {len(portfolio.holdings)} holdings. "
                        f"Current value: ₹{tool_result.get('total_current_value', 0):,.0f}. "
                        f"Overall gain: {tool_result.get('overall_gain_pct', 0):.1f}%.")

    # Find best/worst holdings
    holdings_enriched = tool_result.get("holdings_enriched", portfolio.holdings)
    sorted_by_gain = sorted(
        [h for h in holdings_enriched if isinstance(h, dict)],
        key=lambda x: x.get("gain_pct", 0),
        reverse=True
    )
    best = sorted_by_gain[0].get("symbol", "N/A") if sorted_by_gain else "N/A"
    worst = sorted_by_gain[-1].get("symbol", "N/A") if sorted_by_gain else "N/A"

    return PortfolioAnalysisResponse(
        portfolio=portfolio,
        analysis=analysis_text,
        risk_assessment=f"Risk Profile: {portfolio.risk_profile}",
        top_holding=best,
        weakest_holding=worst,
        recommendations=[
            "Review sector concentration quarterly",
            "Consider stop-loss orders for underperformers",
            "Rebalance if any single position exceeds 25% of portfolio"
        ],
    )


async def get_suggestions(symbol: Optional[str] = None) -> List[SuggestedQuestion]:
    """
    Get context-aware suggested questions for a symbol or general market.

    Args:
        symbol: Optional stock symbol to generate specific questions for.

    Returns:
        List of SuggestedQuestion objects.
    """
    if symbol:
        sym = symbol.upper().replace(".NS", "")
        return [
            SuggestedQuestion(question=f"Analyze {sym} fundamentals and give a target price", category="fundamental"),
            SuggestedQuestion(question=f"What technical patterns are forming on {sym}?", category="technical"),
            SuggestedQuestion(question=f"Compare {sym} with its top 3 competitors", category="fundamental"),
            SuggestedQuestion(question=f"What are the biggest risks facing {sym} in FY26?", category="fundamental"),
            SuggestedQuestion(question=f"Should I buy, hold, or sell {sym} at current levels?", category="portfolio"),
        ]
    return [
        SuggestedQuestion(question="What are the top large-cap opportunities right now?", category="fundamental"),
        SuggestedQuestion(question="Analyze my portfolio and identify the weakest holding", category="portfolio"),
        SuggestedQuestion(question="Compare HDFC Bank vs ICICI Bank on all key metrics", category="fundamental"),
        SuggestedQuestion(question="Which sectors are showing the strongest momentum?", category="sector"),
        SuggestedQuestion(question="What is the overall market outlook for the next quarter?", category="fundamental"),
    ]
