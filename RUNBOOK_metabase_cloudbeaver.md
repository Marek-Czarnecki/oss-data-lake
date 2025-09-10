
runbook: metabase + cloudbeaver overlay verification

context
- environment: docker compose on wsl
- repo working folder: "/mnt/c/Users/marek/Downloads/medium/oss data lake/oss-data-lake-10-dag-improvement/oss-data-lake"
- verified source folder: "/mnt/c/Users/marek/Downloads/medium/oss data lake/oss-data-lake-10-dag-improvement/oss-data-lake-verify"
- compose files (always include all three with -f):
  - docker-compose.yaml
  - docker-compose.airflow.yaml
  - docker-compose.metabase-cloudbeaver.yaml

1. prepare the working directory (manual clone equivalent)
- create the destination folder if needed
- copy the baseline files from the verified folder:
  - docker-compose.yaml
  - docker-compose.airflow.yaml
  - .env.example
  - requirements.txt
  - create-yfinance-warehouse.json
  - directories: dags/, notebooks/, examples/
- copy overlay assets from the verified folder:
  - docker-compose.metabase-cloudbeaver.yaml
  - metabase-plugins/ (contains the starburst/trino metabase driver jar)
  - scripts/fetch-metabase-trino-driver.sh

2. start minio only, then check and create the bucket
- start minio only
  docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml up -d minio
- list aliases/buckets (expect to see 'local')
  docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml exec -T minio mc ls local
- create the demo bucket (idempotent)
  docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml exec -T minio mc mb --ignore-existing local/demo-bucket
- verify the bucket exists
  docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml exec -T minio mc ls local/demo-bucket

3. bring up the full stack
- start all services
  docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml up -d
- check container health
  docker ps --format '{{.Names}}: {{.Status}}' | sort

4. ensure the warehouse exists (lakekeeper on :8181)
- list warehouses
  curl -s http://localhost:8181/management/v1/warehouse
- create the yfinance warehouse if missing
  curl -s http://localhost:8181/management/v1/warehouse | grep -q '"name":"yfinance"' || \
    curl -s -X POST http://localhost:8181/management/v1/warehouse \
      -H "Content-Type: application/json" \
      --data @create-yfinance-warehouse.json
- re-check warehouses
  curl -s http://localhost:8181/management/v1/warehouse

5. unpause and trigger the airflow dag
- unpause the dag (container: airflow-webserver)
  docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml exec -T airflow-webserver airflow dags unpause yfinance_to_minio
- trigger a run
  docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml exec -T airflow-webserver airflow dags trigger yfinance_to_minio --run-id "manual__$(date +%s)"
- verify parquet files landed in minio (correct curated path)
  docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml exec -T minio mc ls -r local/demo-bucket/warehouse/finance/yahoo/curated_price | head -n 40

6. install the trino sqlalchemy driver inside the jupyter container
- install driver
  docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml exec -T jupyter pip install "trino[sqlalchemy]"
- quick import test
  docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml exec -T jupyter python -c "import trino, sqlalchemy; print('sqlalchemy+trino OK')"

7. create schema and table in trino (iceberg.yfinance.fact_price)
- create schema (idempotent)
  docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml exec -T trino trino --server http://localhost:8080 --user admin --execute "CREATE SCHEMA IF NOT EXISTS iceberg.yfinance"
- create table (idempotent, partitioning by day(ts))
  docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml exec -T trino trino --server http://localhost:8080 --user admin --execute "CREATE TABLE IF NOT EXISTS iceberg.yfinance.fact_price (ticker VARCHAR, ts TIMESTAMP(3) WITH TIME ZONE, open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume BIGINT, ingest_date DATE) WITH (partitioning = ARRAY['day(ts)'])"
- verify tables
  docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml exec -T trino trino --server http://localhost:8080 --user admin --execute "SHOW TABLES FROM iceberg.yfinance"

8. run the notebook etl cells (parallel data analysis flow)
- open jupyter: http://localhost:8888/lab
- open the copied notebook for parallel data analysis
- run cells top to bottom to perform the python etl and any ddl as defined in the notebook
- verify row count in sql:
  docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml exec -T trino trino --server http://localhost:8080 --user admin --execute "SELECT COUNT(*) FROM iceberg.yfinance.fact_price"

9. start and prepare metabase and cloudbeaver
- ensure metabase has the trino driver jar
  docker exec -t metabase ls -1 /plugins
  docker cp ./metabase-plugins/ metabase:/plugins    # only if missing
  docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml -f docker-compose.metabase-cloudbeaver.yaml restart metabase
- open dashboards
  metabase:   http://localhost:3000
  cloudbeaver: http://localhost:8978
- configure connections in each gui
  trino host: trino
  trino port: 8080
  catalog: iceberg
  schema: yfinance
  username: any non-empty (e.g., metabase-smoke / cloudbeaver); no password
- refresh metadata
  metabase: admin → databases → sync database schema now (and re-scan field values)
  cloudbeaver: right-click trino connection → refresh
- verify queries from each gui
  SELECT COUNT(*) FROM iceberg.yfinance.fact_price;
  SELECT ticker, DATE(ts) AS d, AVG(close) AS avg_close
  FROM iceberg.yfinance.fact_price
  GROUP BY ticker, DATE(ts)
  ORDER BY ticker, d
  LIMIT 20;

notes
- always include all three compose files with -f for every docker compose command
- airflow cli commands run in container: airflow-webserver
- curated parquet path under minio:
  local/demo-bucket/warehouse/finance/yahoo/curated_price/date=YYYY-MM-DD/part-....parquet
- if a service shows 'error' on first start, re-run the 'up -d' command; verify with: docker ps --format '{{.Names}}: {{.Status}}' | sort
