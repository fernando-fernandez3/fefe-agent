from pathlib import Path

from autonomy.models import Signal
from autonomy.sensors.base import BaseSensor, SensorContext, SensorResult


class ExampleSensor(BaseSensor):
    @property
    def name(self) -> str:
        return 'example_sensor'

    def collect(self, context: SensorContext) -> SensorResult:
        signal = Signal(
            id='sig_example',
            domain=context.domain,
            source_sensor=self.name,
            entity_type='repo',
            entity_key=str(context.repo_path),
            signal_type='example',
            signal_strength=0.5,
            evidence={'ok': True},
        )
        return SensorResult(sensor_name=self.name, signals=[signal])


def test_sensor_base_contract():
    sensor = ExampleSensor()
    result = sensor.collect(SensorContext(domain='code_projects', repo_path=Path('/tmp/repo')))
    assert result.sensor_name == 'example_sensor'
    assert result.signals[0].signal_type == 'example'
