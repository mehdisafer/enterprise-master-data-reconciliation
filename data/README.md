# Synthetic source data and identity truth

All records were authored for this repository. The company names, addresses,
registration identifiers, contact details and business relationships are fictional.
No client export, personal dataset, existing project code or third-party dataset
was copied. The repository's eventual license decision also covers this original
fixture content; this file does not choose that license.

`fixtures/v1/erp_alpha.json`, `erp_beta.json` and `erp_gamma.json` are three independent
ERP inputs. They contain 34 source identities in total. `late_correction.json`
updates an existing composite source key, with a business-valid date preceding its
source change timestamp. The ingestion layer must assign the separate observation
time and preserve the earlier assertion.

`truth/v1/identity_truth.json` identifies 14 positive unordered pairs across two
disjoint sets: 18 development source identities and 16 held-out source identities.
Every pair within each set is explicitly labeled positive or negative. All source
records for one truth identity belong to the same set, preventing pair-level
leakage. These labels are not input fields and are never read by matching code.

The small held-out set exercises failures that a portfolio demonstration should
make visible. It is not independent production validation or a statistically
representative benchmark. Its ambiguous false review is retained intentionally.
Changing policy after seeing these labels requires a new version and a new
independent holdout before claiming generalization.

| Scenario | Source identities | Intended outcome |
| --- | --- | --- |
| Northstar | ALPHA `NORTHSTAR-01`, BETA `NS-44`, GAMMA `NS-900` | One organization, both customer and supplier roles, attribute provenance retained |
| Vélora | ALPHA `VELORA-01`, BETA `VELORA-20` | Spelling variation without legal ID; fuzzy evidence proposes review |
| Asteria | ALPHA `ASTERIA-HOLDING`, BETA `ASTERIA-PLANT`, GAMMA establishment `ASTERIA-SITE` | Parent, subsidiary and establishment remain distinct |
| Hélios bridge | ALPHA `BRIDGE-A`, BETA `BRIDGE-B`, GAMMA `BRIDGE-C` | A-B and B-C are plausible; incompatible A-C IDs prevent a three-record group |
| Orion | ALPHA `ORION-01`, BETA `ORION-02` | Shared name/address and missing IDs; deliberate human error can be corrected by split |
| Bolts | ALPHA product `BOLT-M8`, BETA product `B-008`, GAMMA product `BOLT-M8-BOX` | First two match; unit-versus-box must remain distinct |
| Thermal sensors | ALPHA product `THERMAL-S12`, BETA product `TS-009`, GAMMA product `THERMAL-ALT` | First two match; a different manufacturer blocks the third |
| Cypress | Two BETA source IDs | Same-ERP duplicates must not be excluded from candidate generation |

The Python fixture factory is `mdm.synthetic.demo_records()`. Tests compare the
factory, the JSON input files and truth file so code and the published fixtures
cannot drift unnoticed. `scale_records(entity_count, seed)` creates exactly three
source records per synthetic identity with reproducible identifiers. That load
corpus measures work, memory and recovery; its complete identifiers deliberately
make it unsuitable for measuring difficult matching accuracy.

