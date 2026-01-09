from __future__ import annotations

import os
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

import yaml

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    load_dotenv = None


_ENV_PATTERN = re.compile(r"\$\{([^}]+)\}")

_DEFAULT_SETTINGS: Dict[str, Any] = {
    "polymarket": {
        "api_key": "${POLYMARKET_API_KEY}",
        "wallet_address": "${WALLET_ADDRESS}",
    },
    "trading": {
        "mode": "paper",
        "bankroll": 500.0,
        "max_bet_pct": 0.05,
        "max_daily_loss_pct": 0.10,
        "min_edge": 0.05,
        "kelly_fraction": 0.5,
    },
    "news": {
        "sources": ["rss_politics", "rss_crypto"],
        "check_interval_seconds": 60,
    },
    "strategies": {
        "news_speed": {
            "enabled": True,
            "weight": 1.0,
        }
    },
}

_DEFAULT_STRATEGIES: Dict[str, Any] = {
    "news_speed": {
        "enabled": True,
        "weight": 1.0,
        "min_confidence": 6,
        "max_markets_per_cycle": 5,
    }
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_path(path: str) -> Path:
    raw = Path(path)
    if raw.is_absolute():
        return raw
    return _repo_root() / raw


def _deep_merge(base: Any, override: Any) -> Any:
    if isinstance(base, dict) and isinstance(override, dict):
        merged = dict(base)
        for key, value in override.items():
            if key in merged:
                merged[key] = _deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged
    return override


def _interpolate_env(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _interpolate_env(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_interpolate_env(item) for item in value]
    if isinstance(value, str):
        return _ENV_PATTERN.sub(lambda m: os.getenv(m.group(1), ""), value)
    return value


def _load_yaml(path: Path, defaults: Dict[str, Any]) -> Dict[str, Any]:
    if not path.exists():
        return _interpolate_env(deepcopy(defaults))
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    merged = _deep_merge(defaults, loaded)
    return _interpolate_env(merged)


class Config:
    def __init__(self, config_path: str = "config/settings.yaml") -> None:
        if load_dotenv is not None:
            load_dotenv(_repo_root() / ".env")
        self._settings = _load_yaml(_resolve_path(config_path), _DEFAULT_SETTINGS)
        self._strategies = _load_yaml(
            _resolve_path("config/strategies.yaml"), _DEFAULT_STRATEGIES
        )

    @property
    def trading_mode(self) -> str:
        return str(self._settings.get("trading", {}).get("mode", "paper"))

    @property
    def bankroll(self) -> float:
        return float(self._settings.get("trading", {}).get("bankroll", 0.0))

    @property
    def max_bet_pct(self) -> float:
        return float(self._settings.get("trading", {}).get("max_bet_pct", 0.0))

    @property
    def max_daily_loss_pct(self) -> float:
        return float(self._settings.get("trading", {}).get("max_daily_loss_pct", 0.0))

    @property
    def min_edge(self) -> float:
        return float(self._settings.get("trading", {}).get("min_edge", 0.0))

    @property
    def kelly_fraction(self) -> float:
        return float(self._settings.get("trading", {}).get("kelly_fraction", 0.0))

    @property
    def settings(self) -> Dict[str, Any]:
        return self._settings

    @property
    def strategies(self) -> Dict[str, Any]:
        return self._strategies
