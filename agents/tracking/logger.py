from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_dir(log_dir: str) -> Path:
    raw = Path(log_dir)
    if raw.is_absolute():
        return raw
    return _repo_root() / raw


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_timestamp(value: Optional[datetime] = None) -> str:
    stamp = value or _utc_now()
    return stamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _json_default(obj: Any) -> str:
    if isinstance(obj, datetime):
        return _iso_timestamp(obj)
    return str(obj)


def _with_timestamp(payload: Dict[str, Any]) -> Dict[str, Any]:
    entry = dict(payload)
    timestamp = entry.get("timestamp")
    if isinstance(timestamp, datetime):
        entry["timestamp"] = _iso_timestamp(timestamp)
    elif not timestamp:
        entry["timestamp"] = _iso_timestamp()
    return entry


class BotLogger:
    def __init__(self, log_dir: str = "data/logs") -> None:
        self.log_dir = _resolve_dir(log_dir)
        self.signals_dir = self.log_dir / "signals"
        self.bets_dir = self.log_dir / "bets"
        self.performance_dir = self.log_dir / "performance"

        for directory in (self.log_dir, self.signals_dir, self.bets_dir, self.performance_dir):
            directory.mkdir(parents=True, exist_ok=True)

    def log_signal(self, signal: Dict[str, Any]) -> None:
        entry = _with_timestamp(signal)
        date_stamp = _utc_now().date().isoformat()
        path = self.signals_dir / f"{date_stamp}.jsonl"
        self._write_jsonl(path, entry)

    def log_bet(self, bet: Dict[str, Any]) -> None:
        entry = _with_timestamp(bet)
        date_stamp = _utc_now().date().isoformat()
        path = self.bets_dir / f"{date_stamp}.jsonl"
        self._write_jsonl(path, entry)

    def log_performance(self, metrics: Dict[str, Any]) -> None:
        entry = _with_timestamp(metrics)
        path = self.performance_dir / "daily_summary.json"
        existing: list[Dict[str, Any]] = []

        if path.exists():
            try:
                with path.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
                if isinstance(data, list):
                    existing = data
                elif isinstance(data, dict):
                    existing = [data]
            except json.JSONDecodeError:
                existing = []

        existing.append(entry)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(existing, handle, indent=2, sort_keys=True, default=_json_default)

    def _write_jsonl(self, path: Path, entry: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, default=_json_default))
            handle.write("\n")
