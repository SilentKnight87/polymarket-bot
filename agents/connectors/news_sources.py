from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

try:
    import feedparser
except ImportError:  # pragma: no cover
    feedparser = None

try:
    import trafilatura
except ImportError:  # pragma: no cover
    trafilatura = None

from agents.utils.config import Config

logger = logging.getLogger(__name__)


@dataclass
class NewsArticle:
    headline: str
    summary: str
    source: str
    url: str
    published_at: datetime
    category: Optional[str] = None


class NewsAggregator:
    def __init__(self, config: Config):
        self.config = config
        self.rss_feeds = {
            "politics": [
                "https://feeds.npr.org/1001/rss.xml",  # NPR Politics
                "https://rss.politico.com/politics-news.xml",
            ],
            "crypto": [
                "https://cointelegraph.com/rss",
                "https://decrypt.co/feed",
            ],
        }
        self.last_fetch_time: Optional[datetime] = None

    def fetch_new_articles(self, since: Optional[datetime] = None) -> list[NewsArticle]:
        """Fetch articles newer than `since` timestamp."""
        cutoff = since or self.last_fetch_time
        categories = self._resolve_categories()
        articles: list[NewsArticle] = []

        for category in categories:
            for url in self.rss_feeds.get(category, []):
                try:
                    articles.extend(self._parse_rss_feed(url, category))
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Failed to parse feed %s: %s", url, exc)

        if cutoff is not None:
            articles = [article for article in articles if article.published_at > cutoff]

        if articles:
            self.last_fetch_time = max(article.published_at for article in articles)
        else:
            self.last_fetch_time = datetime.now(timezone.utc)

        return articles

    def _resolve_categories(self) -> list[str]:
        sources = self.config.settings.get("news", {}).get("sources", [])
        if not sources:
            return list(self.rss_feeds.keys())

        categories: list[str] = []
        for entry in sources:
            normalized = str(entry).lower()
            if normalized in {"rss_politics", "politics"}:
                categories.append("politics")
            elif normalized in {"rss_crypto", "crypto"}:
                categories.append("crypto")

        return categories or list(self.rss_feeds.keys())

    def _parse_rss_feed(self, url: str, category: str) -> list[NewsArticle]:
        """Parse a single RSS feed."""
        if feedparser is None:  # pragma: no cover
            raise RuntimeError("feedparser is required for RSS ingestion (pip install feedparser).")
        feed = feedparser.parse(url)
        if getattr(feed, "bozo", False):
            logger.warning("Malformed feed for %s", url)

        articles: list[NewsArticle] = []
        for entry in feed.entries:
            published_at = self._parse_entry_time(entry)
            headline = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            summary = entry.get("summary", "").strip()

            if not summary and link:
                summary = self._extract_full_text(link) or ""

            if not headline or not link or published_at is None:
                continue

            articles.append(
                NewsArticle(
                    headline=headline,
                    summary=summary,
                    source=feed.feed.get("title", "unknown"),
                    url=link,
                    published_at=published_at,
                    category=category,
                )
            )

        return articles

    def _parse_entry_time(self, entry: dict) -> Optional[datetime]:
        time_struct = entry.get("published_parsed") or entry.get("updated_parsed")
        if not time_struct:
            return None
        return datetime.fromtimestamp(
            feedparser.mktime_tz(time_struct), tz=timezone.utc
        )

    def _extract_full_text(self, url: str) -> Optional[str]:
        if trafilatura is None:  # pragma: no cover
            return None
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return None
        return trafilatura.extract(downloaded)
