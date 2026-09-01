from __future__ import annotations

from dataclasses import dataclass

from packages.contracts.reconciliation import (
    AuthorityCandidate,
    AuthorityResolution,
    AuthorityResolver,
    DuplicateStrategy,
    MatchEvaluation,
    ReconciliationObservation,
)


@dataclass(frozen=True, slots=True)
class ReconciliationResult:
    """Provider-neutral result of identity evaluation plus optional authority resolution."""

    match_evaluation: MatchEvaluation
    authority_resolution: AuthorityResolution | None = None


class ReconciliationEngine:
    """Runs externally configured reconciliation without embedding provider precedence."""

    def __init__(
        self,
        *,
        duplicate_strategy: DuplicateStrategy,
        authority_resolver: AuthorityResolver | None = None,
    ) -> None:
        self._duplicate_strategy = duplicate_strategy
        self._authority_resolver = authority_resolver

    def evaluate_identity(
        self,
        left: ReconciliationObservation,
        right: ReconciliationObservation,
    ) -> MatchEvaluation:
        if left.entity_type != right.entity_type:
            return MatchEvaluation(
                left_observation_id=left.observation_id,
                right_observation_id=right.observation_id,
                strategy_id=self._duplicate_strategy.strategy_id,
                strategy_version=self._duplicate_strategy.strategy_version,
                decision="NO_MATCH",
                evidence_reference="entity_type_mismatch",
            )
        return self._duplicate_strategy.evaluate(left, right)

    def resolve_authority(
        self,
        *,
        entity_type: str,
        metric_reference: str,
        candidates: tuple[AuthorityCandidate, ...],
    ) -> AuthorityResolution:
        if self._authority_resolver is None:
            return AuthorityResolution(
                selected_observation_id=None,
                authority_version="UNAVAILABLE",
                rule_reference=None,
                decision="UNRESOLVED",
                reason_code="AUTHORITY_RESOLVER_NOT_CONFIGURED",
            )
        return self._authority_resolver.resolve(
            entity_type=entity_type,
            metric_reference=metric_reference,
            candidates=candidates,
        )

    def reconcile(
        self,
        *,
        left: ReconciliationObservation,
        right: ReconciliationObservation,
        metric_reference: str | None = None,
        candidates: tuple[AuthorityCandidate, ...] = (),
    ) -> ReconciliationResult:
        evaluation = self.evaluate_identity(left, right)
        if evaluation.decision != "MATCH" or metric_reference is None:
            return ReconciliationResult(match_evaluation=evaluation)

        authority = self.resolve_authority(
            entity_type=left.entity_type,
            metric_reference=metric_reference,
            candidates=candidates,
        )
        return ReconciliationResult(
            match_evaluation=evaluation,
            authority_resolution=authority,
        )


def deterministic_external_identity_strategy(
    *, strategy_id: str, strategy_version: str
) -> DuplicateStrategy:
    """Build the only Engineering-default matcher: exact persisted external identity equality."""

    class _ExactExternalIdentityStrategy:
        def __init__(self) -> None:
            self.strategy_id = strategy_id
            self.strategy_version = strategy_version

        def evaluate(
            self,
            left: ReconciliationObservation,
            right: ReconciliationObservation,
        ) -> MatchEvaluation:
            exact_match = (
                left.external_identity is not None
                and left.external_identity == right.external_identity
                and left.source == right.source
            )
            return MatchEvaluation(
                left_observation_id=left.observation_id,
                right_observation_id=right.observation_id,
                strategy_id=self.strategy_id,
                strategy_version=self.strategy_version,
                decision="MATCH" if exact_match else "NO_MATCH",
                score=1.0 if exact_match else 0.0,
                evidence_reference="exact_external_identity",
            )

    return _ExactExternalIdentityStrategy()
