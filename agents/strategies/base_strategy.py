from __future__ import annotations

from abc import ABC, abstractmethod

from agents.connectors.news_sources import NewsArticle
from agents.utils.models import Signal


class BaseStrategy(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy name for logging."""

    @abstractmethod
    def generate_signals(self, articles: list[NewsArticle], markets: list[dict]) -> list[Signal]:
        """
        Analyze inputs and generate trading signals.

        Args:
            articles: New news articles since last check
            markets: Current Polymarket markets with prices/metadata

        Returns:
            List of trading signals (may be empty)
        """

