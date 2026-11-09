# Evaluation Metrics

## Overview

Evaluation is a first-class component of this project. All metrics are computed from reproducible experiments on known ground truth.

## Metric Categories

### 1. Retrieval Metrics

Measures how well the retrieval pipeline finds relevant documents.

| Metric | Description | Target |
|---|---|---|
| **Recall@K** | Fraction of relevant documents in top-K results | > 0.85 |
| **Precision@K** | Fraction of top-K results that are relevant | > 0.70 |
| **MRR** | Mean Reciprocal Rank of first relevant result | > 0.75 |
| **NDCG@K** | Normalized Discounted Cumulative Gain | > 0.80 |
| **Context Precision** | Fraction of context used by LLM that is relevant | > 0.80 |
| **Context Recall** | Fraction of answer facts supported by context | > 0.85 |

**Benchmark:** `data/evaluation/retrieval_benchmark.json` (200 queries)

### 2. RAG Metrics

Measures the quality of generated answers.

| Metric | Description | Target |
|---|---|---|
| **Faithfulness** | Answer is grounded in provided context (no hallucination) | > 0.90 |
| **Answer Relevancy** | Answer addresses the user's question | > 0.85 |
| **Context Precision** | Relevant context is ranked higher than irrelevant | > 0.80 |
| **Context Recall** | All necessary context is retrieved | > 0.85 |

**Benchmark:** Generated from `retrieval_benchmark.json` + LLM judging

### 3. Agent Metrics

Measures the agent's ability to select tools and route correctly.

| Metric | Description | Target |
|---|---|---|
| **Tool Selection Accuracy** | Correct tool chosen for the task | > 0.90 |
| **Routing Accuracy** | Correct workflow selected for the intent | > 0.95 |
| **Workflow Completion Rate** | Workflow reaches a valid end state | > 0.95 |
| **Step Efficiency** | Number of steps vs. optimal path | < 1.5x optimal |

**Benchmark:** `data/evaluation/agent_benchmark.json` (100 tasks)

### 3b. Open-Ended Agent Metrics

Measures the tool-calling fallback introduced for comparative and arbitrary
data questions.

| Metric | Description |
|---|---|
| **Routing Accuracy** | Planner sends open-ended questions to the agent |
| **Tool Selection Accuracy** | Expected primary tool appeared in the run |
| **Answer Term Coverage** | Required terms are present in the final answer (not semantic correctness) |
| **Tool Success Rate** | Tool calls complete without an error |
| **Average Agent Steps** | Mean tool-calling rounds (hard cap: 6) |
| **Adversarial SQL Block Rate** | Unsafe statements rejected by the SQL guard |

**Benchmark:** `data/evaluation/open_ended_benchmark.json` (5 curated tasks)

**Results and limitations:** [OPEN_ENDED.md](OPEN_ENDED.md)

```bash
uv run python scripts/evaluate_open_ended.py \
  --output docs/evaluation/open_ended_results.json
```

### 4. Business Metrics

Measures detection and compliance performance.

| Metric | Description | Target |
|---|---|---|
| **Anomaly Precision** | Fraction of flagged anomalies that are true anomalies | > 0.80 |
| **Anomaly Recall** | Fraction of true anomalies that are detected | > 0.85 |
| **Policy Violation F1** | F1 score for policy violation detection | > 0.80 |
| **False Positive Rate** | Fraction of normal records incorrectly flagged | < 0.10 |

**Benchmark:** `data/evaluation/anomaly_ground_truth.json` (500 labeled records)

### 5. System Metrics

Measures operational performance.

| Metric | Description | Target |
|---|---|---|
| **P50 Latency** | Median end-to-end response time | < 5s |
| **P95 Latency** | 95th percentile response time | < 15s |
| **Throughput** | Requests per second | > 10 |
| **Error Rate** | Fraction of requests that fail | < 0.01 |

## Evaluation Scripts

```bash
# Run all evaluations
python scripts/run_evaluations.py --all

# Run specific category
python scripts/run_evaluations.py --retrieval
python scripts/run_evaluations.py --rag
python scripts/run_evaluations.py --agent
python scripts/run_evaluations.py --business

# Generate report
python scripts/run_evaluations.py --report --output docs/evaluation/RESULTS.md
```

## Reproducibility

All evaluations are reproducible:
- Fixed random seeds
- Versioned benchmark datasets
- Pinned dependency versions (via `uv.lock`)
- Documented evaluation environment

Results are stored in `docs/evaluation/RESULTS.md` with:
- Date of evaluation
- Git commit hash
- Dependency versions
- Full metric tables
