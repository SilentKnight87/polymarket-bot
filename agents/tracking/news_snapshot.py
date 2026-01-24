from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

from agents.connectors.news_sources import NewsArticle


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_path(path: str) -> Path:
    raw = Path(path)
    if raw.is_absolute():
        return raw
    return _repo_root() / raw


def _article_to_dict(article: NewsArticle) -> dict[str, Any]:
    """Convert NewsArticle dataclass to dictionary for JSON serialization."""
    return {
        "headline": article.headline,
        "summary": article.summary,
        "source": article.source,
        "url": article.url,
        "published_at": article.published_at.isoformat().replace("+00:00", "Z"),
        "category": article.category,
    }


def _article_key(article: dict) -> tuple[str, str]:
    """Return a unique key for deduplication (url, headline)."""
    return (article.get("url", ""), article.get("headline", ""))


class NewsSnapshotter:
    """Persist daily news snapshots for historical backtest replay."""

    def __init__(self, base_dir: str = "data/historical"):
        self.base_dir = _resolve_path(base_dir)
        self.news_dir = self.base_dir / "news"
        self.news_dir.mkdir(parents=True, exist_ok=True)

    def record_daily_snapshot(
        self,
        articles: list[NewsArticle],
        snapshot_date: Optional[date] = None,
    ) -> bool:
        """
        Append new articles for the day and write to:
        data/historical/news/YYYY-MM-DD.json

        Returns True if new articles were added, False otherwise.
        """
        if not articles:
            return False

        day = snapshot_date or datetime.now(timezone.utc).date()
        path = self.news_dir / f"{day.isoformat()}.json"

        # Load existing articles for deduplication
        existing_articles: list[dict] = []
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                existing_articles = data.get("articles", [])
            except Exception:  # noqa: BLE001
                existing_articles = []

        seen_keys = {_article_key(a) for a in existing_articles}
        new_articles: list[dict] = []

        for article in articles:
            article_dict = _article_to_dict(article)
            key = _article_key(article_dict)
            if key in seen_keys:
                continue
            new_articles.append(article_dict)
            seen_keys.add(key)

        if not new_articles:
            return False

        # Append new articles and write
        all_articles = existing_articles + new_articles
        payload = {
            "date": day.isoformat(),
            "articles": all_articles,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return True

    def get_articles_for_date(self, target_date: date) -> list[dict]:
        """Load articles from a historical snapshot for backtesting."""
        path = self.news_dir / f"{target_date.isoformat()}.json"
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data.get("articles", [])
        except Exception:  # noqa: BLE001
            return []

    def list_available_dates(self) -> list[date]:
        """List all dates with news snapshots available."""
        dates: list[date] = []
        for path in sorted(self.news_dir.glob("*.json")):
            try:
                d = date.fromisoformat(path.stem)
                dates.append(d)
            except ValueError:
                continue
        return dates
