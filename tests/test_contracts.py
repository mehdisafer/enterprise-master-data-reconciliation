import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
import pytest

from mdm.api import MergeInput, SplitInput, UnmergeInput, VersionInput
from mdm.demo import demonstrate

ROOT = Path(__file__).resolve().parents[1]


def test_published_operation_schemas_match_executable_contracts():
    for name, cls in [("merge", MergeInput), ("split", SplitInput), ("unmerge", UnmergeInput), ("decision-transition", VersionInput)]:
        assert json.loads((ROOT / "contracts" / f"{name}.v1.schema.json").read_text()) == cls.model_json_schema()


@pytest.mark.integration
def test_every_real_outbox_payload_satisfies_the_published_schema(service):
    demonstrate(service)
    schema = json.loads((ROOT / "contracts/golden-event.v1.schema.json").read_text())
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    with service.db.connect() as conn:
        for row in conn.execute("SELECT payload FROM outbox"):
            validator.validate(row["payload"])
