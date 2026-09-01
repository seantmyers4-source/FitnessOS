# IMP-FOS-006 — Garmin-Centered Canonical Vertical Slice

Status: IMPLEMENTATION ACTIVE — INTEGRATION BOUNDARY

## Purpose

Prove the provider-neutral source-to-canonical path using Garmin as the first provider, without moving Garmin-specific behavior or source authority into Engineering.

## Engineering-owned path

Provider adapter -> SourceEnvelope -> immutable evidence -> validation/normalization -> reconciliation -> external CMAM authority -> canonical commit request -> history/provenance/current projection/outbox.

## Integration Engineering dependency

The Garmin adapter must be supplied by FitnessOS Integration Engineering through the existing ProviderAdapter and SourceEnvelope contracts. Engineering does not implement Garmin authentication, Garmin API semantics, Garmin schema ownership, provider pagination semantics, or provider field mapping in this package.

## Hard gates

- No canonical commit when authority required for a metric remains UNRESOLVED.
- Provider IDs cannot become canonical IDs.
- Provider-specific schemas cannot become canonical schemas.
- Canonical events cannot publish before canonical persistence.
- AG-ENG-005 remains open; automated entity merge/split is excluded.

## Current increment

This branch establishes the provider-neutral integration contract for the vertical slice. A live Garmin path remains blocked until Integration Engineering returns a conforming Garmin adapter and approved mapping fixtures.
