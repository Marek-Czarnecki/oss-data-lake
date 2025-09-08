# OSS Data Lake Test

## Quick Start (Smoke Test)

```bash
git clone https://github.com/Marek-Czarnecki/oss-data-lake && cd oss-data-lake/oss-data-lake-test
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml down -v --remove-orphans
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml config >/dev/null
docker compose up -d minio
docker compose exec minio mc alias set local http://minio:9000 minio-root-user minio-root-password
docker compose exec minio mc ls local/demo-bucket >/dev/null 2>&1 || docker compose exec minio mc mb local/demo-bucket
docker compose exec minio mc ls local
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml up -d
curl -s -X POST http://localhost:8181/management/v1/warehouse -H "Content-Type: application/json" --data @create-yfinance-warehouse.json
curl -s http://localhost:8181/management/v1/warehouse
docker compose exec -it trino trino --server http://localhost:8080 --user admin
```

### In Trino CLI
```sql
SHOW CATALOGS;
CREATE SCHEMA IF NOT EXISTS iceberg.yf_demo;
CREATE TABLE IF NOT EXISTS iceberg.yf_demo.smoke (id INT, msg VARCHAR);
INSERT INTO iceberg.yf_demo.smoke VALUES (1,'ok');
SELECT * FROM iceberg.yf_demo.smoke;
```

### Verify files in MinIO
```bash
docker compose exec minio mc ls -r local/demo-bucket/warehouse | head -n 20
```

---

## Web UIs

- Airflow: http://localhost:8081  
- JupyterLab: http://localhost:8888  (token from: `docker compose logs jupyter | grep -m1 'token='`)  
- Trino UI: http://localhost:9999  
- MinIO Console: http://localhost:9001 (creds: `docker compose exec -T minio sh -lc 'echo "$MINIO_ROOT_USER"; echo "$MINIO_ROOT_PASSWORD"'`)  
- Lakekeeper mgmt API: http://localhost:8181/management/v1/warehouse
