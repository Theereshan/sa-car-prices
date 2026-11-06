-- Phase 1 practice queries. Run with: docker exec -it sa-car-prices-db psql -U cars -d cars

-- 1. How much data per source, and how much survived cleaning?
SELECT r.source,
       COUNT(*)                       AS raw_rows,
       COUNT(c.id)                    AS clean_rows,
       ROUND(100.0 * COUNT(c.id) / COUNT(*), 1) AS pct_kept
FROM raw_listings r
LEFT JOIN listings_clean c ON c.id = r.id
GROUP BY r.source;

-- 2. Median price by make (only makes with enough listings to trust)
SELECT make,
       COUNT(*) AS n,
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price_zar) AS median_price
FROM listings_clean
GROUP BY make
HAVING COUNT(*) >= 50
ORDER BY median_price DESC;

-- 3. Depreciation curve: median price by car age, per make
SELECT make,
       EXTRACT(YEAR FROM now())::int - year AS age_years,
       COUNT(*) AS n,
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price_zar) AS median_price
FROM listings_clean
WHERE make IN ('Toyota', 'BMW')
GROUP BY make, age_years
HAVING COUNT(*) >= 10
ORDER BY make, age_years;

-- 4. Diesel vs petrol premium for the same make/model/year
WITH by_fuel AS (
    SELECT make, model, year, fuel_type,
           PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price_zar) AS median_price
    FROM listings_clean
    WHERE fuel_type IN ('Diesel', 'Petrol')
    GROUP BY make, model, year, fuel_type
    HAVING COUNT(*) >= 5
)
SELECT d.make, d.model, d.year,
       d.median_price AS diesel, p.median_price AS petrol,
       ROUND(((d.median_price / p.median_price - 1) * 100)::numeric, 1) AS diesel_premium_pct
FROM by_fuel d
JOIN by_fuel p USING (make, model, year)
WHERE d.fuel_type = 'Diesel' AND p.fuel_type = 'Petrol'
ORDER BY diesel_premium_pct DESC;

-- 5. Province price differences
SELECT province, COUNT(*) AS n,
       PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price_zar) AS median_price
FROM listings_clean
GROUP BY province
ORDER BY median_price DESC;
