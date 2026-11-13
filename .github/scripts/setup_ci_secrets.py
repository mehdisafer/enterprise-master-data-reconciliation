"""Create short-lived, non-printed secrets for the isolated Compose smoke test."""

import json
import os
from pathlib import Path
import secrets


path = Path(os.environ["MDM_SECRET_DIR"])
path.mkdir(mode=0o700, parents=True, exist_ok=False)
password = secrets.token_urlsafe(32)
actors = {
    secrets.token_urlsafe(32): {"name": f"ci-{role}", "role": role}
    for role in ("requester", "approver", "executor", "reader")
}
files = {
    "postgres_password": password,
    "database_url": f"postgresql://mdm:{password}@postgres:5432/mdm",
    "actors.json": json.dumps(actors),
}
for name, content in files.items():
    with (path / name).open("x") as file:
        file.write(content)
    # Parent directory is private on the host; UID 10001 reads the bind-mounted file.
    (path / name).chmod(0o444)
