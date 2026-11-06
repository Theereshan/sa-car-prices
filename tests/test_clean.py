import numpy as np
import pandas as pd
import pytest

from src.data.clean import (
    clean, normalise_fuel, normalise_make, normalise_model, normalise_province,
    normalise_transmission, parse_number, parse_year,
)


@pytest.mark.parametrize("raw, expected", [
    ("R 189 900", 189900), ("R189,900.00", 189900), ("85 000 km", 85000),
    ("120k km", 120000), ("120K", 120000), (" R 99 000", 99000), (250000, 250000),
])
def test_parse_number(raw, expected):
    assert parse_number(raw) == expected


@pytest.mark.parametrize("raw", ["POA", "", None, "call us", "1.2.3"])
def test_parse_number_junk_is_nan(raw):
    assert np.isnan(parse_number(raw))


def test_parse_year():
    assert parse_year("2019 Toyota Hilux") == 2019
    assert parse_year("2021") == 2021
    assert np.isnan(parse_year("new"))


def test_normalisers():
    assert normalise_make(" bmw ") == "BMW"
    assert normalise_make("VW") == "Volkswagen"
    assert normalise_make("TOYOTA") == "Toyota"
    assert normalise_model("golf GTI") == "Golf GTI"
    assert normalise_model("x3") == "X3"
    assert normalise_model("320D") == "320d"
    assert normalise_fuel("DIESEL ") == "Diesel"
    assert normalise_transmission("Auto") == "Automatic"
    assert normalise_province("KZN") == "KwaZulu-Natal"
    assert normalise_province("Atlantis") is None


def _raw(**overrides):
    row = dict(id=1, source="t", listing_id="a", make="Toyota", model="Hilux", variant=None,
               year="2020", mileage="80 000 km", price="R 400 000", fuel_type="Diesel",
               transmission="Manual", body_type="Bakkie", province="KZN", city="Durban",
               seller_type="Dealer", collected_at=pd.Timestamp("2026-11-01"))
    row.update(overrides)
    return row


def test_clean_keeps_good_row_and_types_it():
    df, report = clean(pd.DataFrame([_raw()]), current_year=2026)
    assert report["clean_rows"] == 1
    r = df.iloc[0]
    assert (r.year, r.mileage_km, r.price_zar, r.province) == (2020, 80000, 400000, "KwaZulu-Natal")


@pytest.mark.parametrize("override, reason", [
    ({"price": "POA"}, "dropped_missing_core_fields"),
    ({"price": "R 1"}, "dropped_price_out_of_range"),
    ({"year": "1975"}, "dropped_year_out_of_range"),
    ({"mileage": "85"}, "dropped_implausible_low_mileage"),
])
def test_clean_drops_bad_rows(override, reason):
    _, report = clean(pd.DataFrame([_raw(**override)]), current_year=2026)
    assert report["clean_rows"] == 0 and report[reason] == 1


def test_clean_dedupes_reposts_keeping_latest():
    rows = [_raw(id=1, listing_id="a", collected_at=pd.Timestamp("2026-10-01")),
            _raw(id=2, listing_id="b", collected_at=pd.Timestamp("2026-11-01"))]
    df, report = clean(pd.DataFrame(rows), current_year=2026)
    assert report["dropped_duplicate_listing"] == 1
    assert df.iloc[0].id == 2
