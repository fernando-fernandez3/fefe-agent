"""Safe local repo executor for autonomy MVP."""

from __future__ import annotations

import subprocess

from .base import BaseExecutor, ExecutionResult, ExecutionTask


class RepoExecutor(BaseExecutor):
    @property
    def name(self) -> str:
        return 'repo_executor'

    def run(self, task: ExecutionTask) -> ExecutionResult:
        if task.action != 'inspect_repo':
            return ExecutionResult(
                success=False,
                status='unsupported_action',
                outcome={'action': task.action},
            )

        if task.repo_path is None:
            return ExecutionResult(
                success=False,
                status='missing_repo_path',
                outcome={},
            )

        try:
            result = subprocess.run(
                ['git', 'status', '--short'],
                cwd=task.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            return ExecutionResult(
                success=False,
                status='git_failed',
                verification={'command': 'git status --short'},
                outcome={
                    'returncode': exc.returncode,
                    'stderr': exc.stderr.strip(),
                },
            )
        changed_files = [line for line in result.stdout.splitlines() if line.strip()]
        return ExecutionResult(
            success=True,
            status='completed',
            verification={'command': 'git status --short'},
            outcome={'changed_files': changed_files, 'changed_count': len(changed_files)},
        )
