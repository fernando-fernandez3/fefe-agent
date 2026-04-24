"""Base executor contracts for autonomy MVP."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class ExecutionTask:
    id: str
    domain: str
    action: str
    repo_path: Path | None = None
    side_effect_class: str = 'safe_local'
    idempotency_key: str = ''
    verification_plan: dict[str, Any] = field(default_factory=dict)
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ExecutionResult:
    success: bool
    status: str
    verification: dict[str, Any] = field(default_factory=dict)
    outcome: dict[str, Any] = field(default_factory=dict)


class BaseExecutor(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def run(self, task: ExecutionTask) -> ExecutionResult:
        raise NotImplementedError
