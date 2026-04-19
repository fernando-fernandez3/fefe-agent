"""Repo health sensor for autonomy MVP."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from autonomy.models import Signal
from .base import BaseSensor, SensorContext, SensorResult

_FAILED_COUNT_RE = re.compile(r'(\d+)\s+failed\b', re.IGNORECASE)
_NEXT_JS_RE = re.compile(r'\bnext\b', re.IGNORECASE)


class RepoHealthSensor(BaseSensor):
    @property
    def name(self) -> str:
        return 'repo_health'

    def collect(self, context: SensorContext) -> SensorResult:
        if context.repo_path is None:
            raise ValueError('RepoHealthSensor requires repo_path')
        repo_path = Path(context.repo_path)

        command, metadata = self._detect_test_command(repo_path)
        if command is None:
            return SensorResult(
                sensor_name=self.name,
                signals=[
                    Signal(
                        id=f'{self.name}:missing_test_command:{repo_path}',
                        domain=context.domain,
                        source_sensor=self.name,
                        entity_type='repo',
                        entity_key=str(repo_path),
                        signal_type='missing_test_command',
                        signal_strength=0.45,
                        evidence={'repo_path': str(repo_path)},
                    )
                ],
            )

        result = subprocess.run(
            command,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=120,
        )
        combined_output = '\n'.join(part for part in (result.stdout.strip(), result.stderr.strip()) if part).strip()

        if result.returncode == 0:
            if metadata.get('requires_browser_qa'):
                return SensorResult(
                    sensor_name=self.name,
                    signals=[
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
                    ],
                )
            return SensorResult(sensor_name=self.name, signals=[])

        failing_count = self._extract_failing_count(combined_output)
        return SensorResult(
            sensor_name=self.name,
            signals=[
                Signal(
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
                    },
                )
            ],
        )

    def _detect_test_command(self, repo_path: Path) -> tuple[list[str] | None, dict]:
        if (repo_path / 'tests').exists() or (repo_path / 'pytest.ini').exists() or (repo_path / 'pyproject.toml').exists():
            return ['pytest', '-q'], {'framework': 'pytest', 'requires_browser_qa': False}

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
    def _extract_failing_count(output: str) -> int:
        match = _FAILED_COUNT_RE.search(output or '')
        if match:
            return max(1, int(match.group(1)))
        return 1
