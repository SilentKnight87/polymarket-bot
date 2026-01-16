# Phase 10: Daily News Snapshots (Backtest Data)

**Dependencies:** Phase 3 (News Ingestion), Phase 9 (Market Snapshots)

**Tasks:** 1

---

## Task 10.1: Capture Daily News Snapshots

**Goal:** Persist the RSS/news flow to `data/historical/news/` so backtests can replay a full day’s inputs.

**Files to create/modify:**
- `agents/tracking/news_snapshot.py` (new)
- `agents/application/agent_loop.py` (call snapshotter daily)
- `scripts/python/cli.py` (add `news-snapshot` command)

**Requirements:**
```python
class NewsSnapshotter:
    def record_daily_snapshot(self, articles: list[NewsArticle]) -> bool:
        """
        Append new articles for the day and write:
        data/historical/news/YYYY-MM-DD.json
        """
```

**Storage format:**
```json
{
  "date": "2026-01-16",
  "articles": [
    {
      "headline": "...",
      "summary": "...",
      "source": "...",
      "url": "...",
      "published_at": "2026-01-16T12:34:56Z",
      "category": "crypto"
    }
  ]
}
```

**Success criteria:**
- [ ] Daily file written once per UTC day
- [ ] New articles appended without duplicates
- [ ] Works with live loop + manual CLI command

---

## Codex Assignment

**Run Task 10.1** - Enables historical backtests without manual news data.
