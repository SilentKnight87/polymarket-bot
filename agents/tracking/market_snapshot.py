from __future__ import annotations

import ast
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_path(path: str) -> Path:
    raw = Path(path)
    if raw.is_absolute():
        return raw
    return _repo_root() / raw


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _market_id(market: dict) -> Optional[str]:
    for key in ("market_id", "id"):
        if key in market and market[key] is not None:
            return str(market[key])
    return None


def _extract_yes_no_prices(market: dict) -> tuple[Optional[float], Optional[float]]:
    yes = _safe_float(market.get("yes_price"))
    no = _safe_float(market.get("no_price"))
    if yes is not None and no is not None:
        return yes, no

    outcomes = market.get("outcomes") or market.get("outcome") or market.get("outcome_labels")
    prices = market.get("outcomePrices") or market.get("outcome_prices") or market.get("outcomePrice")

    if isinstance(outcomes, str):
        try:
            outcomes = json.loads(outcomes)
        except json.JSONDecodeError:
            try:
                outcomes = ast.literal_eval(outcomes)
            except Exception:  # noqa: BLE001
                pass
    if isinstance(prices, str):
        try:
            prices = json.loads(prices)
        except json.JSONDecodeError:
            try:
                prices = ast.literal_eval(prices)
            except Exception:  # noqa: BLE001
                pass

    if not isinstance(outcomes, list) or not isinstance(prices, list):
        return None, None

    outcome_to_price: dict[str, float] = {}
    for idx, outcome in enumerate(outcomes):
        if idx >= len(prices):
            continue
        price = _safe_float(prices[idx])
        if price is None:
            continue
        outcome_to_price[str(outcome).strip().lower()] = price

    yes_price = None
    no_price = None
    for key, price in outcome_to_price.items():
        if key in {"yes", "y"}:
            yes_price = price
        elif key in {"no", "n"}:
            no_price = price

    return yes_price, no_price


def _normalize_outcome(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, dict):
        for key in ("name", "label", "outcome"):
            if key in value:
                return _normalize_outcome(value[key])
        return None
    if isinstance(value, list):
        if len(value) == 1:
            return _normalize_outcome(value[0])
        return None
    text = str(value).strip().lower()
    if text in {"yes", "y"}:
        return "YES"
    if text in {"no", "n"}:
        return "NO"
    return None


def _extract_outcome(market: dict) -> Optional[str]:
    for key in ("outcome", "winningOutcome", "resolvedOutcome", "result", "resolution"):
        if key in market:
            outcome = _normalize_outcome(market.get(key))
            if outcome:
                return outcome
    return None


class MarketSnapshotter:
    def __init__(self, base_dir: str = "data/historical"):
        self.base_dir = _resolve_path(base_dir)
        self.market_dir = self.base_dir / "markets"
        self.resolution_dir = self.base_dir / "resolutions"
        self.market_dir.mkdir(parents=True, exist_ok=True)
        self.resolution_dir.mkdir(parents=True, exist_ok=True)

    def record_daily_snapshot(self, markets: list[dict], snapshot_date: Optional[date] = None) -> bool:
        day = snapshot_date or datetime.now(timezone.utc).date()
        path = self.market_dir / f"{day.isoformat()}.json"
        if path.exists():
            return False

        simplified: list[dict] = []
        for market in markets:
            mid = _market_id(market)
            if not mid:
                continue
            yes_price, no_price = _extract_yes_no_prices(market)
            if yes_price is None or no_price is None:
                continue
            outcome = _extract_outcome(market)
            simplified.append(
                {
                    "market_id": mid,
                    "question": market.get("question", ""),
                    "yes_price": yes_price,
                    "no_price": no_price,
                    "volume_24h": market.get("volume24hr")
                    or market.get("volume24hrClob")
                    or market.get("volume"),
                    "resolved": outcome is not None,
                    "outcome": outcome,
                    "end_date": market.get("endDate") or market.get("end"),
                }
            )

        payload = {"date": day.isoformat(), "markets": simplified}
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return True

    def detect_resolution(self, market: dict) -> Optional[dict]:
        outcome = _extract_outcome(market)
        if outcome is None:
            return None
        mid = _market_id(market)
        if mid is None:
            return None
        return {
            "market_id": mid,
            "outcome": outcome,
            "resolved_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }

    def record_resolutions(self, resolutions: list[dict], resolved_date: Optional[date] = None) -> bool:
        if not resolutions:
            return False
        day = resolved_date or datetime.now(timezone.utc).date()
        path = self.resolution_dir / f"{day.isoformat()}.json"
        existing: list[dict] = []
        if path.exists():
            try:
                existing = json.loads(path.read_text(encoding="utf-8")).get("resolutions", [])
            except Exception:  # noqa: BLE001
                existing = []

        seen = {(str(item.get("market_id")), str(item.get("outcome"))) for item in existing}
        for resolution in resolutions:
            key = (str(resolution.get("market_id")), str(resolution.get("outcome")))
            if key in seen:
                continue
            existing.append(resolution)
            seen.add(key)

        payload = {"date": day.isoformat(), "resolutions": existing}
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return True

