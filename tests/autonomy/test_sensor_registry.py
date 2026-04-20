import httpx

from autonomy.sensors.autoworkflow_status import AutoWorkflowStatusSensor
from autonomy.sensors.base import SensorContext
from autonomy.sensors.file_freshness import FileFreshnessSensor
from autonomy.sensors.registry import SensorRegistry
from autonomy.sensors.repo_health import RepoHealthSensor
from autonomy.sensors.system_status import SystemStatusSensor


class FakeResponse:
    def __init__(self, payload, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError('boom', request=None, response=None)

    def json(self):
        return self._payload


class FakeHttpClient:
    def __init__(self, payloads: dict[str, object]):
        self.payloads = payloads
        self.calls: list[str] = []

    def get(self, url: str, headers=None, timeout=None):
        self.calls.append(url)
        return FakeResponse(self.payloads[url])


def test_sensor_registry_default_maps_phase_a_asset_types():
    registry = SensorRegistry.default(
        autoworkflow_base_url='http://aw.local',
        autoworkflow_api_token='token-123',
    )

    assert registry.asset_types() == ['doc', 'repo', 'system', 'workflow']
    assert isinstance(registry.resolve('repo'), RepoHealthSensor)
    assert isinstance(registry.resolve('doc'), FileFreshnessSensor)
    assert isinstance(registry.resolve('system'), SystemStatusSensor)

    workflow_sensor = registry.resolve('workflow')
    assert isinstance(workflow_sensor, AutoWorkflowStatusSensor)
    assert workflow_sensor.base_url == 'http://aw.local'
    assert workflow_sensor.api_token == 'token-123'


def test_autoworkflow_status_sensor_emits_pending_failed_and_running_signals():
    base_url = 'http://aw.local'
    client = FakeHttpClient(
        {
            f'{base_url}/api/review-queue': [
                {'id': 'review_1', 'status': 'pending'},
                {'id': 'review_2', 'status': 'resolved'},
            ],
            f'{base_url}/api/workflows': [
                {'id': 'wf_failed', 'status': 'failed'},
                {'id': 'wf_running', 'status': 'running'},
                {'id': 'wf_done', 'status': 'completed'},
            ],
        }
    )
    sensor = AutoWorkflowStatusSensor(
        base_url=base_url,
        api_token='token-123',
        http_client=client,
    )

    result = sensor.collect(
        SensorContext(
            domain='code_projects',
            metadata={'locator': 'autoworkflow://embarka/competitor-gap-issues'},
        )
    )

    assert client.calls == [f'{base_url}/api/review-queue', f'{base_url}/api/workflows']
    signal_types = [signal.signal_type for signal in result.signals]
    assert signal_types == [
        'workflows_pending_review',
        'workflows_failed',
        'workflows_running',
    ]
    pending = result.signals[0]
    assert pending.evidence['pending_count'] == 1
    assert pending.evidence['item_ids'] == ['review_1']
