# IMP-FOS-005 — Identity, Duplicate Detection & Reconciliation Runtime

Status: ENGINEERING CANDIDATE
Parent: EP-FOS-005

## Implemented scope

- provider-neutral reconciliation observation contracts
- pluggable duplicate strategy interface
- exact persisted external-identity matcher as the only Engineering-default matcher
- explicit entity-type mismatch protection
- external CMAM-compatible authority resolver interface
- unresolved authority behavior when no approved resolver is configured
- durable duplicate evaluations
- reconciliation groups and memberships
- explicit conflict persistence
- durable authority decisions
- Alembic migration 0005
- unit tests for provider-scoped exact matching, entity-type isolation, unresolved authority, and external authority control

## Governance boundaries

Engineering does not define probabilistic matching thresholds, source precedence, metric authority, CMAM rules, or canonical merge/split semantics. AMBIGUOUS/UNRESOLVED conditions must remain explicit rather than guessed. AG-ENG-005 remains open for canonical merge/split lifecycle behavior.

## Merge gate

The candidate may merge only after Ruff, mypy, the full Alembic migration chain through 0005, and all tests pass in GitHub Actions.
