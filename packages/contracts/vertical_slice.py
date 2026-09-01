from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from packages.contracts.connectors import SourceEnvelope
from packages.contracts.reconciliation import AuthorityCandidate, ReconciliationObservation


@dataclass(frozen=True, slots=True)
class CanonicalCommitRequest:
    """Provider-neutral handoff into canonical persistence after governed processing."""

    entity_type: str
    canonical_entity_id: UUID | None
    source_envelope: SourceEnvelope
    normalized_observation: ReconciliationObservation
    authority_candidates: tuple[AuthorityCandidate, ...]
    metric_reference: str | None
    effective_from: datetime | None
    quality_state: str
    provenance_reference: str


@dataclass(frozen=True, slots=True)
class VerticalSliceResult:
    """End-to-end processing result without provider-specific canonical semantics."""

    evidence_reference: str
    reconciliation_decision: str
    authority_decision: str | None
    canonical_commit_allowed: bool
    reason_code: str | None = None
