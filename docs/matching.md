# Matching decisions and survivorship

The reconciliation unit is an identity. Customer and supplier are business roles
on an organization. An organization, one of its establishments, and a product are
separate identity domains. A shared address or company group does not establish
identity.

I keep the policy small enough to review: strict source contracts, explicit
candidate blocks, deterministic identifiers, a bounded name similarity signal and
attribute-level survivorship. Metadata describes this fixed policy; it cannot
supply Python expressions, SQL, function names or executable operations.

## Source and normalization contracts

`contracts/source.schema.json` defines the input structure. The Python contract
also enforces timezone-aware source timestamps, role uniqueness, valid composite
parent references, no self-parent, and the fields applicable to each identity
domain. Unknown fields are rejected. A source key is the exact tuple
`source_system:entity_type:source_id`; local IDs cannot contain delimiters, slashes
or SQL text. Identifiers are never coerced to integers.

The accepted source assertion retains original field spellings. Normalization is
a separate comparison projection, versioned as `normalization.v1`. It performs
Unicode casefolding and NFKD accent decomposition, collapses punctuation in names
and addresses, removes a fixed list of trailing legal suffixes and normalizes
identifier separators. Product SKU punctuation and all leading zeroes remain
significant. Phone punctuation and an international `00` prefix are normalized;
no country prefix is guessed. Parent references retain their exact source keys.

`valid_from` describes business validity. `source_updated_at` describes the
source's change time. The application assigns knowledge time when it ingests an
assertion. A late correction must retain all three concepts. A timezone-naive
timestamp is rejected instead of interpreted in the machine's local timezone.

The APIs used for validation and normalization are documented by
[Pydantic](https://docs.pydantic.dev/latest/api/config/) and
[Python's Unicode library](https://docs.python.org/3.12/library/unicodedata.html).
The installed dependency versions are recorded by the project lock and execution
evidence; a documentation page alone does not establish a tested package version.

## Candidate generation

`generate_candidates()` unions exact legal identifier, manufacturer SKU, normalized
name, distinctive name prefix, email, phone, full address/postal code and
postal/name-prefix blocks. Each block includes the identity domain. Source system
and business role are not partitions: two records from one ERP can be duplicates,
and a supplier record can match a customer record.

Common industrial words are excluded from prefix blocks. The full-name block
remains available. Name and contact blocks do not require country, so missing
country data does not silently eliminate a potential match. The comparator
evaluates jurisdiction and other contradictions afterward.

The defaults stop at 1,000 records in one block or 1,000,000 unique candidate
pairs. Limits raise `CandidateLimitExceeded` with the block family or limit; no
top-K truncation, sampling or silent fallback removes records. A failed candidate
run must not mark the affected records as reconciled. These are bounded safety
limits, not a scalability result. The implementation materializes candidate pairs
in memory and large blocks can still be expensive below the limit.

The control evaluator compares candidates with all labeled pairs and reports
candidate recall and the exact missed positive pairs. It defaults to at most
1,000 source records because its exhaustive reference is quadratic. A large load
run should measure candidate work separately and compare against an explicit
small control sample. Partitioning by source or role would break valid matches;
parallel work must preserve the union of block keys and deduplicate pair IDs.

## Pair decisions

`matching.v1` produces the score, individual criterion contributions, normalized
name similarity when used, hard conflicts, rule version and decision. The score is
a rule score between zero and one; it is not a calibrated probability.

| Evidence | Contribution or result |
| --- | --- |
| Organization: exact legal registration and known equal jurisdiction | 0.98, automatic if no hard conflict |
| Product: exact manufacturer, manufacturer SKU and unit | 0.98, automatic if no hard conflict |
| Organization: exact registration with incomplete jurisdiction | 0.65, human review |
| Exact normalized name | 0.45 |
| Similar normalized name, similarity at least 0.86 | 0.45 × similarity; review evidence only |
| Exact full address and postal code | 0.25 |
| Exact email | 0.15 |
| Exact phone | 0.15 |
| Product code with incomplete manufacturer or unit | 0.45; insufficient by itself |

A score of at least 0.60 proposes review when a complete authoritative identifier
is absent. Fuzzy evidence never authorizes an automatic merge. The fuzzy signal
uses the lower of both argument orders of `difflib.SequenceMatcher.ratio()`, with
`autojunk=False`, so pair ordering cannot inflate the score. Python documents its
[order sensitivity and worst-case quadratic behavior](https://docs.python.org/3.12/library/difflib.html#difflib.SequenceMatcher).
Source names are bounded at 240 characters and comparison work is bounded by the
candidate limits. This does not establish latency for a production dataset.

The deterministic and hybrid modes use exactly the same candidate generation.
This makes their difference attributable to the fuzzy name contribution rather
than a different retrieval denominator. Thresholds were fixed on the development
policy before the first held-out evaluation and have not been tuned to held-out
labels. The 34-record corpus is deliberately small and synthetic.

## Hard conflicts and identity groups

A merge is blocked by any of the following:

- Different entity domains, or a direct parent/child source relationship.
- Different nonempty registration identifiers, or a shared identifier with
  contradictory known jurisdictions.
- Two organization names selected for the same business interval, from the same
  authority and exact source change time, that normalize to different values.
- Conflicting known manufacturer, manufacturer SKU or unit for a product.

An establishment cannot match on its parent's legal registration alone. Parent
references describe relationships, not an invitation to merge related companies.
The policy only knows explicit source parent references; it does not infer a
complete corporate ownership graph from names.

`group_conflicts()` checks every pair in the proposed group, including pairs that
were never candidates. Therefore A-B and B-C evidence cannot merge incompatible
A-C endpoints. `survive()` rejects a group with a hard conflict. Connectivity is
never a sufficient group acceptance criterion.

### Historical compatibility

The persistent application checks the current records and the group's business
history before accepting a merge. In [the service](../src/mdm/service.py),
`_business_slices()` is shared by this validation and golden-record reconstruction.
It orders assertions by business validity, source change time, observation time
and raw record ID. For each half-open business interval `[valid_from, valid_to)`,
it selects the latest known assertion for each source that has become effective.
A source does not enter an earlier interval merely because it belongs to the
proposed group today. A late correction replaces an assertion at its business
coordinate without overriding a later business interval.

`_merge_conflicts()` first checks current compatibility. If the current records
are compatible, it reports the first incompatible historical interval, including
its start and end in `historical_interval[start,end):<conflict>`. Merge preview,
request validation, execution and automatic reconciliation all use this check.
A blocked preview exposes the conflicts and no proposed consolidated attributes.
An incompatible automatic candidate retains its comparison evidence, receives
the `group_conflict` disposition, and does not prevent unrelated compatible pairs
from being processed. Reconstruction checks every interval again inside the
serialized transaction; ingestion, split and unmerge cannot persist incompatible
business slices either.

For example, two current registration IDs can agree after a February update while
their January assertions still disagree. They remain incompatible for a merge
that reconstructs the whole history. If the second source only becomes effective
in February, that January conflict does not exist. A subsequent correction of the
January assertion can remove the conflict; earlier golden interpretations remain
available through their closed knowledge-time intervals.

### Comparison evidence and current disposition

The stored comparison describes a specific pair of source revisions and a rule
version. Its score and criterion contributions are distinct from the operational
decision for the complete identity groups:

| Candidate field | Meaning |
| --- | --- |
| `evidence` | Original pair comparison, including its proposed `auto`, `review` or `reject` decision. |
| `disposition` | Current interpretation after membership, whole-group conflicts and human policy are considered. |
| `group_conflicts` | Inspectable current or dated historical incompatibilities for the proposed groups. |
| `policy_blocks` | Recorded human separation or rejection that requires a later explicit human merge. |

Snapshot and quality reads use current source revisions and recompute the
group-dependent disposition. A correction to a third member can change the
compatibility of A-B without revising A or B; an old `group_conflict` disposition
must disappear when its cause disappears. Records already in one group display
`merged`. These reads do not execute a merge: an eligible `auto` disposition can
await a later reconciliation call.

Historical compatibility and human policy remain separate. Correcting a source
does not erase a recorded human rejection or separation. Automatic reconciliation
checks negative links across all members of the proposed groups; only a later
executed explicit human merge can clear the relevant separation. The original
pair score remains visible even when policy changes its disposition to `review`.
Quality counts keep policy-blocked and group-conflicting candidates separate from
actionable review pairs.

Orion deliberately has no hard conflict. Its records share a normalized name and
address but represent distinct companies in truth. The proposed decision is
review. This case exercises human approval error, subsequent separation and
consumer correction; no scoring rule can invent an absent legal identifier.

## Attribute survivorship

`survivorship.v1` selects nonempty values, then source authority for the attribute,
then source freshness, completeness and a stable source-key tie break. A recent
lower-authority name cannot replace an older legal name from the authority.
Missing high-authority values do not erase known lower-authority values.

| Attributes | Highest authority | Second | Third |
| --- | --- | --- | --- |
| Legal name, jurisdiction, registration, parent, product identity and unit | ERP_ALPHA | ERP_BETA | ERP_GAMMA |
| Address, postal code, city | ERP_BETA | ERP_ALPHA | ERP_GAMMA |
| Email and phone | ERP_GAMMA | ERP_BETA | ERP_ALPHA |

Every output attribute contains a provenance entry with source key, source change
time, business validity, rule, authority and selection reason. Contradictory
alternative values remain visible. Missing attributes have explicit null
provenance with a no-source reason. Roles are unioned, with all contributing
source keys listed separately for each role.

The late Northstar correction changes ERP_BETA's address to `22 Rue des Ateliers`.
Because ERP_BETA owns address authority, the golden address changes. Its newer
name `Northstar Industrial Group` is still lower authority than ERP_ALPHA's
`Northstar Équipements SAS`; the latter remains the golden name and the new
disagreement is exposed.

## Evaluation and honest denominators

The versioned truth map has separate development and held-out identity groups.
Matching code does not import the truth or synthetic module. Evaluation reports:

- Candidate recall before any pair decision, and candidate-to-exhaustive work.
- Automatic-match precision and recall, including false automatic merges and
  unresolved positive pairs.
- Suggestion precision and recall for auto plus review. A suggested pair is not
  an approved identity.
- Review count and false review count.
- Optional group pair precision/recall, impure groups and hard-conflicting groups.

An empty denominator produces `null`, not perfect accuracy. Caller-supplied truth
must cover exactly the evaluated records, and supplied groups must partition every
record once. A single global accuracy number is intentionally absent.

These algorithm metrics measure pair evidence and candidate retrieval. They do
not incorporate the persistent application's historical compatibility checks,
current memberships or human policy. Operational dispositions and quality counts
must therefore be interpreted separately from the frozen pair evaluation.

The first pure-Python fixture run observed the following held-out results. These
are reference results for the algorithm. Database, orchestration, warehouse and
UI qualification is recorded separately.

| Held-out result | Deterministic | Hybrid |
| --- | ---: | ---: |
| Source records / exhaustive pairs | 16 / 120 | 16 / 120 |
| Candidate pairs / positive pairs retrieved | 11 / 7 of 7 | 11 / 7 of 7 |
| Automatic true / false matches | 3 / 0 | 3 / 0 |
| Automatic recall | 3/7 | 3/7 |
| Suggested true / false pairs | 6 / 1 | 7 / 1 |
| Suggestion precision | 6/7 | 7/8 |
| Suggestion recall | 6/7 | 7/7 |
| Human-review pairs | 4 | 5 |

The hybrid rule retrieved one additional held-out positive pair with one additional
review and no additional false suggestion. The existing Orion false review remains
visible. The development split showed the same one-pair recall gain. This is enough
to justify the bounded fuzzy review signal in this demonstration; it is not enough
to estimate performance on a real industrial population.

Reproduce the pure contract/algorithm checks with:

```bash
PYTHONPATH=src python -m unittest discover -s tests -p test_matching.py -v
```

For independent datasets, preserve the policy version, label uncertain pairs
explicitly, freeze a new holdout before tuning, and remeasure blocking as well as
matching. Names with different scripts or all distinctive tokens misspelled can
fall outside the current blocks. Missing identifiers are a business review burden;
the fixture result must not hide that limitation.

The database behavior is covered separately by
[temporal regressions](../tests/test_temporal_regressions.py) and
[lifecycle regressions](../tests/test_lifecycle_regressions.py), including dated
conflicts, nonoverlapping source histories, retrospective corrections, group
changes that leave candidate endpoints unchanged, and durable human policy.
Those tests require real PostgreSQL; their presence is not a substitute for an
execution report.

