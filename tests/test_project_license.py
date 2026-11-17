"""Guard the Apache-2.0 project licence and upstream rights boundary."""

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_project_apache_license_complete_and_attributed():
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "Apache License" in text
    assert "Version 2.0, January 2004" in text
    assert "TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION" in text
    assert "9. Accepting Warranty or Additional Liability." in text
    assert "APPENDIX: How to apply the Apache License to your work." in text
    assert "Copyright 2026 Mehdi SAFER" in text
    assert "dbt Labs" not in text


def test_pep639_license_files_declared():
    with (ROOT / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)["project"]
    assert project["license"] == "Apache-2.0"
    assert set(project["license-files"]) == {"LICENSE", "NOTICE", "THIRD_PARTY_NOTICES.md"}
    assert all((ROOT / name).is_file() for name in project["license-files"])


def test_notice_preserves_third_party_rights():
    notice = (ROOT / "NOTICE").read_text(encoding="utf-8")
    third_party = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    assert "Copyright 2026 Mehdi SAFER" in notice
    assert "Apache-2.0" in notice
    assert "third-party" in notice.lower()
    for token in ("dbt-core", "dbt-postgres", "Terraform"):
        assert token in third_party
