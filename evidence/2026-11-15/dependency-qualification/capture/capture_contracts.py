"""Snapshot stable dependency-sensitive contracts, without database access."""
import hashlib
import json
import platform
import sys
from importlib.metadata import version
from pathlib import Path

from mdm.api import MergeInput, SplitInput, UnmergeInput, VersionInput, create_app
from mdm.domain import SourceRecord
from mdm.service import digest
from mdm.synthetic import demo_records, late_record

def checksum(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()

records = [*demo_records(), late_record()]
payloads = [r.model_dump(mode="json") for r in records]
schemas = {cls.__name__: cls.model_json_schema() for cls in (SourceRecord, MergeInput, SplitInput, UnmergeInput, VersionInput)}
openapi = create_app(actor_map={}).openapi()
report = {
    "python": platform.python_version(),
    "packages": {name: version(name) for name in ("fastapi", "pydantic", "pydantic-core", "starlette")},
    "record_count": len(records),
    "serialized_records_sha256": checksum(payloads),
    "ingestion_hashes": [digest(p) for p in payloads],
    "schemas_sha256": {name: checksum(schema) for name, schema in schemas.items()},
    "openapi_sha256": checksum(openapi),
}
Path(sys.argv[1]).write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({"captured_records": len(records), "schemas": len(schemas), "output": sys.argv[1]}))
