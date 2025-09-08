# dags/yfinance_to_minio.py
from __future__ import annotations

from datetime import datetime
import os
import pandas as pd
import yfinance as yf
from airflow import DAG
from airflow.operators.python import PythonOperator

# ---- Config ----
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
MINIO_BUCKET   = os.getenv("MINIO_BUCKET", "demo-bucket")
MINIO_KEY      = os.getenv("MINIO_KEY", "minio-root-user")
MINIO_SECRET   = os.getenv("MINIO_SECRET", "minio-root-password")

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN"]
LOOKBACK_DAYS = int(os.getenv("LOOKBACK_DAYS", "30"))

CURATED_PREFIX = f"{MINIO_BUCKET}/warehouse/finance/yahoo/curated_price"


def fetch_and_write(**_):
    import s3fs

    end = pd.Timestamp.utcnow().normalize()
    start = end - pd.Timedelta(days=LOOKBACK_DAYS)

    raw = yf.download(
        TICKERS,
        start=start.date(),
        end=end.date(),
        group_by="column",
        auto_adjust=False,
        progress=False,
    )
    # raw.index: Date; raw.columns (usually MultiIndex: (field, ticker))

    frames = []
    if isinstance(raw.columns, pd.MultiIndex) and len(raw.columns.levels) >= 2:
        tickers_present = sorted(set(raw.columns.get_level_values(1)))
        for t in tickers_present:
            # slice this ticker's OHLCV columns
            sub = raw.xs(t, axis=1, level=1, drop_level=True).reset_index()
            # standardize column names
            sub.columns = [str(c).lower() for c in sub.columns]
            # rename date -> ts if present
            if "date" in sub.columns:
                sub = sub.rename(columns={"date": "ts"})
            sub["ticker"] = t
            frames.append(sub)
    else:
        # Single-ticker fallback (no MultiIndex)
        sub = raw.reset_index()
        sub.columns = [str(c).lower() for c in sub.columns]
        if "date" in sub.columns:
            sub = sub.rename(columns={"date": "ts"})
        # best-effort ticker
        sub["ticker"] = (TICKERS[0] if TICKERS else "UNKNOWN")
        frames.append(sub)

    tidy = pd.concat(frames, ignore_index=True)

    # Required columns: ticker, ts, open, high, low, close, volume
    # Ensure types
    tidy["ts"] = pd.to_datetime(tidy["ts"], utc=True)
    for c in ("open", "high", "low", "close"):
        if c in tidy.columns:
            tidy[c] = tidy[c].astype(float)
    if "volume" in tidy.columns:
        tidy["volume"] = tidy["volume"].astype("Int64")

    tidy["ingest_date"] = pd.Timestamp.utcnow().date().isoformat()
    tidy["date"] = tidy["ts"].dt.date.astype(str)  # partition key

    # Write partitioned parquet
    fs = s3fs.S3FileSystem(
        key=MINIO_KEY,
        secret=MINIO_SECRET,
        client_kwargs={"endpoint_url": MINIO_ENDPOINT},
    )

    now_ns = pd.Timestamp.utcnow().value
    written = 0
    for d, part in tidy.groupby("date", sort=True):
        if part.empty:
            continue
        path = f"{CURATED_PREFIX}/date={d}/part-{now_ns}.parquet"
        with fs.open(path, "wb") as f:
            part.drop(columns=["date"]).to_parquet(f, index=False)
        written += len(part)

    return {"rows_written": int(written), "partitions": int(tidy['date'].nunique())}

with DAG(
    dag_id="yfinance_to_minio",
    default_args={"owner": "marek"},
    start_date=datetime(2025, 8, 1),
    schedule_interval=None,
    catchup=False,
    tags=["oss-datalake", "yfinance", "minio"],
) as dag:
    PythonOperator(
        task_id="fetch_write_parquet",
        python_callable=fetch_and_write,
    )
