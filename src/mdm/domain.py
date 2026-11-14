"""Versioned, strict source and comparison contracts.

Customer and supplier are roles. Legal organizations, establishments and products
are different identity domains and never share an identity group.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SOURCE_SCHEMA_VERSION = "source.v1"
RULE_VERSION = "matching.v1"
NORMALIZATION_VERSION = "normalization.v1"
SURVIVORSHIP_VERSION = "survivorship.v1"
SourceSystem = Literal["ERP_ALPHA", "ERP_BETA", "ERP_GAMMA"]
EntityType = Literal["organization", "establishment", "product"]
Role = Literal["customer", "supplier"]
Decision = Literal["auto", "reject", "review"]

SOURCE_KEY_PATTERN = re.compile(
    r"^(ERP_ALPHA|ERP_BETA|ERP_GAMMA):(organization|establishment|product):"
    r"[A-Za-z0-9_.-]{1,100}$"
)


class SourceRecord(BaseModel):
    """An immutable source assertion, before normalization.

    ``source_updated_at`` is the source's change timestamp; ``valid_from`` is
    business validity. Ingestion assigns the separate knowledge timestamp.
    Product codes are manufacturer-assigned identifiers, not local ERP IDs.
    """

    model_config = ConfigDict(
        extra="forbid", frozen=True,
        json_schema_extra={
            "allOf": [{
                "if": {"properties": {"entity_type": {"const": "product"}}},
                "then": {"properties": {
                    "registration_id": {"type": "null"},
                    "parent_source_key": {"type": "null"},
                    "roles": {"maxItems": 0},
                }},
                "else": {"properties": {
                    "product_code": {"type": "null"},
                    "manufacturer": {"type": "null"},
                    "unit_of_measure": {"type": "null"},
                }},
            }],
        },
    )

    source_system: SourceSystem
    entity_type: EntityType
    source_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.-]+$")
    name: str = Field(min_length=1, max_length=240, pattern=r"\S")
    valid_from: datetime
    source_updated_at: datetime
    country: str | None = Field(default=None, min_length=2, max_length=2, pattern=r"^[A-Za-z]{2}$")
    registration_id: str | None = Field(default=None, max_length=128)
    parent_source_key: str | None = Field(
        default=None, max_length=140,
        pattern=r"^(ERP_ALPHA|ERP_BETA|ERP_GAMMA):organization:[A-Za-z0-9_.-]{1,100}$",
    )
    address: str | None = Field(default=None, max_length=500)
    postal_code: str | None = Field(default=None, max_length=32)
    city: str | None = Field(default=None, max_length=120)
    email: str | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=64)
    product_code: str | None = Field(default=None, max_length=128)
    manufacturer: str | None = Field(default=None, max_length=240)
    unit_of_measure: str | None = Field(default=None, max_length=32)
    roles: tuple[Role, ...] = Field(default=(), json_schema_extra={"uniqueItems": True})

    @field_validator("valid_from", "source_updated_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("source timestamps must include an explicit timezone")
        return value

    @field_validator("name")
    @classmethod
    def nonblank_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("name must contain non-whitespace characters")
        return value

    @field_validator("country")
    @classmethod
    def country_code(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"[A-Za-z]{2}", value):
            raise ValueError("country must be a two-letter jurisdiction code")
        return value

    @field_validator("parent_source_key")
    @classmethod
    def parent_key(cls, value: str | None) -> str | None:
        if value is not None and not SOURCE_KEY_PATTERN.fullmatch(value):
            raise ValueError("parent_source_key must be a complete, valid composite source key")
        if value is not None and value.split(":")[1] != "organization":
            raise ValueError("a parent must identify an organization")
        return value

    @field_validator("roles")
    @classmethod
    def unique_roles(cls, value: tuple[Role, ...]) -> tuple[Role, ...]:
        if len(value) != len(set(value)):
            raise ValueError("roles must not contain duplicate values")
        return value

    @model_validator(mode="after")
    def identity_domains(self) -> "SourceRecord":
        if self.parent_source_key == self.key:
            raise ValueError("an organization cannot be its own parent")
        if self.entity_type == "product":
            if self.registration_id is not None or self.parent_source_key is not None or self.roles:
                raise ValueError("products cannot carry organization identifiers, parents or business roles")
        elif self.product_code is not None or self.manufacturer is not None or self.unit_of_measure is not None:
            raise ValueError("product identifiers and units are only valid for product records")
        if self.registration_id is not None and self.registration_id.strip() and not any(c.isalnum() for c in self.registration_id):
            raise ValueError("registration_id must contain letters or digits")
        return self

    @property
    def key(self) -> str:
        return f"{self.source_system}:{self.entity_type}:{self.source_id}"


class Evidence(BaseModel):
    """Stored explanation of a versioned pair comparison."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    left_key: str
    right_key: str
    score: float = Field(ge=0, le=1)
    contributions: dict[str, float]
    conflicts: list[str]
    decision: Decision
    rule_version: str = RULE_VERSION
    normalization_version: str = NORMALIZATION_VERSION
    reasons: list[str] = Field(default_factory=list)
    mode: Literal["deterministic", "hybrid"] = "hybrid"

