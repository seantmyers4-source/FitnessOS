# IMP-FOS-002 — Executable APDW Persistence & History

Status: ENGINEERING CANDIDATE
Parent: EP-FOS-002
Governed by: FOS-HND-ENG-001 and ratified FitnessOS v1.0 baseline

## Scope

This increment implements provider-neutral persistence primitives only:

- immutable source-evidence references and fingerprints;
- stable canonical entity identity containers;
- external identity aliases;
- non-destructive canonical versions with effective/system time fields;
- many-to-many provenance links;
- externally governed quality-state storage;
- disposable current-projection pointers;
- idempotency records;
- transactional outbox persistence.

## Explicit exclusions

This increment does not define athlete-domain fields, Canonical Athlete Model semantics, source or metric authority, provider precedence, readiness/load logic, entity merge/split behavior, or public API semantics.

The JSON canonical-version payload is an implementation container only. It does not authorize Engineering to invent canonical fields. Domain payload schemas remain gated by approved canonical contracts.

## Active architecture gates

- AG-ENG-004 — Governed API Semantic Contracts: OPEN.
- AG-ENG-005 — Canonical Entity Merge/Split Semantics: OPEN.

Neither gate is bypassed by this increment.

## Engineering invariants

1. Provider IDs never become canonical IDs.
2. A corrected canonical version supersedes rather than destroys prior history.
3. Current projections are disposable and must reference canonical versions.
4. Source evidence remains independently identifiable after reconciliation.
5. Consequential canonical versions can retain provenance and quality metadata.
6. A canonical event outbox record can participate in the same database transaction as canonical persistence.
7. Identical idempotency scope/key/version combinations identify one logical mutation.
8. Changed source payloads sharing the same external record ID remain distinguishable by payload hash.

## QA evidence target

The candidate must demonstrate successful static checks, Alembic upgrade, PostgreSQL integration tests, history preservation, source-evidence version distinction, projection-to-current-version linkage, and outbox persistence.

Engineering completion means ready for independent QA; it is not QA certification or production approval.
