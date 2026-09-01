# FitnessOS Engineering Implementation Control

## Authority

Implementation proceeds under FOS-HND-ENG-001 and the EP-FOS-001 through EP-FOS-015 engineering design baseline.

Engineering owns implementation only. This repository does not redefine architecture, governance, canonical semantics, source authority, metric authority, QA independence, or release governance.

## Active implementation package

- IMP-FOS-001 — Repository Bootstrap
- Parent engineering package: EP-FOS-001 — Platform Engineering Foundation
- Branch: `eng/imp-fos-001-foundation`

## Open architecture/input gates

- AG-ENG-004 — Governed API Semantic Contracts: required before public v1 API contract freeze.
- AG-ENG-005 — Canonical Entity Merge/Split Semantics: required before automated canonical merge/split behavior.

These are gates, not permissions for Engineering to invent missing semantics.

## Implementation invariants

1. Provider schemas must remain isolated from canonical contracts.
2. Canonical IDs must remain provider-independent.
3. Historical state and lineage may not be destructively overwritten.
4. Source/metric authority must be consumed from governed authority inputs such as CMAM, not hard-coded in application logic.
5. Current-state projections and caches are derived and rebuildable.
6. Provider deliveries are evidence signals, not canonical events.
7. Engineering build success means ready for independent QA, not certified.
8. Production promotion remains outside Engineering authority.

## Current technical baseline

- Python runtime baseline: 3.12+
- API framework: FastAPI
- Typed contracts: Pydantic
- Relational persistence target: PostgreSQL via SQLAlchemy/psycopg
- Schema migrations: Alembic
- Structured telemetry foundation: structlog + OpenTelemetry
- Test framework: pytest
- Static quality: Ruff + mypy
- CI: GitHub Actions

All selections above are Engineering Technical Decisions and remain replaceable if they can be changed without altering governed architecture or semantics.
