# IMP-FOS-003 — Validation, Normalization & Quarantine Runtime

Status: ENGINEERING CANDIDATE
Parent: EP-FOS-003

## Scope

This increment implements:

- the six ordered validation-layer interfaces required by FOS-HND-ENG-001;
- an ordered pipeline executor;
- immutable source-evidence references in pipeline context;
- derived normalization payloads separated from source evidence;
- externally governed outcome strings and explicit continue/stop control;
- durable pipeline execution and stage-execution records;
- durable quarantine records;
- replay requests linked to prior execution history;
- migration and integration tests.

## Governance boundary

Engineering does not define validation outcome vocabulary, semantic plausibility thresholds, CMAM authority, consequential-use policy, or canonical athlete fields in this increment.

The authority/reconciliation and consequential-use layers are mandatory interfaces, but their domain behavior must be supplied by their owning governed components.

## Invariants

1. Raw source evidence is referenced, never mutated by normalization.
2. All six mandated layers are present and ordered.
3. Pipeline outcomes are not interpreted by Engineering beyond the externally supplied continue/stop signal.
4. Original failed executions remain historical after replay.
5. Quarantine is recoverable state, not a discard path.
6. Replay creates a new processing attempt and points back to preserved evidence/prior execution.

## Active architecture gates

- AG-ENG-004 — Governed API Semantic Contracts: OPEN.
- AG-ENG-005 — Canonical Entity Merge/Split Semantics: OPEN.

No new ECR is required by this implementation candidate.
