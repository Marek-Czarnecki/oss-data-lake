# OSS Data Lake — Minimal (Lakekeeper + MinIO + Airflow)

Run a local OSS data lake using Lakekeeper (Iceberg REST) + MinIO, with Airflow to ingest test data.

## Quickstart
1. Clone this repo and `cd` into it.
2. Copy `.env.example` to `.env` and adjust if needed.
3. Start stack:
   ```bash
   docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml up -d
   ```
4. Install Python deps inside Airflow:
   ```bash
   docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml exec airflow-webserver python -m pip install --no-cache-dir -r /requirements.txt
   docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml exec airflow-scheduler  python -m pip install --no-cache-dir -r /requirements.txt
   ```
5. Trigger demo DAG:
   ```bash
   docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml exec airflow-webserver airflow dags trigger yfinance_to_minio
   ```
6. Verify objects in MinIO (see RUNBOOK.md for more commands).

👉 See **RUNBOOK.md** for exact verification steps and troubleshooting.
