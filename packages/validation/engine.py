from __future__ import annotations

from collections.abc import Iterable

from packages.validation.contracts import (
    PIPELINE_ORDER,
    PipelineContext,
    PipelineResult,
    StageExecutionResult,
    StageProcessor,
    ValidationLayer,
)


class PipelineConfigurationError(ValueError):
    """Raised when processors do not satisfy the required pipeline structure."""


class ValidationPipeline:
    """Runs the six mandated layers without defining their domain semantics."""

    def __init__(self, processors: Iterable[StageProcessor]) -> None:
        processor_map: dict[ValidationLayer, StageProcessor] = {}
        for processor in processors:
            if processor.layer in processor_map:
                raise PipelineConfigurationError(
                    f"duplicate processor for layer {processor.layer.value}"
                )
            processor_map[processor.layer] = processor

        missing = [layer.value for layer in PIPELINE_ORDER if layer not in processor_map]
        if missing:
            raise PipelineConfigurationError(f"missing processors: {', '.join(missing)}")

        self._processors = processor_map

    def run(self, context: PipelineContext) -> PipelineResult:
        current = context
        executions: list[StageExecutionResult] = []

        for layer in PIPELINE_ORDER:
            processor = self._processors[layer]
            result = processor.process(current)
            executions.append(
                StageExecutionResult(
                    layer=layer,
                    processor_version=processor.processor_version,
                    outcome=result.outcome,
                    continue_processing=result.continue_processing,
                    rule_reference=result.rule_reference,
                    details_reference=result.details_reference,
                )
            )

            if result.derived_payload is not None:
                current = current.with_derived_payload(result.derived_payload)

            if not result.continue_processing:
                return PipelineResult(
                    evidence_id=context.evidence_id,
                    correlation_id=context.correlation_id,
                    completed=False,
                    final_context=current,
                    stages=tuple(executions),
                )

        return PipelineResult(
            evidence_id=context.evidence_id,
            correlation_id=context.correlation_id,
            completed=True,
            final_context=current,
            stages=tuple(executions),
        )
