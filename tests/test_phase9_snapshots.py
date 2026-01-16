from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.tracking.market_snapshot import MarketSnapshotter


def test_market_snapshot_writes_daily_file(tmp_path: Path) -> None:
    base_dir = tmp_path / "historical"
    snapshotter = MarketSnapshotter(base_dir=str(base_dir))

    markets = [
        {
            "id": 1,
            "question": "Test market",
            "outcomes": ["Yes", "No"],
            "outcomePrices": [0.6, 0.4],
            "volume24hr": 1000,
        }
    ]

    today = date(2025, 12, 1)
    wrote = snapshotter.record_daily_snapshot(markets, snapshot_date=today)
    assert wrote

    path = base_dir / "markets" / "2025-12-01.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["date"] == "2025-12-01"
    assert data["markets"][0]["market_id"] == "1"
    assert abs(data["markets"][0]["yes_price"] - 0.6) < 1e-9


def test_market_snapshot_records_resolution(tmp_path: Path) -> None:
    base_dir = tmp_path / "historical"
    snapshotter = MarketSnapshotter(base_dir=str(base_dir))

    resolutions = [{"market_id": "1", "outcome": "YES", "resolved_at": "2025-12-01T00:00:00Z"}]
    wrote = snapshotter.record_resolutions(resolutions, resolved_date=date(2025, 12, 1))
    assert wrote

    path = base_dir / "resolutions" / "2025-12-01.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["resolutions"]) == 1
    assert data["resolutions"][0]["market_id"] == "1"
