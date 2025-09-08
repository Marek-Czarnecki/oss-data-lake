# Changelog

All notable changes for the OSS Data Lake Test environment runbook and setup.

## [Unreleased]

### Added
- `RUNBOOK.md` with full, tested sequence from clean clone → smoke test → clean shutdown.
- `README.md` with quick start instructions, Trino smoke test, and Web UI endpoints.
- `CHANGELOG.md` documenting changes.

### Changed
- Corrected Trino CLI command to use `--server http://localhost:8080` when executed **inside the container**.
- Updated bucket creation step to use `mc` directly (removed `sh -lc` wrapper).
- Removed all references to `jq` for JSON parsing — instructions now show raw `curl` output.
- Replaced placeholders with actual repo URL and path:
  `https://github.com/Marek-Czarnecki/oss-data-lake && cd oss-data-lake/oss-data-lake-test`.

### Verified
- `demo-bucket` and `examples` buckets created in MinIO.
- `yfinance` warehouse registered successfully in Lakekeeper.
- Trino CLI smoke test (create schema, table, insert, select) completed successfully.
- Iceberg files confirmed in `demo-bucket/warehouse` via MinIO client.

---
