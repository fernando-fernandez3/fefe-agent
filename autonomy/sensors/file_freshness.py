"""File freshness sensor — reports how recently a doc/file/dir was modified."""

from __future__ import annotations

import time
from pathlib import Path

from autonomy.models import Signal
from .base import BaseSensor, SensorContext, SensorResult


RECENT_WINDOW_SECONDS = 7 * 24 * 3600
STALE_WINDOW_SECONDS = 30 * 24 * 3600


class FileFreshnessSensor(BaseSensor):
    @property
    def name(self) -> str:
        return "file_freshness"

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
                        id=f"{self.name}:missing_asset:{target}",
                        domain=context.domain,
                        source_sensor=self.name,
                        entity_type="doc",
                        entity_key=str(target),
                        signal_type="missing_asset",
                        signal_strength=0.6,
                        evidence={"locator": str(target)},
                    )
                ],
            )

        mtime = self._latest_mtime(target)
        now_epoch = int(context.metadata.get("now_epoch", time.time()))
        age_seconds = max(0, now_epoch - int(mtime))

        signal_type, strength = self._classify(age_seconds)
        return SensorResult(
            sensor_name=self.name,
            signals=[
                Signal(
                    id=f"{self.name}:{signal_type}:{target}",
                    domain=context.domain,
                    source_sensor=self.name,
                    entity_type="doc",
                    entity_key=str(target),
                    signal_type=signal_type,
                    signal_strength=strength,
                    evidence={
                        "locator": str(target),
                        "age_seconds": age_seconds,
                        "mtime_epoch": int(mtime),
                        "is_dir": target.is_dir(),
                    },
                )
            ],
        )

    @staticmethod
    def _classify(age_seconds: int) -> tuple[str, float]:
        if age_seconds >= STALE_WINDOW_SECONDS:
            return "doc_very_stale", min(1.0, 0.75 + age_seconds / (180 * 24 * 3600))
        if age_seconds >= RECENT_WINDOW_SECONDS:
            return "doc_stale", 0.55
        return "doc_recently_modified", 0.25

    @staticmethod
    def _latest_mtime(target: Path) -> float:
        if target.is_file():
            return target.stat().st_mtime

        latest = target.stat().st_mtime
        try:
            for child in target.rglob("*"):
                if child.is_file():
                    latest = max(latest, child.stat().st_mtime)
        except (PermissionError, OSError):
            pass
        return latest
