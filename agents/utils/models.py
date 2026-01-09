from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Signal(BaseModel):
    timestamp: datetime
    market_id: str
    market_question: str
    direction: Literal["YES", "NO"]
    current_odds: float
    estimated_prob: float
    edge: float
    confidence: int = Field(ge=1, le=10)
    reasoning: str
    news_headline: str


class Bet(BaseModel):
    timestamp: datetime
    market_id: str
    direction: Literal["YES", "NO"]
    amount_usd: float
    odds_at_execution: float
    estimated_prob: float
    kelly_fraction: float
    mode: Literal["backtest", "paper", "live"]
    signal_id: Optional[str] = None


class Position(BaseModel):
    market_id: str
    direction: Literal["YES", "NO"]
    shares: float
    avg_price: float
    current_price: float
    unrealized_pnl: float


class PerformanceMetrics(BaseModel):
    date: str
    total_pnl: float
    win_rate: float
    num_bets: int
    avg_edge: float
    max_drawdown: float
