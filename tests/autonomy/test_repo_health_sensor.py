from pathlib import Path
import subprocess

import pytest

from autonomy.sensors.repo_health import RepoHealthSensor
from autonomy.sensors.base import SensorContext


def test_repo_health_sensor_emits_missing_test_command_signal(tmp_path):
    repo = tmp_path / 'repo'
    repo.mkdir()

    result = RepoHealthSensor().collect(SensorContext(domain='code_projects', repo_path=repo))

    assert len(result.signals) == 1
    signal = result.signals[0]
    assert signal.signal_type == 'missing_test_command'
    assert signal.entity_key == str(repo)


def test_repo_health_sensor_emits_failing_tests_signal(monkeypatch, tmp_path):
    repo = tmp_path / 'repo'
    repo.mkdir()
    (repo / 'tests').mkdir()

    def fake_run(command, cwd=None, capture_output=None, text=None, timeout=None):
        return subprocess.CompletedProcess(
            args=command,
            returncode=1,
            stdout='2 failed, 5 passed in 1.23s\n',
            stderr='',
        )

    monkeypatch.setattr(subprocess, 'run', fake_run)

    result = RepoHealthSensor().collect(SensorContext(domain='code_projects', repo_path=repo))

    assert len(result.signals) == 1
    signal = result.signals[0]
    assert signal.signal_type == 'failing_tests'
    assert signal.evidence['failing_count'] == 2
    assert signal.evidence['test_command'] == 'pytest -q'


def test_repo_health_sensor_returns_no_signal_for_passing_tests(monkeypatch, tmp_path):
    repo = tmp_path / 'repo'
    repo.mkdir()
    (repo / 'tests').mkdir()

    def fake_run(command, cwd=None, capture_output=None, text=None, timeout=None):
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout='7 passed in 0.55s\n',
            stderr='',
        )

    monkeypatch.setattr(subprocess, 'run', fake_run)

    result = RepoHealthSensor().collect(SensorContext(domain='code_projects', repo_path=repo))

    assert result.signals == []


@pytest.mark.parametrize('stdout, stderr', [
    ('', 'ERROR collecting tests/test_app.py\n'),
    ('no tests ran in 0.01s\n', ''),
])
def test_repo_health_sensor_still_flags_failures_without_failed_count(monkeypatch, tmp_path, stdout, stderr):
    repo = tmp_path / 'repo'
    repo.mkdir()
    (repo / 'tests').mkdir()

    def fake_run(command, cwd=None, capture_output=None, text=None, timeout=None):
        return subprocess.CompletedProcess(
            args=command,
            returncode=2,
            stdout=stdout,
            stderr=stderr,
        )

    monkeypatch.setattr(subprocess, 'run', fake_run)

    result = RepoHealthSensor().collect(SensorContext(domain='code_projects', repo_path=repo))

    assert len(result.signals) == 1
    signal = result.signals[0]
    assert signal.signal_type == 'failing_tests'
    assert signal.evidence['failing_count'] >= 1


def test_repo_health_sensor_detects_package_json_test_script(monkeypatch, tmp_path):
    repo = tmp_path / 'repo'
    repo.mkdir()
    (repo / 'package.json').write_text('{"scripts": {"test": "vitest run"}}', encoding='utf-8')

    def fake_run(command, cwd=None, capture_output=None, text=None, timeout=None):
        return subprocess.CompletedProcess(
            args=command,
            returncode=1,
            stdout='3 failed, 9 passed\n',
            stderr='',
        )

    monkeypatch.setattr(subprocess, 'run', fake_run)

    result = RepoHealthSensor().collect(SensorContext(domain='code_projects', repo_path=repo))

    assert len(result.signals) == 1
    signal = result.signals[0]
    assert signal.signal_type == 'failing_tests'
    assert signal.evidence['test_command'] == 'npm test -- --runInBand'
    assert signal.evidence['failing_count'] == 3


@pytest.mark.parametrize(
    'package_json, expected_signal, expected_command',
    [
        ('{"scripts": {"lint": "eslint ."}}', 'missing_test_command', None),
        ('{"scripts": {"test": "next test"}, "dependencies": {"next": "15.0.0"}}', 'missing_browser_qa_signal', 'npm test -- --runInBand'),
    ],
)
def test_repo_health_sensor_handles_javascript_repo_health_cases(monkeypatch, tmp_path, package_json, expected_signal, expected_command):
    repo = tmp_path / 'repo'
    repo.mkdir()
    (repo / 'package.json').write_text(package_json, encoding='utf-8')

    def fake_run(command, cwd=None, capture_output=None, text=None, timeout=None):
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout='all good\n',
            stderr='',
        )

    monkeypatch.setattr(subprocess, 'run', fake_run)

    result = RepoHealthSensor().collect(SensorContext(domain='code_projects', repo_path=repo))

    assert len(result.signals) == 1
    signal = result.signals[0]
    assert signal.signal_type == expected_signal
    if expected_command:
        assert signal.evidence['test_command'] == expected_command
