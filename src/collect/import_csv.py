"""Load any CSV of car listings into raw_listings.

Use this for public datasets (Kaggle etc.) or the synthetic sample.
Column names are mapped onto the raw schema with an optional JSON file.

    python -m src.collect.import_csv data/raw/sample_listings.csv --source synthetic
    python -m src.collect.import_csv data/raw/kaggle.csv --source kaggle --mapping mappings/kaggle.json --id-column ad_id
"""
import argparse
import json
from pathlib import Path

import pandas as pd

from src.db import RAW_COLUMNS, insert_raw


def import_csv(path: Path, source: str, mapping: dict | None = None, id_column: str | None = None) -> int:
    df = pd.read_csv(path, dtype=str)
    if mapping:
        df = df.rename(columns=mapping)

    if id_column:
        df["listing_id"] = df[id_column]
    elif "listing_id" not in df.columns:
        # No natural ID: use row number. Re-importing the SAME file is still idempotent.
        df["listing_id"] = [f"{path.stem}-{i}" for i in range(len(df))]

    df["source"] = source
    unknown = [c for c in df.columns if c not in RAW_COLUMNS]
    if unknown:
        print(f"Ignoring unmapped columns: {unknown}")
    return insert_raw(df)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("csv", type=Path)
    p.add_argument("--source", required=True)
    p.add_argument("--mapping", type=Path, help="JSON {csv_column: raw_column}")
    p.add_argument("--id-column", help="CSV column holding a unique listing ID")
    a = p.parse_args()

    mapping = json.loads(a.mapping.read_text()) if a.mapping else None
    n = import_csv(a.csv, a.source, mapping, a.id_column)
    print(f"Inserted {n} new rows from {a.csv} (source={a.source})")


if __name__ == "__main__":
    main()
