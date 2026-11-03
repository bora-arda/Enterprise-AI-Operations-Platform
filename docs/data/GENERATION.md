# Synthetic Data Generation

## Overview

The synthetic data layer builds on top of the public procurement backbone (UK Contracts Finder) to create a realistic enterprise environment with purchase orders, invoices, payments, and documents.

## Principles

1. **Deterministic** — Same seed always produces the same data
2. **Referential integrity** — Every synthetic record references a valid parent
3. **Internally consistent** — Documents match database records
4. **Controlled anomalies** — Known ground truth for evaluation
5. **Reproducible** — All scripts can be re-run to regenerate identical data

## Generation Pipeline

```
Public Contracts (CSV)
    ↓
[1] Parse & Normalize → buyers, vendors, contracts
    ↓
[2] Generate Purchase Orders (linked to contracts)
    ↓
[3] Generate Invoices (linked to POs)
    ↓
[4] Generate Payments (linked to invoices)
    ↓
[5] Generate Approvals (linked to invoices)
    ↓
[6] Generate Documents (from structured records)
    ↓
[7] Inject Anomalies (with ground truth)
    ↓
[8] Build Evaluation Dataset
```

## Scripts

### `scripts/download_public_data.py`

**Input:** `data/raw/united_kingdom_contracts_finder_releases_full.csv`
**Output:** `data/processed/` (normalized JSON/CSV)

- Parse the flattened OCDS CSV
- Extract buyers, suppliers, contracts
- Normalize field names and data types
- Handle missing values
- Deduplicate by OCID
- Save to processed directory

### `scripts/generate_synthetic_data.py`

**Input:** `data/processed/` + configuration
**Output:** PostgreSQL database

Configuration (via environment variables or config):
```yaml
seed: 42
num_departments: 8
num_users: 50
pos_per_contract_avg: 3
invoices_per_po_avg: 2
payments_rate: 0.85  # 85% of invoices get paid
approval_rate: 0.70  # 70% of invoices get approved
anomaly_rate: 0.08   # 8% of records have anomalies
```

Generation rules:
- POs reference valid contracts from public data
- Invoices reference valid POs
- Payments reference valid invoices
- Approval requests reference valid invoices
- All IDs follow deterministic patterns (e.g., `PO-2025-0001`, `INV-2025-0001`)

### `scripts/generate_documents.py`

**Input:** PostgreSQL database
**Output:** `data/processed/documents/` + pgvector

Document types generated:
- Contract PDFs (values match database)
- Procurement policy documents
- Approval policy documents
- Payment policy documents
- Invoice PDFs
- PO documents
- Email threads
- Operational notes

### `scripts/inject_anomalies.py`

**Input:** PostgreSQL database
**Output:** Modified database + `data/evaluation/anomaly_ground_truth.json`

Anomaly types (each with known ground truth):
| Type | Count | Detection Method |
|---|---|---|
| Invoice > PO amount | ~30 | Deterministic rule |
| Invoice > contract limit | ~20 | Deterministic rule |
| Duplicate invoice | ~15 | Fuzzy matching |
| Missing approval | ~25 | Deterministic rule |
| Expired contract | ~10 | Deterministic rule |
| Wrong vendor | ~10 | Deterministic rule |
| Already-paid invoice | ~10 | Deterministic rule |
| Invalid PO reference | ~10 | Deterministic rule |
| Wrong currency | ~10 | Deterministic rule |
| Payment mismatch | ~10 | Deterministic rule |
| Unusual amount | ~50 | ML (Isolation Forest) |

### `scripts/build_evaluation_set.py`

**Input:** PostgreSQL database + anomaly ground truth
**Output:** `data/evaluation/` benchmark datasets

Creates:
- `retrieval_benchmark.json` — 200 queries with expected sources
- `sql_benchmark.json` — 100 questions with expected SQL results
- `compliance_benchmark.json` — 50 compliance check cases
- `anomaly_ground_truth.json` — 500 labeled records
- `agent_benchmark.json` — 100 agent tasks with expected tool calls

### `scripts/run_evaluations.py`

**Input:** Benchmark datasets + running system
**Output:** `docs/evaluation/RESULTS.md`

Runs all evaluations and generates a report.

## Running the Full Pipeline

```bash
# 1. Start infrastructure
docker compose up -d postgres

# 2. Run migrations
uv run alembic upgrade head

# 3. Download and parse public data
python scripts/download_public_data.py \
    --input data/raw/united_kingdom_contracts_finder_releases_full.csv \
    --output data/processed/

# 4. Generate synthetic data
python scripts/generate_synthetic_data.py \
    --config configs/synthetic.yaml

# 5. Generate documents
python scripts/generate_documents.py

# 6. Inject anomalies
python scripts/inject_anomalies.py

# 7. Build evaluation datasets
python scripts/build_evaluation_set.py

# 8. Run evaluations (after system is deployed)
python scripts/run_evaluations.py --all
```

## Data Volume Estimates

| Entity | Estimated Count |
|---|---|
| Buyers | ~500 (from public data) |
| Vendors | ~2,000 (from public data) |
| Contracts | ~5,000 (from public data) |
| Purchase Orders | ~15,000 |
| Invoices | ~30,000 |
| Payments | ~25,000 |
| Approval Requests | ~21,000 |
| Documents | ~50,000 chunks |
| Exceptions | ~2,500 |
