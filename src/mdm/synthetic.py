"""Small, fully fictional industrial ERP corpus and separately labeled truth.

No client data or external dataset is used. Matching code does not import this
module. Held-out labels are for evaluation only; policy v1 is fixed in code.
"""

from __future__ import annotations

from hashlib import sha256
from itertools import combinations

from mdm.domain import RULE_VERSION, SOURCE_SCHEMA_VERSION, SourceRecord

DATASET_VERSION = "synthetic-industrial.v1"
TRUTH_VERSION = "identity-truth.v1"
BASE_VALID_FROM = "2026-01-01T00:00:00Z"
SOURCE_DATES = {
    "ERP_ALPHA": "2026-01-10T09:00:00Z",
    "ERP_BETA": "2026-01-12T09:00:00Z",
    "ERP_GAMMA": "2026-01-14T09:00:00Z",
}


def _r(source: str, source_id: str, name: str, **fields) -> SourceRecord:
    defaults = {
        "source_system": source, "entity_type": "organization", "source_id": source_id,
        "name": name, "valid_from": BASE_VALID_FROM, "source_updated_at": SOURCE_DATES[source],
        "country": "FR",
    }
    defaults.update(fields)
    return SourceRecord(**defaults)


def _labeled_records() -> list[tuple[SourceRecord, str, str]]:
    """Records, truth identity, split. Identity groups never cross evaluation splits."""
    return [
        (_r("ERP_ALPHA", "NORTHSTAR-01", "Northstar Équipements SAS",
            registration_id="FR-SYN-NORTHSTAR-001", address="18 Rue des Ateliers", postal_code="69007", city="Lyon",
            email="contact@northstar.example", phone="+33 4 00 00 00 01", roles=("customer",)), "northstar", "development"),
        (_r("ERP_BETA", "NS-44", "NORTHSTAR EQUIPEMENTS",
            registration_id="fr syn northstar 001", address="20 rue des Ateliers", postal_code="69007", city="LYON",
            email="achats@northstar.example", phone="0033 4 00 00 00 01", roles=("supplier",)), "northstar", "development"),
        (_r("ERP_GAMMA", "NS-900", "Northstar Equipements S.A.S.",
            registration_id="FR.SYN.NORTHSTAR.001", address=None, postal_code="69007", city="Lyon",
            email="operations@northstar.example", phone="+33400000001", roles=("customer", "supplier")), "northstar", "development"),
        (_r("ERP_ALPHA", "VELORA-01", "Vélora Industrial Components SAS",
            address="7 Rue des Vannes", postal_code="38100", city="Grenoble", roles=("customer",)), "velora", "development"),
        (_r("ERP_BETA", "VELORA-20", "Velora Industrial Componants",
            address="7 rue des Vannes", postal_code="38100", city="Grenoble", roles=("supplier",)), "velora", "development"),
        (_r("ERP_ALPHA", "ASTERIA-HOLDING", "Asteria Industrial Group",
            registration_id="FR-SYN-ASTERIA-HOLD", address="10 Parc Industriel", postal_code="13008", city="Marseille",
            phone="+33400000002", roles=("supplier",)), "asteria-holding", "development"),
        (_r("ERP_BETA", "ASTERIA-PLANT", "Asteria Industrial Group Manufacturing",
            registration_id="FR-SYN-ASTERIA-PLANT", parent_source_key="ERP_ALPHA:organization:ASTERIA-HOLDING",
            address="10 Parc Industriel", postal_code="13008", city="Marseille",
            phone="+33400000002", roles=("supplier",)), "asteria-subsidiary", "development"),
        (_r("ERP_GAMMA", "ASTERIA-SITE", "Asteria Industrial Group",
            entity_type="establishment", registration_id="FR-SYN-ASTERIA-HOLD",
            parent_source_key="ERP_ALPHA:organization:ASTERIA-HOLDING", address="10 Parc Industriel",
            postal_code="13008", city="Marseille", phone="+33400000002"), "asteria-site", "development"),
        (_r("ERP_ALPHA", "BRIDGE-A", "Hélios Components SAS", registration_id="FR-SYN-BRIDGE-A",
            address="14 Rue du Lierre", postal_code="91000", city="Evry", phone="+33100000003",
            roles=("customer",)), "helios-a", "development"),
        (_r("ERP_BETA", "BRIDGE-B", "Helios Components",
            address="14 rue du Lierre", postal_code="91000", city="Evry", phone="+33100000003",
            roles=("supplier",)), "helios-a", "development"),
        (_r("ERP_GAMMA", "BRIDGE-C", "Helios Components SARL", registration_id="FR-SYN-BRIDGE-C",
            address="14 Rue du Lierre", postal_code="91000", city="Evry", phone="+33100000003",
            roles=("customer",)), "helios-c", "development"),
        (_r("ERP_ALPHA", "MISTRAL-01", "Mistral Sensors", registration_id="FR-SYN-MISTRAL-001",
            address="9 Centre Technique", postal_code="06000", city="Nice", roles=("supplier",)), "mistral-one", "development"),
        (_r("ERP_BETA", "MISTRAL-02", "Mistral Sensor Systems", registration_id="FR-SYN-MISTRAL-002",
            address="9 Centre Technique", postal_code="06000", city="Nice", roles=("supplier",)), "mistral-two", "development"),
        (_r("ERP_ALPHA", "BOLT-M8", "Stainless steel bolt M8", entity_type="product",
            product_code="BOLT-M8-A", manufacturer="Asteria Tooling", unit_of_measure="EA"), "bolt-each", "development"),
        (_r("ERP_BETA", "B-008", "Boulon inox M8", entity_type="product",
            product_code="BOLT-M8-A", manufacturer="ASTERIA TOOLING SAS", unit_of_measure="EA"), "bolt-each", "development"),
        (_r("ERP_GAMMA", "BOLT-M8-BOX", "Stainless steel bolt M8", entity_type="product",
            product_code="BOLT-M8-A", manufacturer="Asteria Tooling", unit_of_measure="BOX"), "bolt-box", "development"),
        (_r("ERP_ALPHA", "SOLARA-01", "Solara Filtration", registration_id="FR-SYN-SOLARA-001",
            address="5 Allée du Lac", postal_code="74000", city="Annecy", roles=("customer",)), "solara", "development"),
        (_r("ERP_GAMMA", "SOLA-09", "Solara Filtres", registration_id="FR-SYN-SOLARA-001", country=None,
            address=None, postal_code=None, city=None, roles=("supplier",)), "solara", "development"),
        # These two look alike but are intentionally distinct businesses. A
        # human can make the wrong decision; the operation must be reversible.
        (_r("ERP_ALPHA", "ORION-01", "Orion Services SAS", address="6 Avenue du Port",
            postal_code="33000", city="Bordeaux", roles=("customer",)), "orion-one", "heldout"),
        (_r("ERP_BETA", "ORION-02", "ORION SERVICES", address="6 avenue du Port",
            postal_code="33000", city="Bordeaux", roles=("supplier",)), "orion-two", "heldout"),
        (_r("ERP_ALPHA", "CELADON-01", "Céladon Precision Valves", address="21 Route du Canal",
            postal_code="59000", city="Lille", roles=("supplier",)), "celadon", "heldout"),
        (_r("ERP_GAMMA", "CELADON-99", "Celadon Precision Valve", address="21 route du Canal",
            postal_code="59000", city="Lille", roles=("customer",)), "celadon", "heldout"),
        (_r("ERP_ALPHA", "NOVA-01", "Nova Métrologie SAS", registration_id="FR-SYN-NOVA-009",
            address="3 Rue des Mesures", postal_code="31000", city="Toulouse", roles=("customer",)), "nova", "heldout"),
        (_r("ERP_GAMMA", "NOVA-88", "NOVA METROLOGIE", registration_id="fr syn nova 009",
            address="3 rue des mesures", postal_code="31000", city="Toulouse", roles=("supplier",)), "nova", "heldout"),
        (_r("ERP_ALPHA", "HORIZON-01", "Horizon Assemblage SAS", address="8 Rue des Machines",
            postal_code="44000", city="Nantes", email="contact@horizon.example", roles=("customer",)), "horizon", "heldout"),
        (_r("ERP_BETA", "HORIZON-77", "HORIZON ASSEMBLAGE", address="8 rue des machines",
            postal_code="44000", city="Nantes", email="CONTACT@HORIZON.EXAMPLE", roles=("supplier",)), "horizon", "heldout"),
        (_r("ERP_GAMMA", "HORIZON-91", "Horizon Assemblage Ltd", address="8 Rue des Machines",
            postal_code="44000", city="Nantes", email="contact@horizon.example", roles=("customer", "supplier")), "horizon", "heldout"),
        (_r("ERP_ALPHA", "THERMAL-S12", "Thermal Sensor S12", entity_type="product",
            product_code="TS-012", manufacturer="Ficta Instruments", unit_of_measure="EA"), "thermal-ficta", "heldout"),
        (_r("ERP_BETA", "TS-009", "Capteur thermique S12", entity_type="product",
            product_code="TS-012", manufacturer="FICTA INSTRUMENTS SAS", unit_of_measure="EA"), "thermal-ficta", "heldout"),
        (_r("ERP_GAMMA", "THERMAL-ALT", "Thermal Sensor S12", entity_type="product",
            product_code="TS-012", manufacturer="Altair Instruments", unit_of_measure="EA"), "thermal-altair", "heldout"),
        (_r("ERP_BETA", "NOVA-LYON", "Nova Lyon Works", entity_type="establishment",
            registration_id="FR-SYN-NOVA-009", parent_source_key="ERP_ALPHA:organization:NOVA-01",
            address="17 Rue des Mesures", postal_code="69007", city="Lyon"), "nova-lyon-site", "heldout"),
        (_r("ERP_GAMMA", "NOVA-NANTES", "Nova Nantes Works", entity_type="establishment",
            registration_id="FR-SYN-NOVA-009", parent_source_key="ERP_ALPHA:organization:NOVA-01",
            address="24 Rue des Machines", postal_code="44000", city="Nantes"), "nova-nantes-site", "heldout"),
        # Same source duplicates must not be excluded by source-based blocking.
        (_r("ERP_BETA", "CYPRESS-01", "Cypress Hydraulics SAS", registration_id="FR-SYN-CYPRESS-003",
            address="4 Rue du Levant", postal_code="67000", city="Strasbourg", roles=("supplier",)), "cypress", "heldout"),
        (_r("ERP_BETA", "CYPRESS-02", "CYPRESS HYDRAULICS", registration_id="FR-SYN-CYPRESS-003",
            address="4 rue du Levant", postal_code="67000", city="Strasbourg", roles=("customer",)), "cypress", "heldout"),
    ]


def demo_records() -> list[SourceRecord]:
    """Three-ERP baseline; every returned object is a new immutable model."""
    return [record for record, _, _ in _labeled_records()]


def late_record() -> SourceRecord:
    """Late business correction: reliable address update, lower-authority name.

    It is known only on ingestion. The business validity date predates the source
    update. A consumer must see a correction event, not an erased prior fact.
    """
    original = next(record for record in demo_records() if record.key == "ERP_BETA:organization:NS-44")
    return SourceRecord.model_validate({
        **original.model_dump(mode="json"),
        "name": "Northstar Industrial Group",
        "address": "22 Rue des Ateliers",
        "valid_from": "2026-01-15T00:00:00Z",
        "source_updated_at": "2026-02-14T10:30:00Z",
    })


def truth() -> dict:
    """Explicit exhaustive labels, partitioned by entity, not by pair.

    All unlabeled/unknown real-world records must be excluded from evaluation.
    This synthetic corpus is not an estimate of production matching quality.
    """
    rows = _labeled_records()
    result = {
        "version": TRUTH_VERSION, "dataset_version": DATASET_VERSION,
        "source_schema_version": SOURCE_SCHEMA_VERSION, "rule_version": RULE_VERSION,
        "policy": "Thresholds fixed on development; heldout is evaluated without tuning.",
        "identity_by_key": {record.key: identity for record, identity, _ in rows},
        "splits": {},
    }
    for split in ("development", "heldout"):
        labels = {record.key: identity for record, identity, part in rows if part == split}
        pairs = list(combinations(sorted(labels), 2))
        result["splits"][split] = {
            "identity_by_key": labels,
            "positive_pairs": [list(p) for p in pairs if labels[p[0]] == labels[p[1]]],
            "negative_pairs": [list(p) for p in pairs if labels[p[0]] != labels[p[1]]],
        }
    result["scenarios"] = {
        "automatic_duplicate": ["ERP_ALPHA:organization:NORTHSTAR-01", "ERP_BETA:organization:NS-44", "ERP_GAMMA:organization:NS-900"],
        "manual_positive": ["ERP_ALPHA:organization:VELORA-01", "ERP_BETA:organization:VELORA-20"],
        "mistaken_merge_then_split": ["ERP_ALPHA:organization:ORION-01", "ERP_BETA:organization:ORION-02"],
        "transitive_bridge": ["ERP_ALPHA:organization:BRIDGE-A", "ERP_BETA:organization:BRIDGE-B", "ERP_GAMMA:organization:BRIDGE-C"],
        "late_correction": "ERP_BETA:organization:NS-44",
    }
    return result


def scale_records(entity_count: int = 100, seed: int = 42) -> tuple[list[SourceRecord], dict[str, str]]:
    """Deterministic synthetic load corpus with three versions per identity.

    It measures work/cost and replay invariants, not statistical quality: unlike
    the held-out hard cases, every scale identity has complete identifiers.
    """
    if not 1 <= entity_count <= 100_000:
        raise ValueError("entity_count must be in [1, 100000]; larger runs need an explicit new profile")
    records: list[SourceRecord] = []
    labels: dict[str, str] = {}
    for index in range(entity_count):
        token = sha256(f"{seed}:{index}".encode()).hexdigest()[:16]
        identity = f"scale-{seed}-{index:06d}"
        for source in SOURCE_DATES:
            suffix = {"ERP_ALPHA": "SAS", "ERP_BETA": "LTD", "ERP_GAMMA": "SARL"}[source]
            record = _r(
                source, f"S{index:06d}", f"F{token} {suffix}",
                registration_id=f"FR-SYN-SCALE-{seed}-{index:06d}",
                address=f"{index + 1} Synthetic Avenue", postal_code=f"{index % 100000:05d}",
                city="Synthetic City", roles=("customer",) if source == "ERP_ALPHA" else ("supplier",),
            )
            records.append(record)
            labels[record.key] = identity
    return records, labels

