# OSS Data Lake (MinIO · Iceberg/Lakekeeper · Trino · Airflow · Jupyter · Metabase · CloudBeaver)

Lightweight, reproducible, all-open-source data lake you can run locally with Docker Compose.
This repo lands curated Parquet to MinIO, manages tables with Apache Iceberg (via Lakekeeper REST catalog), queries with Trino, and now adds **Metabase** dashboards and **CloudBeaver** for browser-based SQL exploration.

---

## Quick Start

```bash
# 0) Clone
mkdir -p oss-data-lake && cd oss-data-lake
git clone https://github.com/Marek-Czarnecki/oss-data-lake .

# 1) Start MinIO and create bucket
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml up -d minio
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml exec -T minio mc mb --ignore-existing local/demo-bucket

# 2) Bring up full stack
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml up -d
docker ps --format '{{.Names}}: {{.Status}}' | sort

# 3) Register Lakekeeper warehouse (if missing)
curl -s http://localhost:8181/management/v1/warehouse | grep -q '"name":"yfinance"' || \
  curl -s -X POST http://localhost:8181/management/v1/warehouse \
    -H "Content-Type: application/json" \
    --data @create-yfinance-warehouse.json

# 4) Run the demo DAG → writes Parquet to MinIO
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml exec -T airflow-webserver airflow dags unpause yfinance_to_minio
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml exec -T airflow-webserver airflow dags trigger yfinance_to_minio --run-id "manual__$(date +%s)"

# 5) Create Iceberg schema + table (target for curated data)
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml exec -T trino trino --server http://localhost:8080 --user admin \
  --execute "CREATE SCHEMA IF NOT EXISTS iceberg.yfinance"
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml exec -T trino trino --server http://localhost:8080 --user admin \
  --execute "CREATE TABLE IF NOT EXISTS iceberg.yfinance.fact_price (ticker VARCHAR, ts TIMESTAMP(3) WITH TIME ZONE, open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume BIGINT, ingest_date DATE) WITH (partitioning = ARRAY['day(ts)'])"

# 6) Jupyter ETL → load Parquet into Iceberg
# Open http://localhost:8888/lab and run the provided notebook end-to-end, then:
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml exec -T trino trino --server http://localhost:8080 --user admin \
  --execute "SELECT COUNT(*) FROM iceberg.yfinance.fact_price"

# 7) Metabase + CloudBeaver
./scripts/fetch-metabase-trino-driver.sh
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml restart metabase
# Metabase:    http://localhost:3000   (connect to Trino: host=trino, port=8080, catalog=iceberg, schema=yfinance)
# CloudBeaver: http://localhost:8978   (same connection settings)
```

For the full, step-by-step guide, see **[RUNBOOK.md](RUNBOOK.md)**.

---

## Services & Ports

* **Airflow** — [http://localhost:8080](http://localhost:8080) (DAGs, runs, logs)
* **MinIO Console** — [http://localhost:9001](http://localhost:9001) (buckets, Parquet inspection)
* **Lakekeeper UI** — [http://localhost:8181/ui](http://localhost:8181/ui) (warehouse/cat metadata)
* **Trino** — localhost:8080 (SQL engine endpoint)
* **JupyterLab** — [http://localhost:8888](http://localhost:8888) (notebooks & ETL)
* **Metabase** — [http://localhost:3000](http://localhost:3000) (dashboards)
* **CloudBeaver** — [http://localhost:8978](http://localhost:8978) (browser SQL workbench)

Health check:

```bash
docker ps --format '{{.Names}}: {{.Status}}' | sort
```

---

## Project Structure (high level)

```
.
├─ dags/                         # Airflow DAGs (e.g., yfinance_to_minio)
├─ notebooks/                    # Jupyter notebooks (ETL & analysis)
├─ examples/                     # Sample data/scripts (optional)
├─ metabase-plugins/             # Metabase driver JARs (ignored by git)
├─ scripts/
│  └─ fetch-metabase-trino-driver.sh
├─ docker-compose.yaml
├─ docker-compose.airflow.yaml
├─ docker-compose.metabase-cloudbeaver.yaml
├─ create-yfinance-warehouse.json
├─ RUNBOOK.md
└─ README.md
```

---

## Articles in the Series

* **#7** — [Automating Data Ingestion with Airflow](https://medium.com/@marekczarnecki_50908/oss-data-lake-7-automating-data-ingestion-with-airflow-a6648dcf303a)
* **#8** — [Your First Data-Science-Ready Lake, Running Locally in Less Than an Hour](https://medium.com/@marekczarnecki_50908/oss-data-lake-8-your-first-data-science-ready-lake-running-locally-in-less-than-an-hour-8ede450cd611)
* **#9** — [Running Your First SQL Queries Against the Lake](https://medium.com/@marekczarnecki_50908/oss-data-lake-9-running-your-first-sql-queries-against-the-lake-775eae439d95)
* **#10** — [Parallel Data Analysis in Python and SQL](https://medium.com/@marekczarnecki_50908/oss-data-lake-parallel-data-analysis-in-python-and-sql-89e796e355e4)
* **#11** — Data Exploration with CloudBeaver and Metabase — *link*

---

## Troubleshooting (quick)

```bash
# Containers healthy?
docker ps --format '{{.Names}}: {{.Status}}' | sort

# MinIO buckets & files
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml exec -T minio mc ls -r local/demo-bucket | head

# Lakekeeper warehouse
curl -s http://localhost:8181/management/v1/warehouse

# Trino schemas/tables
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml exec -T trino trino --server http://localhost:8080 --user admin --execute "SHOW SCHEMAS FROM iceberg"
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml exec -T trino trino --server http://localhost:8080 --user admin --execute "SHOW TABLES FROM iceberg.yfinance"
```

* **Airflow GUI trigger**: If CLI trigger looks stuck, open [http://localhost:8080](http://localhost:8080) and trigger `yfinance_to_minio` manually.
* **Metabase driver**:

  ```
  ./scripts/fetch-metabase-trino-driver.sh
  docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml restart metabase
  ```
* **CloudBeaver metadata**: Refresh the Trino connection; if needed, run:

  ```
  SELECT COUNT(*) FROM iceberg.yfinance.fact_price;
  ```

See **RUNBOOK.md** for the full troubleshooting list and clean shutdown commands.

---

## Git Hygiene

The repo ignores driver binaries:

```
# Ignore all JARs (recommended)
*.jar
# …or, to scope narrowly:
# /metabase-plugins/*.jar
```

You may also want common Python/Notebook ignores:

```
__pycache__/
.ipynb_checkpoints/
.env
```

---

## License

MIT.

