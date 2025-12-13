# TODO

Short list of next refinements now that the core stack is working.

1. **Automate driver fetch during compose up** – optionally add an init container or Make target that runs `scripts/fetch-metabase-trino-driver.sh` so Metabase always launches with Trino support.
2. **Notebook cleanup** – convert the legacy `notebooks/test_airflow_yfinance.ipynb` to a lightweight SQL + Python script for easier diffing, or replace with a DBT-style workflow.
3. **Health checks** – add lightweight smoke tests (e.g., `scripts/validate-stack.sh`) that verify MinIO bucket, Lakekeeper warehouse, and Trino table existence after startup.
4. **CI hook** – configure GitHub Actions to lint DAGs and run `scripts/check-upstream.sh` so upstream Lakekeeper drift is detected automatically.
