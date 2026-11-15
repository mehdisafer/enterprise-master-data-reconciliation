"""Smoke contracts for upgrades to Python, Pydantic and FastAPI; no database required."""

from __future__ import annotations

import tomllib
from importlib.metadata import version
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from mdm.api import (
    IngestInput, MergeInput, PreviewInput, SplitInput, UnmergeInput, VersionInput,
    create_app,
)
from mdm.config import Actor


@pytest.mark.parametrize("distribution", ["fastapi", "uvicorn", "pydantic", "psycopg"])
def test_installed_runtime_distributions_match_direct_pins(distribution):
    data = tomllib.loads((Path(__file__).resolve().parents[1] / "pyproject.toml").read_text())
    pins = {}
    for requirement in data["project"]["dependencies"]:
        name, sep, exact_version = requirement.partition("==")
        assert sep and exact_version and ";" not in exact_version, requirement
        pins[name.split("[")[0]] = exact_version
    assert version(distribution) == pins[distribution]


@pytest.mark.parametrize(("model", "data"), [
    (MergeInput, {"group_ids": ["g1", "g2"], "expected_versions": {"g1": 1, "g2": 1},
                  "reason": "unit", "idempotency_key": "test-merge"}),
    (PreviewInput, {"group_ids": ["g1", "g2"]}),
    (SplitInput, {"group_id": "g1", "partitions": [["a"], ["b"]], "expected_version": 1,
                  "reason": "unit", "idempotency_key": "test-split"}),
    (UnmergeInput, {"merge_decision_id": "m1", "expected_versions": {"g1": 1},
                    "reason": "unit", "idempotency_key": "test-unmerge"}),
    (VersionInput, {"expected_version": 1}),
    (IngestInput, {"records": []}),
])
def test_pydantic_inputs_preserve_strict_unknown_field_rejection(model, data):
    assert model.model_validate(data).model_dump(exclude_none=True)
    with pytest.raises(ValidationError):
        model.model_validate({**data, "unreviewed_field": "must be refused"})


def test_authentic_openapi_is_bearer_protected_and_preserves_domain_routes():
    token = "unit-only-contract-token"
    client = TestClient(create_app(actor_map={token: Actor("unit-reader", "reader")}))
    assert client.get("/api/openapi.json").status_code == 401
    response = client.get("/api/openapi.json", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    for path in ("/api/decisions/merge", "/api/decisions/split", "/api/decisions/unmerge",
                 "/api/preview-merge", "/api/ingest"):
        assert path in response.json()["paths"]
    assert client.get("/openapi.json").status_code == 404
