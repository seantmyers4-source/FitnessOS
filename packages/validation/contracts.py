from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol
from uuid import UUID


class ValidationLayer(StrEnum):
    """Ordered validation layers mandated by the FitnessOS engineering handoff."""

    TRANSPORT_INTEGRITY = "transport_integrity"
    SCHEMA = "schema"
    NORMALIZATION = "normalization"
    SEMANTIC_PLAUSIBILITY = "semantic_plausibility"
    AUTHORITY_RECONCILIATION = "authority_reconciliation"
    CONSEQUENTIAL_USE = "consequential_use"


PIPELINE_ORDER: tuple[ValidationLayer, ...] = (
    ValidationLayer.TRANSPORT_INTEGRITY,
    ValidationLayer.SCHEMA,
    ValidationLayer.NORMALIZATION,
    ValidationLayer.SEMANTIC_PLAUSIBILITY,
    ValidationLayer.AUTHORITY_RECONCILIATION,
    ValidationLayer.CONSEQUENTIAL_USE,
)


@dataclass(frozen=True, slots=True)
class PipelineContext:
    """Immutable references passed through the pipeline; raw evidence is never modified."""

    evidence_id: UUID
    correlation_id: str
    source_payload_reference: str
    source_metadata: Mapping[str, str] = field(default_factory=dict)
    derived_payload: Mapping[str, object] = field(default_factory=dict)

    def with_derived_payload(self, payload: Mapping[str, object]) -> PipelineContext:
        return PipelineContext(
            evidence_id=self.evidence_id,
            correlation_id=self.correlation_id,
            source_payload_reference=self.source_payload_reference,
            source_metadata=self.source_metadata,
            derived_payload=dict(payload),
        )


@dataclass(frozen=True, slots=True)
class StageResult:
    """Processor result using externally supplied outcome semantics."""

    outcome: str
    continue_processing: bool
    rule_reference: str | None = None
    details_reference: str | None = None
    derived_payload: Mapping[str, object] | None = None


class StageProcessor(Protocol):
    """Implementation contract for one pipeline layer."""

    @property
    def layer(self) -> ValidationLayer: ...

    @property
    def processor_version(self) -> str: ...

    def process(self, context: PipelineContext) -> StageResult: ...


@dataclass(frozen=True, slots=True)
class StageExecutionResult:
    layer: ValidationLayer
    processor_version: str
    outcome: str
    continue_processing: bool
    rule_reference: str | None
    details_reference: str | None


@dataclass(frozen=True, slots=True)
class PipelineResult:
    evidence_id: UUID
    correlation_id: str
    completed: bool
    final_context: PipelineContext
    stages: tuple[StageExecutionResult, ...]
