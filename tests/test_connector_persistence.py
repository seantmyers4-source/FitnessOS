from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from packages.persistence.apdw import CanonicalEntity
from packages.persistence.connectors import (
    ConnectorRegistration,
    ProviderConnection,
    SyncCheckpoint,
    SyncJob,
)

DATABASE_URL = os.environ.get(
    "FITNESSOS_DATABASE_URL",
    "postgresql+psycopg://fitnessos:fitnessos@localhost:5432/fitnessos",
)


def test_connector_connection_job_and_checkpoint_preserve_secret_reference_boundary() -> None:
    engine = create_engine(DATABASE_URL)
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    try:
        athlete = CanonicalEntity(entity_type="test_athlete")
        registration = ConnectorRegistration(
            provider="test_provider",
            connector_version="1.0.0",
            capability_manifest_reference="contract://test-provider/1.0.0",
        )
        session.add_all([athlete, registration])
        session.flush()

        provider_connection = ProviderConnection(
            connector_id=registration.connector_id,
            athlete_entity_id=athlete.entity_id,
            external_account_reference="external-account-test",
            credential_reference="secret://connector/test-credential",
            connection_state="externally-governed-connected-state",
        )
        session.add(provider_connection)
        session.flush()

        job = SyncJob(
            connection_id=provider_connection.connection_id,
            sync_mode="incremental",
            status="externally-governed-complete-state",
            correlation_id="corr-sync-001",
            checkpoint_before=None,
            checkpoint_after="cursor-001",
            records_observed=2,
            records_persisted=2,
            records_failed=0,
        )
        session.add(job)
        session.flush()

        checkpoint = SyncCheckpoint(
            connection_id=provider_connection.connection_id,
            source_stream="activities",
            cursor_type="opaque_cursor",
            cursor_value="cursor-001",
            sync_job_id=job.sync_job_id,
        )
        session.add(checkpoint)
        session.flush()

        assert provider_connection.credential_reference == "secret://connector/test-credential"
        assert checkpoint.cursor_value == "cursor-001"
        assert checkpoint.sync_job_id == job.sync_job_id
        assert job.records_persisted == 2
    finally:
        session.close()
        transaction.rollback()
        connection.close()
        engine.dispose()
