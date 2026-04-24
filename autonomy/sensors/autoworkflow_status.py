"""AutoWorkflow status sensor — pulls pending reviews, workflow health, and local workflow artifacts."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from autonomy.models import Signal
from .base import BaseSensor, SensorContext, SensorResult


class AutoWorkflowStatusSensor(BaseSensor):
    def __init__(
        self,
        *,
        base_url: str | None = None,
        api_token: str | None = None,
        http_client: httpx.Client | None = None,
        timeout_seconds: float = 10.0,
    ):
        self.base_url = (
            base_url or os.getenv("AUTOWORKFLOW_BASE_URL") or "http://127.0.0.1:8882"
        ).rstrip("/")
        self.api_token = api_token or os.getenv("AUTOWORKFLOW_API_TOKEN") or ""
        self._client = http_client
        self.timeout_seconds = timeout_seconds

    @property
    def name(self) -> str:
        return "autoworkflow_status"

    def collect(self, context: SensorContext) -> SensorResult:
        entity_key = context.metadata.get("locator") or self.base_url
        signals: list[Signal] = []
        metadata: dict[str, Any] = {"base_url": self.base_url}

        try:
            review_items = self._fetch_json("/api/review-queue") or []
            workflows = self._fetch_json("/api/workflows") or []
        except (httpx.HTTPError, OSError) as exc:
            metadata["status"] = "autoworkflow_unreachable"
            metadata["error"] = str(exc)
            review_items = []
            workflows = []

        pending = [
            item
            for item in review_items
            if self._is_pending(item) and self._matches_locator(item, str(entity_key))
        ]
        if pending:
            signals.append(
                Signal(
                    id=f"{self.name}:workflows_pending_review:{entity_key}",
                    domain=context.domain,
                    source_sensor=self.name,
                    entity_type="workflow",
                    entity_key=str(entity_key),
                    signal_type="workflows_pending_review",
                    signal_strength=min(1.0, 0.5 + 0.1 * len(pending)),
                    evidence={
                        "pending_count": len(pending),
                        "item_ids": [item.get("id") for item in pending[:10]],
                    },
                )
            )

        failed = [
            wf for wf in workflows if self._is_failed(wf) and self._matches_locator(wf, str(entity_key))
        ]
        if failed:
            signals.append(
                Signal(
                    id=f"{self.name}:workflows_failed:{entity_key}",
                    domain=context.domain,
                    source_sensor=self.name,
                    entity_type="workflow",
                    entity_key=str(entity_key),
                    signal_type="workflows_failed",
                    signal_strength=min(1.0, 0.7 + 0.1 * len(failed)),
                    evidence={
                        "failed_count": len(failed),
                        "workflow_ids": [wf.get("id") for wf in failed[:10]],
                    },
                )
            )

        running = [
            wf for wf in workflows if self._is_running(wf) and self._matches_locator(wf, str(entity_key))
        ]
        if running:
            signals.append(
                Signal(
                    id=f"{self.name}:workflows_running:{entity_key}",
                    domain=context.domain,
                    source_sensor=self.name,
                    entity_type="workflow",
                    entity_key=str(entity_key),
                    signal_type="workflows_running",
                    signal_strength=0.35,
                    evidence={
                        "running_count": len(running),
                        "workflow_ids": [wf.get("id") for wf in running[:10]],
                    },
                )
            )

        signals.extend(self._structured_signals(context, entity_key=str(entity_key), pending=pending))
        signals.extend(self._artifact_signals(context, entity_key=str(entity_key)))

        metadata["review_items_total"] = len(review_items)
        metadata["workflows_total"] = len(workflows)
        metadata["matched_pending_count"] = len(pending)
        metadata["matched_failed_count"] = len(failed)
        metadata["matched_running_count"] = len(running)
        return SensorResult(sensor_name=self.name, signals=signals, metadata=metadata)

    def _fetch_json(self, path: str) -> Any:
        url = f"{self.base_url}{path}"
        headers = {"Accept": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"

        if self._client is not None:
            response = self._client.get(
                url, headers=headers, timeout=self.timeout_seconds
            )
            response.raise_for_status()
            return response.json()

        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()

    @staticmethod
    def _is_pending(item: dict) -> bool:
        status = str(item.get("status") or "").lower()
        return status in {"pending", "awaiting_review", "needs_review", "open"}

    @staticmethod
    def _is_failed(workflow: dict) -> bool:
        status = str(workflow.get("status") or workflow.get("state") or "").lower()
        return status in {"failed", "error", "errored"}

    @staticmethod
    def _is_running(workflow: dict) -> bool:
        status = str(workflow.get("status") or workflow.get("state") or "").lower()
        return status in {"running", "in_progress", "started"}

    def _structured_signals(
        self,
        context: SensorContext,
        *,
        entity_key: str,
        pending: list[dict],
    ) -> list[Signal]:
        locator = str(entity_key).lower()
        if not pending:
            return []

        if "feedback" in locator:
            return self._feedback_signals(context, entity_key=entity_key, pending=pending)
        if "competitor" in locator or "gap" in locator:
            return self._competitor_signals(context, entity_key=entity_key, pending=pending)
        return []

    def _feedback_signals(
        self,
        context: SensorContext,
        *,
        entity_key: str,
        pending: list[dict],
    ) -> list[Signal]:
        patterns = {
            "feedback_onboarding_friction": [
                "onboarding",
                "sign up",
                "signup",
                "sign-up",
                "getting started",
                "first trip",
                "too many steps",
                "confusing",
                "stuck",
                "friction",
            ],
            "feedback_family_constraint_gap": [
                "family",
                "kids",
                "kid",
                "child",
                "children",
                "toddler",
                "baby",
                "stroller",
                "nap",
                "age",
                "family logistics",
                "traveling with kids",
            ],
        }
        return self._semantic_signals(
            context,
            entity_key=entity_key,
            pending=pending,
            patterns=patterns,
        )

    def _competitor_signals(
        self,
        context: SensorContext,
        *,
        entity_key: str,
        pending: list[dict],
    ) -> list[Signal]:
        patterns = {
            "competitor_family_feature_threat": [
                "family mode",
                "family travel",
                "kids",
                "kid",
                "child",
                "children",
                "stroller",
                "nap",
                "parents",
                "traveling with kids",
            ],
            "competitor_positioning_shift": [
                "for families",
                "for parents",
                "family-friendly",
                "built for families",
                "collaboration",
                "shared itinerary",
                "group planning",
                "positioning",
            ],
        }
        return self._semantic_signals(
            context,
            entity_key=entity_key,
            pending=pending,
            patterns=patterns,
        )

    def _semantic_signals(
        self,
        context: SensorContext,
        *,
        entity_key: str,
        pending: list[dict],
        patterns: dict[str, list[str]],
    ) -> list[Signal]:
        emitted: list[Signal] = []
        for signal_type, keywords in patterns.items():
            matches: list[dict[str, Any]] = []
            for item in pending:
                text = self._record_text(item).lower()
                hit_keywords = [kw for kw in keywords if kw in text]
                if not hit_keywords:
                    continue
                matches.append(
                    {
                        "id": item.get("id"),
                        "title": item.get("title") or item.get("name"),
                        "matched_keywords": hit_keywords,
                        "snippet": self._record_snippet(item, hit_keywords),
                    }
                )
            if not matches:
                continue
            emitted.append(
                Signal(
                    id=f"{self.name}:{signal_type}:{entity_key}",
                    domain=context.domain,
                    source_sensor=self.name,
                    entity_type="workflow",
                    entity_key=str(entity_key),
                    signal_type=signal_type,
                    signal_strength=min(1.0, 0.55 + 0.1 * len(matches)),
                    evidence={
                        "pending_count": len(matches),
                        "matches": matches[:5],
                    },
                )
            )
        return emitted

    def _artifact_signals(self, context: SensorContext, *, entity_key: str) -> list[Signal]:
        paths = self._artifact_paths(context, entity_key=entity_key)
        if not paths:
            return []
        if 'feedback' in entity_key.lower():
            return self._feedback_artifact_signals(context, entity_key=entity_key, paths=paths)
        if 'competitor' in entity_key.lower() or 'gap' in entity_key.lower():
            return self._competitor_artifact_signals(context, entity_key=entity_key, paths=paths)
        return []

    def _feedback_artifact_signals(
        self, context: SensorContext, *, entity_key: str, paths: dict[str, Path]
    ) -> list[Signal]:
        texts = self._artifact_texts(paths)
        records = self._load_jsonl_records(paths.get('discovered'))
        if not texts and not records:
            return []
        joined = '\n'.join(texts).lower()
        signals: list[Signal] = []
        canonical_keys = {str(record.get('canonical_key') or '') for record in records if record.get('canonical_key')}
        implementation_hints = ' '.join(str(record.get('implementation_hint') or '') for record in records).lower()
        artifact_evidence = self._artifact_evidence(paths, canonical_keys=sorted(k for k in canonical_keys if k))

        if 'trip-itinerary-mobile-floating-menu' in canonical_keys or any(token in joined for token in ['mobile', 'responsive', 'floating menu', 'overlap', 'scroll']):
            signals.append(self._emit_artifact_signal(context, sensor_name=self.name, entity_key=entity_key, signal_type='feedback_mobile_usability_gap', signal_strength=0.8, artifact_evidence=artifact_evidence))
        if any(token in joined for token in ['trust', 'accurate', 'accuracy', 'wrong', 'hallucination', 'reliable', 'confidence']):
            signals.append(self._emit_artifact_signal(context, sensor_name=self.name, entity_key=entity_key, signal_type='feedback_trip_output_trust_gap', signal_strength=0.75, artifact_evidence=artifact_evidence))
        if 'trip-plan-version-history' in canonical_keys or any(token in joined for token in ['edit itinerary', 'change itinerary', 'version history', 'updated plan', 'refine itinerary', 'edit trip']):
            signals.append(self._emit_artifact_signal(context, sensor_name=self.name, entity_key=entity_key, signal_type='feedback_itinerary_editing_gap', signal_strength=0.78, artifact_evidence=artifact_evidence))
        if any(key in canonical_keys for key in ['family-profile-capture', 'family-logistics-profile']) or any(token in joined for token in ['kids ages', 'traveler ages', 'family profile', 'child age', 'ages of kids', 'travel party']) or 'family profile' in implementation_hints:
            signals.append(self._emit_artifact_signal(context, sensor_name=self.name, entity_key=entity_key, signal_type='feedback_family_profile_capture_gap', signal_strength=0.76, artifact_evidence=artifact_evidence))
        if 'booking-readiness' in canonical_keys or any(token in joined for token in ['booking', 'book now', 'reservation', 'tickets', 'ready to book', 'booking readiness']):
            signals.append(self._emit_artifact_signal(context, sensor_name=self.name, entity_key=entity_key, signal_type='feedback_booking_readiness_gap', signal_strength=0.74, artifact_evidence=artifact_evidence))
        if any(key in canonical_keys for key in ['family-logistics-gap', 'traveling-with-kids-gap']):
            signals.append(self._emit_artifact_signal(context, sensor_name=self.name, entity_key=entity_key, signal_type='feedback_family_logistics_gap', signal_strength=0.8, artifact_evidence=artifact_evidence))
        if any(key in canonical_keys for key in ['trip-memory-gap', 'remember-family-preferences']):
            signals.append(self._emit_artifact_signal(context, sensor_name=self.name, entity_key=entity_key, signal_type='feedback_trip_memory_gap', signal_strength=0.72, artifact_evidence=artifact_evidence))
        if any(key in canonical_keys for key in ['shared-trip-link', 'collaborative-trip-planning']):
            signals.append(self._emit_artifact_signal(context, sensor_name=self.name, entity_key=entity_key, signal_type='feedback_collaboration_gap', signal_strength=0.78, artifact_evidence=artifact_evidence))
        if any(key in canonical_keys for key in ['booking-confidence-gap', 'trip-output-trust-gap']):
            signals.append(self._emit_artifact_signal(context, sensor_name=self.name, entity_key=entity_key, signal_type='feedback_booking_confidence_gap', signal_strength=0.76, artifact_evidence=artifact_evidence))
        return signals

    def _competitor_artifact_signals(
        self, context: SensorContext, *, entity_key: str, paths: dict[str, Path]
    ) -> list[Signal]:
        signals: list[Signal] = []
        candidates_path = paths.get('candidates')
        candidates = self._load_json_candidates(candidates_path) if candidates_path else []
        keys = {str(item.get('candidate_key') or '') for item in candidates}
        joined = '\n'.join(self._artifact_texts(paths)).lower()
        artifact_evidence = {'artifact_paths': {k: str(v) for k, v in paths.items() if v is not None}}
        if 'shared-trip-link' in keys or any(token in joined for token in ['shared itinerary', 'group travel', 'real-time editing', 'collaboration']):
            signals.append(
                Signal(
                    id=f'{self.name}:competitor_collaboration_feature_threat:{entity_key}',
                    domain=context.domain,
                    source_sensor=self.name,
                    entity_type='workflow',
                    entity_key=str(entity_key),
                    signal_type='competitor_collaboration_feature_threat',
                    signal_strength=0.85,
                    evidence=artifact_evidence,
                )
            )
        if 'trip-plan-budget-rollup' in keys or any(token in joined for token in ['budget', 'shared expenses', 'spend', 'cost', 'budget overview']):
            signals.append(
                Signal(
                    id=f'{self.name}:competitor_budget_visibility_threat:{entity_key}',
                    domain=context.domain,
                    source_sensor=self.name,
                    entity_type='workflow',
                    entity_key=str(entity_key),
                    signal_type='competitor_budget_visibility_threat',
                    signal_strength=0.8,
                    evidence=artifact_evidence,
                )
            )
        if 'trip-plan-version-history' in keys or any(token in joined for token in ['version history', 'change history', 'updated itinerary', 'edit itinerary', 'change management']):
            signals.append(
                Signal(
                    id=f'{self.name}:competitor_trip_change_management_threat:{entity_key}',
                    domain=context.domain,
                    source_sensor=self.name,
                    entity_type='workflow',
                    entity_key=str(entity_key),
                    signal_type='competitor_trip_change_management_threat',
                    signal_strength=0.82,
                    evidence=artifact_evidence,
                )
            )
        return signals

    def _artifact_paths(self, context: SensorContext, *, entity_key: str) -> dict[str, Path]:
        metadata = context.metadata or {}
        explicit = {}
        for key in ['workspace', 'candidates_path', 'discovered_path', 'proposal_path', 'audit_summary_path', 'review_packet_path']:
            value = metadata.get(key)
            if value:
                explicit[key] = Path(str(value))
        if explicit:
            return {
                'workspace': explicit.get('workspace'),
                'candidates': explicit.get('candidates_path'),
                'discovered': explicit.get('discovered_path'),
                'proposal': explicit.get('proposal_path'),
                'audit_summary': explicit.get('audit_summary_path'),
                'review_packet': explicit.get('review_packet_path'),
            }

        locator = entity_key.lower()
        if 'competitor' in locator or 'gap' in locator:
            workspace = Path('/home/fefernandez/embarka/.autoworkflow/competitor-gap-issues')
            return {
                'workspace': workspace,
                'candidates': workspace / 'candidates.json',
                'discovered': workspace / 'discovered.jsonl',
                'proposal': workspace / 'top-issue.md',
                'audit_summary': Path('/home/fefernandez/embarka/.autoworkflow/daily-audit/audit-summary.json'),
                'review_packet': None,
            }
        if 'feedback' in locator:
            workspace_candidates = [
                Path('/home/fefernandez/autoworkflow/.autoworkflow/feedback/embarka-intake'),
                Path('/home/fefernandez/embarka/.autoworkflow/feedback/embarka-intake'),
            ]
            workspace = next((candidate for candidate in workspace_candidates if candidate.exists()), workspace_candidates[0])
            return {
                'workspace': workspace,
                'candidates': workspace / 'candidates.json',
                'discovered': workspace / 'discovered.jsonl',
                'proposal': workspace / 'draft-remediation-proposal.md',
                'audit_summary': None,
                'review_packet': workspace / 'weekly-product-risks.md',
            }
        return {}

    @staticmethod
    def _load_json_candidates(path: Path | None) -> list[dict[str, Any]]:
        if path is None or not path.exists():
            return []
        try:
            data = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            return []
        return data if isinstance(data, list) else []

    @staticmethod
    def _load_jsonl_records(path: Path | None) -> list[dict[str, Any]]:
        if path is None or not path.exists():
            return []
        records: list[dict[str, Any]] = []
        try:
            for line in path.read_text().splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(record, dict):
                    records.append(record)
        except OSError:
            return []
        return records

    @staticmethod
    def _emit_artifact_signal(
        context: SensorContext,
        *,
        sensor_name: str,
        entity_key: str,
        signal_type: str,
        signal_strength: float,
        artifact_evidence: dict[str, Any],
    ) -> Signal:
        return Signal(
            id=f'{sensor_name}:{signal_type}:{entity_key}',
            domain=context.domain,
            source_sensor=sensor_name,
            entity_type='workflow',
            entity_key=str(entity_key),
            signal_type=signal_type,
            signal_strength=signal_strength,
            evidence=artifact_evidence,
        )

    @staticmethod
    def _artifact_evidence(paths: dict[str, Path], **extra: Any) -> dict[str, Any]:
        evidence = {'artifact_paths': {k: str(v) for k, v in paths.items() if v is not None}}
        evidence.update({k: v for k, v in extra.items() if v is not None})
        return evidence

    @staticmethod
    def _artifact_texts(paths: dict[str, Path]) -> list[str]:
        texts: list[str] = []
        for key in ['candidates', 'discovered', 'proposal', 'audit_summary', 'review_packet']:
            path = paths.get(key)
            if path is None or not path.exists() or not path.is_file():
                continue
            try:
                texts.append(path.read_text())
            except OSError:
                continue
        return texts

    @staticmethod
    def _matches_locator(record: dict, locator: str) -> bool:
        text = AutoWorkflowStatusSensor._record_text(record).lower()
        tokens = AutoWorkflowStatusSensor._locator_tokens(locator)
        if not tokens:
            return True
        if len(tokens) == 1:
            return tokens[0] in text
        head, rest = tokens[0], tokens[1:]
        return head in text and any(token in text for token in rest)

    @staticmethod
    def _locator_tokens(locator: str) -> list[str]:
        parsed = urlparse(locator)
        raw = ' '.join(part for part in [parsed.netloc, parsed.path] if part)
        if not raw:
            raw = locator
        parts = re.split(r'[^a-zA-Z0-9]+', raw.lower())
        return [part for part in parts if len(part) >= 3]

    @staticmethod
    def _record_text(payload: Any) -> str:
        parts: list[str] = []

        def visit(value: Any) -> None:
            if isinstance(value, str):
                parts.append(value)
            elif isinstance(value, dict):
                for item in value.values():
                    visit(item)
            elif isinstance(value, list):
                for item in value:
                    visit(item)

        visit(payload)
        return ' '.join(parts)

    @classmethod
    def _record_snippet(cls, item: dict[str, Any], keywords: list[str]) -> str:
        text = cls._record_text(item)
        lower = text.lower()
        for keyword in keywords:
            idx = lower.find(keyword)
            if idx >= 0:
                start = max(0, idx - 40)
                end = min(len(text), idx + max(len(keyword), 80))
                return text[start:end].strip()
        return text[:120].strip()
