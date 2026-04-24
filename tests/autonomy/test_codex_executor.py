from pathlib import Path
import subprocess

from autonomy.executors.base import ExecutionTask
from autonomy.executors.codex_executor import CodexExecutor


def test_codex_executor_runs_codex_task(monkeypatch, tmp_path):
    repo = tmp_path / 'repo'
    repo.mkdir()
    calls: list[dict] = []

    def fake_run(command, cwd=None, capture_output=None, text=None, check=None):
        calls.append(
            {
                'command': command,
                'cwd': cwd,
                'capture_output': capture_output,
                'text': text,
                'check': check,
            }
        )
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout='Implemented feature\n',
            stderr='warning: sandbox disabled\n',
        )

    monkeypatch.setattr(subprocess, 'run', fake_run)

    task = ExecutionTask(
        id='exec_1',
        domain='code_projects',
        action='codex_task',
        repo_path=Path(repo),
        idempotency_key='repo:codex:exec_1',
        payload={
            'prompt': 'Implement the failing test and run pytest.',
            'model': 'gpt-5.3-codex',
        },
    )

    result = CodexExecutor().run(task)

    assert result.success is True
    assert result.status == 'completed'
    assert result.verification['model'] == 'gpt-5.3-codex'
    assert result.outcome['stdout'] == 'Implemented feature'
    assert result.outcome['stderr'] == 'warning: sandbox disabled'
    assert calls == [
        {
            'command': ['codex', 'exec', '--yolo', '-m', 'gpt-5.3-codex', 'Implement the failing test and run pytest.'],
            'cwd': repo,
            'capture_output': True,
            'text': True,
            'check': True,
        }
    ]


def test_codex_executor_requires_repo_path():
    result = CodexExecutor().run(
        ExecutionTask(
            id='exec_2',
            domain='code_projects',
            action='codex_task',
            payload={'prompt': 'Fix the bug.'},
        )
    )

    assert result.success is False
    assert result.status == 'missing_repo_path'


def test_codex_executor_requires_prompt(tmp_path):
    result = CodexExecutor().run(
        ExecutionTask(
            id='exec_3',
            domain='code_projects',
            action='codex_task',
            repo_path=tmp_path,
            payload={},
        )
    )

    assert result.success is False
    assert result.status == 'missing_prompt'


def test_codex_executor_returns_failure_details(monkeypatch, tmp_path):
    def fake_run(command, cwd=None, capture_output=None, text=None, check=None):
        raise subprocess.CalledProcessError(
            returncode=42,
            cmd=command,
            stderr='codex failed hard\n',
            output='partial output\n',
        )

    monkeypatch.setattr(subprocess, 'run', fake_run)

    result = CodexExecutor().run(
        ExecutionTask(
            id='exec_4',
            domain='code_projects',
            action='codex_task',
            repo_path=tmp_path,
            payload={'prompt': 'Do the thing.'},
        )
    )

    assert result.success is False
    assert result.status == 'codex_failed'
    assert result.outcome['returncode'] == 42
    assert result.outcome['stderr'] == 'codex failed hard'
    assert result.outcome['stdout'] == 'partial output'
