#!/usr/bin/env python3
"""
Download and parse UK Contracts Finder public procurement data.

Input:  data/raw/united_kingdom_contracts_finder_releases_full.csv/full/*.csv
Output: data/processed/buyers.json, vendors.json, contracts.json

The data is in OCDS flattened CSV format with multiple related files:
- main.csv: main contracting process (buyer, tender info)
- awards.csv: award values, dates, status
- awards_suppliers.csv: supplier names per award
- parties.csv: all parties (buyers + suppliers) with addresses
"""

import argparse
import csv
import json
import logging
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def parse_value(value):
    if value is None or value == "":
        return None
    if isinstance(value, str):
        value = value.strip()
        if value == "":
            return None
    return value


def parse_amount(value):
    if value is None or value == "":
        return None
    try:
        cleaned = re.sub(r"[£$,€\s]", "", str(value))
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def parse_date(value):
    if value is None or value == "":
        return None
    try:
        for fmt in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y", "%m/%d/%Y"]:
            try:
                dt = datetime.strptime(str(value).split("T")[0], fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
    except (ValueError, TypeError):
        pass
    return None


def load_csv(filepath: Path) -> list[dict]:
    """Load a CSV file and return list of dicts."""
    if not filepath.exists():
        logger.warning(f"File not found: {filepath}")
        return []
    with open(filepath, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def main():
    parser = argparse.ArgumentParser(description="Parse UK Contracts Finder OCDS data")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/raw/united_kingdom_contracts_finder_releases_full.csv/full"),
        help="Input directory with OCDS CSV files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed"),
        help="Output directory",
    )
    parser.add_argument("--limit", type=int, default=None, help="Limit rows for testing")
    args = parser.parse_args()

    if not args.input.exists():
        logger.error(f"Input directory not found: {args.input}")
        sys.exit(1)

    logger.info(f"Loading OCDS data from: {args.input}")

    # Load all CSV files
    main_rows = load_csv(args.input / "main.csv")
    awards_rows = load_csv(args.input / "awards.csv")
    awards_suppliers_rows = load_csv(args.input / "awards_suppliers.csv")
    parties_rows = load_csv(args.input / "parties.csv")

    logger.info(
        f"Loaded: main={len(main_rows):,}, awards={len(awards_rows):,}, "
        f"awards_suppliers={len(awards_suppliers_rows):,}, parties={len(parties_rows):,}"
    )

    if args.limit:
        main_rows = main_rows[: args.limit]
        awards_rows = awards_rows[: args.limit]
        awards_suppliers_rows = awards_suppliers_rows[: args.limit]
        parties_rows = parties_rows[: args.limit]
        logger.info(f"Limited to {args.limit} rows for testing")

    # Build lookup dictionaries
    # Awards by ocid
    awards_by_ocid = defaultdict(list)
    for row in awards_rows:
        ocid = parse_value(row.get("main_ocid"))
        if ocid:
            awards_by_ocid[ocid].append(row)

    # Suppliers by awards_id
    suppliers_by_award = defaultdict(list)
    for row in awards_suppliers_rows:
        award_id = parse_value(row.get("awards_id"))
        if award_id:
            suppliers_by_award[award_id].append(row)

    # Parties by main_ocid
    parties_by_ocid = defaultdict(list)
    for row in parties_rows:
        ocid = parse_value(row.get("main_ocid"))
        if ocid:
            parties_by_ocid[ocid].append(row)

    # Extract entities
    buyers = {}
    vendors = {}
    contracts = {}

    for main_row in main_rows:
        ocid = parse_value(main_row.get("ocid"))
        if not ocid:
            continue

        # Extract buyer from main.csv
        buyer_id = parse_value(main_row.get("buyer_id"))
        buyer_name = parse_value(main_row.get("buyer_name"))
        if buyer_id and buyer_name and buyer_id not in buyers:
            buyers[buyer_id] = {
                "id": buyer_id,
                "name": buyer_name,
                "country": "United Kingdom",
                "identifier": buyer_id,
                "source": "contracts_finder",
            }

        # Get parties for this ocid
        ocid_parties = parties_by_ocid.get(ocid, [])

        # Extract buyer from parties (more detail)
        for party in ocid_parties:
            roles = parse_value(party.get("roles", ""))
            if roles and "buyer" in roles:
                party_id = parse_value(party.get("id"))
                party_name = parse_value(party.get("name"))
                if party_id and party_name:
                    buyers[party_id] = {
                        "id": party_id,
                        "name": party_name,
                        "country": parse_value(party.get("address_countryName")) or "United Kingdom",
                        "identifier": party_id,
                        "source": "contracts_finder",
                    }

        # Get awards for this ocid
        awards = awards_by_ocid.get(ocid, [])

        for award in awards:
            award_id = parse_value(award.get("id"))
            if not award_id:
                continue

            # Get suppliers for this award
            award_suppliers = suppliers_by_award.get(award_id, [])

            for supplier_row in award_suppliers:
                supplier_id = parse_value(supplier_row.get("id"))
                supplier_name = parse_value(supplier_row.get("name"))

                if supplier_id and supplier_name:
                    # Add vendor
                    if supplier_id not in vendors:
                        vendors[supplier_id] = {
                            "id": supplier_id,
                            "name": supplier_name,
                            "country": "United Kingdom",
                            "tax_id": None,
                            "status": "active",
                            "source": "contracts_finder",
                        }

                    # Create contract
                    contract_value = parse_amount(award.get("value_amount"))
                    contract_currency = parse_value(award.get("value_currency")) or "GBP"
                    start_date = parse_date(award.get("contractPeriod_startDate"))
                    end_date = parse_date(award.get("contractPeriod_endDate"))

                    # Use ocid + award_id as unique contract ID
                    contract_id = f"{ocid}_{award_id}"

                    # Generate contract number
                    year = datetime.now().year
                    if start_date:
                        try:
                            year = int(start_date[:4])
                        except (ValueError, IndexError):
                            pass

                    contract_number = f"CF-{year}-{len(contracts) + 1:05d}"

                    # Get title/description from main.csv
                    title = parse_value(main_row.get("tender_title")) or "Untitled Contract"
                    description = parse_value(main_row.get("tender_description"))

                    # Get tender details
                    tender_method = parse_value(main_row.get("tender_procurementMethod"))
                    cpv_id = parse_value(main_row.get("tender_classification_id"))
                    cpv_desc = parse_value(main_row.get("tender_classification_description"))
                    published_date = parse_date(main_row.get("tender_datePublished"))

                    contracts[contract_id] = {
                        "id": contract_id,
                        "contract_number": contract_number,
                        "title": title,
                        "description": description,
                        "buyer_id": buyer_id,
                        "vendor_id": supplier_id,
                        "value": contract_value,
                        "max_value": contract_value * 1.2 if contract_value else None,
                        "currency": contract_currency,
                        "start_date": start_date,
                        "end_date": end_date,
                        "published_date": published_date,
                        "category": cpv_id,
                        "category_description": cpv_desc,
                        "procurement_method": tender_method,
                        "status": "active",
                        "source": "contracts_finder",
                        "source_reference": ocid,
                    }

    logger.info("\nExtraction complete:")
    logger.info(f"  Unique buyers: {len(buyers):,}")
    logger.info(f"  Unique vendors: {len(vendors):,}")
    logger.info(f"  Contracts: {len(contracts):,}")

    # Save
    args.output.mkdir(parents=True, exist_ok=True)

    for name, data in [
        ("buyers", list(buyers.values())),
        ("vendors", list(vendors.values())),
        ("contracts", list(contracts.values())),
    ]:
        output_path = args.output / f"{name}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"Saved {len(data):,} {name} to {output_path}")

    # Save metadata
    metadata = {
        "source": "UK Contracts Finder",
        "source_url": "https://www.contractsfinder.service.gov.uk/",
        "license": "Open Government Licence v3.0",
        "downloaded_at": datetime.now().isoformat(),
        "total_buyers": len(buyers),
        "total_vendors": len(vendors),
        "total_contracts": len(contracts),
        "files_processed": ["main.csv", "awards.csv", "awards_suppliers.csv", "parties.csv"],
    }
    with open(args.output / "metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info("Data parsing complete!")


if __name__ == "__main__":
    main()
