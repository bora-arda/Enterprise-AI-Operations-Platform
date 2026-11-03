"""Evaluation runner for orchestrating all evaluations."""

import json
import logging
from datetime import datetime
from pathlib import Path

from procurement_ai.evaluation.business_eval import evaluate_business
from procurement_ai.evaluation.rag_eval import evaluate_rag
from procurement_ai.evaluation.retrieval_eval import evaluate_retrieval

logger = logging.getLogger(__name__)


def run_all_evaluations(
    eval_dir: Path,
    results_dir: Path | None = None,
) -> dict:
    """Run all evaluations and return results."""
    results = {}

    # Load benchmark data
    benchmark_files = {
        "retrieval": "retrieval_benchmark.json",
        "agent": "agent_benchmark.json",
        "ground_truth": "anomaly_ground_truth.json",
    }

    benchmarks = {}
    for key, filename in benchmark_files.items():
        filepath = eval_dir / filename
        if filepath.exists():
            with open(filepath) as f:
                benchmarks[key] = json.load(f)

    # Run retrieval evaluation
    if "retrieval" in benchmarks:
        # TODO: Run actual retrieval and compare
        results["retrieval"] = evaluate_retrieval(benchmarks["retrieval"], {})

    # Run RAG evaluation
    if "retrieval" in benchmarks:
        # TODO: Run actual RAG and compare
        results["rag"] = evaluate_rag(benchmarks["retrieval"], {})

    # Run agent evaluation
    if "agent" in benchmarks:
        # TODO: Run actual agent and compare
        results["agent"] = {"total_tasks": len(benchmarks["agent"])}

    # Run business evaluation
    if "ground_truth" in benchmarks:
        results["business"] = evaluate_business(benchmarks["ground_truth"], [])

    return results


def generate_report(results: dict, output_path: Path) -> None:
    """Generate markdown evaluation report."""
    report = f"""# Evaluation Results

**Generated:** {datetime.now().isoformat()}

## Retrieval Metrics

```json
{json.dumps(results.get("retrieval", {}), indent=2)}
```

## RAG Metrics

```json
{json.dumps(results.get("rag", {}), indent=2)}
```

## Agent Metrics

```json
{json.dumps(results.get("agent", {}), indent=2)}
```

## Business Metrics

```json
{json.dumps(results.get("business", {}), indent=2)}
```
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(report)
    logger.info(f"Report saved to {output_path}")
