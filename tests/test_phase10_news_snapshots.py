from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agents.connectors.news_sources import NewsArticle
from agents.tracking.news_snapshot import NewsSnapshotter


def test_news_snapshot_writes_daily_file(tmp_path: Path) -> None:
    """Test that news snapshot writes articles to daily JSON file."""
    base_dir = tmp_path / "historical"
    snapshotter = NewsSnapshotter(base_dir=str(base_dir))

    articles = [
        NewsArticle(
            headline="Test headline",
            summary="Test summary",
            source="Test Source",
            url="https://example.com/article1",
            published_at=datetime(2026, 1, 16, 12, 0, 0, tzinfo=timezone.utc),
            category="crypto",
        )
    ]

    today = date(2026, 1, 16)
    wrote = snapshotter.record_daily_snapshot(articles, snapshot_date=today)
    assert wrote

    path = base_dir / "news" / "2026-01-16.json"
    assert path.exists()

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["date"] == "2026-01-16"
    assert len(data["articles"]) == 1
    assert data["articles"][0]["headline"] == "Test headline"
    assert data["articles"][0]["category"] == "crypto"


def test_news_snapshot_appends_without_duplicates(tmp_path: Path) -> None:
    """Test that calling record_daily_snapshot multiple times doesn't duplicate articles."""
    base_dir = tmp_path / "historical"
    snapshotter = NewsSnapshotter(base_dir=str(base_dir))
    today = date(2026, 1, 16)

    article1 = NewsArticle(
        headline="First headline",
        summary="First summary",
        source="Source A",
        url="https://example.com/article1",
        published_at=datetime(2026, 1, 16, 10, 0, 0, tzinfo=timezone.utc),
        category="politics",
    )

    article2 = NewsArticle(
        headline="Second headline",
        summary="Second summary",
        source="Source B",
        url="https://example.com/article2",
        published_at=datetime(2026, 1, 16, 11, 0, 0, tzinfo=timezone.utc),
        category="crypto",
    )

    # Write first article
    wrote1 = snapshotter.record_daily_snapshot([article1], snapshot_date=today)
    assert wrote1

    # Write second article (should append)
    wrote2 = snapshotter.record_daily_snapshot([article2], snapshot_date=today)
    assert wrote2

    # Try to write first article again (should not add duplicate)
    wrote3 = snapshotter.record_daily_snapshot([article1], snapshot_date=today)
    assert not wrote3  # No new articles added

    path = base_dir / "news" / "2026-01-16.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert len(data["articles"]) == 2


def test_news_snapshot_get_articles_for_date(tmp_path: Path) -> None:
    """Test retrieving articles for a specific date."""
    base_dir = tmp_path / "historical"
    snapshotter = NewsSnapshotter(base_dir=str(base_dir))
    today = date(2026, 1, 16)

    articles = [
        NewsArticle(
            headline="Test headline",
            summary="Test summary",
            source="Test Source",
            url="https://example.com/article1",
            published_at=datetime(2026, 1, 16, 12, 0, 0, tzinfo=timezone.utc),
            category="crypto",
        )
    ]

    snapshotter.record_daily_snapshot(articles, snapshot_date=today)

    # Retrieve articles
    retrieved = snapshotter.get_articles_for_date(today)
    assert len(retrieved) == 1
    assert retrieved[0]["headline"] == "Test headline"

    # Try non-existent date
    empty = snapshotter.get_articles_for_date(date(2020, 1, 1))
    assert empty == []


def test_news_snapshot_list_available_dates(tmp_path: Path) -> None:
    """Test listing all available snapshot dates."""
    base_dir = tmp_path / "historical"
    snapshotter = NewsSnapshotter(base_dir=str(base_dir))

    article = NewsArticle(
        headline="Test",
        summary="Test",
        source="Test",
        url="https://example.com/test",
        published_at=datetime(2026, 1, 16, 12, 0, 0, tzinfo=timezone.utc),
        category="crypto",
    )

    snapshotter.record_daily_snapshot([article], snapshot_date=date(2026, 1, 15))
    snapshotter.record_daily_snapshot([article], snapshot_date=date(2026, 1, 16))
    snapshotter.record_daily_snapshot([article], snapshot_date=date(2026, 1, 17))

    dates = snapshotter.list_available_dates()
    assert len(dates) == 3
    assert date(2026, 1, 15) in dates
    assert date(2026, 1, 16) in dates
    assert date(2026, 1, 17) in dates


def test_news_snapshot_empty_articles_returns_false(tmp_path: Path) -> None:
    """Test that empty article list returns False."""
    base_dir = tmp_path / "historical"
    snapshotter = NewsSnapshotter(base_dir=str(base_dir))

    wrote = snapshotter.record_daily_snapshot([], snapshot_date=date(2026, 1, 16))
    assert not wrote
