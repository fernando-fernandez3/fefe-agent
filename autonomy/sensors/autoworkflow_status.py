"""AutoWorkflow status sensor — pulls pending reviews and workflow health from AW."""

from __future__ import annotations

import os
from typing import Any

import httpx

from autonomy.models import Signal
from .base import BaseSensor, SensorContext, SensorResult


class AutoWorkflowStatusSensor(BaseSensor):
    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_token: str | None = None,
        http_client: httpx.Client | None = None,
        timeout_seconds: float = 10.0,
    ):
        self.base_url = (
            base_url or os.getenv("AUTOWORKFLOW_BASE_URL") or "http://127.0.0.1:8882"
        ).rstrip("/")
        self.api_token = api_token or os.getenv("AUTOWORKFLOW_API_TOKEN") or ""
        self._client = http_client
        self.timeout_seconds = timeout_seconds

    @property
    def name(self) -> str:
        return "autoworkflow_status"

    def collect(self, context: SensorContext) -> SensorResult:
        entity_key = context.metadata.get("locator") or self.base_url
        signals: list[Signal] = []
        metadata: dict[str, Any] = {"base_url": self.base_url}

        try:
            review_items = self._fetch_json("/api/review-queue") or []
            workflows = self._fetch_json("/api/workflows") or []
        except (httpx.HTTPError, OSError) as exc:
            metadata["status"] = "autoworkflow_unreachable"
            metadata["error"] = str(exc)
            return SensorResult(sensor_name=self.name, signals=[], metadata=metadata)

        pending = [item for item in review_items if self._is_pending(item)]
        if pending:
            signals.append(
                Signal(
                    id=f"{self.name}:workflows_pending_review:{entity_key}",
                    domain=context.domain,
                    source_sensor=self.name,
                    entity_type="workflow",
                    entity_key=str(entity_key),
                    signal_type="workflows_pending_review",
                    signal_strength=min(1.0, 0.5 + 0.1 * len(pending)),
                    evidence={
                        "pending_count": len(pending),
                        "item_ids": [item.get("id") for item in pending[:10]],
                    },
                )
            )

        failed = [wf for wf in workflows if self._is_failed(wf)]
        if failed:
            signals.append(
                Signal(
                    id=f"{self.name}:workflows_failed:{entity_key}",
                    domain=context.domain,
                    source_sensor=self.name,
                    entity_type="workflow",
                    entity_key=str(entity_key),
                    signal_type="workflows_failed",
                    signal_strength=min(1.0, 0.7 + 0.1 * len(failed)),
                    evidence={
                        "failed_count": len(failed),
                        "workflow_ids": [wf.get("id") for wf in failed[:10]],
                    },
                )
            )

        running = [wf for wf in workflows if self._is_running(wf)]
        if running:
            signals.append(
                Signal(
                    id=f"{self.name}:workflows_running:{entity_key}",
                    domain=context.domain,
                    source_sensor=self.name,
                    entity_type="workflow",
                    entity_key=str(entity_key),
                    signal_type="workflows_running",
                    signal_strength=0.35,
                    evidence={
                        "running_count": len(running),
                        "workflow_ids": [wf.get("id") for wf in running[:10]],
                    },
                )
            )

        metadata["review_items_total"] = len(review_items)
        metadata["workflows_total"] = len(workflows)
        return SensorResult(sensor_name=self.name, signals=signals, metadata=metadata)

    def _fetch_json(self, path: str) -> Any:
        url = f"{self.base_url}{path}"
        headers = {"Accept": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"

        if self._client is not None:
            response = self._client.get(
                url, headers=headers, timeout=self.timeout_seconds
            )
            response.raise_for_status()
            return response.json()

        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()

    @staticmethod
    def _is_pending(item: dict) -> bool:
        status = str(item.get("status") or "").lower()
        return status in {"pending", "awaiting_review", "needs_review", "open"}

    @staticmethod
    def _is_failed(workflow: dict) -> bool:
        status = str(workflow.get("status") or workflow.get("state") or "").lower()
        return status in {"failed", "error", "errored"}

    @staticmethod
    def _is_running(workflow: dict) -> bool:
        status = str(workflow.get("status") or workflow.get("state") or "").lower()
        return status in {"running", "in_progress", "started"}
