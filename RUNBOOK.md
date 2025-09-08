# OSS Data Lake Test - Runbook

## From clean clone to smoke test

```bash
# 0) (if needed) clone + cd
git clone https://github.com/Marek-Czarnecki/oss-data-lake && cd oss-data-lake/oss-data-lake-test

# 1) ensure clean project state
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml down -v --remove-orphans
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml config >/dev/null

# 2) start MinIO to prep bucket
docker compose up -d minio

# 3) create bucket (idempotent) + list buckets
docker compose exec minio mc alias set local http://minio:9000 minio-root-user minio-root-password
docker compose exec minio mc ls local/demo-bucket >/dev/null 2>&1 || docker compose exec minio mc mb local/demo-bucket
docker compose exec minio mc ls local

# 4) bring full stack up
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml up -d
docker ps --format '{{.Names}}: {{.Status}}' | sort

# 5) register the yfinance warehouse (idempotent) and verify
curl -s -X POST http://localhost:8181/management/v1/warehouse   -H "Content-Type: application/json"   --data @create-yfinance-warehouse.json
curl -s http://localhost:8181/management/v1/warehouse

# 6) open Trino CLI (inside container → server is 8080)
docker compose exec -it trino trino --server http://localhost:8080 --user admin
```

Inside Trino prompt:
```sql
SHOW CATALOGS;
CREATE SCHEMA IF NOT EXISTS iceberg.yf_demo;
CREATE TABLE IF NOT EXISTS iceberg.yf_demo.smoke (id INT, msg VARCHAR);
INSERT INTO iceberg.yf_demo.smoke VALUES (1,'ok');
SELECT * FROM iceberg.yf_demo.smoke;
```

Back in shell:
```bash
# 7) confirm Iceberg files landed in MinIO
docker compose exec minio mc ls -r local/demo-bucket/warehouse | head -n 20
```

---

## Clean shutdown

- **Stop containers (keep data):**
```bash
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml down --remove-orphans
```

- **Full reset (also remove volumes):**
```bash
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml down -v --remove-orphans
```
