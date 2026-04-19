import time
from pathlib import Path

import pytest

from autonomy.sensors import RepoGitStateSensor, SensorContext


def git(repo: Path, *args: str) -> None:
    import subprocess

    subprocess.run(['git', *args], cwd=repo, check=True, capture_output=True, text=True)


def git_output(repo: Path, *args: str) -> str:
    import subprocess

    result = subprocess.run(['git', *args], cwd=repo, check=True, capture_output=True, text=True)
    return result.stdout


def setup_repo(tmp_path: Path) -> Path:
    repo = tmp_path / 'repo'
    repo.mkdir()
    git(repo, 'init', '-b', 'main')
    git(repo, 'config', 'user.email', 'test@example.com')
    git(repo, 'config', 'user.name', 'Test User')
    (repo / 'README.md').write_text('hello\n')
    git(repo, 'add', 'README.md')
    git(repo, 'commit', '-m', 'initial')
    return repo


def test_git_state_sensor_detects_dirty_worktree(tmp_path):
    repo = setup_repo(tmp_path)
    (repo / 'README.md').write_text('changed\n')

    sensor = RepoGitStateSensor()
    result = sensor.collect(SensorContext(domain='code_projects', repo_path=repo))

    signal_types = {signal.signal_type for signal in result.signals}
    assert 'dirty_worktree' in signal_types


def test_git_state_sensor_detects_stale_branch(tmp_path):
    repo = setup_repo(tmp_path)
    git(repo, 'checkout', '-b', 'feature/stale')
    commit_epoch = int(git_output(repo, 'log', '-1', '--format=%ct').strip())
    stale_now = commit_epoch + (8 * 24 * 3600)

    sensor = RepoGitStateSensor()
    result = sensor.collect(
        SensorContext(
            domain='code_projects',
            repo_path=repo,
            metadata={'now_epoch': stale_now, 'stale_branch_after_seconds': 7 * 24 * 3600},
        )
    )

    signal_types = {signal.signal_type for signal in result.signals}
    assert 'stale_branch' in signal_types


def test_git_state_sensor_requires_repo_path():
    sensor = RepoGitStateSensor()

    with pytest.raises(ValueError, match='requires repo_path'):
        sensor.collect(SensorContext(domain='code_projects'))


def test_git_state_sensor_handles_non_git_directory(tmp_path):
    sensor = RepoGitStateSensor()

    result = sensor.collect(SensorContext(domain='code_projects', repo_path=tmp_path))

    assert result.signals == []
    assert result.metadata['status'] == 'git_failed'
