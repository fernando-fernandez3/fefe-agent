"""Sensor registry — maps asset types to sensor instances for the desired-state sweep."""

from __future__ import annotations

from typing import Callable

from .autoworkflow_status import AutoWorkflowStatusSensor
from .base import BaseSensor
from .file_freshness import FileFreshnessSensor
from .repo_health import RepoHealthSensor
from .system_status import SystemStatusSensor


SensorFactory = Callable[[], BaseSensor]


class SensorRegistry:
    def __init__(self, sensors: dict[str, BaseSensor] | None = None):
        self._sensors: dict[str, BaseSensor] = dict(sensors or {})

    def register(self, asset_type: str, sensor: BaseSensor) -> None:
        self._sensors[asset_type] = sensor

    def resolve(self, asset_type: str) -> BaseSensor | None:
        return self._sensors.get(asset_type)

    def asset_types(self) -> list[str]:
        return sorted(self._sensors.keys())

    @classmethod
    def default(
        cls,
        *,
        autoworkflow_base_url: str | None = None,
        autoworkflow_api_token: str | None = None,
    ) -> "SensorRegistry":
        return cls(
            {
                "repo": RepoHealthSensor(),
                "workflow": AutoWorkflowStatusSensor(
                    base_url=autoworkflow_base_url,
                    api_token=autoworkflow_api_token,
                ),
                "doc": FileFreshnessSensor(),
                "system": SystemStatusSensor(),
            }
        )
