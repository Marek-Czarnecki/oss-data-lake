# Upstream Provenance

This repository vendors the **Lakekeeper minimal example** as the base compose.

- Upstream repo: https://github.com/lakekeeper-io/lakekeeper
- Path: `examples/minimal`
- Commit: `<COMMIT_SHA>`  ← Replace with the exact commit hash you vendored

Rationale: vendoring avoids submodule friction and enables a simple clone → run experience.

---

## Check for upstream changes

1) Fill in the `Commit:` above **or** set an environment variable when running:
   ```bash
   # either edit UPSTREAM.md (replace <COMMIT_SHA>) and run:
   ./scripts/check-upstream.sh

   # or override via environment:
   LK_COMMIT=<commit_hash> ./scripts/check-upstream.sh
   ```

2) The script fetches `examples/minimal/docker-compose.yaml` at that commit and compares it to your local `docker-compose.yaml`.

- **Exit code 0:** no differences
- **Exit code 2:** differences detected (review before updating)
- **Exit code 1:** commit unknown / not set

If you decide to vendor updates, update `docker-compose.yaml` and bump the `Commit:` here.
