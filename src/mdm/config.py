"""External secrets and fixed configuration; no SQL or expressions from metadata."""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from psycopg.conninfo import conninfo_to_dict


def secret(name: str, *, required: bool = True) -> str:
    direct, file = os.environ.get(name), os.environ.get(name + "_FILE")
    if direct and file:
        raise ValueError(f"set only one of {name} and {name}_FILE")
    value = Path(file).read_text(encoding="utf-8").strip() if file else direct
    if required and not value:
        raise ValueError(f"{name} or {name}_FILE must be configured")
    return value or ""


def database_url() -> str:
    value = secret("MDM_DATABASE_URL")
    parts = conninfo_to_dict(value)
    if not parts.get("dbname"):
        raise ValueError("an explicit dedicated database name is required")
    if parts.get("dbname") in {"postgres", "template0", "template1"}:
        raise ValueError("use a dedicated application database, not a system database")
    return value


@dataclass(frozen=True)
class Actor:
    name: str
    role: str

    def require(self, role: str) -> None:
        if self.role != role:
            raise PermissionError(f"the {role} role is required")


def actors() -> dict[str, Actor]:
    raw = json.loads(secret("MDM_ACTORS_JSON"))
    if not isinstance(raw, dict) or not raw:
        raise ValueError("actor configuration must be a nonempty object")
    result: dict[str, Actor] = {}
    for token, entry in raw.items():
        if not isinstance(token, str) or len(token) < 24:
            raise ValueError("actor tokens must contain at least 24 characters")
        if set(entry) != {"name", "role"}:
            raise ValueError("actor configuration accepts only name and role")
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", entry["name"]):
            raise ValueError("invalid actor name")
        if entry["role"] not in {"requester", "approver", "executor", "reader"}:
            raise ValueError("invalid actor role")
        result[token] = Actor(**entry)
    return result

