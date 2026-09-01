# IMP-FOS-004 — Connector SDK & Shared Synchronization Core

Status: ENGINEERING CANDIDATE
Parent: EP-FOS-004

## Scope

This increment implements shared Engineering-owned connector infrastructure:

- provider-neutral connector capability contracts;
- provider-neutral source-record and source-envelope contracts;
- shared synchronization modes;
- provider-adapter, evidence-sink, and checkpoint-store interfaces;
- persistence-before-checkpoint synchronization ordering;
- capability enforcement before synchronization;
- durable connector registrations;
- provider connection metadata with credential references rather than raw secrets;
- durable sync-job metadata;
- durable resumable checkpoints;
- migration and tests.

## Explicit exclusions

This increment does not implement Garmin, Strava, Runna, Fuelin, or any other provider-specific API behavior. Provider authentication semantics, endpoint behavior, pagination rules, rate-limit interpretation, field mappings, and source schemas remain owned by FitnessOS Integration Engineering.

It also does not define source authority, canonical metric semantics, CMAM precedence, or Canonical Athlete Model fields.

## Engineering invariants

1. Provider adapters emit provider-neutral SourceRecord values into a shared SourceEnvelope.
2. Shared infrastructure validates declared capabilities rather than hard-coding provider branches.
3. Evidence persistence occurs before checkpoint advancement.
4. A persistence failure prevents advancement of the corresponding resume cursor.
5. Incomplete pages require a resume cursor.
6. Credentials are represented by references to approved secret infrastructure, not stored raw in connector tables.
7. Provider connection state and sync-job state accept externally governed state values rather than inventing domain policy.
8. Provider-specific code cannot directly create canonical truth through this package.

## Active architecture gates

- AG-ENG-004 — Governed API Semantic Contracts: OPEN.
- AG-ENG-005 — Canonical Entity Merge/Split Semantics: OPEN.

No new ECR is required by this implementation candidate.

## QA evidence target

CI must prove static correctness, complete Alembic migration through 0004, persistence of connector/job/checkpoint metadata, capability rejection, persistence-before-checkpoint ordering, and failure-before-checkpoint behavior.

Engineering completion means ready for independent QA; it is not QA certification or production approval.
