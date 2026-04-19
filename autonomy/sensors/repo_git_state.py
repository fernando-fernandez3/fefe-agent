"""Repo git-state sensor for autonomy MVP."""

from __future__ import annotations

import subprocess
from pathlib import Path

from autonomy.models import Signal
from .base import BaseSensor, SensorContext, SensorResult


class RepoGitStateSensor(BaseSensor):
    @property
    def name(self) -> str:
        return 'repo_git_state'

    def collect(self, context: SensorContext) -> SensorResult:
        if context.repo_path is None:
            raise ValueError('RepoGitStateSensor requires repo_path')
        repo_path = Path(context.repo_path)

        try:
            status_output = self._run_git(repo_path, 'status', '--porcelain', '--branch')
        except subprocess.CalledProcessError as exc:
            return SensorResult(
                sensor_name=self.name,
                signals=[],
                metadata={
                    'status': 'git_failed',
                    'command': exc.cmd,
                    'returncode': exc.returncode,
                    'stderr': exc.stderr.strip(),
                },
            )

        lines = [line for line in status_output.splitlines() if line.strip()]
        signals: list[Signal] = []

        branch_line = lines[0] if lines and lines[0].startswith('##') else ''
        branch_name = branch_line[2:].strip().split('...')[0] if branch_line else 'unknown'
        worktree_lines = [line for line in lines if not line.startswith('##')]

        if worktree_lines:
            signals.append(
                Signal(
                    id=f'{self.name}:dirty_worktree:{repo_path}',
                    domain=context.domain,
                    source_sensor=self.name,
                    entity_type='repo',
                    entity_key=str(repo_path),
                    signal_type='dirty_worktree',
                    signal_strength=min(1.0, 0.2 * len(worktree_lines)),
                    evidence={
                        'branch': branch_name,
                        'changed_files': worktree_lines,
                        'changed_count': len(worktree_lines),
                    },
                )
            )

        if 'ahead ' in branch_line or 'behind ' in branch_line:
            signals.append(
                Signal(
                    id=f'{self.name}:ahead_behind:{repo_path}',
                    domain=context.domain,
                    source_sensor=self.name,
                    entity_type='repo',
                    entity_key=str(repo_path),
                    signal_type='ahead_or_behind_remote',
                    signal_strength=0.7,
                    evidence={'branch': branch_name, 'branch_line': branch_line},
                )
            )

        if branch_name not in {'main', 'master', 'unknown'}:
            commit_epoch = int(self._run_git(repo_path, 'log', '-1', '--format=%ct').strip())
            now_epoch = int(context.metadata.get('now_epoch', commit_epoch))
            age_seconds = max(0, now_epoch - commit_epoch)
            if age_seconds >= int(context.metadata.get('stale_branch_after_seconds', 7 * 24 * 3600)):
                signals.append(
                    Signal(
                        id=f'{self.name}:stale_branch:{repo_path}',
                        domain=context.domain,
                        source_sensor=self.name,
                        entity_type='repo',
                        entity_key=str(repo_path),
                        signal_type='stale_branch',
                        signal_strength=min(1.0, age_seconds / (14 * 24 * 3600)),
                        evidence={
                            'branch': branch_name,
                            'age_seconds': age_seconds,
                        },
                    )
                )

        return SensorResult(sensor_name=self.name, signals=signals)

    def _run_git(self, repo_path: Path, *args: str) -> str:
        result = subprocess.run(
            ['git', *args],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
