from __future__ import annotations

import json

import pytest

from packages.connectors.contracts import SyncMode
from packages.connectors.garmin import (
    GarminActivityPage,
    GarminClientError,
    GarminCompletedActivityAdapter,
)
from packages.core.errors import ErrorClass, FitnessOSError


class MemoryEvidenceStore:
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
        reference = f"evidence://garmin/{connection_id}/{source_record_id}/{payload_hash}"
        self.payloads[reference] = payload
        return reference


class FixtureClient:
    def __init__(self, pages: dict[str | None, GarminActivityPage]) -> None:
        self.pages = pages

    def fetch_completed_activities(
        self,
        *,
        connection_id: str,
        cursor: str | None,
        backfill: bool,
    ) -> GarminActivityPage:
        return self.pages[cursor]


def activity(*, distance: float = 10000.0, extra: object | None = None) -> dict[str, object]:
    result: dict[str, object] = {
        "activityId": "G123",
        "activityType": "RUNNING",
        "startTimeInSeconds": 1788200000,
        "durationInSeconds": 3600,
        "distanceInMeters": distance,
        "averageHeartRateInBeatsPerMinute": 148,
        "deviceName": "Garmin test device",
    }
    if extra is not None:
        result["futureGarminField"] = extra
    return result


def test_capability_manifest_is_provider_specific() -> None:
    adapter = GarminCompletedActivityAdapter(
        client=FixtureClient({}), evidence_store=MemoryEvidenceStore()
    )
    assert adapter.capabilities.provider == "garmin"
    assert adapter.capabilities.supported_source_types == ("completed_activity",)
    assert adapter.capabilities.supports_incremental_sync
    assert adapter.capabilities.supports_backfill


def test_fetch_page_produces_recoverable_source_evidence() -> None:
    store = MemoryEvidenceStore()
    adapter = GarminCompletedActivityAdapter(
        client=FixtureClient({None: GarminActivityPage((activity(extra={"x": 1}),))}),
        evidence_store=store,
    )
    page = adapter.fetch_page(connection_id="conn-1", mode=SyncMode.INCREMENTAL, cursor=None)
    record = page.records[0]
    assert record.source_record_id == "G123"
    assert record.source_schema_version == "garmin.completed_activity.v1"
    assert record.payload_hash
    restored = json.loads(store.payloads[record.payload_reference])
    assert restored["futureGarminField"] == {"x": 1}


def test_duplicate_delivery_has_identical_hash() -> None:
    store = MemoryEvidenceStore()
    adapter = GarminCompletedActivityAdapter(
        client=FixtureClient({None: GarminActivityPage((activity(), activity()))}),
        evidence_store=store,
    )
    page = adapter.fetch_page(connection_id="conn-1", mode=SyncMode.INCREMENTAL, cursor=None)
    records = page.records
    assert records[0].source_record_id == records[1].source_record_id
    assert records[0].payload_hash == records[1].payload_hash


def test_updated_provider_record_has_changed_hash() -> None:
    store = MemoryEvidenceStore()
    adapter = GarminCompletedActivityAdapter(
        client=FixtureClient({None: GarminActivityPage((activity(), activity(distance=10010.0)))}),
        evidence_store=store,
    )
    page = adapter.fetch_page(connection_id="conn-1", mode=SyncMode.INCREMENTAL, cursor=None)
    records = page.records
    assert records[0].source_record_id == records[1].source_record_id == "G123"
    assert records[0].payload_hash != records[1].payload_hash


def test_pagination_cursor_is_preserved() -> None:
    page_one = GarminActivityPage((activity(),), next_cursor="page-2", complete=False)
    adapter = GarminCompletedActivityAdapter(
        client=FixtureClient({None: page_one}),
        evidence_store=MemoryEvidenceStore(),
    )
    page = adapter.fetch_page(connection_id="conn-1", mode=SyncMode.BACKFILL, cursor=None)
    assert page.next_cursor == "page-2"
    assert not page.complete


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
        raise GarminClientError(status_code=self.status, diagnostic_reference="diag://safe")


@pytest.mark.parametrize(
    ("status", "expected_class", "retryable"),
    [
        (401, ErrorClass.AUTHENTICATION, False),
        (429, ErrorClass.RATE_LIMIT, True),
        (503, ErrorClass.DEPENDENCY, True),
    ],
)
def test_provider_errors_are_normalized(
    status: int,
    expected_class: ErrorClass,
    retryable: bool,
) -> None:
    adapter = GarminCompletedActivityAdapter(
        client=ErrorClient(status), evidence_store=MemoryEvidenceStore()
    )
    with pytest.raises(FitnessOSError) as captured:
        adapter.fetch_page(connection_id="conn-1", mode=SyncMode.INCREMENTAL, cursor=None)
    assert captured.value.error_class is expected_class
    assert captured.value.retryable is retryable
