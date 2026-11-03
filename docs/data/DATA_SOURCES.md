# Data Sources

## Primary Source: UK Contracts Finder

| Attribute | Value |
|---|---|
| **Source** | UK Contracts Finder |
| **URL** | https://www.contractsfinder.service.gov.uk/ |
| **License** | Open Government Licence v3.0 |
| **Format** | CSV (flattened OCDS) |
| **Size** | ~493 MB (full history) |
| **Date Range** | 2016–present |
| **Update Frequency** | Daily |

### What it provides

- **Buyers:** UK public sector organizations (central government, local authorities, NHS)
- **Suppliers:** Vendor names and addresses
- **Contracts:** Title, description, value, currency, dates
- **Categories:** CPV (Common Procurement Vocabulary) codes
- **Procurement methods:** Open, restricted, negotiated, etc.

### License Terms (OGL v3.0)

You are free to:
- Copy, publish, distribute, and transmit the data
- Adapt the data
- Exploit the data commercially and non-commercially

You must:
- Acknowledge the source (UK Contracts Finder)
- Provide a link to the OGL license
- Not mislead by implying official status

Full license: https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/

---

## Alternative Sources (for future expansion)

| Source | Jurisdiction | License | Format | URL |
|---|---|---|---|---|
| OpenTender EU | 27 EU states + 8 more | CC BY-NC-SA 4.0 | JSONL/Excel/CSV | https://opentender.eu/eu/download |
| Italy ANAC | Italy | Open (Italian law) | JSON/Excel/CSV | https://dati.anticorruzione.it/opendata/dataset?q=ocds |
| South Africa National Treasury | South Africa | PDDL | JSON/Excel/CSV | https://ocds-api.etenders.gov.za/ |
| Greece Diavgis | Greece | CC BY 4.0 | JSON/Excel/CSV | https://api.diavgis.gr/ocds |

---

## Data Provenance

All public data is clearly marked as originating from UK Contracts Finder. The synthetic enterprise layer (purchase orders, invoices, payments) is generated deterministically from this public backbone and does NOT represent real company data.

---

## Data Pipeline

```
data/raw/united_kingdom_contracts_finder_releases_full.csv
    ↓
scripts/download_public_data.py  (parse, clean, normalize)
    ↓
data/processed/
    ↓
PostgreSQL (buyers, vendors, contracts tables)
```

See [GENERATION.md](GENERATION.md) for the synthetic data generation pipeline.
