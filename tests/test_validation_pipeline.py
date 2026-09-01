from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

import pytest

from packages.validation.contracts import (
    PIPELINE_ORDER,
    PipelineContext,
    StageResult,
    ValidationLayer,
)
from packages.validation.engine import PipelineConfigurationError, ValidationPipeline


@dataclass(frozen=True, slots=True)
class Processor:
    layer: ValidationLayer
    outcome: str = "test-pass"
    continue_processing: bool = True
    derived_payload: dict[str, object] | None = None
    processor_version: str = "1.0.0"

    def process(self, context: PipelineContext) -> StageResult:
        return StageResult(
            outcome=self.outcome,
            continue_processing=self.continue_processing,
            derived_payload=self.derived_payload,
        )


def _processors() -> list[Processor]:
    return [Processor(layer=layer) for layer in PIPELINE_ORDER]


def _context() -> PipelineContext:
    return PipelineContext(
        evidence_id=uuid4(),
        correlation_id="corr-test",
        source_payload_reference="object://immutable/source",
    )


def test_pipeline_executes_all_six_layers_in_mandated_order() -> None:
    pipeline = ValidationPipeline(_processors())

    result = pipeline.run(_context())

    assert result.completed is True
    assert tuple(stage.layer for stage in result.stages) == PIPELINE_ORDER


def test_pipeline_stops_without_interpreting_outcome_vocabulary() -> None:
    processors = _processors()
    processors[2] = Processor(
        layer=ValidationLayer.NORMALIZATION,
        outcome="externally-governed-stop-state",
        continue_processing=False,
    )
    pipeline = ValidationPipeline(processors)

    result = pipeline.run(_context())

    assert result.completed is False
    assert tuple(stage.layer for stage in result.stages) == PIPELINE_ORDER[:3]
    assert result.stages[-1].outcome == "externally-governed-stop-state"


def test_normalization_creates_derived_payload_without_mutating_source_reference() -> None:
    processors = _processors()
    processors[2] = Processor(
        layer=ValidationLayer.NORMALIZATION,
        derived_payload={"normalized_test_value": 42},
    )
    context = _context()

    result = ValidationPipeline(processors).run(context)

    assert context.derived_payload == {}
    assert result.final_context.derived_payload == {"normalized_test_value": 42}
    assert result.final_context.source_payload_reference == context.source_payload_reference


def test_pipeline_rejects_missing_required_layer() -> None:
    processors = _processors()[:-1]

    with pytest.raises(PipelineConfigurationError, match="consequential_use"):
        ValidationPipeline(processors)


def test_pipeline_rejects_duplicate_layer() -> None:
    processors = _processors()
    processors.append(Processor(layer=ValidationLayer.SCHEMA))

    with pytest.raises(PipelineConfigurationError, match="duplicate processor"):
        ValidationPipeline(processors)
