"""Codex-backed executor for implementation-heavy autonomy tasks."""

from __future__ import annotations

import subprocess
from pathlib import Path

from .base import BaseExecutor, ExecutionResult, ExecutionTask

DEFAULT_CODEX_MODEL = 'gpt-5.3-codex'


class CodexExecutor(BaseExecutor):
    @property
    def name(self) -> str:
        return 'codex_executor'

    def run(self, task: ExecutionTask) -> ExecutionResult:
        if task.action != 'codex_task':
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

        prompt = str(task.payload.get('prompt') or '').strip()
        if not prompt:
            return ExecutionResult(
                success=False,
                status='missing_prompt',
                outcome={},
            )

        model = str(task.payload.get('model') or DEFAULT_CODEX_MODEL)
        command = ['codex', 'exec', '--yolo', '-m', model, prompt]

        try:
            result = subprocess.run(
                command,
                cwd=Path(task.repo_path),
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            return ExecutionResult(
                success=False,
                status='codex_failed',
                verification={
                    'command': 'codex exec --yolo',
                    'model': model,
                },
                outcome={
                    'returncode': exc.returncode,
                    'stdout': str(exc.output or '').strip(),
                    'stderr': str(exc.stderr or '').strip(),
                    'prompt': prompt,
                },
            )

        return ExecutionResult(
            success=True,
            status='completed',
            verification={
                'command': 'codex exec --yolo',
                'model': model,
            },
            outcome={
                'stdout': result.stdout.strip(),
                'stderr': result.stderr.strip(),
                'prompt': prompt,
            },
        )
