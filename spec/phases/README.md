# Implementation Phases

**Project:** Polymarket Prediction Markets Bot

**Base:** Fork of Polymarket/agents

---

## Overview

| Phase | File | Tasks | Description |
|-------|------|-------|-------------|
| 1 | [archive/phase1_infrastructure.md](archive/phase1_infrastructure.md) | 3 | Config, Logging, Data Models |
| 2 | [archive/phase2_kelly_risk.md](archive/phase2_kelly_risk.md) | 2 | Kelly Sizing, Risk Manager |
| 3 | [phase3_news.md](phase3_news.md) | 1 | News Sources (RSS) |
| 4 | [phase4_signals.md](phase4_signals.md) | 2 | Base Strategy, News Speed Strategy |
| 5 | [phase5_agent_loop.md](phase5_agent_loop.md) | 2 | Agent Loop, CLI Entry Point |
| 6 | [phase6_paper_trading.md](phase6_paper_trading.md) | 1 | Paper Trade Executor |
| 7 | [phase7_performance.md](phase7_performance.md) | 1 | Performance Tracker |
| 8 | [phase8_backtesting.md](phase8_backtesting.md) | 1 | Backtest Runner |

**Total: 13 Tasks**

## Current Status (as of 2026-01-15)

- Completed: Phases 1–3 (config/logging/models, kelly/risk, RSS news ingestion)
- Next: Phase 4 (signal generation + news speed strategy)

---

## Dependency Graph

```
Phase 1: Configuration & Infrastructure
├── Task 1.1: Config System
├── Task 1.2: Logging
└── Task 1.3: Data Models
         │
         ▼
    ┌────┴────┐
    │         │
    ▼         ▼
Phase 2    Phase 3
Kelly/Risk   News
    │         │
    └────┬────┘
         │
         ▼
      Phase 4
   Signal Generation
         │
         ▼
      Phase 5
    Agent Loop
         │
         ▼
      Phase 6
   Paper Trading
         │
         ▼
      Phase 7
   Performance
         │
         ▼
      Phase 8
   Backtesting
```

---

## Suggested Codex Assignment Order

### Batch 1 (Parallel)
- Task 1.1: Config System
- Task 1.2: Logging
- Task 1.3: Data Models

### Batch 2 (Parallel)
- Task 2.1: Kelly Sizing
- Task 2.2: Risk Manager
- Task 3.1: News Sources

### Batch 3 (Sequential)
- Task 4.1: Base Strategy
- Task 4.2: News Speed Strategy

### Batch 4 (Sequential)
- Task 5.1: Agent Loop
- Task 5.2: CLI Entry Point

### Batch 5 (Parallel)
- Task 6.1: Paper Trade Executor
- Task 7.1: Performance Tracker

### Final
- Task 8.1: Backtest Runner

---

## Quick Reference

Each phase file contains:
- **Dependencies** - What must be complete first
- **Files to create** - Exact paths
- **Requirements** - Python code interfaces
- **Success criteria** - Checkboxes for completion
- **Codex assignment notes** - How to run tasks

---

*Each task is designed to be self-contained and testable independently.*
