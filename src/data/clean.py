"""Raw -> clean. Every rule lives in a small pure function so it can be unit-tested.

    python -m src.data.clean            # rebuild listings_clean from raw_listings
"""
import re
from datetime import date

import numpy as np
import pandas as pd
from sqlalchemy import text

from src.db import get_engine

# ---- sanity bounds (anything outside is almost certainly a data error) --------
MIN_PRICE, MAX_PRICE = 15_000, 5_000_000
MIN_YEAR = 1990
MAX_MILEAGE = 600_000

FUEL_MAP = {
    "petrol": "Petrol", "gasoline": "Petrol", "unleaded": "Petrol", "p": "Petrol",
    "diesel": "Diesel", "d": "Diesel", "tdi": "Diesel", "d-4d": "Diesel",
    "hybrid": "Hybrid", "petrol hybrid": "Hybrid", "plug-in hybrid": "Hybrid",
    "electric": "Electric", "ev": "Electric",
}
TRANSMISSION_MAP = {
    "manual": "Manual", "m": "Manual", "mt": "Manual",
    "automatic": "Automatic", "auto": "Automatic", "a": "Automatic", "at": "Automatic",
    "cvt": "Automatic", "dct": "Automatic", "dsg": "Automatic", "tiptronic": "Automatic",
}
PROVINCE_MAP = {
    "gauteng": "Gauteng", "gp": "Gauteng", "gau": "Gauteng",
    "kwazulu-natal": "KwaZulu-Natal", "kwazulu natal": "KwaZulu-Natal", "kzn": "KwaZulu-Natal",
    "western cape": "Western Cape", "wc": "Western Cape",
    "eastern cape": "Eastern Cape", "ec": "Eastern Cape",
    "free state": "Free State", "fs": "Free State",
    "limpopo": "Limpopo", "lp": "Limpopo",
    "mpumalanga": "Mpumalanga", "mp": "Mpumalanga",
    "north west": "North West", "nw": "North West",
    "northern cape": "Northern Cape", "nc": "Northern Cape",
}
SELLER_MAP = {"dealer": "Dealer", "dealership": "Dealer", "private": "Private", "private seller": "Private"}
# Brands whose standard title-casing is wrong
MAKE_OVERRIDES = {"bmw": "BMW", "vw": "Volkswagen", "volkswagen": "Volkswagen",
                  "mercedes": "Mercedes-Benz", "mercedes benz": "Mercedes-Benz",
                  "mercedes-benz": "Mercedes-Benz", "gwm": "GWM", "mg": "MG", "kia": "Kia"}


# ---- field parsers -------------------------------------------------------------
def parse_number(value) -> float:
    """'R 189 900' -> 189900, '85 000 km' -> 85000, '120k' -> 120000, junk -> NaN."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return np.nan
    s = str(value).lower().replace(" ", " ").strip()
    multiplier = 1000 if re.search(r"\d\s*k\b", s) else 1
    s = re.sub(r"[^\d.]", "", s.replace(",", ""))   # drop R, spaces, km, commas
    if s.count(".") > 1 or s in ("", "."):
        return np.nan
    return float(s) * multiplier


def parse_year(value) -> float:
    m = re.search(r"\b(19|20)\d{2}\b", str(value)) if value is not None else None
    return float(m.group()) if m else np.nan


def _lookup(value, mapping: dict):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    key = re.sub(r"\s+", " ", str(value).strip().lower())
    return mapping.get(key)


def normalise_fuel(v):         return _lookup(v, FUEL_MAP)
def normalise_transmission(v): return _lookup(v, TRANSMISSION_MAP)
def normalise_province(v):     return _lookup(v, PROVINCE_MAP)
def normalise_seller(v):       return _lookup(v, SELLER_MAP)


def normalise_make(value):
    if value is None or (isinstance(value, float) and np.isnan(value)) or not str(value).strip():
        return None
    key = re.sub(r"\s+", " ", str(value).strip().lower())
    return MAKE_OVERRIDES.get(key, key.title())


def normalise_model(value):
    if value is None or (isinstance(value, float) and np.isnan(value)) or not str(value).strip():
        return None
    s = re.sub(r"\s+", " ", str(value).strip())
    def fix(w: str) -> str:
        if re.fullmatch(r"\d+[a-z]", w.lower()):  # BMW-style engine codes: 320d, 118i
            return w.lower()
        if any(c.isdigit() for c in w) or w.isupper():  # model codes: X3, CR-V, GTI
            return w.upper()
        return w.title()
    return " ".join(fix(w) for w in s.split(" "))


# ---- pipeline ------------------------------------------------------------------
def clean(raw: pd.DataFrame, current_year: int | None = None) -> tuple[pd.DataFrame, dict]:
    """Return (clean_df, report). report counts how many rows each rule dropped,
    so you can see whether a rule is too aggressive."""
    current_year = current_year or date.today().year
    report = {"raw_rows": len(raw)}
    df = pd.DataFrame({
        "id": raw["id"],
        "source": raw["source"],
        "listing_id": raw["listing_id"],
        "make": raw["make"].map(normalise_make),
        "model": raw["model"].map(normalise_model),
        "variant": raw["variant"].where(raw["variant"].notna(), None),
        "year": raw["year"].map(parse_year),
        "mileage_km": raw["mileage"].map(parse_number),
        "price_zar": raw["price"].map(parse_number),
        "fuel_type": raw["fuel_type"].map(normalise_fuel),
        "transmission": raw["transmission"].map(normalise_transmission),
        "body_type": raw["body_type"].map(lambda v: str(v).strip().title() if isinstance(v, str) and v.strip() else None),
        "province": raw["province"].map(normalise_province),
        "city": raw["city"].map(lambda v: str(v).strip().title() if isinstance(v, str) and v.strip() else None),
        "seller_type": raw["seller_type"].map(normalise_seller),
        "collected_at": raw["collected_at"],
    })

    def drop(mask: pd.Series, reason: str):
        nonlocal df
        report[f"dropped_{reason}"] = int(mask.sum())
        df = df[~mask]

    drop(df[["make", "model", "year", "mileage_km", "price_zar"]].isna().any(axis=1), "missing_core_fields")
    drop(~df["price_zar"].between(MIN_PRICE, MAX_PRICE), "price_out_of_range")
    drop(~df["year"].between(MIN_YEAR, current_year + 1), "year_out_of_range")
    drop(~df["mileage_km"].between(0, MAX_MILEAGE), "mileage_out_of_range")
    # Old car with near-zero km is almost always a typo (e.g. 85 instead of 85 000)
    drop((current_year - df["year"] >= 3) & (df["mileage_km"] < 1_000), "implausible_low_mileage")

    # Same car re-posted (or listed by two dealers): keep the most recent copy
    df = df.sort_values("collected_at")
    dup = df.duplicated(subset=["make", "model", "year", "mileage_km", "price_zar", "province"], keep="last")
    drop(dup, "duplicate_listing")

    df = df.astype({"year": int, "mileage_km": int})
    report["clean_rows"] = len(df)
    return df.reset_index(drop=True), report


def rebuild_clean_table() -> dict:
    engine = get_engine()
    raw = pd.read_sql("SELECT * FROM raw_listings", engine)
    df, report = clean(raw)
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE listings_clean"))
        df.to_sql("listings_clean", conn, if_exists="append", index=False, method="multi", chunksize=1000)
    return report


if __name__ == "__main__":
    for k, v in rebuild_clean_table().items():
        print(f"{k:>32}: {v}")
