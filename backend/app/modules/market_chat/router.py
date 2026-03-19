"""
ET InvestorIQ — Market Chat Router
FastAPI router for the AI chat module.
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.modules.market_chat import service
from app.modules.market_chat.schemas import (
    ChatRequest, ChatResponse, Portfolio, PortfolioAnalysisResponse
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["Market Chat"])


@router.post("/message", response_model=ChatResponse)
async def chat_message(request: ChatRequest):
    """
    Send a chat message and get a full AI response.
    Supports portfolio context and live data tools.
    """
    return await service.chat(request)


@router.post("/stream")
async def stream_chat(request: ChatRequest):
    """
    Stream a chat response via Server-Sent Events.
    Connect with EventSource on the frontend.
    """
    async def generate():
        async for chunk in service.stream_chat(request):
            yield chunk

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/portfolio/analyze", response_model=PortfolioAnalysisResponse)
async def analyze_portfolio(portfolio: Portfolio):
    """
    Perform a comprehensive portfolio analysis without a chat conversation.
    Returns risk assessment, sector concentration, and recommendations.
    """
    return await service.analyze_portfolio(portfolio)


@router.get("/suggestions")
async def get_suggestions(symbol: Optional[str] = None):
    """
    Get AI-powered suggested questions for a symbol or general market context.
    Used to populate the chat UI with starter prompts.
    """
    suggestions = await service.get_suggestions(symbol=symbol)
    return [s.model_dump() for s in suggestions]
