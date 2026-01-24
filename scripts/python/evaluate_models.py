#!/usr/bin/env python3
"""CLI for running model evaluation comparisons.

Usage:
    # Compare default models on sample scenarios
    PYTHONPATH=. python scripts/python/evaluate_models.py

    # Compare specific models
    PYTHONPATH=. python scripts/python/evaluate_models.py --models gpt-4o claude-sonnet-4

    # Limit scenarios (for testing/cost control)
    PYTHONPATH=. python scripts/python/evaluate_models.py --max-scenarios 3

    # Custom scenario file
    PYTHONPATH=. python scripts/python/evaluate_models.py --scenarios data/evaluation/custom.json

    # Save results
    PYTHONPATH=. python scripts/python/evaluate_models.py --output data/evaluation/results.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agents.evaluation import ModelEvaluator, get_provider, list_available_models


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate LLM models on prediction market probability estimation"
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=["gpt-4o", "claude-sonnet-4"],
        help="Models to evaluate (default: gpt-4o claude-sonnet-4)",
    )
    parser.add_argument(
        "--scenarios",
        type=str,
        default="data/evaluation/sample_scenarios.json",
        help="Path to scenarios JSON file",
    )
    parser.add_argument(
        "--max-scenarios",
        type=int,
        default=None,
        help="Maximum scenarios to evaluate per model (for testing/cost control)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Save results to JSON file",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List available models and exit",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration without running evaluation",
    )

    args = parser.parse_args()

    if args.list_models:
        print("Available models:")
        for model in list_available_models():
            print(f"  - {model}")
        return 0

    # Validate scenarios file
    scenarios_path = Path(args.scenarios)
    if not scenarios_path.exists():
        print(f"Error: Scenarios file not found: {scenarios_path}")
        return 1

    # Load scenarios
    evaluator = ModelEvaluator()
    count = evaluator.load_scenarios_from_file(scenarios_path)
    print(f"Loaded {count} scenarios from {scenarios_path}")

    if args.max_scenarios:
        print(f"Limiting to {args.max_scenarios} scenarios per model")

    # Validate models
    available = set(list_available_models())
    invalid = [m for m in args.models if m not in available]
    if invalid:
        print(f"Error: Unknown models: {', '.join(invalid)}")
        print(f"Available: {', '.join(sorted(available))}")
        return 1

    if args.dry_run:
        print(f"\nDry run - would evaluate: {', '.join(args.models)}")
        print(f"Scenarios: {count}")
        return 0

    # Run evaluation
    print(f"\nEvaluating models: {', '.join(args.models)}")
    print("-" * 60)

    results = evaluator.compare_models(args.models, max_scenarios=args.max_scenarios)

    # Generate and print report
    report = evaluator.generate_report(results)
    print("\n" + report)

    # Save results if requested
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        evaluator.save_results(output_path, results)
        print(f"\nResults saved to: {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
