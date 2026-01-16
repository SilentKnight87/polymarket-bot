# Repository Guidelines

## Project Structure

- `agents/`: core bot/agent code (application flow, connectors, Polymarket clients, strategies, tracking, utilities).
- `scripts/python/`: developer entrypoints (e.g., `cli.py` for the Typer CLI).
- `config/`: YAML configuration (defaults + env interpolation), e.g. `config/settings.yaml`.
- `tests/`: `pytest` tests (see `tests/test_*.py`).
- `docs/` and `spec/`: documentation and implementation notes/roadmap.
- `data/`: runtime artifacts such as logs (don’t commit generated output).

## Build, Test, and Development Commands

- Create env + install deps: `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- Configure secrets: `cp .env.example .env` (fill required keys).
- Run CLI: `PYTHONPATH=. python scripts/python/cli.py --help`
- Run an example command: `PYTHONPATH=. python scripts/python/cli.py get-all-markets --limit 5 --sort-by spread`
- Run tests: `PYTHONPATH=. python -m pytest`
- Format (pre-commit): `pre-commit install && pre-commit run -a`
- Docker (pinned Python 3.9): `./scripts/bash/build-docker.sh` then `./scripts/bash/run-docker-dev.sh`

## Coding Style & Naming

- Python: 4-space indentation, type hints where practical, keep functions small and composable.
- Formatting: Black (via `pre-commit`); don’t hand-format around it.
- Files: prefer `snake_case.py`; tests follow `tests/test_*.py`.

## Testing Guidelines

- Framework: `pytest` (keep tests deterministic; avoid network calls by default).
- Add new tests alongside the relevant phase/module (e.g., `tests/test_phase*_*.py`) and keep fixtures minimal.

## Commit & Pull Request Guidelines

- Commits in this repo are short and action-oriented (examples seen: `Fix ...`, `Implement ...`, `init: ...`).
- PRs: include a clear description, how to run/verify (commands), and note any config/env changes (update `.env.example` when adding variables).

## Security & Configuration Tips

- Never commit secrets: `.env`, private keys, API keys, or wallet details.
- Prefer `config/settings.yaml` for non-secret behavior (e.g., `trading.mode: paper|backtest|live`) and use env vars for sensitive values (`POLYMARKET_API_KEY`, `WALLET_ADDRESS`, etc.).
