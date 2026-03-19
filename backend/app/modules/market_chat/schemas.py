"""
ET InvestorIQ — Market Chat Schemas
Pydantic v2 models for the AI-powered portfolio-aware chat module.
"""

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class RiskProfile(str, Enum):
    """Investor risk tolerance."""
    CONSERVATIVE = "CONSERVATIVE"
    MODERATE = "MODERATE"
    AGGRESSIVE = "AGGRESSIVE"


class InvestmentHorizon(str, Enum):
    """Investment time horizon."""
    SHORT = "SHORT"     # < 6 months
    MEDIUM = "MEDIUM"   # 6 months - 3 years
    LONG = "LONG"       # > 3 years


class Holding(BaseModel):
    """Single portfolio holding."""
    symbol: str
    quantity: int
    avg_cost: float
    current_value: Optional[float] = None
    gain_pct: Optional[float] = None


class Portfolio(BaseModel):
    """User's investment portfolio context for AI-aware chat."""
    holdings: List[Holding] = Field(default_factory=list)
    total_value: float = 0.0
    total_invested: float = 0.0
    overall_gain_pct: float = 0.0
    risk_profile: RiskProfile = RiskProfile.MODERATE
    investment_horizon: InvestmentHorizon = InvestmentHorizon.MEDIUM


class Source(BaseModel):
    """Data source citation for a chat response."""
    name: str
    url: Optional[str] = None
    type: str = "tool"  # tool, web, filing, news


class ToolCallRecord(BaseModel):
    """Record of a tool called by Claude during a conversation turn."""
    name: str
    input: Dict = Field(default_factory=dict)
    output_summary: str = ""


class ChatMessage(BaseModel):
    """A single chat message in the conversation."""
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    sources: List[Source] = Field(default_factory=list)
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)


class ChatRequest(BaseModel):
    """Incoming chat request with conversation history and portfolio context."""
    messages: List[ChatMessage]
    portfolio: Optional[Portfolio] = None
    session_id: str = ""


class ChatResponse(BaseModel):
    """Full chat response with sources, tool calls, and follow-up suggestions."""
    response: str
    sources: List[Source] = Field(default_factory=list)
    tool_calls: List[ToolCallRecord] = Field(default_factory=list)
    follow_up_suggestions: List[str] = Field(default_factory=list)
    session_id: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class PortfolioAnalysisResponse(BaseModel):
    """Portfolio analysis response (non-chat context)."""
    portfolio: Portfolio
    analysis: str
    risk_assessment: str
    top_holding: str
    weakest_holding: str
    recommendations: List[str] = Field(default_factory=list)
    sector_concentration: Dict[str, float] = Field(default_factory=dict)
    suggested_actions: List[str] = Field(default_factory=list)


class SuggestedQuestion(BaseModel):
    """A suggested chat question for a given stock or topic."""
    question: str
    category: str  # fundamental, technical, sector, portfolio
