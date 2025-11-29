# Project Context

Purpose: reproducible, all-open-source data lake you can run locally with Docker Compose. Ingests Yahoo Finance prices with Airflow, stores Parquet in MinIO, registers Iceberg tables through Lakekeeper, queries with Trino, and explores data via Jupyter, Metabase, and CloudBeaver.

## Stack and Data Flow
- Storage: MinIO (S3-compatible). Demo bucket `demo-bucket`.
- Catalog: Lakekeeper REST catalog backed by Postgres. Bootstraps and seeds a warehouse from `create-default-warehouse.json`; `create-yfinance-warehouse.json` registers the demo warehouse.
- Query: Trino with Iceberg (REST) and Hive (file) catalogs; StarRocks available for experimentation.
- Orchestration: Airflow DAG `yfinance_to_minio` fetches OHLCV from Yahoo Finance and writes partitioned Parquet to `warehouse/finance/yahoo/curated_price`.
- Notebooks: Mounted into Jupyter at `/home/jovyan/examples/` for loading Parquet into Iceberg via Trino.
- BI: Metabase (requires Trino driver JAR in `metabase-plugins/`) and CloudBeaver for SQL workbench access.

## Boot Sequence (dependency chain)
1) MinIO, Postgres, and `migrate` start first.
2) Lakekeeper waits on Postgres and MinIO; `bootstrap` accepts terms; `initialwarehouse` seeds the default warehouse.
3) Trino mounts catalogs from `etc/catalog`; Iceberg REST catalog uses Lakekeeper; Hive file metastore is for samples.
4) Jupyter waits on Lakekeeper, `initialwarehouse`, Trino, and StarRocks.
5) Airflow overlay: `airflow-db` -> `airflow-init` (pip installs `requirements.txt`, migrates DB, creates admin user) -> scheduler and webserver.
6) Metabase/CloudBeaver overlay is optional; Metabase needs the Trino driver JAR (use `scripts/fetch-metabase-trino-driver.sh`).

## Core Workflows
- Start stack: `COMPOSE="docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml"`; then `up -d minio`, create bucket, and `up -d` for the rest.
- Ingest: unpause and trigger `yfinance_to_minio` from CLI or Airflow UI; Parquet lands under `demo-bucket/warehouse/finance/yahoo/curated_price`.
- Curate: create Iceberg schema/table in Trino, then run the notebook in Jupyter to load Parquet into `iceberg.yfinance.fact_price`.
- Analyze: connect Metabase or CloudBeaver to Trino (host `trino`, port `8080`, catalog `iceberg`, schema `yfinance`); run queries/dashboards.
- Shutdown: `$COMPOSE down --remove-orphans` (keep volumes) or `$COMPOSE down -v --remove-orphans` (reset).

## Validation and Tests
- Containers healthy: `$COMPOSE ps`.
- Bucket exists: `$COMPOSE exec -T minio mc ls local/demo-bucket`.
- Warehouse exists: `curl -s http://localhost:8181/management/v1/warehouse` includes `yfinance`.
- DAG output: `$COMPOSE exec -T minio mc ls -r local/demo-bucket/warehouse/finance/yahoo/curated_price | head`.
- Trino smoke: `SHOW SCHEMAS FROM iceberg; SHOW TABLES FROM iceberg.yfinance; SELECT COUNT(*) FROM iceberg.yfinance.fact_price;` inside the Trino container.
- Notebook deps: `$COMPOSE exec -T jupyter pip install "trino[sqlalchemy]"` then `python -c "import trino, sqlalchemy"`.

## Common Errors and Fixes
- Missing bucket: create with `$COMPOSE exec -T minio mc mb --ignore-existing local/demo-bucket`.
- Warehouse missing: POST `create-yfinance-warehouse.json` to Lakekeeper as shown in README.
- Metabase cannot see Trino: fetch driver (`./scripts/fetch-metabase-trino-driver.sh`) and restart Metabase.
- Airflow DAG stuck: trigger from the UI at http://localhost:8080.
- Trino connection confusion: inside container use `--server http://localhost:8080`; host port is `9999`.

## Repository Processes
- Upstream tracking: `UPSTREAM.md` records the Lakekeeper compose provenance; `scripts/check-upstream.sh` diffs your `docker-compose.yaml` against an upstream commit (set `LK_COMMIT` or fill the commit in `UPSTREAM.md`).
- Secrets and env: `.env.example` holds defaults; copy to `.env` for local overrides.
- Python deps for DAGs: `requirements.txt` is installed during Airflow init.
- Binary ignores: driver JARs live in `metabase-plugins/` and are git-ignored.
- Docs: operational guide in `RUNBOOK.md`; quick usage in `README.md`; plugin note in `metabase-plugins/README.md`.
