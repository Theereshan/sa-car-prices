-- Raw layer: exactly what was collected, never edited.
-- Cleaning reads from here and writes listings_clean, so you can always re-run it.
CREATE TABLE IF NOT EXISTS raw_listings (
    id            BIGSERIAL PRIMARY KEY,
    source        TEXT        NOT NULL,          -- e.g. 'synthetic', 'kaggle', '<site name>'
    listing_id    TEXT        NOT NULL,          -- the source's own ID for the ad
    url           TEXT,
    title         TEXT,
    make          TEXT,
    model         TEXT,
    variant       TEXT,
    year          TEXT,                          -- TEXT on purpose: raw data is messy
    mileage       TEXT,
    price         TEXT,
    fuel_type     TEXT,
    transmission  TEXT,
    body_type     TEXT,
    province      TEXT,
    city          TEXT,
    seller_type   TEXT,
    collected_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (source, listing_id)                  -- re-running a collector never duplicates
);

-- Clean layer: typed, normalised, filtered. Rebuilt by src/data/clean.py.
CREATE TABLE IF NOT EXISTS listings_clean (
    id            BIGINT PRIMARY KEY,           -- = raw_listings.id
    source        TEXT        NOT NULL,
    listing_id    TEXT        NOT NULL,
    make          TEXT        NOT NULL,
    model         TEXT        NOT NULL,
    variant       TEXT,
    year          INT         NOT NULL,
    mileage_km    INT         NOT NULL,
    price_zar     NUMERIC(12,2) NOT NULL,
    fuel_type     TEXT,
    transmission  TEXT,
    body_type     TEXT,
    province      TEXT,
    city          TEXT,
    seller_type   TEXT,
    collected_at  TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_clean_make_model ON listings_clean (make, model);
CREATE INDEX IF NOT EXISTS ix_clean_year       ON listings_clean (year);
