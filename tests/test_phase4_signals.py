from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.connectors.news_sources import NewsArticle
from agents.strategies.news_speed import NewsSpeedStrategy
from agents.utils.config import Config


class _LLMResult:
    def __init__(self, content: str) -> None:
        self.content = content


class _StubLLM:
    def __init__(self, content: str) -> None:
        self._content = content

    def invoke(self, _messages):
        return _LLMResult(self._content)


def test_news_speed_strategy_generates_signal_from_mock_llm(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "settings.yaml"
    config_path.write_text(
        """
trading:
  min_edge: 0.05
""".strip()
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("POLYMARKET_API_KEY", "test-key")

    config = Config(config_path=str(config_path))

    llm = _StubLLM(
        """
        Here you go:
        {
          "affected_markets": [
            {
              "market_id": "1",
              "direction": "YES",
              "estimated_prob": 0.80,
              "confidence": 8,
              "reasoning": "directly impacted"
            }
          ]
        }
        """
    )

    strategy = NewsSpeedStrategy(config=config, llm=llm)

    article = NewsArticle(
        headline="SEC announces decision date",
        summary="The SEC set a decision date for the ETF approval.",
        source="test",
        url="https://example.com",
        published_at=datetime.now(timezone.utc),
        category="crypto",
    )

    markets = [
        {
            "id": 1,
            "question": "Will the ETF be approved by Friday?",
            "outcomes": ["Yes", "No"],
            "outcomePrices": [0.6, 0.4],
            "volume24hr": 100000,
        },
        {
            "id": 2,
            "question": "Will it rain tomorrow?",
            "outcomes": ["Yes", "No"],
            "outcomePrices": [0.5, 0.5],
        },
    ]

    signals = strategy.generate_signals([article], markets)
    assert len(signals) == 1

    signal = signals[0]
    assert signal.market_id == "1"
    assert signal.direction == "YES"
    assert abs(signal.current_odds - 0.6) < 1e-9
    assert abs(signal.estimated_prob - 0.8) < 1e-9
    assert abs(signal.edge - 0.2) < 1e-9

