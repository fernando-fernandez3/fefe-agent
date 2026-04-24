"""URL status sensor — reports whether a URL is reachable and healthy enough to matter."""
from __future__ import annotations

from typing import Any

import httpx

from autonomy.models import Signal
from .base import BaseSensor, SensorContext, SensorResult


class URLStatusSensor(BaseSensor):
    def __init__(
        self,
        *,
        http_client: httpx.Client | None = None,
        timeout_seconds: float = 10.0,
    ):
        self._client = http_client
        self.timeout_seconds = timeout_seconds

    @property
    def name(self) -> str:
        return "url_status"

    def collect(self, context: SensorContext) -> SensorResult:
        locator = context.metadata.get("locator")
        if not locator:
            return SensorResult(
                sensor_name=self.name,
                signals=[],
                metadata={"status": "missing_locator"},
            )

        metadata: dict[str, Any] = {"url": str(locator)}
        try:
            response = self._request(str(locator))
        except (httpx.HTTPError, OSError) as exc:
            metadata["status"] = "url_unreachable"
            metadata["error"] = str(exc)
            return SensorResult(
                sensor_name=self.name,
                signals=[
                    Signal(
                        id=f"{self.name}:site_down:{locator}",
                        domain=context.domain,
                        source_sensor=self.name,
                        entity_type="url",
                        entity_key=str(locator),
                        signal_type="site_down",
                        signal_strength=0.9,
                        evidence={"url": str(locator), "error": str(exc)},
                    )
                ],
                metadata=metadata,
            )

        status_code = response.status_code
        metadata["status_code"] = status_code
        if status_code >= 500:
            return SensorResult(
                sensor_name=self.name,
                signals=[
                    Signal(
                        id=f"{self.name}:site_down:{locator}",
                        domain=context.domain,
                        source_sensor=self.name,
                        entity_type="url",
                        entity_key=str(locator),
                        signal_type="site_down",
                        signal_strength=0.85,
                        evidence={"url": str(locator), "status_code": status_code},
                    )
                ],
                metadata=metadata,
            )
        if status_code >= 400:
            return SensorResult(
                sensor_name=self.name,
                signals=[
                    Signal(
                        id=f"{self.name}:site_degraded:{locator}",
                        domain=context.domain,
                        source_sensor=self.name,
                        entity_type="url",
                        entity_key=str(locator),
                        signal_type="site_degraded",
                        signal_strength=0.6,
                        evidence={"url": str(locator), "status_code": status_code},
                    )
                ],
                metadata=metadata,
            )

        return SensorResult(
            sensor_name=self.name,
            signals=[
                Signal(
                    id=f"{self.name}:site_healthy:{locator}",
                    domain=context.domain,
                    source_sensor=self.name,
                    entity_type="url",
                    entity_key=str(locator),
                    signal_type="site_healthy",
                    signal_strength=0.1,
                    evidence={"url": str(locator), "status_code": status_code},
                )
            ],
            metadata=metadata,
        )

    def _request(self, url: str) -> httpx.Response:
        if self._client is not None:
            return self._client.get(
                url, follow_redirects=True, timeout=self.timeout_seconds
            )

        with httpx.Client(timeout=self.timeout_seconds, follow_redirects=True) as client:
            return client.get(url)