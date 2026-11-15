"""Combine captured, hash-verified PRs without resolving unrelated dependencies."""
from pathlib import Path
import hashlib
import json
import re
import tomllib
from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "combined"
OUT.mkdir(exist_ok=True)

manifest = json.loads((ROOT / "source-manifest.json").read_text())
for name, expected in manifest.items():
    data = (ROOT / name).read_bytes()
    actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    assert actual == expected["git_blob_sha1"], (name, actual)

def blocks(text):
    chunks = text.split("[[package]]\n")
    result = {}
    for chunk in chunks[1:]:
        name = re.search(r'^name = "([^"]+)"$', chunk, re.MULTILINE).group(1)
        assert name not in result
        result[name] = "[[package]]\n" + chunk
    return chunks[0], result

base_text = (ROOT / "base_lock.lock").read_text()
header, base = blocks(base_text)
_, fastapi = blocks((ROOT / "pr4_lock.lock").read_text())
_, pydantic = blocks((ROOT / "pr5_lock.lock").read_text())
assert set(base) == set(fastapi) == set(pydantic)
assert {n for n in base if base[n] != fastapi[n]} == {"enterprise-master-data-reconciliation", "fastapi"}
assert {n for n in base if base[n] != pydantic[n]} == {"enterprise-master-data-reconciliation", "pydantic", "pydantic-core"}

combined = dict(base)
combined["fastapi"] = fastapi["fastapi"]
combined["pydantic"] = pydantic["pydantic"]
combined["pydantic-core"] = pydantic["pydantic-core"]
root = combined["enterprise-master-data-reconciliation"]
for old, new in [("==0.141.1", "==0.162.4"), ("==2.13.4", "==2.14.3")]:
    assert root.count(old) == 1
    root = root.replace(old, new)
combined["enterprise-master-data-reconciliation"] = root
lock = header + "".join(combined.values())
parsed = tomllib.loads(lock)
packages = {p["name"]: p for p in parsed["package"]}
assert len(packages) == len(base)
for package in packages.values():
    for dep in package.get("dependencies", []):
        assert dep["name"] in packages, (package["name"], dep)

checks = []
for file in ["upstream_fastapi.toml", "upstream_pydantic.toml"]:
    upstream = tomllib.loads((ROOT / file).read_text())["project"]
    for value in upstream["dependencies"]:
        requirement = Requirement(value)
        if requirement.marker is None or requirement.marker.evaluate({"python_version": "3.12", "extra": ""}):
            version = packages[requirement.name.lower().replace("_", "-")]["version"]
            assert version in requirement.specifier, (file, value, version)
            checks.append({"source": file, "requirement": value, "locked_version": version, "satisfied": True})

project = (ROOT / "base_pyproject.toml").read_text()
for old, new in [("hatchling==1.29.0", "hatchling==1.33.0"), ("fastapi==0.141.1", "fastapi==0.162.4"), ("pydantic==2.13.4", "pydantic==2.14.3")]:
    assert project.count(old) == 1
    project = project.replace(old, new)
tomllib.loads(project)
(OUT / "pyproject.toml").write_text(project)
(OUT / "uv.lock").write_text(lock)
(OUT / "Dockerfile").write_bytes((ROOT / "pr7_Dockerfile.txt").read_bytes())
report = {
    "input_main_sha": "16f7325c5f8b16ce2c5259d2fba44f40e78bebe7",
    "package_count": len(packages),
    "changed_package_blocks": [n for n in base if base[n] != combined[n]],
    "all_other_package_blocks_preserved_byte_for_byte": True,
    "direct_upstream_dependency_constraints": checks,
    "changed_versions": {n: packages[n]["version"] for n in ["fastapi", "pydantic", "pydantic-core"]},
    "build_backend": "hatchling==1.33.0",
    "build_backend_in_application_lock": "hatchling" in packages,
    "runtime_validation": "not executed by this static composition script",
    "output_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file()},
}
(ROOT / "combined-static-check.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
