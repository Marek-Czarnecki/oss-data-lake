# Open Data Lake — Runbook

This runbook documents the complete sequence to go from a clean clone of the repository to a fully working Open Data Lake with dashboards in **Metabase** and interactive SQL in **CloudBeaver**.

---

## 1. Get the Code

```bash
# Create a working folder and clone the repository
mkdir -p oss-data-lake && cd oss-data-lake
git clone https://github.com/Marek-Czarnecki/oss-data-lake .
```

---

## 2. Start MinIO Only, Then Create the Bucket

```bash
# Start MinIO only
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml up -d minio

# List configured aliases/buckets (expect to see 'local')
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml exec -T minio mc ls local

# Create the demo bucket (idempotent)
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml exec -T minio mc mb --ignore-existing local/demo-bucket

# Verify the bucket exists
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml exec -T minio mc ls local/demo-bucket
```

---

## 3. Bring Up the Full Stack

```bash
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml up -d
docker ps --format '{{.Names}}: {{.Status}}' | sort
```

---

## 4. Ensure the Lakekeeper Warehouse Exists

```bash
# List warehouses
curl -s http://localhost:8181/management/v1/warehouse

# Create the 'yfinance' warehouse if it is missing
curl -s http://localhost:8181/management/v1/warehouse | grep -q '"name":"yfinance"' ||   curl -s -X POST http://localhost:8181/management/v1/warehouse     -H "Content-Type: application/json"     --data @create-yfinance-warehouse.json

# Re-check warehouses
curl -s http://localhost:8181/management/v1/warehouse
```

---

## 5. Unpause and Trigger the Airflow DAG

```bash
# Unpause the DAG
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml exec -T airflow-webserver airflow dags unpause yfinance_to_minio

# Trigger a run
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml exec -T airflow-webserver airflow dags trigger yfinance_to_minio --run-id "manual__$(date +%s)"

# Verify Parquet files landed in MinIO
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml exec -T minio mc ls -r local/demo-bucket/warehouse/finance/yahoo/curated_price | head -n 40
```

---

## 6. Install the Trino SQLAlchemy Driver in Jupyter

```bash
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml exec -T jupyter pip install "trino[sqlalchemy]"
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml exec -T jupyter python -c "import trino, sqlalchemy; print('sqlalchemy+trino OK')"
```

---

## 7. Create the Iceberg Schema and Table

```bash
# Create schema
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml exec -T trino trino --server http://localhost:8080 --user admin   --execute "CREATE SCHEMA IF NOT EXISTS iceberg.yfinance"

# Create table (partitioned by day(ts))
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml exec -T trino trino --server http://localhost:8080 --user admin   --execute "CREATE TABLE IF NOT EXISTS iceberg.yfinance.fact_price (ticker VARCHAR, ts TIMESTAMP(3) WITH TIME ZONE, open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume BIGINT, ingest_date DATE) WITH (partitioning = ARRAY['day(ts)'])"

# Verify tables
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml exec -T trino trino --server http://localhost:8080 --user admin   --execute "SHOW TABLES FROM iceberg.yfinance"
```

---

## 8. Run the Jupyter Notebook ETL Cells

Open JupyterLab in your browser at [http://localhost:8888/lab](http://localhost:8888/lab).  
Run the parallel data analysis notebook top to bottom. It will copy the Parquet files from MinIO into the Iceberg `fact_price` table via Trino.

```bash
# Quick smoke test
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml exec -T trino trino --server http://localhost:8080 --user admin   --execute "SELECT COUNT(*) FROM iceberg.yfinance.fact_price"
```

---

## 9. Start and Prepare Metabase and CloudBeaver

```bash
# Fetch the Trino driver JAR for Metabase
./scripts/fetch-metabase-trino-driver.sh

# Restart Metabase to load the driver
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml restart metabase
```

- **Metabase**: [http://localhost:3000](http://localhost:3000)  
  Configure a Trino connection with: host=`trino`, port=`8080`, catalog=`iceberg`, schema=`yfinance`.  
- **CloudBeaver**: [http://localhost:8978](http://localhost:8978)  
  Create a Trino connection with the same settings.  

Verify queries in both UIs, for example:  

```sql
SELECT ticker, DATE(ts) AS d, AVG(close) AS avg_close
FROM iceberg.yfinance.fact_price
GROUP BY ticker, DATE(ts)
ORDER BY ticker, d
LIMIT 20;
```

---

## 10. Troubleshooting

- **Container health**  
  ```bash
  docker ps --format '{{.Names}}: {{.Status}}' | sort
  ```

- **Check MinIO bucket**  
  ```bash
  docker compose exec minio mc ls local/demo-bucket
  ```

- **Verify Lakekeeper warehouse**  
  ```bash
  curl -s http://localhost:8181/management/v1/warehouse
  ```

- **Check Trino schema/tables**  
  ```bash
  docker compose exec -T trino trino --server http://localhost:8080 --user admin --execute "SHOW SCHEMAS FROM iceberg"
  docker compose exec -T trino trino --server http://localhost:8080 --user admin --execute "SHOW TABLES FROM iceberg.yfinance"
  ```

- **Airflow DAG issues**  
  ```bash
  docker compose exec -T airflow-webserver airflow dags list
  ```
  You can also trigger the DAG manually from the Airflow web UI ([http://localhost:8080](http://localhost:8080)).

- **Metabase driver issues**  
  ```bash
  ./scripts/fetch-metabase-trino-driver.sh
  docker compose restart metabase
  ```

- **CloudBeaver metadata issues**  
  Refresh the connection in the UI, or run a verification query:  
  ```sql
  SELECT COUNT(*) FROM iceberg.yfinance.fact_price;
  ```

---

## 11. Clean Shutdown

- **Stop containers (keep data):**
```bash
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml down --remove-orphans
```

- **Full reset (also remove volumes):**
```bash
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml down -v --remove-orphans
```
