from __future__ import annotations

import pytest

from packages.connectors.contracts import SyncMode
from packages.connectors.garmin import (
    GarminActivityPage,
    GarminClientError,
    GarminCompletedActivityAdapter,
)
from packages.core.errors import ErrorClass, FitnessOSError


class EvidenceStore:
    def __init__(self) -> None:
        self.payloads: dict[str, bytes] = {}

    def persist_payload(
        self,
        *,
        connection_id: str,
        source_record_id: str,
        payload: bytes,
        payload_hash: str,
    ) -> str:
        reference = f"evidence://{source_record_id}/{payload_hash}"
        self.payloads[reference] = payload
        return reference


class ErrorClient:
    def __init__(self, status: int) -> None:
        self.status = status

    def fetch_completed_activities(
        self,
        *,
        connection_id: str,
        cursor: str | None,
        backfill: bool,
    ) -> GarminActivityPage:
        raise GarminClientError(
            status_code=self.status,
            diagnostic_reference=f"diag://{self.status}",
        )


class PayloadClient:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def fetch_completed_activities(
        self,
        *,
        connection_id: str,
        cursor: str | None,
        backfill: bool,
    ) -> GarminActivityPage:
        return GarminActivityPage((self.payload,), complete=True)


@pytest.mark.parametrize(
    ("status", "error_class", "retryable"),
    [
        (401, ErrorClass.AUTHENTICATION, False),
        (403, ErrorClass.AUTHORIZATION, False),
        (429, ErrorClass.RATE_LIMIT, True),
        (503, ErrorClass.DEPENDENCY, True),
    ],
)
def test_provider_error_matrix(
    status: int, error_class: ErrorClass, retryable: bool
) -> None:
    adapter = GarminCompletedActivityAdapter(
        client=ErrorClient(status), evidence_store=EvidenceStore()
    )

    with pytest.raises(FitnessOSError) as caught:
        adapter.fetch_page(
            connection_id="connection", mode=SyncMode.INCREMENTAL, cursor=None
        )

    assert caught.value.error_class is error_class
    assert caught.value.retryable is retryable


def test_missing_activity_id_is_non_retryable_validation_failure() -> None:
    adapter = GarminCompletedActivityAdapter(
        client=PayloadClient({"activityType": "RUNNING", "distanceInMeters": 1000.0}),
        evidence_store=EvidenceStore(),
    )

    with pytest.raises(FitnessOSError) as caught:
        adapter.fetch_page(
            connection_id="connection", mode=SyncMode.INCREMENTAL, cursor=None
        )

    assert caught.value.error_class is ErrorClass.VALIDATION
    assert not caught.value.retryable


def test_unknown_additive_field_remains_in_raw_evidence() -> None:
    store = EvidenceStore()
    payload = {
        "activityId": "G-UNKNOWN",
        "activityType": "RUNNING",
        "startTimeInSeconds": 1788200000,
        "futureGarminField": {"nested": True},
    }
    adapter = GarminCompletedActivityAdapter(
        client=PayloadClient(payload), evidence_store=store
    )

    page = adapter.fetch_page(
        connection_id="connection", mode=SyncMode.INCREMENTAL, cursor=None
    )
    record = page.records[0]

    assert b"futureGarminField" in store.payloads[record.payload_reference]
