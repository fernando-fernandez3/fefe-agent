"""Base contracts for autonomy sensors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from autonomy.models import Signal


@dataclass(slots=True)
class SensorContext:
    domain: str
    repo_path: Path | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SensorResult:
    sensor_name: str
    signals: list[Signal]
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseSensor(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def collect(self, context: SensorContext) -> SensorResult:
        raise NotImplementedError
