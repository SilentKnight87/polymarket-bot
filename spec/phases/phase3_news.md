# Phase 3: News Ingestion

**Dependencies:** Phase 1 (Config)

**Tasks:** 1

---

## Task 3.1: Create News Sources Connector

**Goal:** Fetch news from RSS feeds and NewsAPI.

**Files to create:**
- `agents/connectors/news_sources.py`

**Dependencies to add to requirements.txt:**
```
feedparser
trafilatura
```

**Requirements:**
```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
import feedparser  # pip install feedparser

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

    def _parse_rss_feed(self, url: str, category: str) -> list[NewsArticle]:
        """Parse a single RSS feed."""
```

**RSS Feed Categories:**

| Category | Feeds | Polymarket Relevance |
|----------|-------|---------------------|
| Politics | NPR, Politico, AP | Elections, policy, legislation |
| Crypto | Cointelegraph, Decrypt | Token prices, regulations, hacks |
| Sports | ESPN (future) | Game outcomes, player trades |
| Tech | TechCrunch (future) | Product launches, earnings |

**Implementation Notes:**

1. **feedparser** handles RSS/Atom parsing with timezone normalization
2. **trafilatura** extracts clean article text from URLs (for full article analysis)
3. Track `last_fetch_time` to avoid re-processing old articles
4. Handle feed errors gracefully (timeout, malformed XML, 404)

**Example Usage:**
```python
from agents.connectors.news_sources import NewsAggregator
from agents.utils.config import Config

config = Config()
news = NewsAggregator(config)

# First fetch - gets recent articles
articles = news.fetch_new_articles()
print(f"Found {len(articles)} articles")

# Subsequent fetch - only new articles
import time
time.sleep(60)
new_articles = news.fetch_new_articles()
print(f"Found {len(new_articles)} new articles")
```

**Success criteria:**
- [ ] Fetches from multiple RSS feeds
- [ ] Returns only new articles (since last check)
- [ ] Handles feed errors gracefully (no crash on bad feed)
- [ ] Test: Fetch articles, print headlines

---

## Codex Assignment

**Run Task 3.1** - Can run in parallel with Phase 2 since it only depends on Phase 1 Config.
