from datetime import datetime, timedelta
import os
import pandas as pd
import yfinance as yf

from airflow import DAG
from airflow.operators.python import PythonOperator

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "demo-bucket")
MINIO_KEY = os.getenv("MINIO_KEY")
MINIO_SECRET = os.getenv("MINIO_SECRET")

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN"]
LOOKBACK_DAYS = 30

def fetch_and_write(**_):
    end = datetime.utcnow().date()
    start = end - timedelta(days=LOOKBACK_DAYS)
    ingest_date = end.strftime("%Y-%m-%d")
    base_prefix = f"{MINIO_BUCKET}/finance/yahoo/daily/ingest_date={ingest_date}"

    storage_options = {
        "key": MINIO_KEY,
        "secret": MINIO_SECRET,
        "client_kwargs": {"endpoint_url": MINIO_ENDPOINT},
    }

    for t in TICKERS:
        df = yf.download(t, start=start.isoformat(), end=end.isoformat(), progress=False)
        if df is None or df.empty:
            continue
        df.reset_index(inplace=True)  # Date becomes a column
        df["ticker"] = t

        path = f"s3://{base_prefix}/{t}.parquet"
        df.to_parquet(path, index=False, storage_options=storage_options)

with DAG(
    dag_id="yfinance_to_minio_v1",
    default_args={"owner": "marek"},
    start_date=datetime(2025, 8, 1),
    schedule_interval=None,  # trigger manually first
    catchup=False,
    tags=["oss-datalake", "yfinance", "minio"],
):
    PythonOperator(
        task_id="fetch_write_parquet",
        python_callable=fetch_and_write,
    )

