# FOS-INT-GARMIN-001 — Garmin Completed Running Activity Integration Candidate

Status: ENGINEERING CANDIDATE
Parent: EP-FOS-006 / IMP-FOS-006
Provider: Garmin
Connector version: 1.0.0
Source type: `completed_activity`

## Scope

This package implements the provider-side seam for completed activity evidence. It emits shared `SourceRecord` objects and relies on the existing shared synchronization engine to construct `SourceEnvelope` objects, persist evidence before checkpoint advancement, and route downstream processing.

No canonical write, canonical identity assignment, CMAM precedence, or reconciliation authority is implemented here.

## Capability manifest

- provider: `garmin`
- source type: `completed_activity`
- polling: declared
- incremental sync: declared
- bounded/resumable backfill: supported through provider cursor semantics
- auth refresh: declared for the eventual approved Garmin client implementation
- webhooks: not declared in this candidate because provider-access prerequisites have not yet established an approved webhook contract

## Authentication and provider access

The adapter deliberately depends on a `GarminActivityClient` protocol rather than embedding credentials or an unapproved Garmin access mechanism. Production client wiring must use the approved Garmin program/API credentials through FitnessOS credential references. Authentication/authorization failures are translated to the shared error taxonomy and invalid credentials are terminal rather than indefinitely retried.

## Rate limiting and recovery

HTTP/provider 429 is mapped to `RATE_LIMIT` and marked retryable. Provider 5xx failures map to retryable `DEPENDENCY`. Retry timing, jitter, workload scheduling, checkpoint persistence, and backpressure remain responsibilities of shared infrastructure; this connector does not introduce a Garmin scheduler.

## Payload integrity and privacy

Payloads are serialized deterministically and SHA-256 hashed. The evidence store returns a durable `payload_reference`. Unknown additive fields remain in raw evidence. Full athlete payloads and credentials are not logged by this implementation.

Same provider identity + same payload yields the same hash. Same provider identity + changed payload yields a different hash and therefore distinct evidence.

## Mapping v1

`packages/connectors/garmin_mapping.py` defines the versioned Garmin-to-provider-neutral candidate mapping. It does not express canonical authority.

Initial candidates cover provider activity identity, activity type, start time, duration, distance, average heart rate, average speed, and external device label where supplied.

Heart-rate series, explicit end timestamp, provider account identity, and richer device identifiers remain dependent on the exact approved Garmin payload contract and must not be invented.

## Fixtures / contract evidence

Automated tests cover:

- capability declaration;
- valid source evidence and durable payload recovery;
- preservation of unknown additive fields;
- identical duplicate delivery;
- changed payload for the same provider ID;
- pagination/resume cursor;
- authentication failure;
- rate limiting;
- transient provider 5xx behavior.

The repository does not yet contain an approved live Garmin API client or sanctioned Garmin production fixture set. Historical retrieval is represented through the shared cursor/backfill contract but requires provider-access verification before claiming live backfill certification.

## Known limitations / prerequisites

1. Approved Garmin developer/program access and exact API contract are required before live provider calls can be implemented safely.
2. The handoff requests Garmin authentication according to the officially supported mechanism available to this deployment; no such credential or endpoint contract is present in the repository, so this package intentionally avoids guessing it.
3. Heart-rate series and provider-specific webhook support are not claimed until the approved Garmin API exposes and authorizes them.
4. This is certification-ready source-adapter structure, not QA certification and not production authorization.

## Boundary statement

This implementation changes no canonical schema, canonical identity semantics, source authority, CMAM decision, reconciliation policy, APDW persistence model, or release authority. Another provider can implement the same `ProviderAdapter` contract without changing canonical persistence semantics.
