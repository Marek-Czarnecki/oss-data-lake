# Repository Contents

Quick orientation for the top-level files and directories. Pair this with `README.md` and `RUNBOOK.md` when navigating the stack.

## Documentation
- `README.md` – quick start workflow, validation commands, and service map.
- `RUNBOOK.md` – step-by-step procedure from clone to dashboards.
- `PROJECT_CONTEXT.md` – architecture, data flow, and operational notes.
- `UPSTREAM.md` – provenance for the Lakekeeper compose definition.
- `CHANGELOG.md`, `ATTRIBUTION.md` – release notes and credits.

## Compose and Config
- `docker-compose*.yaml` – core stack, Airflow overlay, and Metabase/CloudBeaver overlay.
- `.env.example` (copy to `.env`) – overridable defaults for compose services.
- `requirements.txt` – Python dependencies installed into Airflow during init.
- `create-default-warehouse.json`, `create-yfinance-warehouse.json` – Lakekeeper bootstrap payloads.

## Code and Assets
- `dags/` – Airflow DAGs (current ingestion pipeline is `yfinance_to_minio.py`).
- `notebooks/` – Jupyter notebooks mounted into `/home/jovyan/examples/`.
- `scripts/` – helper scripts (driver download, upstream diffs, etc.).
- `etc/catalog/` – Trino catalog definitions (Iceberg REST + Hive file metastore).
- `metabase-plugins/` – location for the Trino driver JAR and plugin README.

## Runtime Artifacts
- `docker-compose.metabase-cloudbeaver.yaml` expects driver JARs in `metabase-plugins/`.
- Buckets and Iceberg metadata live in Docker volumes; manage lifecycle via `docker compose ... down [-v]` commands in the docs.

## Getting Started
1. Read `README.md` for the condensed quick start.
2. Use `RUNBOOK.md` if you prefer a detailed, linear guide.
3. Refer back to this file when you need to remember where a component lives.
