from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.connectors.news_sources import NewsArticle
from agents.strategies.base_strategy import BaseStrategy
from agents.tracking.backtest import BacktestRunner
from agents.utils.config import Config
from agents.utils.models import Signal


class _DummyStrategy(BaseStrategy):
    @property
    def name(self) -> str:
        return "dummy"

    def generate_signals(self, articles: list[NewsArticle], markets: list[dict]) -> list[Signal]:
        if not articles:
            return []
        return [
            Signal(
                timestamp=datetime.now(timezone.utc),
                market_id="m1",
                market_question="Test market",
                direction="YES",
                current_odds=0.5,
                estimated_prob=0.6,
                edge=0.1,
                confidence=7,
                reasoning="test",
                news_headline=articles[0].headline,
            )
        ]


def test_backtest_runner_runs_on_sample_data(tmp_path: Path, monkeypatch) -> None:
    base_dir = tmp_path / "historical"
    (base_dir / "news").mkdir(parents=True)
    (base_dir / "markets").mkdir(parents=True)
    (base_dir / "resolutions").mkdir(parents=True)

    day = "2025-12-01"
    (base_dir / "news" / f"{day}.json").write_text(
        json.dumps(
            {
                "date": day,
                "articles": [
                    {
                        "headline": "Test headline",
                        "summary": "Test summary",
                        "source": "unit",
                        "published_at": "2025-12-01T00:00:00Z",
                        "category": "politics",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (base_dir / "markets" / f"{day}.json").write_text(
        json.dumps(
            {
                "date": day,
                "markets": [
                    {"market_id": "m1", "question": "Test market", "yes_price": 0.5, "no_price": 0.5}
                ],
            }
        ),
        encoding="utf-8",
    )
    (base_dir / "resolutions" / f"{day}.json").write_text(
        json.dumps({"date": day, "resolutions": [{"market_id": "m1", "outcome": "YES"}]}),
        encoding="utf-8",
    )

    monkeypatch.setenv("POLYMARKET_API_KEY", "test-key")
    config = Config(overrides={"trading": {"bankroll": 100.0}})

    runner = BacktestRunner(
        strategy=_DummyStrategy(),
        start_date=datetime.fromisoformat(day),
        end_date=datetime.fromisoformat(day),
        initial_bankroll=100.0,
        base_dir=str(base_dir),
        config=config,
    )

    result = runner.run()
    assert result.num_trades == 1
    assert result.total_pnl > 0

