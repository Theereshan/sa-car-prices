#!/usr/bin/env bash
# Runs once when the Codespace is created: installs packages and loads sample data.
set -euo pipefail

pip install --no-cache-dir -r requirements.txt
[ -f .env ] || cp .env.example .env

# Belt-and-braces: wait for Postgres even though compose already health-checks it
for i in $(seq 1 30); do
  python -c "from src.db import get_engine; get_engine().connect().close()" 2>/dev/null && break
  echo "Waiting for Postgres ($i)..."; sleep 2
done

python scripts/make_sample_data.py --rows 5000
python -m src.collect.import_csv data/raw/sample_listings.csv --source synthetic
python -m src.data.clean

echo "✅ Ready. Open notebooks/01_eda.ipynb and click 'Run All'."
