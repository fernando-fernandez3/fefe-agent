"""AutoWorkflow executor for delegated repeatable workflows."""
from __future__ import annotations

import os
from typing import Any

import httpx

from .base import BaseExecutor, ExecutionResult, ExecutionTask


class AutoWorkflowExecutor(BaseExecutor):
    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_token: str | None = None,
        http_client: httpx.Client | Any | None = None,
        timeout_seconds: float = 15.0,
    ):
        self.base_url = (base_url or os.getenv("AUTOWORKFLOW_BASE_URL") or "http://127.0.0.1:8882").rstrip("/")
        self.api_token = api_token or os.getenv("AUTOWORKFLOW_API_TOKEN") or ""
        self._client = http_client
        self.timeout_seconds = timeout_seconds

    @property
    def name(self) -> str:
        return "autoworkflow_executor"

    def run(self, task: ExecutionTask) -> ExecutionResult:
        if task.action != "autoworkflow_run":
            return ExecutionResult(
                success=False,
                status="unsupported_action",
                outcome={"action": task.action},
            )

        target = str(task.payload.get("delegation_target") or "").strip()
        if not target:
            return ExecutionResult(
                success=False,
                status="missing_delegation_target",
                outcome={},
            )

        url = self._launch_url(target)
        headers = {"Accept": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        payload = {"execution_id": task.id, "source": "hermes"}

        try:
            response = self._post(url, headers=headers, json=payload)
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, OSError, ValueError) as exc:
            return ExecutionResult(
                success=False,
                status="autoworkflow_unreachable",
                verification={"url": url, "target": target},
                outcome={"error": str(exc), "target": target},
            )

        run_id = str(body.get("run_id") or body.get("id") or "").strip()
        if not run_id:
            return ExecutionResult(
                success=False,
                status="missing_run_id",
                verification={"url": url, "target": target},
                outcome={"response": body, "target": target},
            )

        return ExecutionResult(
            success=True,
            status="completed",
            verification={"url": url, "target": target},
            outcome={"run_id": run_id, "response": body, "target": target},
        )

    def _post(self, url: str, *, headers: dict[str, str], json: dict[str, Any]):
        if self._client is not None:
            return self._client.post(url, headers=headers, json=json, timeout=self.timeout_seconds)
        with httpx.Client(timeout=self.timeout_seconds) as client:
            return client.post(url, headers=headers, json=json)

    def _launch_url(self, target: str) -> str:
        if target.startswith("definition:"):
            definition_id = target.split(":", 1)[1].strip()
            return f"{self.base_url}/api/workflow-definitions/{definition_id}/launch"
        cleaned = target.removeprefix("autoworkflow://").strip("/")
        workflow_id = cleaned.split("/")[-1]
        return f"{self.base_url}/api/workflows/{workflow_id}/start"
