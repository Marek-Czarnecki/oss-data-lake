# RUNBOOK — Clone → Run → Verify

## 0) Prereqs
- Docker & Docker Compose v2
- Internet access for Airflow to download Python deps and yfinance data

## 1) Start stack
```bash
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml up -d
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml ps
```

## 2) Dependencies in Airflow
```bash
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml exec airflow-webserver python -m pip install --no-cache-dir -r /requirements.txt
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml exec airflow-scheduler  python -m pip install --no-cache-dir -r /requirements.txt
```

## 3) Optional: create MinIO bucket if volume is fresh
```bash
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml exec airflow-webserver python - <<'PY'
import os,boto3
s3=boto3.client('s3',endpoint_url=os.environ['MINIO_ENDPOINT'],
                aws_access_key_id=os.environ['MINIO_KEY'],
                aws_secret_access_key=os.environ['MINIO_SECRET'])
try:
    s3.create_bucket(Bucket=os.environ.get('MINIO_BUCKET','demo-bucket'))
except Exception as e:
    print(e)
print("OK")
PY
```

## 4) Airflow: diagnose and trigger
```bash
# Import errors (should be empty)
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml exec airflow-webserver airflow dags list-import-errors -o table

# Trigger the demo DAG
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml exec airflow-webserver airflow dags trigger yfinance_to_minio

# Tail task logs (adjust attempt number if needed)
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml exec airflow-scheduler bash -lc 'tail -n 200 /opt/airflow/logs/dag_id=yfinance_to_minio/*/*/task_id=fetch_write_parquet/attempt=1.log'
```

## 5) Verify data landed in MinIO
```bash
# Should print HTTP 200
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml exec airflow-webserver sh -lc 'curl -sS -o /dev/null -w "%{http_code}\n" http://minio:9000/minio/health/ready'

# List buckets
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml exec airflow-webserver python - <<'PY'
import os,boto3
s3=boto3.client('s3',endpoint_url=os.environ['MINIO_ENDPOINT'],
                aws_access_key_id=os.environ['MINIO_KEY'],
                aws_secret_access_key=os.environ['MINIO_SECRET'])
print([b['Name'] for b in s3.list_buckets().get('Buckets',[])])
PY

# List objects in the target bucket
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml exec airflow-webserver python - <<'PY'
import os,boto3
bucket=os.environ.get('MINIO_BUCKET','demo-bucket')
s3=boto3.client('s3',endpoint_url=os.environ['MINIO_ENDPOINT'],
                aws_access_key_id=os.environ['MINIO_KEY'],
                aws_secret_access_key=os.environ['MINIO_SECRET'])
r=s3.list_objects_v2(Bucket=bucket, Prefix='finance/yahoo/daily/')
print([o['Key'] for o in r.get('Contents',[])])
PY
```

## 6) Stop / restart
```bash
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml down
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml up -d
```

## Notes
- Trino SQL shell is intentionally out of scope for this runbook.
- See the `notebooks/test_airflow_yfinance.ipynb` for a minimal stats check (run locally or via your preferred Jupyter).
