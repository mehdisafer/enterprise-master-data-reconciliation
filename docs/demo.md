# Reproduce and inspect the business scenario

Use a dedicated synthetic database. `mdm demo` is a local operator scenario, not an API shortcut that bypasses real user roles. Its three named demo actors are fixtures; real API calls derive an actor and role from server-side token configuration.

## Automatic demonstration

```bash
mdm migrate
mdm demo --output artifacts/demo.json
mdm check
```

The output records baseline ingestion, repeat ingestion, the initial consumer view, mistaken Orion merge, late Northstar correction, a source update after the Orion merge, the unmerge, a committed-but-unpublished state, and the corrected reporting view. It asserts preserved source identities, restored original Orion IDs, the later source address, event replay idempotency and coherent reporting crosswalks.

## Interactive stewardship

To start before any deliberate human mistake, create a manifest from the three original ERP files:

```bash
python - <<'PY'
import json
from pathlib import Path
manifest = {f"ERP_{name.upper()}": json.loads(Path(f"data/fixtures/v1/erp_{name}.json").read_text()) for name in ("alpha", "beta", "gamma")}
Path("artifacts").mkdir(exist_ok=True)
Path("artifacts/source-manifest.json").write_text(json.dumps(manifest, indent=2))
PY
mdm migrate
mdm run --input artifacts/source-manifest.json --run-key interactive-v1
```

1. Open the console with a requester token. Review the two Orion source records and their missing legal IDs. Inspect the scores, conflicts, current provenance and proposed survivorship. Submit a merge with an explicit reason.
2. Connect with a separate approver token. The decision ledger offers approval or rejection. Requester self-approval is rejected by the service even if a token is misconfigured with the same person under another role.
3. Connect with a separate executor token. Execute the approved decision; the expected group versions are checked again. Any source change invalidates the stale approval.
4. Inspect the golden identity and its source crosswalk. Use attribute lineage and history to see business validity separately from when the platform learned it.
5. After proving the Orion records are different companies, request an unmerge from the executed decision. An explicit split is available when later topology changes make a simple unmerge ambiguous.
6. Observe that the reporting consumer can remain behind after the domain commit. Apply pending corrections with the executor role. Every source pointer should return to a coherent reporting identity.

The known Orion ambiguity deliberately demonstrates a human mistake and its correction. It is not counted as an automatic false merge by the matching evaluator.

## Failed and partial runs

A manifest must name all three ERP systems. Use JSON `null` for an explicitly unavailable source. The run is marked `degraded`, and existing source rows are retained. Restored source availability requires a new run key because the input manifest changed.

The single application orchestrator records `ingestion`, `reconciliation`, `publication` and `complete` phases. Retrying a failed run uses the same manifest and key, at most three attempts. Raw hashes make a crash after ingestion and before the phase checkpoint safe. A session advisory lock releases automatically when a failed process disconnects. No second scheduler is required by this reference.

## Corrections and downstream responsibility

Events carry source keys, golden version, provenance and a `correction_for` decision ID. The reporting consumer applies the entire snapshot and deduplicates event IDs in the same transaction. Other applications must define their own correction procedure for orders, invoices, caches and facts. They must not assume an unmerge physically rolls back business transactions.
