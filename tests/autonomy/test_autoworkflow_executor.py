import httpx

from autonomy.executors.autoworkflow_executor import AutoWorkflowExecutor
from autonomy.executors.base import ExecutionTask


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("boom", request=None, response=None)

    def json(self) -> dict:
        return self._payload


class FakeHttpClient:
    def __init__(self, response: FakeResponse | None = None, error: Exception | None = None):
        self.response = response or FakeResponse({"run_id": "run_123"})
        self.error = error
        self.calls: list[tuple[str, dict, dict]] = []

    def post(self, url: str, headers: dict | None = None, json: dict | None = None, timeout: float | None = None):
        self.calls.append((url, headers or {}, json or {}))
        if self.error is not None:
            raise self.error
        return self.response


def make_task(target: str | None) -> ExecutionTask:
    payload = {}
    if target is not None:
        payload["delegation_target"] = target
    return ExecutionTask(
        id="exec_aw",
        domain="code_projects",
        action="autoworkflow_run",
        idempotency_key="exec_aw:autoworkflow_run",
        payload=payload,
    )


def test_autoworkflow_executor_launches_workflow_and_returns_run_id():
    client = FakeHttpClient(response=FakeResponse({"run_id": "run_123", "status": "queued"}))
    executor = AutoWorkflowExecutor(
        base_url="http://127.0.0.1:8882",
        api_token="token-123",
        http_client=client,
    )

    result = executor.run(make_task("workflow_abc"))

    assert result.success is True
    assert result.status == "completed"
    assert result.outcome["run_id"] == "run_123"
    assert client.calls == [
        (
            "http://127.0.0.1:8882/api/workflows/workflow_abc/start",
            {"Accept": "application/json", "Authorization": "Bearer token-123"},
            {"execution_id": "exec_aw", "source": "hermes"},
        )
    ]


def test_autoworkflow_executor_returns_missing_target_when_delegation_target_missing():
    executor = AutoWorkflowExecutor(base_url="http://127.0.0.1:8882", api_token="token-123")

    result = executor.run(make_task(None))

    assert result.success is False
    assert result.status == "missing_delegation_target"


def test_autoworkflow_executor_handles_connection_errors_gracefully():
    client = FakeHttpClient(error=httpx.ConnectError("boom"))
    executor = AutoWorkflowExecutor(
        base_url="http://127.0.0.1:8882",
        api_token="token-123",
        http_client=client,
    )

    result = executor.run(make_task("workflow_abc"))

    assert result.success is False
    assert result.status == "autoworkflow_unreachable"
    assert "boom" in result.outcome["error"]
