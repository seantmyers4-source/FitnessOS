from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True, slots=True)
class GarminFieldMapping:
    provider_field: str
    provider_meaning: str
    provider_unit: str | None
    timestamp_semantics: str | None
    normalized_target_reference: str
    mapping_version: str


MAPPING_VERSION: Final = "garmin.completed_activity.mapping.v1"

COMPLETED_ACTIVITY_MAPPING: Final[tuple[GarminFieldMapping, ...]] = (
    GarminFieldMapping(
        "activityId",
        "provider activity identity",
        None,
        None,
        "external_activity_id",
        MAPPING_VERSION,
    ),
    GarminFieldMapping(
        "activityType",
        "provider activity type",
        None,
        None,
        "activity_type_candidate",
        MAPPING_VERSION,
    ),
    GarminFieldMapping(
        "startTimeInSeconds",
        "activity start",
        "unix_seconds",
        "provider-recorded start",
        "start_at_candidate",
        MAPPING_VERSION,
    ),
    GarminFieldMapping(
        "durationInSeconds",
        "elapsed duration",
        "seconds",
        None,
        "duration_seconds_candidate",
        MAPPING_VERSION,
    ),
    GarminFieldMapping(
        "distanceInMeters",
        "activity distance",
        "meters",
        None,
        "distance_meters_candidate",
        MAPPING_VERSION,
    ),
    GarminFieldMapping(
        "averageHeartRateInBeatsPerMinute",
        "average heart rate",
        "bpm",
        None,
        "average_heart_rate_bpm_candidate",
        MAPPING_VERSION,
    ),
    GarminFieldMapping(
        "averageSpeedInMetersPerSecond",
        "average speed",
        "m/s",
        None,
        "average_speed_mps_candidate",
        MAPPING_VERSION,
    ),
    GarminFieldMapping(
        "deviceName",
        "recording device label",
        None,
        None,
        "external_device_label",
        MAPPING_VERSION,
    ),
)
