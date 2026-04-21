from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import time

import pytest

from autonomy.sensors.base import SensorContext
from autonomy.sensors.repo_health import RepoHealthSensor


def test_repo_health_sensor_emits_missing_test_command_signal(tmp_path):
    repo = tmp_path / 'repo'
    repo.mkdir()

    result = RepoHealthSensor().collect(SensorContext(domain='code_projects', repo_path=repo))

    assert len(result.signals) == 1
    signal = result.signals[0]
    assert signal.signal_type == 'missing_test_command'
    assert signal.entity_key == str(repo)


def test_repo_health_sensor_returns_quickly_for_repo_with_no_tests(tmp_path):
    repo = tmp_path / 'repo'
    repo.mkdir()

    started = time.monotonic()
    result = RepoHealthSensor().collect(SensorContext(domain='code_projects', repo_path=repo))
    elapsed = time.monotonic() - started

    assert elapsed < 5
    assert [signal.signal_type for signal in result.signals] == ['missing_test_command']


def test_repo_health_sensor_does_not_execute_full_test_suite(monkeypatch, tmp_path):
    repo = tmp_path / 'repo'
    repo.mkdir()
    (repo / 'tests').mkdir()

    commands: list[list[str]] = []

    def fake_run(command, cwd=None, capture_output=None, text=None, timeout=None, check=False):
        commands.append(command)
        if command == ['git', 'status', '--porcelain']:
            return subprocess.CompletedProcess(args=command, returncode=0, stdout='', stderr='')
        if command == ['pytest', '--collect-only', '-q']:
            return subprocess.CompletedProcess(args=command, returncode=0, stdout='no tests collected\n', stderr='')
        raise AssertionError(f'unexpected command: {command}')

    monkeypatch.setattr(subprocess, 'run', fake_run)
    monkeypatch.setattr(shutil, 'which', lambda name: '/usr/bin/pytest' if name == 'pytest' else None)

    result = RepoHealthSensor().collect(SensorContext(domain='code_projects', repo_path=repo))

    assert result.signals == []
    assert ['pytest', '-q'] not in commands
    assert ['pytest', '--collect-only', '-q'] in commands


def test_repo_health_sensor_emits_test_collection_slow_signal_when_collection_times_out(monkeypatch, tmp_path):
    repo = tmp_path / 'repo'
    repo.mkdir()
    (repo / 'tests').mkdir()

    def fake_run(command, cwd=None, capture_output=None, text=None, timeout=None, check=False):
        if command == ['git', 'status', '--porcelain']:
            return subprocess.CompletedProcess(args=command, returncode=0, stdout='', stderr='')
        if command == ['pytest', '--collect-only', '-q']:
            raise subprocess.TimeoutExpired(command, timeout)
        raise AssertionError(f'unexpected command: {command}')

    monkeypatch.setattr(subprocess, 'run', fake_run)
    monkeypatch.setattr(shutil, 'which', lambda name: '/usr/bin/pytest' if name == 'pytest' else None)

    result = RepoHealthSensor().collect(SensorContext(domain='code_projects', repo_path=repo))

    assert len(result.signals) == 1
    signal = result.signals[0]
    assert signal.signal_type == 'test_collection_slow'
    assert signal.evidence['test_command'] == 'pytest --collect-only -q'
    assert signal.evidence['timeout_seconds'] == 30


def test_repo_health_sensor_handles_missing_pytest_gracefully(monkeypatch, tmp_path):
    repo = tmp_path / 'repo'
    repo.mkdir()
    (repo / 'tests').mkdir()

    commands: list[list[str]] = []

    def fake_run(command, cwd=None, capture_output=None, text=None, timeout=None, check=False):
        commands.append(command)
        if command == ['git', 'status', '--porcelain']:
            return subprocess.CompletedProcess(args=command, returncode=0, stdout='', stderr='')
        raise AssertionError(f'unexpected command: {command}')

    monkeypatch.setattr(subprocess, 'run', fake_run)
    monkeypatch.setattr(shutil, 'which', lambda name: None)

    result = RepoHealthSensor().collect(SensorContext(domain='code_projects', repo_path=repo))

    assert len(result.signals) == 1
    signal = result.signals[0]
    assert signal.signal_type == 'missing_test_command'
    assert signal.evidence['reason'] == 'pytest_not_installed'
    assert ['pytest', '--collect-only', '-q'] not in commands


def test_repo_health_sensor_emits_failing_tests_signal_for_collection_errors(monkeypatch, tmp_path):
    repo = tmp_path / 'repo'
    repo.mkdir()
    (repo / 'tests').mkdir()

    def fake_run(command, cwd=None, capture_output=None, text=None, timeout=None, check=False):
        if command == ['git', 'status', '--porcelain']:
            return subprocess.CompletedProcess(args=command, returncode=0, stdout='', stderr='')
        if command == ['pytest', '--collect-only', '-q']:
            return subprocess.CompletedProcess(
                args=command,
                returncode=2,
                stdout='',
                stderr='ERROR collecting tests/test_app.py\nSyntaxError: invalid syntax\n',
            )
        raise AssertionError(f'unexpected command: {command}')

    monkeypatch.setattr(subprocess, 'run', fake_run)
    monkeypatch.setattr(shutil, 'which', lambda name: '/usr/bin/pytest' if name == 'pytest' else None)

    result = RepoHealthSensor().collect(SensorContext(domain='code_projects', repo_path=repo))

    assert len(result.signals) == 1
    signal = result.signals[0]
    assert signal.signal_type == 'failing_tests'
    assert signal.evidence['test_command'] == 'pytest --collect-only -q'
    assert signal.evidence['check_mode'] == 'collect_only'


@pytest.mark.parametrize(
    'package_json, expected_signal',
    [
        ('{"scripts": {"lint": "eslint ."}}', 'missing_test_command'),
        ('{"scripts": {"test": "next test"}, "dependencies": {"next": "15.0.0"}}', 'missing_browser_qa_signal'),
    ],
)
def test_repo_health_sensor_handles_javascript_repo_health_cases(tmp_path, package_json, expected_signal):
    repo = tmp_path / 'repo'
    repo.mkdir()
    (repo / 'package.json').write_text(package_json, encoding='utf-8')

    result = RepoHealthSensor().collect(SensorContext(domain='code_projects', repo_path=repo))

    assert len(result.signals) == 1
    signal = result.signals[0]
    assert signal.signal_type == expected_signal
