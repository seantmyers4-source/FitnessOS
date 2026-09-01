from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from packages.connectors.contracts import ConnectorCapabilities, FetchPage, SourceRecord, SyncMode
from packages.core.errors import ErrorClass, FitnessOSError

PROVIDER = "garmin"
CONNECTOR_VERSION = "1.0.0"
SOURCE_TYPE = "completed_activity"
SOURCE_SCHEMA_VERSION = "garmin.completed_activity.v1"


class GarminClientError(Exception):
    def __init__(self, *, status_code: int | None, diagnostic_reference: str | None = None) -> None:
        super().__init__("Garmin provider request failed")
        self.status_code = status_code
        self.diagnostic_reference = diagnostic_reference


@dataclass(frozen=True, slots=True)
class GarminActivityPage:
    activities: tuple[Mapping[str, object], ...]
    next_cursor: str | None = None
    complete: bool = True


class GarminActivityClient(Protocol):
    def fetch_completed_activities(
        self,
        *,
        connection_id: str,
        cursor: str | None,
        backfill: bool,
    ) -> GarminActivityPage: ...


class GarminEvidenceStore(Protocol):
    def persist_payload(
        self,
        *,
        connection_id: str,
        source_record_id: str,
        payload: bytes,
        payload_hash: str,
    ) -> str: ...


class GarminCompletedActivityAdapter:
    """Garmin source adapter. It emits source evidence only; never canonical entities."""

    def __init__(self, *, client: GarminActivityClient, evidence_store: GarminEvidenceStore) -> None:
        self._client = client
        self._evidence_store = evidence_store

    @property
    def capabilities(self) -> ConnectorCapabilities:
        return ConnectorCapabilities(
            provider=PROVIDER,
            connector_version=CONNECTOR_VERSION,
            supported_source_types=(SOURCE_TYPE,),
            supports_polling=True,
            supports_backfill=True,
            supports_incremental_sync=True,
            supports_auth_refresh=True,
            checkpoint_strategy="provider_cursor",
        )

    def fetch_page(
        self,
        *,
        connection_id: str,
        mode: SyncMode,
        cursor: str | None,
    ) -> FetchPage:
        if mode not in {SyncMode.INCREMENTAL, SyncMode.BACKFILL, SyncMode.REPLAY}:
            raise ValueError(f"unsupported Garmin sync mode: {mode.value}")
        try:
            page = self._client.fetch_completed_activities(
                connection_id=connection_id,
                cursor=cursor,
                backfill=mode is SyncMode.BACKFILL,
            )
        except GarminClientError as exc:
            raise _map_provider_error(exc, connection_id=connection_id) from exc

        records = tuple(
            self._to_source_record(connection_id=connection_id, payload=activity)
            for activity in page.activities
        )
        return FetchPage(records=records, next_cursor=page.next_cursor, complete=page.complete)

    def _to_source_record(
        self,
        *,
        connection_id: str,
        payload: Mapping[str, object],
    ) -> SourceRecord:
        source_id = _activity_id(payload)
        payload_bytes = _stable_json(payload)
        payload_hash = hashlib.sha256(payload_bytes).hexdigest()
        reference = self._evidence_store.persist_payload(
            connection_id=connection_id,
            source_record_id=source_id,
            payload=payload_bytes,
            payload_hash=payload_hash,
        )
        return SourceRecord(
            source_record_type=SOURCE_TYPE,
            source_record_id=source_id,
            source_schema_version=SOURCE_SCHEMA_VERSION,
            payload_reference=reference,
            payload_hash=payload_hash,
            observed_at=_observed_at(payload),
        )


def _activity_id(payload: Mapping[str, object]) -> str:
    for key in ("activityId", "activity_id", "summaryId", "summary_id"):
        value = payload.get(key)
        if value is not None and str(value):
            return str(value)
    raise FitnessOSError(
        error_code="GARMIN_ACTIVITY_ID_MISSING",
        error_class=ErrorClass.VALIDATION,
        service="garmin_connector",
        operation="extract_completed_activity",
        correlation_id="provider-record",
        retryable=False,
        safe_message="Garmin completed activity did not contain a provider activity identifier.",
    )


def _observed_at(payload: Mapping[str, object]) -> datetime:
    for key in ("lastUpdatedAt", "last_updated_at", "startTimeInSeconds"):
        value = payload.get(key)
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, tz=UTC)
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
            except ValueError:
                continue
    return datetime.now(UTC)


def _stable_json(payload: Mapping[str, object]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _map_provider_error(exc: GarminClientError, *, connection_id: str) -> FitnessOSError:
    status = exc.status_code
    if status == 401:
        error_class, retryable, code = ErrorClass.AUTHENTICATION, False, "GARMIN_AUTHENTICATION"
    elif status == 403:
        error_class, retryable, code = ErrorClass.AUTHORIZATION, False, "GARMIN_AUTHORIZATION"
    elif status == 429:
        error_class, retryable, code = ErrorClass.RATE_LIMIT, True, "GARMIN_RATE_LIMIT"
    elif status is not None and 500 <= status <= 599:
        error_class, retryable, code = ErrorClass.DEPENDENCY, True, "GARMIN_DEPENDENCY"
    else:
        error_class, retryable, code = ErrorClass.DEPENDENCY, True, "GARMIN_PROVIDER_FAILURE"
    return FitnessOSError(
        error_code=code,
        error_class=error_class,
        service="garmin_connector",
        operation="fetch_completed_activities",
        correlation_id=connection_id,
        retryable=retryable,
        safe_message="Garmin provider request could not be completed.",
        details_reference=exc.diagnostic_reference,
    )
