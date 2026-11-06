"""Database helpers. One place owns the connection and the raw-insert logic."""
from functools import lru_cache

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.config import DATABASE_URL

RAW_COLUMNS = [
    "source", "listing_id", "url", "title", "make", "model", "variant",
    "year", "mileage", "price", "fuel_type", "transmission", "body_type",
    "province", "city", "seller_type",
]


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return create_engine(DATABASE_URL, pool_pre_ping=True)


def insert_raw(df: pd.DataFrame) -> int:
    """Insert rows into raw_listings. Existing (source, listing_id) pairs are skipped,
    so collectors and imports are safe to re-run. Returns rows actually inserted."""
    missing = {"source", "listing_id"} - set(df.columns)
    if missing:
        raise ValueError(f"DataFrame missing required columns: {missing}")

    df = df.reindex(columns=RAW_COLUMNS)
    # Raw layer stores everything as text; NaN -> NULL
    df = df.astype(object).where(df.notna(), None)
    for col in RAW_COLUMNS:
        df[col] = df[col].map(lambda v: None if v is None else str(v))

    cols = ", ".join(RAW_COLUMNS)
    params = ", ".join(f":{c}" for c in RAW_COLUMNS)
    sql = text(
        f"INSERT INTO raw_listings ({cols}) VALUES ({params}) "
        "ON CONFLICT (source, listing_id) DO NOTHING"
    )
    inserted = 0
    with get_engine().begin() as conn:
        for chunk_start in range(0, len(df), 1000):
            records = df.iloc[chunk_start:chunk_start + 1000].to_dict("records")
            result = conn.execute(sql, records)
            inserted += result.rowcount or 0
    return inserted


def read_sql(query: str, **params) -> pd.DataFrame:
    with get_engine().connect() as conn:
        return pd.read_sql(text(query), conn, params=params)
