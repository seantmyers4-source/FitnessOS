from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from packages.persistence.apdw import SourceEvidence
from packages.persistence.validation import (
    PipelineExecution,
    PipelineStageExecution,
    QuarantineRecord,
    ReplayRequest,
)

DATABASE_URL = os.environ.get(
    "FITNESSOS_DATABASE_URL",
    "postgresql+psycopg://fitnessos:fitnessos@localhost:5432/fitnessos",
)


def test_quarantine_and_replay_preserve_original_execution_history() -> None:
    engine = create_engine(DATABASE_URL)
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    try:
        evidence = SourceEvidence(
            provider="test_provider",
            source_record_type="test_record",
            source_record_id="validation-001",
            payload_reference="object://test/validation-001",
            payload_hash="validation-hash-001",
            correlation_id="corr-validation",
        )
        session.add(evidence)
        session.flush()

        execution = PipelineExecution(
            evidence_id=evidence.evidence_id,
            pipeline_version="1.0.0",
            status="externally-governed-stopped-state",
            correlation_id="corr-validation",
            retry_count=0,
            failure_stage="schema",
        )
        session.add(execution)
        session.flush()

        stage = PipelineStageExecution(
            execution_id=execution.execution_id,
            stage="schema",
            stage_order=2,
            processor_version="1.0.0",
            outcome="externally-governed-stop-state",
        )
        quarantine = QuarantineRecord(
            evidence_id=evidence.evidence_id,
            execution_id=execution.execution_id,
            failure_stage="schema",
            resolution_state="externally-governed-waiting-state",
        )
        session.add_all([stage, quarantine])
        session.flush()

        replay = ReplayRequest(
            evidence_id=evidence.evidence_id,
            prior_execution_id=execution.execution_id,
            reason="processor-updated",
            requested_pipeline_version="1.1.0",
            requested_by="test-suite",
            status="externally-governed-requested-state",
        )
        session.add(replay)
        session.flush()

        assert replay.evidence_id == evidence.evidence_id
        assert replay.prior_execution_id == execution.execution_id
        assert quarantine.execution_id == execution.execution_id
        assert stage.outcome == "externally-governed-stop-state"
    finally:
        session.close()
        transaction.rollback()
        connection.close()
        engine.dispose()
