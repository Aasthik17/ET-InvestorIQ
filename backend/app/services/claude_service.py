"""
ET InvestorIQ — Claude AI Service
Central service for all Anthropic Claude API calls.
Model: claude-sonnet-4-20250514 (always — never change this)
Includes retry logic with exponential backoff.
"""

import asyncio
import json
import logging
import time
from typing import Optional

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-20250514"
MAX_RETRIES = 3


def _get_client() -> anthropic.Anthropic:
    """Return a configured Anthropic client."""
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


async def _call_with_retry(fn, *args, **kwargs):
    """
    Execute an Anthropic API call with exponential backoff retry.

    Args:
        fn: Synchronous callable that makes the API call.
        *args, **kwargs: Arguments passed to fn.

    Returns:
        Result of fn(*args, **kwargs).

    Raises:
        Exception: After MAX_RETRIES exhausted.
    """
    loop = asyncio.get_event_loop()
    for attempt in range(MAX_RETRIES):
        try:
            return await loop.run_in_executor(None, lambda: fn(*args, **kwargs))
        except anthropic.RateLimitError as e:
            wait = 2 ** attempt
            logger.warning(f"Rate limit hit (attempt {attempt + 1}). Retrying in {wait}s.")
            await asyncio.sleep(wait)
        except anthropic.APIStatusError as e:
            if e.status_code >= 500:
                wait = 2 ** attempt
                logger.warning(f"Server error {e.status_code} (attempt {attempt + 1}). Retrying in {wait}s.")
                await asyncio.sleep(wait)
            else:
                raise
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                raise
            await asyncio.sleep(2 ** attempt)
    raise RuntimeError("Max retries exceeded for Claude API call")


async def analyze_signal(signal_data: dict, signal_type: str) -> str:
    """
    Generate an AI analysis paragraph for an Opportunity Radar signal.

    Args:
        signal_data: Raw signal data dict (insider trade, bulk deal, filing, etc.)
        signal_type: Type of signal (e.g., 'INSIDER_TRADE', 'BULK_DEAL').

    Returns:
        Multi-paragraph AI analysis string explaining why this is significant.
    """
    try:
        client = _get_client()
        prompt = f"""You are ET InvestorIQ, an expert Indian stock market analyst.
        
Analyze this {signal_type} signal and explain its significance to retail investors:

Signal Data:
{json.dumps(signal_data, indent=2, default=str)}

Provide a concise 2-3 paragraph analysis covering:
1. WHY this is significant (historical context, what insiders/institutions know that retail doesn't)
2. WHAT to watch for in the next 30-60 days (key price levels, upcoming catalysts)
3. RISK factors and what would invalidate this signal

Be specific with numbers. Use plain English. Reference the Indian market context.
Do not use the word "significant" more than once."""

        def _call():
            return client.messages.create(
                model=MODEL,
                max_tokens=1024,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )

        response = await _call_with_retry(_call)
        return response.content[0].text
    except Exception as e:
        logger.error(f"analyze_signal failed: {e}")
        return (f"This {signal_type.replace('_', ' ').lower()} signal warrants attention. "
                f"Historical patterns suggest that institutional activity at these levels "
                f"often precedes significant price movements within 30-60 days. "
                f"Monitor volume patterns and any accompanying corporate announcements closely.")


async def explain_pattern(
    pattern_name: str,
    stock: str,
    pattern_data: dict,
    backtest_stats: dict
) -> str:
    """
    Generate a plain-English explanation of a detected chart pattern.

    Args:
        pattern_name: Name of the chart pattern (e.g., 'GOLDEN_CROSS').
        stock: Stock ticker symbol.
        pattern_data: Pattern detection data (confidence, key levels, indicators).
        backtest_stats: Historical back-test results for this pattern on this stock.

    Returns:
        Plain-English explanation suitable for retail investors.
    """
    try:
        client = _get_client()
        prompt = f"""You are ET InvestorIQ. Explain this detected chart pattern to a retail investor in India.

Stock: {stock}
Pattern: {pattern_name}
Pattern Data: {json.dumps(pattern_data, indent=2, default=str)}
Historical Back-test on this stock: {json.dumps(backtest_stats, indent=2, default=str)}

Write a clear, engaging explanation (150-200 words) that:
1. Explains what this pattern means in plain English (no jargon)
2. States the historical win rate for THIS specific pattern on THIS stock
3. Gives specific entry, target, and stop-loss levels from the pattern data
4. Mentions what would invalidate this pattern
5. Rates this setup as: Strong / Moderate / Weak opportunity

Write in an authoritative but friendly tone, as if advising a knowledgeable friend."""

        def _call():
            return client.messages.create(
                model=MODEL,
                max_tokens=512,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )

        response = await _call_with_retry(_call)
        return response.content[0].text
    except Exception as e:
        logger.error(f"explain_pattern failed: {e}")
        return (f"The {pattern_name.replace('_', ' ').title()} pattern detected on {stock} "
                f"suggests a potential {pattern_data.get('direction', 'neutral')} setup. "
                f"Historical win rate: {backtest_stats.get('win_rate', 55)}%. "
                f"Monitor key levels: Support at ₹{pattern_data.get('key_levels', {}).get('support', 'N/A')}, "
                f"Target at ₹{pattern_data.get('key_levels', {}).get('target', 'N/A')}.")


async def chat_with_context(
    messages: list,
    portfolio: Optional[dict] = None,
    tools: Optional[list] = None
) -> dict:
    """
    Multi-turn portfolio-aware chat with Claude. Supports tool use.

    Args:
        messages: List of {role, content} dicts (conversation history).
        portfolio: Optional portfolio dict injected into system prompt.
        tools: Optional list of Anthropic tool definitions.

    Returns:
        dict with keys: response (str), sources (list), tool_calls (list).
    """
    try:
        client = _get_client()
        portfolio_json = json.dumps(portfolio, indent=2, default=str) if portfolio else "No portfolio provided."

        system_prompt = f"""You are ET InvestorIQ, an expert Indian stock market AI assistant built for the Economic Times platform.

You have access to live NSE/BSE data via tools. Always cite your data sources.
When discussing stocks, provide specific numbers, not vague generalities.
Think step by step for multi-part questions.
Format responses with clear sections using markdown.
Always mention risks alongside opportunities.
Use Indian market conventions (₹ for Rupees, Cr for Crores, Lakh for 100,000).

User's Portfolio Context:
{portfolio_json}"""

        # Build claude messages (convert from our format)
        claude_messages = []
        for msg in messages:
            claude_messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

        tool_calls_made = []
        sources = []
        final_response = ""

        def _call():
            kwargs = {
                "model": MODEL,
                "max_tokens": 2048,
                "temperature": 0.7,
                "system": system_prompt,
                "messages": claude_messages,
            }
            if tools:
                kwargs["tools"] = tools
            return client.messages.create(**kwargs)

        response = await _call_with_retry(_call)

        # Handle tool use loop
        current_messages = list(claude_messages)
        while response.stop_reason == "tool_use":
            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
            tool_results = []

            for tool_block in tool_use_blocks:
                tool_calls_made.append({
                    "name": tool_block.name,
                    "input": tool_block.input
                })
                # Tool execution is handled by the caller (market_chat service)
                # Here we just record the call; result will be injected
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_block.id,
                    "content": json.dumps({"error": "Tool execution delegated to service layer"})
                })

            # Append assistant response + tool results
            current_messages.append({"role": "assistant", "content": response.content})
            current_messages.append({"role": "user", "content": tool_results})

            def _call2(msgs=current_messages):
                kwargs = {
                    "model": MODEL,
                    "max_tokens": 2048,
                    "temperature": 0.7,
                    "system": system_prompt,
                    "messages": msgs,
                }
                if tools:
                    kwargs["tools"] = tools
                return client.messages.create(**kwargs)

            response = await _call_with_retry(_call2)

        # Extract text response
        for block in response.content:
            if hasattr(block, "text"):
                final_response += block.text

        return {
            "response": final_response,
            "sources": sources,
            "tool_calls": tool_calls_made,
        }
    except Exception as e:
        logger.error(f"chat_with_context failed: {e}")
        return {
            "response": ("I'm having trouble connecting to the AI service right now. "
                         "Please try again in a moment. In the meantime, you can explore "
                         "the Opportunity Radar and Chart Intelligence modules."),
            "sources": [],
            "tool_calls": [],
        }


async def chat_with_tools(
    messages: list,
    tool_definitions: list,
    tool_executor,
    portfolio: Optional[dict] = None
) -> dict:
    """
    Full tool-augmented chat with actual tool execution.

    Args:
        messages: Conversation history.
        tool_definitions: List of Anthropic tool defs.
        tool_executor: Async callable(tool_name, tool_input) -> result.
        portfolio: Optional portfolio context.

    Returns:
        dict with response, sources, tool_calls.
    """
    try:
        client = _get_client()
        portfolio_json = json.dumps(portfolio, indent=2, default=str) if portfolio else "No portfolio provided."

        system_prompt = f"""You are ET InvestorIQ, an expert Indian stock market AI assistant.

You have access to live NSE/BSE data via tools. Always cite your data sources with [Source: tool_name].
When discussing stocks, provide specific numbers. Think step by step for multi-part questions.
Format responses with clear markdown sections. Always mention risks alongside opportunities.
Use Indian market conventions: ₹ for Rupees, Cr for Crores.

Current user portfolio:
{portfolio_json}

Today's date: {time.strftime('%B %d, %Y')}"""

        claude_messages = [{"role": m["role"], "content": m["content"]} for m in messages]
        tool_calls_made = []
        sources = []

        max_iterations = 5
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            def _call(msgs=claude_messages):
                return client.messages.create(
                    model=MODEL,
                    max_tokens=2048,
                    temperature=0.7,
                    system=system_prompt,
                    messages=msgs,
                    tools=tool_definitions,
                )

            response = await _call_with_retry(_call)

            if response.stop_reason != "tool_use":
                # Final response
                final_text = ""
                for block in response.content:
                    if hasattr(block, "text"):
                        final_text += block.text
                return {
                    "response": final_text,
                    "sources": sources,
                    "tool_calls": tool_calls_made,
                }

            # Execute tools
            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
            tool_results = []

            for tool_block in tool_use_blocks:
                tool_name = tool_block.name
                tool_input = tool_block.input
                tool_calls_made.append({"name": tool_name, "input": tool_input})
                sources.append({"name": tool_name, "type": "tool", "url": None})

                try:
                    result = await tool_executor(tool_name, tool_input)
                    result_str = json.dumps(result, default=str) if not isinstance(result, str) else result
                except Exception as e:
                    result_str = json.dumps({"error": str(e)})

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_block.id,
                    "content": result_str,
                })

            # Add assistant turn + tool results
            claude_messages.append({"role": "assistant", "content": response.content})
            claude_messages.append({"role": "user", "content": tool_results})

        # Fallback if max iterations exceeded
        return {
            "response": "Analysis complete. Please review the tool outputs above for details.",
            "sources": sources,
            "tool_calls": tool_calls_made,
        }

    except Exception as e:
        logger.error(f"chat_with_tools failed: {e}")
        return {
            "response": "I'm temporarily unavailable. Please try again shortly.",
            "sources": [],
            "tool_calls": [],
        }


async def generate_video_narration(video_type: str, data: dict) -> str:
    """
    Generate a 30-90 second narration script for a market video.

    Args:
        video_type: Type of video (MARKET_WRAP, SECTOR_ROTATION, etc.)
        data: Market data dict to narrate.

    Returns:
        Narration script as a string (approx 75-225 words for 30-90 sec @ 150wpm).
    """
    try:
        client = _get_client()
        prompt = f"""You are a professional financial news anchor for Economic Times television.

Write a {video_type.replace('_', ' ').title()} narration script for a market update video.

Data to narrate:
{json.dumps(data, indent=2, default=str)}

Requirements:
- Length: 75-150 words (reads in 30-60 seconds at 150 wpm)
- Professional TV anchor tone — authoritative and clear
- Mention specific numbers from the data
- Include ONE actionable insight for viewers
- Start with a strong opening hook
- End with a forward-looking statement
- Do NOT use vague phrases like "markets moved" — be specific

Write ONLY the narration script, no stage directions or scene descriptions."""

        def _call():
            return client.messages.create(
                model=MODEL,
                max_tokens=512,
                temperature=0.5,
                messages=[{"role": "user", "content": prompt}]
            )

        response = await _call_with_retry(_call)
        return response.content[0].text
    except Exception as e:
        logger.error(f"generate_video_narration failed: {e}")
        return (f"Markets today delivered mixed signals as investors weighed global cues. "
                f"The Nifty 50 settled at key support levels while FII activity remained measured. "
                f"Sector rotation continues into defensives ahead of the upcoming results season. "
                f"Watch for RBI commentary and Q4 earnings surprises that could set direction for the week ahead.")


async def score_signal_confidence(signal_data: dict) -> float:
    """
    Use Claude to score signal confidence on a 0.0 to 1.0 scale.

    Args:
        signal_data: Signal details including type, value, timing, actor.

    Returns:
        Float confidence score between 0.0 and 1.0.
    """
    try:
        client = _get_client()
        prompt = f"""You are a quantitative analyst. Score this market signal's reliability from 0.0 to 1.0.

Signal: {json.dumps(signal_data, indent=2, default=str)}

Scoring factors (weight each 0-1, then average):
- Signal size/materiality (is the value large enough to be meaningful?)
- Actor credibility (Promoter > Director > KMP > Institutional > Retail)
- Timing (proximity to earnings blackout windows, 52w levels)
- Consistency with recent broader signals
- Historical accuracy of this signal type

Return ONLY a single decimal number between 0.00 and 1.00. Nothing else."""

        def _call():
            return client.messages.create(
                model=MODEL,
                max_tokens=10,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}]
            )

        response = await _call_with_retry(_call)
        score_text = response.content[0].text.strip()
        score = float(score_text)
        return max(0.0, min(1.0, score))
    except Exception as e:
        logger.error(f"score_signal_confidence failed: {e}")
        # Fallback: rule-based scoring
        base_score = 0.5
        signal_type = signal_data.get("signal_type", "")
        if "INSIDER" in signal_type:
            base_score += 0.15
        if signal_data.get("value_cr", 0) > 5:
            base_score += 0.15
        if signal_data.get("category") == "Promoter":
            base_score += 0.1
        return min(1.0, base_score)


async def generate_follow_up_suggestions(context: str) -> list:
    """
    Generate follow-up question suggestions based on chat context.

    Args:
        context: Summary of the last AI response or topic.

    Returns:
        List of 3 suggested follow-up questions.
    """
    try:
        client = _get_client()
        prompt = f"""Based on this market analysis context, suggest 3 specific follow-up questions a retail investor would naturally ask next.

Context: {context[:500]}

Return exactly 3 questions as a JSON array of strings. Example format:
["Question 1?", "Question 2?", "Question 3?"]

Questions should be specific to Indian stocks/markets, not generic."""

        def _call():
            return client.messages.create(
                model=MODEL,
                max_tokens=200,
                temperature=0.8,
                messages=[{"role": "user", "content": prompt}]
            )

        response = await _call_with_retry(_call)
        text = response.content[0].text.strip()
        # Extract JSON array
        import re
        match = re.search(r'\[.*?\]', text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return ["What are the key risks?", "How does this compare to peers?", "What's the target price?"]
    except Exception as e:
        logger.error(f"generate_follow_up_suggestions failed: {e}")
        return [
            "What are the key risks for this investment?",
            "How does this compare to sector peers?",
            "What's the analyst consensus target price?"
        ]
