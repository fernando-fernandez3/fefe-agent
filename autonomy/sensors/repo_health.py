"""Repo health sensor for autonomy MVP."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tomllib
from pathlib import Path

from autonomy.models import Signal
from .base import BaseSensor, SensorContext, SensorResult

_FAILED_COUNT_RE = re.compile(r'(\d+)\s+failed\b', re.IGNORECASE)
_NEXT_JS_RE = re.compile(r'\bnext\b', re.IGNORECASE)
_GIT_STATUS_TIMEOUT_SECONDS = 5
_PYTEST_COLLECTION_TIMEOUT_SECONDS = 30


class RepoHealthSensor(BaseSensor):
    @property
    def name(self) -> str:
        return 'repo_health'

    def collect(self, context: SensorContext) -> SensorResult:
        if context.repo_path is None:
            raise ValueError('RepoHealthSensor requires repo_path')
        repo_path = Path(context.repo_path)

        signals: list[Signal] = []
        dirty_signal = self._check_dirty_worktree(context, repo_path)
        if dirty_signal is not None:
            signals.append(dirty_signal)

        command, metadata = self._detect_test_command(repo_path)
        if command is None:
            signals.append(self._build_missing_test_command_signal(context, repo_path, metadata))
            return SensorResult(sensor_name=self.name, signals=signals)

        if metadata.get('framework') == 'pytest':
            collect_signal = self._run_pytest_collection_check(context, repo_path, metadata)
            if collect_signal is not None:
                signals.append(collect_signal)

        if metadata.get('requires_browser_qa'):
            signals.append(
                Signal(
                    id=f'{self.name}:missing_browser_qa:{repo_path}',
                    domain=context.domain,
                    source_sensor=self.name,
                    entity_type='repo',
                    entity_key=str(repo_path),
                    signal_type='missing_browser_qa_signal',
                    signal_strength=0.55,
                    evidence={
                        'test_command': ' '.join(command),
                        'framework': metadata.get('framework', 'nextjs'),
                    },
                )
            )

        return SensorResult(sensor_name=self.name, signals=signals)

    def _check_dirty_worktree(self, context: SensorContext, repo_path: Path) -> Signal | None:
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=_GIT_STATUS_TIMEOUT_SECONDS,
            )
        except (FileNotFoundError, subprocess.SubprocessError, OSError):
            return None

        if result.returncode != 0:
            return None

        changed_files = [line for line in result.stdout.splitlines() if line.strip()]
        if not changed_files:
            return None

        return Signal(
            id=f'{self.name}:dirty_worktree:{repo_path}',
            domain=context.domain,
            source_sensor=self.name,
            entity_type='repo',
            entity_key=str(repo_path),
            signal_type='dirty_worktree',
            signal_strength=min(1.0, 0.2 * len(changed_files)),
            evidence={
                'changed_files': changed_files,
                'changed_count': len(changed_files),
            },
        )

    def _build_missing_test_command_signal(self, context: SensorContext, repo_path: Path, metadata: dict) -> Signal:
        evidence = {'repo_path': str(repo_path)}
        if metadata.get('reason'):
            evidence['reason'] = metadata['reason']
        if metadata.get('framework'):
            evidence['framework'] = metadata['framework']
        return Signal(
            id=f'{self.name}:missing_test_command:{repo_path}',
            domain=context.domain,
            source_sensor=self.name,
            entity_type='repo',
            entity_key=str(repo_path),
            signal_type='missing_test_command',
            signal_strength=0.45,
            evidence=evidence,
        )

    def _run_pytest_collection_check(self, context: SensorContext, repo_path: Path, metadata: dict) -> Signal | None:
        command = metadata['collect_command']
        try:
            result = subprocess.run(
                command,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=_PYTEST_COLLECTION_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            return Signal(
                id=f'{self.name}:test_collection_slow:{repo_path}',
                domain=context.domain,
                source_sensor=self.name,
                entity_type='repo',
                entity_key=str(repo_path),
                signal_type='test_collection_slow',
                signal_strength=0.35,
                evidence={
                    'test_command': ' '.join(command),
                    'timeout_seconds': _PYTEST_COLLECTION_TIMEOUT_SECONDS,
                    'check_mode': 'collect_only',
                },
            )
        except (FileNotFoundError, subprocess.SubprocessError, OSError):
            return self._build_missing_test_command_signal(
                context,
                repo_path,
                {'framework': 'pytest', 'reason': 'pytest_not_installed'},
            )

        if result.returncode == 0:
            return None

        combined_output = '\n'.join(part for part in (result.stdout.strip(), result.stderr.strip()) if part).strip()
        failing_count = self._extract_failing_count(combined_output)
        return Signal(
            id=f'{self.name}:failing_tests:{repo_path}',
            domain=context.domain,
            source_sensor=self.name,
            entity_type='repo',
            entity_key=str(repo_path),
            signal_type='failing_tests',
            signal_strength=min(1.0, 0.55 + (0.1 * failing_count)),
            evidence={
                'test_command': ' '.join(command),
                'returncode': result.returncode,
                'failing_count': failing_count,
                'output_excerpt': combined_output[:500],
                'check_mode': 'collect_only',
            },
        )

    def _detect_test_command(self, repo_path: Path) -> tuple[list[str] | None, dict]:
        if self._is_pytest_repo(repo_path):
            if shutil.which('pytest') is None:
                return None, {'framework': 'pytest', 'reason': 'pytest_not_installed'}
            return ['pytest', '-q'], {
                'framework': 'pytest',
                'requires_browser_qa': False,
                'collect_command': ['pytest', '--collect-only', '-q'],
            }

        package_json = repo_path / 'package.json'
        if not package_json.exists():
            return None, {}

        try:
            package_data = json.loads(package_json.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, OSError):
            return None, {}

        scripts = package_data.get('scripts') or {}
        test_script = str(scripts.get('test') or '').strip()
        if not test_script:
            return None, {}

        dependencies = {
            **(package_data.get('dependencies') or {}),
            **(package_data.get('devDependencies') or {}),
        }
        is_nextjs = 'next' in dependencies or bool(_NEXT_JS_RE.search(test_script))
        return ['npm', 'test', '--', '--runInBand'], {
            'framework': 'npm',
            'requires_browser_qa': is_nextjs,
        }

    @staticmethod
    def _is_pytest_repo(repo_path: Path) -> bool:
        if (repo_path / 'tests').exists() or (repo_path / 'pytest.ini').exists():
            return True

        pyproject_path = repo_path / 'pyproject.toml'
        if not pyproject_path.exists():
            return False

        try:
            pyproject_data = tomllib.loads(pyproject_path.read_text(encoding='utf-8'))
        except (tomllib.TOMLDecodeError, OSError):
            return False

        tool_config = pyproject_data.get('tool') or {}
        pytest_config = tool_config.get('pytest') or {}
        return 'ini_options' in pytest_config

    @staticmethod
    def _extract_failing_count(output: str) -> int:
        match = _FAILED_COUNT_RE.search(output or '')
        if match:
            return max(1, int(match.group(1)))
        return 1
