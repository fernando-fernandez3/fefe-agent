"""System status sensor — reports whether an arbitrary system asset exists and is accessible."""

from __future__ import annotations

from pathlib import Path

from autonomy.models import Signal
from .base import BaseSensor, SensorContext, SensorResult


class SystemStatusSensor(BaseSensor):
    @property
    def name(self) -> str:
        return "system_status"

    def collect(self, context: SensorContext) -> SensorResult:
        locator = context.metadata.get("locator") or (
            str(context.repo_path) if context.repo_path else None
        )
        if not locator:
            return SensorResult(
                sensor_name=self.name,
                signals=[],
                metadata={"status": "missing_locator"},
            )

        target = Path(locator)
        if not target.exists():
            return SensorResult(
                sensor_name=self.name,
                signals=[
                    Signal(
                        id=f"{self.name}:system_missing:{target}",
                        domain=context.domain,
                        source_sensor=self.name,
                        entity_type="system",
                        entity_key=str(target),
                        signal_type="system_missing",
                        signal_strength=0.7,
                        evidence={"locator": str(target)},
                    )
                ],
            )

        return SensorResult(
            sensor_name=self.name,
            signals=[
                Signal(
                    id=f"{self.name}:system_present:{target}",
                    domain=context.domain,
                    source_sensor=self.name,
                    entity_type="system",
                    entity_key=str(target),
                    signal_type="system_present",
                    signal_strength=0.1,
                    evidence={
                        "locator": str(target),
                        "is_dir": target.is_dir(),
                    },
                )
            ],
        )
