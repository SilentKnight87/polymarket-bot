from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from agents.connectors.news_sources import NewsArticle


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_path(path: str) -> Path:
    raw = Path(path)
    if raw.is_absolute():
        return raw
    return _repo_root() / raw


def _format_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _article_key(article: dict) -> tuple[str, str, str]:
    return (
        str(article.get("url") or ""),
        str(article.get("headline") or ""),
        str(article.get("published_at") or ""),
    )


def _serialize_article(article: NewsArticle) -> dict:
    return {
        "headline": article.headline,
        "summary": article.summary,
        "source": article.source,
        "url": article.url,
        "published_at": _format_datetime(article.published_at),
        "category": article.category,
    }


class NewsSnapshotter:
    def __init__(self, base_dir: str = "data/historical") -> None:
        self.base_dir = _resolve_path(base_dir)
        self.news_dir = self.base_dir / "news"
        self.news_dir.mkdir(parents=True, exist_ok=True)

    def record_daily_snapshot(
        self, articles: list[NewsArticle], snapshot_date: Optional[date] = None
    ) -> bool:
        day = snapshot_date or datetime.now(timezone.utc).date()
        path = self.news_dir / f"{day.isoformat()}.json"

        existing_articles: list[dict] = []
        if path.exists():
            try:
                existing_articles = json.loads(path.read_text(encoding="utf-8")).get(
                    "articles", []
                )
            except Exception:  # noqa: BLE001
                existing_articles = []

        existing_keys = {_article_key(article) for article in existing_articles}
        new_entries: list[dict] = []
        for article in articles:
            entry = _serialize_article(article)
            key = _article_key(entry)
            if key in existing_keys:
                continue
            existing_keys.add(key)
            new_entries.append(entry)

        if not path.exists():
            payload = {"date": day.isoformat(), "articles": existing_articles + new_entries}
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            return True

        if not new_entries:
            return False

        payload = {"date": day.isoformat(), "articles": existing_articles + new_entries}
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return True
