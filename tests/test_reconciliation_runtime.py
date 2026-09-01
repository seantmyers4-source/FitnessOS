from __future__ import annotations

from uuid import uuid4

from packages.contracts.reconciliation import (
    AuthorityCandidate,
    AuthorityResolution,
    MatchEvaluation,
    ReconciliationObservation,
)
from packages.reconciliation.runtime import (
    ReconciliationEngine,
    deterministic_external_identity_strategy,
)


def test_exact_identity_match_is_provider_scoped() -> None:
    strategy = deterministic_external_identity_strategy(
        strategy_id="exact_external_identity", strategy_version="1"
    )
    left = ReconciliationObservation(uuid4(), "activity", "garmin", "A123")
    right = ReconciliationObservation(uuid4(), "activity", "garmin", "A123")
    other_source = ReconciliationObservation(uuid4(), "activity", "strava", "A123")

    assert strategy.evaluate(left, right).decision == "MATCH"
    assert strategy.evaluate(left, other_source).decision == "NO_MATCH"


def test_entity_type_mismatch_never_matches() -> None:
    strategy = deterministic_external_identity_strategy(
        strategy_id="exact_external_identity", strategy_version="1"
    )
    engine = ReconciliationEngine(duplicate_strategy=strategy)
    left = ReconciliationObservation(uuid4(), "activity", "garmin", "A123")
    right = ReconciliationObservation(uuid4(), "device", "garmin", "A123")

    result = engine.evaluate_identity(left, right)

    assert result.decision == "NO_MATCH"
    assert result.evidence_reference == "entity_type_mismatch"


def test_missing_authority_resolver_stays_unresolved() -> None:
    strategy = deterministic_external_identity_strategy(
        strategy_id="exact_external_identity", strategy_version="1"
    )
    engine = ReconciliationEngine(duplicate_strategy=strategy)
    candidate = AuthorityCandidate(uuid4(), "distance", "garmin", "obs://distance")

    result = engine.resolve_authority(
        entity_type="activity",
        metric_reference="distance",
        candidates=(candidate,),
    )

    assert result.decision == "UNRESOLVED"
    assert result.selected_observation_id is None
    assert result.reason_code == "AUTHORITY_RESOLVER_NOT_CONFIGURED"


def test_external_authority_resolver_controls_selection() -> None:
    class StubStrategy:
        strategy_id = "configured"
        strategy_version = "7"

        def evaluate(
            self,
            left: ReconciliationObservation,
            right: ReconciliationObservation,
        ) -> MatchEvaluation:
            return MatchEvaluation(
                left.observation_id,
                right.observation_id,
                self.strategy_id,
                self.strategy_version,
                "MATCH",
            )

    selected = uuid4()

    class StubResolver:
        def resolve(
            self,
            *,
            entity_type: str,
            metric_reference: str,
            candidates: tuple[AuthorityCandidate, ...],
        ) -> AuthorityResolution:
            assert entity_type == "activity"
            assert metric_reference == "distance"
            assert candidates
            return AuthorityResolution(
                selected_observation_id=selected,
                authority_version="CMAM-test",
                rule_reference="rule://distance",
                decision="RESOLVED",
            )

    engine = ReconciliationEngine(
        duplicate_strategy=StubStrategy(), authority_resolver=StubResolver()
    )
    left = ReconciliationObservation(uuid4(), "activity", "garmin", "A123")
    right = ReconciliationObservation(uuid4(), "activity", "strava", "S987")
    candidate = AuthorityCandidate(selected, "distance", "garmin", "obs://distance")

    result = engine.reconcile(
        left=left,
        right=right,
        metric_reference="distance",
        candidates=(candidate,),
    )

    assert result.authority_resolution is not None
    assert result.authority_resolution.selected_observation_id == selected
    assert result.authority_resolution.authority_version == "CMAM-test"
