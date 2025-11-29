# Open Data Lake (MinIO + Lakekeeper + Trino + Airflow + Jupyter + Metabase + CloudBeaver)

All-open-source data lake that lands curated Parquet into MinIO, manages Iceberg tables through Lakekeeper, queries with Trino, orchestrates with Airflow, and surfaces analytics in Jupyter, Metabase, and CloudBeaver. Runs locally with Docker Compose.

For the detailed, click-by-click version use `RUNBOOK.md`. This README captures the tested startup sequence, validations, and common pitfalls.

---

## Quick Start (about 15 minutes)

```bash
# Clone
mkdir -p oss-data-lake && cd oss-data-lake
git clone https://github.com/Marek-Czarnecki/oss-data-lake .

# (Optional) Copy defaults and edit if needed
cp .env.example .env

# Helper to shorten compose invocations
COMPOSE="docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml"

# 1) Start MinIO only and create the demo bucket
$COMPOSE up -d minio
$COMPOSE exec -T minio mc mb --ignore-existing local/demo-bucket

# 2) Bring up the full stack
$COMPOSE up -d
$COMPOSE ps

# 3) Register the Lakekeeper warehouse if it is missing
curl -s http://localhost:8181/management/v1/warehouse | grep -q '"name":"yfinance"' || \
  curl -s -X POST http://localhost:8181/management/v1/warehouse \
    -H "Content-Type: application/json" \
    --data @create-yfinance-warehouse.json

# 4) Run the demo DAG (lands Parquet in MinIO)
$COMPOSE exec -T airflow-webserver airflow dags unpause yfinance_to_minio
$COMPOSE exec -T airflow-webserver airflow dags trigger yfinance_to_minio --run-id "manual__$(date +%s)"
$COMPOSE exec -T minio mc ls -r local/demo-bucket/warehouse/finance/yahoo/curated_price | head

# 5) Create the Iceberg schema and table (inside the Trino container, server=http://localhost:8080)
$COMPOSE exec -T trino trino --server http://localhost:8080 --user admin \
  --execute "CREATE SCHEMA IF NOT EXISTS iceberg.yfinance"
$COMPOSE exec -T trino trino --server http://localhost:8080 --user admin \
  --execute "CREATE TABLE IF NOT EXISTS iceberg.yfinance.fact_price (ticker VARCHAR, ts TIMESTAMP(3) WITH TIME ZONE, open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume BIGINT, ingest_date DATE) WITH (partitioning = ARRAY['day(ts)'])"

# 6) Load Parquet into Iceberg via Jupyter (http://localhost:8888/lab)
# Open the notebook, run all cells, then validate from Trino:
$COMPOSE exec -T trino trino --server http://localhost:8080 --user admin \
  --execute "SELECT COUNT(*) FROM iceberg.yfinance.fact_price"

# 7) Metabase and CloudBeaver
./scripts/fetch-metabase-trino-driver.sh
$COMPOSE restart metabase
# Metabase:    http://localhost:3000   (Trino connection: host=trino, port=8080, catalog=iceberg, schema=yfinance)
# CloudBeaver: http://localhost:8978   (same connection settings)
```

Clean shutdown:
```bash
$COMPOSE down --remove-orphans        # keep volumes
$COMPOSE down -v --remove-orphans     # full reset
```

---

## Services and Ports

- Airflow: http://localhost:8080 (DAGs and logs)
- MinIO Console: http://localhost:9001 (buckets, Parquet inspection)
- Lakekeeper UI: http://localhost:8181/ui (catalog metadata)
- Trino: host port 9999 -> container 8080 (CLI, JDBC)
- JupyterLab: http://localhost:8888 (notebooks, ETL)
- Metabase: http://localhost:3000 (dashboards; needs Trino driver JAR)
- CloudBeaver: http://localhost:8978 (browser SQL workbench)

---

## Boot Sequence (compose wiring)

- MinIO and Postgres start first; `migrate` seeds the Lakekeeper database.
- Lakekeeper waits on Postgres and MinIO, then `bootstrap` accepts terms and `initialwarehouse` creates a default warehouse from `create-default-warehouse.json`.
- Trino mounts catalogs from `etc/catalog`, with Iceberg using Lakekeeper as a REST catalog backed by MinIO.
- Jupyter waits on Lakekeeper, `initialwarehouse`, Trino, and StarRocks before starting.
- Airflow overlay: `airflow-db` -> `airflow-init` (installs Python deps, migrates DB, creates admin user) -> `airflow-scheduler` and `airflow-webserver`.
- Metabase/CloudBeaver overlay is independent of Airflow; Metabase needs the Trino driver JAR placed in `metabase-plugins/` (or use the fetch script).

---

## Validations, Tests, and Common Errors

- Container health: `$COMPOSE ps` should show `healthy` for Lakekeeper, Trino, StarRocks, MinIO, and the Airflow DB.
- Bucket present: `$COMPOSE exec -T minio mc ls local/demo-bucket` (create it if missing).
- Warehouse present: `curl -s http://localhost:8181/management/v1/warehouse` should list `yfinance`.
- DAG ran: `$COMPOSE exec -T minio mc ls -r local/demo-bucket/warehouse/finance/yahoo/curated_price | head` should show Parquet.
- Trino smoke test: run `SHOW SCHEMAS FROM iceberg; SHOW TABLES FROM iceberg.yfinance; SELECT COUNT(*) FROM iceberg.yfinance.fact_price;` via `$COMPOSE exec -T trino ...`.
- Jupyter driver: inside Jupyter, install once if missing: `$COMPOSE exec -T jupyter pip install "trino[sqlalchemy]"` then `python -c "import trino, sqlalchemy"`.
- Metabase driver not found: rerun `./scripts/fetch-metabase-trino-driver.sh` then `$COMPOSE restart metabase`.
- Airflow UI trigger fallback: trigger `yfinance_to_minio` from http://localhost:8080 if CLI trigger stalls.

---

## Repository and Workflow Notes

- DAGs live in `dags/`; `yfinance_to_minio.py` is the active ingestion DAG. `yfinance_to_minio_v1.py` is an older variant kept for reference.
- Notebooks live in `notebooks/` and mount into Jupyter at `/home/jovyan/examples/`.
- Trino catalogs live in `etc/catalog/` (Iceberg REST catalog points at Lakekeeper; Hive file metastore is provided for examples).
- Metabase plugins go in `metabase-plugins/` (see `scripts/fetch-metabase-trino-driver.sh` for the Starburst/Trino driver).
- Upstream tracking: `UPSTREAM.md` documents the Lakekeeper compose provenance; `scripts/check-upstream.sh` diffs your `docker-compose.yaml` against a chosen Lakekeeper commit (set `LK_COMMIT` or edit the commit hash in `UPSTREAM.md`).
- Python dependencies for DAGs live in `requirements.txt`; Airflow containers install them on start.
- `.env.example` provides default MinIO credentials and Airflow toggles; copy to `.env` if you want overrides.

---

## References and Further Reading

- Full step-by-step: `RUNBOOK.md`
- Metabase plugin note: `metabase-plugins/README.md`
- Articles:
  - #7 Automating Data Ingestion with Airflow
  - #8 Your First Data-Science-Ready Lake, Running Locally in Less Than an Hour
  - #9 Running Your First SQL Queries Against the Lake
  - #10 Parallel Data Analysis in Python and SQL
  - #11 Data Exploration with CloudBeaver and Metabase (link forthcoming)

---

## License

MIT
