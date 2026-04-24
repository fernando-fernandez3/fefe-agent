import httpx

from autonomy.sensors.base import SensorContext
from autonomy.sensors.url_status import URLStatusSensor


class FakeResponse:
    def __init__(self, status_code: int = 200):
        self.status_code = status_code


class FakeHttpClient:
    def __init__(self, response=None, exc: Exception | None = None):
        self._response = response
        self._exc = exc
        self.calls: list[str] = []

    def get(self, url: str, follow_redirects=True, timeout=None):
        self.calls.append(url)
        if self._exc is not None:
            raise self._exc
        return self._response


def test_url_status_sensor_emits_site_healthy_for_2xx_response():
    client = FakeHttpClient(response=FakeResponse(status_code=200))
    sensor = URLStatusSensor(http_client=client)

    result = sensor.collect(
        SensorContext(domain='code_projects', metadata={'locator': 'https://embarka.ai'})
    )

    assert client.calls == ['https://embarka.ai']
    assert len(result.signals) == 1
    assert result.signals[0].signal_type == 'site_healthy'
    assert result.signals[0].evidence['status_code'] == 200


def test_url_status_sensor_emits_site_down_for_transport_error():
    client = FakeHttpClient(exc=httpx.ConnectError('boom'))
    sensor = URLStatusSensor(http_client=client)

    result = sensor.collect(
        SensorContext(domain='code_projects', metadata={'locator': 'https://embarka.ai'})
    )

    assert len(result.signals) == 1
    assert result.signals[0].signal_type == 'site_down'
    assert 'boom' in result.signals[0].evidence['error']


def test_url_status_sensor_emits_site_degraded_for_4xx_response():
    client = FakeHttpClient(response=FakeResponse(status_code=404))
    sensor = URLStatusSensor(http_client=client)

    result = sensor.collect(
        SensorContext(domain='code_projects', metadata={'locator': 'https://embarka.ai/missing'})
    )

    assert len(result.signals) == 1
    assert result.signals[0].signal_type == 'site_degraded'
    assert result.signals[0].evidence['status_code'] == 404