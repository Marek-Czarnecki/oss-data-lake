# OSS Data Lake Verification Runbook

This runbook documents the **complete sequence** to go from a clean clone to running dashboards in **Metabase** and exploring SQL in **CloudBeaver**.

---

## 1. Prepare a Clean Working Directory

```bash
mkdir oss-data-lake-verify
cd oss-data-lake-verify
git clone git@github.com:Marek-Czarnecki/oss-data-lake.git .
git status   # confirm: On branch main, working tree clean
```

---

## 2. Bring Up the Core Stack

```bash
docker compose -f docker-compose.yml up -d
docker ps --format '{{.Names}}: {{.Status}}' | sort
```

---

## 3. MinIO Bucket Setup

Set the alias and create `demo-bucket` if missing:

```bash
docker compose exec minio mc alias set local http://minio:9000 minio-root-user minio-root-password
docker compose exec minio mc ls local/demo-bucket >/dev/null 2>&1 ||   docker compose exec minio mc mb local/demo-bucket
docker compose exec minio mc ls local
```

---

## 4. Register the `yfinance` Warehouse with Lakekeeper

```bash
curl -s -X POST http://localhost:8181/management/v1/warehouse   -H "Content-Type: application/json"   --data @create-yfinance-warehouse.json
```

Check it exists:

```bash
curl -s http://localhost:8181/management/v1/warehouse
```

---

## 5. Verify Trino Catalogs and Schemas

```bash
docker compose exec trino trino --execute "SHOW CATALOGS"
docker compose exec trino trino --execute "SHOW SCHEMAS FROM iceberg"
```

*(At first, only `information_schema` will appear.)*

---

## 6. Create the Schema in Iceberg

```bash
docker compose exec trino trino --execute "CREATE SCHEMA IF NOT EXISTS iceberg.yfinance"
docker compose exec trino trino --execute "SHOW SCHEMAS FROM iceberg"
```

Now you should see `information_schema` and `yfinance`.

---

## 7. Quick Smoke Table

```bash
docker compose exec trino trino --execute "CREATE TABLE IF NOT EXISTS iceberg.yfinance.hello_world (id int, msg varchar)"
docker compose exec trino trino --execute "INSERT INTO iceberg.yfinance.hello_world VALUES (1,'hello'),(2,'world')"
docker compose exec trino trino --execute "SELECT * FROM iceberg.yfinance.hello_world"
```

---

## 8. Jupyter: Install Trino SQLAlchemy Driver

```bash
docker compose exec -T jupyter pip install "trino[sqlalchemy]"
docker compose exec -T jupyter python -c "import trino, sqlalchemy; print('sqlalchemy+trino OK')"
```

---

## 9. Jupyter Notebook: Create Fact Table

In the notebook cell, use fully-qualified table names:

```python
conn.exec_driver_sql("""
CREATE TABLE IF NOT EXISTS iceberg.yfinance.fact_price (
    ticker VARCHAR,
    ts TIMESTAMP,
    open DOUBLE,
    high DOUBLE,
    low  DOUBLE,
    close DOUBLE,
    volume BIGINT,
    ingest_date DATE
)
""")
```

Insert rows with:

```python
conn.exec_driver_sql("""
INSERT INTO iceberg.yfinance.fact_price (ticker, ts, open, high, low, close, volume, ingest_date)
VALUES ('AAPL', TIMESTAMP '2025-09-01 09:30:00', 190.0, 191.0, 189.0, 190.5, 1000000, DATE '2025-09-01')
""")
```

Verify from Trino:

```bash
docker compose exec trino trino --execute "SHOW TABLES FROM iceberg.yfinance"
docker compose exec trino trino --execute "SELECT COUNT(*) FROM iceberg.yfinance.fact_price"
```

---

## 10. Add the Dashboards Overlay

Copy the overlay file:

```bash
cp ../oss-data-lake/docker-compose.metabase-cloudbeaver.yaml .
```

Bring up Metabase + CloudBeaver:

```bash
docker compose -f docker-compose.yml -f docker-compose.metabase-cloudbeaver.yaml up -d metabase cloudbeaver
```

---

## 11. Add the Starburst Driver to Metabase

Copy the JAR from the other repo into the running container:

```bash
docker cp ../oss-data-lake/metabase-plugins/starburst-6.1.0.metabase-driver.jar metabase:/plugins/
docker compose -f docker-compose.yml -f docker-compose.metabase-cloudbeaver.yaml restart metabase
```

Check logs:

```bash
docker logs -f metabase | grep -i -E "plugin|driver|starburst|trino"
```

---

## 12. Access the UIs

- **Metabase**: [http://localhost:3000](http://localhost:3000)  
- **CloudBeaver**: [http://localhost:8978](http://localhost:8978)

---

## 13. Configure the Connections

### Metabase

1. Admin → Databases → Add Database.  
2. Select **Starburst/Trino**.  
3. Fill in:  
   - Host: `trino`  
   - Port: `8080`  
   - Catalog: `iceberg`  
   - Schema: `yfinance`  
   - Username: `metabase-smoke` (non-empty, any string)  
   - Password: leave blank.  
4. Save → Metabase syncs schema.  

### CloudBeaver

1. Click **New Connection** → choose **Trino**.  
2. Fill in:  
   - Host: `trino`  
   - Port: `8080`  
   - Catalog: `iceberg`  
   - Schema: `yfinance`  
   - Username: `cloudbeaver` (non-empty)  
   - Password: leave blank.  
3. Test → Save.  

---

## 14. Verify End-to-End

In Metabase, run:

```sql
SELECT ticker, DATE(ts) AS day, AVG(close) AS avg_close
FROM iceberg.yfinance.fact_price
GROUP BY ticker, DATE(ts)
ORDER BY ticker, day
LIMIT 20;
```

In CloudBeaver, open SQL Console → run:

```sql
SELECT COUNT(*) FROM iceberg.yfinance.fact_price;
```

---

✅ At this point, you have:  
- Data flowing into Iceberg (`fact_price` table).  
- Queries working in Trino CLI, Jupyter (SQLAlchemy), Metabase, and CloudBeaver.  
- Dashboards possible in Metabase, schema exploration in CloudBeaver.
