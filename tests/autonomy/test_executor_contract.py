from pathlib import Path

from autonomy.executors import ExecutionTask, RepoExecutor


def test_repo_executor_inspects_repo(tmp_path):
    repo = tmp_path / 'repo'
    repo.mkdir()

    import subprocess

    subprocess.run(['git', 'init', '-b', 'main'], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=repo, check=True, capture_output=True, text=True)
    (repo / 'README.md').write_text('hello\n')
    subprocess.run(['git', 'add', 'README.md'], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(['git', 'commit', '-m', 'initial'], cwd=repo, check=True, capture_output=True, text=True)
    (repo / 'README.md').write_text('changed\n')

    task = ExecutionTask(
        id='task_1',
        domain='code_projects',
        action='inspect_repo',
        repo_path=Path(repo),
        idempotency_key='repo:inspect',
    )
    result = RepoExecutor().run(task)

    assert result.success is True
    assert result.status == 'completed'
    assert result.outcome['changed_count'] == 1


def test_repo_executor_rejects_unknown_action(tmp_path):
    task = ExecutionTask(
        id='task_2',
        domain='code_projects',
        action='delete_repo',
        repo_path=tmp_path,
    )
    result = RepoExecutor().run(task)
    assert result.success is False
    assert result.status == 'unsupported_action'


def test_repo_executor_inspect_repo_without_path_fails():
    result = RepoExecutor().run(ExecutionTask(id='exec_1', domain='code_projects', action='inspect_repo'))
    assert result.success is False
    assert result.status == 'missing_repo_path'


def test_repo_executor_returns_failed_result_for_non_git_directory(tmp_path):
    result = RepoExecutor().run(
        ExecutionTask(
            id='exec_1',
            domain='code_projects',
            action='inspect_repo',
            repo_path=tmp_path,
        )
    )

    assert result.success is False
    assert result.status == 'git_failed'
    assert result.outcome['returncode'] == 128
