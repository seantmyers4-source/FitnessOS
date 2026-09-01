from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ReconciliationObservation:
    """Provider-neutral observation identity supplied to reconciliation."""

    observation_id: UUID
    entity_type: str
    source: str
    external_identity: str | None = None


@dataclass(frozen=True, slots=True)
class MatchEvaluation:
    """One versioned duplicate/identity evaluation result."""

    left_observation_id: UUID
    right_observation_id: UUID
    strategy_id: str
    strategy_version: str
    decision: str
    score: float | None = None
    evidence_reference: str | None = None


@dataclass(frozen=True, slots=True)
class AuthorityCandidate:
    """Candidate value submitted to an externally governed authority resolver."""

    observation_id: UUID
    metric_reference: str
    source: str
    value_reference: str


@dataclass(frozen=True, slots=True)
class AuthorityResolution:
    """Result returned by an external CMAM-compatible authority resolver."""

    selected_observation_id: UUID | None
    authority_version: str
    rule_reference: str | None
    decision: str
    reason_code: str | None = None


class DuplicateStrategy(Protocol):
    """Pluggable strategy; thresholds and semantics are supplied outside Engineering."""

    strategy_id: str
    strategy_version: str

    def evaluate(
        self,
        left: ReconciliationObservation,
        right: ReconciliationObservation,
    ) -> MatchEvaluation: ...


class AuthorityResolver(Protocol):
    """External source/metric authority boundary implemented from approved CMAM rules."""

    def resolve(
        self,
        *,
        entity_type: str,
        metric_reference: str,
        candidates: tuple[AuthorityCandidate, ...],
    ) -> AuthorityResolution: ...
