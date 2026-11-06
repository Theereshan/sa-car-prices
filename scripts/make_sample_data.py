"""Generate a SYNTHETIC, deliberately messy listings CSV so the whole pipeline
can be built and tested before real data exists. Never present results from
this data as real market findings.

    python scripts/make_sample_data.py --rows 5000
"""
import argparse
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

# make, model, new_price_zar, fuel options, annual depreciation rate
CATALOGUE = [
    ("Toyota", "Corolla", 420_000, ["Petrol"], 0.09),
    ("Toyota", "Hilux", 650_000, ["Diesel", "Petrol"], 0.07),
    ("Toyota", "Fortuner", 750_000, ["Diesel"], 0.075),
    ("Toyota", "Yaris", 300_000, ["Petrol"], 0.10),
    ("Volkswagen", "Polo", 350_000, ["Petrol"], 0.10),
    ("Volkswagen", "Golf GTI", 750_000, ["Petrol"], 0.12),
    ("BMW", "320d", 850_000, ["Diesel"], 0.14),
    ("BMW", "X3", 1_050_000, ["Diesel", "Petrol"], 0.13),
    ("Mercedes-Benz", "C200", 900_000, ["Petrol"], 0.14),
    ("Ford", "Ranger", 680_000, ["Diesel"], 0.09),
    ("Suzuki", "Swift", 230_000, ["Petrol"], 0.08),
    ("Hyundai", "Tucson", 550_000, ["Petrol", "Diesel"], 0.11),
]
PROVINCES = {"Gauteng": 1.03, "Western Cape": 1.04, "KwaZulu-Natal": 1.00,
             "Eastern Cape": 0.97, "Free State": 0.96, "Limpopo": 0.96, "Mpumalanga": 0.97,
             "North West": 0.96, "Northern Cape": 0.95}
PROVINCE_WEIGHTS = [0.38, 0.2, 0.17, 0.07, 0.04, 0.04, 0.05, 0.03, 0.02]


def messy(rng, value: str, variants: list[str], p: float = 0.3) -> str:
    """With probability p, replace a clean value with a messy real-world variant."""
    return rng.choice(variants) if rng.random() < p else value


def generate(rows: int, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    this_year = date.today().year
    out = []
    for i in range(rows):
        make, model, new_price, fuels, dep = CATALOGUE[rng.integers(len(CATALOGUE))]
        age = int(min(rng.exponential(5), 20))
        year = this_year - age
        km = max(0, int(rng.normal(18_000, 6_000) * max(age, 0.3)))
        fuel = rng.choice(fuels)
        trans = rng.choice(["Manual", "Automatic"], p=[0.45, 0.55])
        province = rng.choice(list(PROVINCES), p=PROVINCE_WEIGHTS)
        seller = rng.choice(["Dealer", "Private"], p=[0.7, 0.3])

        price = new_price * (1 - dep) ** age
        price *= 1 - 0.15 * (km - 18_000 * age) / 200_000       # above-average km lowers price
        price *= 1.05 if fuel == "Diesel" else 1.0
        price *= 1.04 if trans == "Automatic" else 1.0
        price *= 1.06 if seller == "Dealer" else 1.0
        price *= PROVINCES[province]
        price *= rng.normal(1, 0.07)                            # market noise
        price = round(max(price, 20_000), -2)

        row = {
            "listing_id": f"SYN-{i:06d}",
            "title": f"{year} {make} {model}",
            "make": messy(rng, make, [make.upper(), make.lower(), f" {make} "] + (["VW"] if make == "Volkswagen" else []), 0.15),
            "model": model,
            "year": str(year),
            "mileage": messy(rng, f"{km:,} km".replace(",", " "), [str(km), f"{km/1000:.0f}k km"], 0.3),
            "price": messy(rng, f"R {price:,.0f}".replace(",", " "), [f"{price:.0f}", f"R{price:,.2f}"], 0.3),
            "fuel_type": messy(rng, fuel, [fuel.upper(), fuel.lower() + " "], 0.2),
            "transmission": messy(rng, trans, ["Auto", "AT", "MT"] if trans == "Automatic" else ["MT", "manual"], 0.25),
            "province": messy(rng, province, {"Gauteng": ["GP", "gauteng"], "KwaZulu-Natal": ["KZN", "Kwazulu Natal"],
                                                  "Western Cape": ["WC"]}.get(province, [province]), 0.3),
            "seller_type": seller,
        }
        out.append(row)

    df = pd.DataFrame(out)
    # Inject the errors real data has, so cleaning has something to catch
    n = len(df)
    bad = rng.choice(n, size=int(n * 0.03), replace=False)
    df.loc[bad[: len(bad) // 3], "price"] = "POA"                       # price on application
    df.loc[bad[len(bad) // 3: 2 * len(bad) // 3], "price"] = "R 1"       # placeholder price
    df.loc[bad[2 * len(bad) // 3:], "mileage"] = "85"                    # missing thousands
    dupes = df.sample(int(n * 0.02), random_state=seed).copy()
    dupes["listing_id"] = dupes["listing_id"] + "-REPOST"
    return pd.concat([df, dupes], ignore_index=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--rows", type=int, default=5000)
    p.add_argument("--out", type=Path, default=Path("data/raw/sample_listings.csv"))
    a = p.parse_args()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    df = generate(a.rows)
    df.to_csv(a.out, index=False)
    print(f"Wrote {len(df)} synthetic rows to {a.out}")
