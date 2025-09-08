# RUNBOOK — yFinance DAG v2, Notebook, and Trino Queries

This runbook documents the sequence to run the normalized **yfinance_to_minio** DAG, inspect results in Jupyter, and query via Trino/Iceberg.

---

## 1. Prerequisites
- Docker Compose stack is running and healthy.
- v2 `yfinance_to_minio.py` DAG is deployed with:
  ```python
  CURATED_PREFIX = f"{MINIO_BUCKET}/warehouse/finance/yahoo/curated_price"
  ```
  → ensures output is written under the Iceberg warehouse.

---

## 2. Run the DAG
Unpause and trigger the DAG:

```bash
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml exec -T airflow-webserver \\
  airflow dags unpause yfinance_to_minio

docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml exec -T airflow-webserver \\
  airflow dags trigger yfinance_to_minio --run-id "manual__$(date +%s)"
```

Verify output in MinIO:

```bash
docker compose exec minio mc ls -r local/demo-bucket/warehouse/finance/yahoo/curated_price | head -n 20
# Expect partitioned files: .../date=YYYY-MM-DD/part-<timestamp>.parquet
```

---

## 3. Jupyter Notebook — Verify & Analyze

### 3.1 Install Trino SQLAlchemy dialect (one-time)
```bash
docker compose -f docker-compose.yaml -f docker-compose.airflow.yaml exec -T jupyter \\
  pip install "trino[sqlalchemy]"
```

### 3.2 Inspect data with Pandas
Paste into a Jupyter cell:

```python
import pandas as pd, s3fs

FS_OPTS = {
    "key": "minio-root-user",
    "secret": "minio-root-password",
    "client_kwargs": {"endpoint_url": "http://minio:9000"},
}
SRC_GLOB = "demo-bucket/warehouse/finance/yahoo/curated_price/date=*/part-*.parquet"

fs = s3fs.S3FileSystem(**FS_OPTS)
paths = fs.glob(SRC_GLOB)
df = pd.concat([pd.read_parquet(f"s3://{p}", storage_options=FS_OPTS) for p in paths], ignore_index=True)

# Average close per ticker per day
out = (
    df.assign(d=df["ts"].dt.date)
      .groupby(["ticker","d"])["close"].mean()
      .reset_index(name="avg_close")
      .sort_values(["ticker","d"])
)

out.head(20)

# Overall average close per ticker
df.groupby("ticker")["close"].mean()
```

---

## 4. Trino CLI — Create Iceberg Table

Enter Trino CLI:

```bash
docker compose exec -it trino trino --server http://localhost:8080 --user admin
```

In Trino:

```sql
USE iceberg.curated;

DROP TABLE IF EXISTS fact_price;

CREATE TABLE fact_price (
  ticker VARCHAR,
  ts TIMESTAMP(3) WITH TIME ZONE,
  open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE,
  volume BIGINT,
  ingest_date VARCHAR
)
WITH (partitioning = ARRAY['day(ts)']);
```

---

## 5. Jupyter — Load Data into Iceberg

Paste into a Jupyter cell (uses SQLAlchemy + Trino connector):

```python
import pandas as pd, numpy as np, s3fs
from sqlalchemy.engine import create_engine

FS_OPTS = {"key":"minio-root-user","secret":"minio-root-password","client_kwargs":{"endpoint_url":"http://minio:9000"}}
SRC_GLOB = "demo-bucket/warehouse/finance/yahoo/curated_price/date=*/part-*.parquet"

fs = s3fs.S3FileSystem(**FS_OPTS)
paths = fs.glob(SRC_GLOB)
df = pd.concat([pd.read_parquet(f"s3://{p}", storage_options=FS_OPTS) for p in paths], ignore_index=True)

cols = ["ticker","ts","open","high","low","close","volume","ingest_date"]
df = df[cols].copy()
df["ts"] = pd.to_datetime(df["ts"], utc=True)
for c in ["open","high","low","close"]: df[c] = df[c].astype(float)
df["volume"] = df["volume"].astype("Int64")
df["ingest_date"] = df["ingest_date"].astype(str)

engine = create_engine("trino://user@trino:8080/iceberg/curated")

def sql_literal(s: str) -> str: return s.replace("'", "''")

rows=0; chunk_size=400
for chunk in np.array_split(df, max(1, int(np.ceil(len(df)/chunk_size)))):
    if chunk.empty: continue
    values=[]
    for _, r in chunk.iterrows():
        ts_iso = pd.to_datetime(r["ts"], utc=True).isoformat()
        values.append("("
          f"'{sql_literal(str(r['ticker']))}', "
          f"from_iso8601_timestamp('{sql_literal(ts_iso)}'), "
          f"{'NULL' if pd.isna(r['open']) else r['open']}, "
          f"{'NULL' if pd.isna(r['high']) else r['high']}, "
          f"{'NULL' if pd.isna(r['low']) else r['low']}, "
          f"{'NULL' if pd.isna(r['close']) else r['close']}, "
          f"{'NULL' if pd.isna(r['volume']) else int(r['volume'])}, "
          f"'{sql_literal(str(r['ingest_date']))}'"
          ")")
    sql = "INSERT INTO fact_price (ticker, ts, open, high, low, close, volume, ingest_date) VALUES " + ",".join(values)
    with engine.begin() as conn:
        conn.exec_driver_sql(sql)
    rows += len(values)

print(f"Inserted {rows} rows into iceberg.curated.fact_price")

with engine.connect() as conn:
    print(conn.exec_driver_sql(
        "SELECT ticker, AVG(close) AS avg_close FROM fact_price GROUP BY ticker ORDER BY ticker"
    ).fetchall())
```

---

## 6. Trino Queries

From the Trino CLI:

```sql
-- overall average close per ticker
SELECT ticker, AVG(close) AS avg_close
FROM fact_price
GROUP BY ticker
ORDER BY ticker;

-- daily average close per ticker
SELECT ticker, DATE(ts) AS d, AVG(close) AS avg_close
FROM fact_price
GROUP BY ticker, DATE(ts)
ORDER BY ticker, d
LIMIT 50;
```

---

✅ End of runbook.
