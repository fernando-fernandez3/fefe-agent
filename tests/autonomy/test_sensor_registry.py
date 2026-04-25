import httpx

from autonomy.sensors.autoworkflow_status import AutoWorkflowStatusSensor
from autonomy.sensors.base import SensorContext
from autonomy.sensors.file_freshness import FileFreshnessSensor
from autonomy.sensors.registry import SensorRegistry
from autonomy.sensors.repo_health import RepoHealthSensor
from autonomy.sensors.system_status import SystemStatusSensor
from autonomy.sensors.url_status import URLStatusSensor


class FakeResponse:
    def __init__(self, payload, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError('boom', request=None, response=None)

    def json(self):
        return self._payload


class FakeHttpClient:
    def __init__(self, payloads: dict[str, object]):
        self.payloads = payloads
        self.calls: list[str] = []

    def get(self, url: str, headers=None, timeout=None):
        self.calls.append(url)
        return FakeResponse(self.payloads[url])


def test_sensor_registry_default_maps_phase_a_asset_types():
    registry = SensorRegistry.default(
        autoworkflow_base_url='http://aw.local',
        autoworkflow_api_token='token-123',
    )

    assert registry.asset_types() == ['doc', 'repo', 'system', 'url', 'workflow']
    assert isinstance(registry.resolve('repo'), RepoHealthSensor)
    assert isinstance(registry.resolve('doc'), FileFreshnessSensor)
    assert isinstance(registry.resolve('system'), SystemStatusSensor)
    assert isinstance(registry.resolve('url'), URLStatusSensor)

    workflow_sensor = registry.resolve('workflow')
    assert isinstance(workflow_sensor, AutoWorkflowStatusSensor)
    assert workflow_sensor.base_url == 'http://aw.local'
    assert workflow_sensor.api_token == 'token-123'


def test_autoworkflow_status_sensor_emits_pending_failed_and_running_signals():
    base_url = 'http://aw.local'
    client = FakeHttpClient(
        {
            f'{base_url}/api/review-queue': [
                {
                    'id': 'review_1',
                    'status': 'pending',
                    'title': 'Embarka competitor gap: shared itinerary missing',
                },
                {'id': 'review_2', 'status': 'resolved', 'title': 'Other workflow'},
            ],
            f'{base_url}/api/workflows': [
                {'id': 'wf_failed', 'status': 'failed', 'name': 'Embarka competitor gap issues'},
                {'id': 'wf_running', 'status': 'running', 'name': 'Embarka competitor gap issues'},
                {'id': 'wf_done', 'status': 'completed', 'name': 'Other workflow'},
            ],
        }
    )
    sensor = AutoWorkflowStatusSensor(
        base_url=base_url,
        api_token='token-123',
        http_client=client,
    )

    result = sensor.collect(
        SensorContext(
            domain='code_projects',
            metadata={'locator': 'autoworkflow://embarka/competitor-gap-issues'},
        )
    )

    assert client.calls == [f'{base_url}/api/review-queue', f'{base_url}/api/workflows']
    signal_types = [signal.signal_type for signal in result.signals]
    assert signal_types[:3] == [
        'workflows_pending_review',
        'workflows_failed',
        'workflows_running',
    ]
    assert 'competitor_positioning_shift' in signal_types
    pending = result.signals[0]
    assert pending.evidence['pending_count'] == 1
    assert pending.evidence['item_ids'] == ['review_1']


def test_autoworkflow_status_sensor_accepts_paginated_review_queue_payload():
    base_url = 'http://aw.local'
    client = FakeHttpClient(
        {
            f'{base_url}/api/review-queue': {
                'items': [
                    {
                        'id': 'review_1',
                        'type': 'review_item',
                        'workflow_name': 'embarka-feedback-intake',
                        'data': {'status': 'awaiting_review'},
                        'summary': 'Embarka feedback item needs review',
                    }
                ],
                'total': 1,
                'counts': {'awaiting_review': 1},
            },
            f'{base_url}/api/workflows': {'items': []},
        }
    )
    sensor = AutoWorkflowStatusSensor(base_url=base_url, http_client=client)

    result = sensor.collect(
        SensorContext(
            domain='code_projects',
            metadata={'locator': 'autoworkflow://embarka/feedback'},
        )
    )

    signal_types = [signal.signal_type for signal in result.signals]
    assert 'workflows_pending_review' in signal_types
    pending = next(signal for signal in result.signals if signal.signal_type == 'workflows_pending_review')
    assert pending.evidence['pending_count'] == 1
    assert pending.evidence['item_ids'] == ['review_1']


def test_autoworkflow_status_sensor_emits_structured_feedback_and_competitor_signals():
    base_url = 'http://aw.local'
    client = FakeHttpClient(
        {
            f'{base_url}/api/review-queue': [
                {
                    'id': 'fb_1',
                    'status': 'pending',
                    'title': 'Embarka feedback: onboarding friction for first trip',
                    'summary': 'Users are confused during onboarding and get stuck before creating the first trip.',
                },
                {
                    'id': 'fb_2',
                    'status': 'pending',
                    'title': 'Embarka feedback: family logistics gap',
                    'summary': 'Parents traveling with kids want stroller and nap-aware planning.',
                },
                {
                    'id': 'cg_1',
                    'status': 'pending',
                    'title': 'Embarka competitor gap: competitor launched family mode',
                    'summary': 'A competitor is now positioning itself for families and parents with a shared itinerary feature.',
                },
            ],
            f'{base_url}/api/workflows': [],
        }
    )
    sensor = AutoWorkflowStatusSensor(base_url=base_url, http_client=client)

    feedback_result = sensor.collect(
        SensorContext(
            domain='code_projects',
            metadata={'locator': 'autoworkflow://embarka/feedback'},
        )
    )
    feedback_signal_types = [signal.signal_type for signal in feedback_result.signals]
    assert 'feedback_onboarding_friction' in feedback_signal_types
    assert 'feedback_family_constraint_gap' in feedback_signal_types

    competitor_result = sensor.collect(
        SensorContext(
            domain='code_projects',
            metadata={'locator': 'autoworkflow://embarka/competitor-gap-issues'},
        )
    )
    competitor_signal_types = [signal.signal_type for signal in competitor_result.signals]
    assert 'competitor_family_feature_threat' in competitor_signal_types
    assert 'competitor_positioning_shift' in competitor_signal_types


def test_autoworkflow_status_sensor_reads_competitor_artifacts_for_structured_threats(tmp_path):
    workspace = tmp_path / 'competitor-gap-issues'
    workspace.mkdir()
    (workspace / 'candidates.json').write_text(
        '[{"candidate_key":"shared-trip-link","title":"Shared itinerary planning","fit_verdict":"compatible"},'
        '{"candidate_key":"trip-plan-budget-rollup","title":"Budget overview","fit_verdict":"compatible"},'
        '{"candidate_key":"trip-plan-version-history","title":"Change history","fit_verdict":"blocked"}]'
    )
    (workspace / 'discovered.jsonl').write_text(
        '{"title":"Group travel collaboration","body":"Real-time editing and shared itinerary matter."}\n'
        '{"title":"Budget pain","body":"Need better budget overview and shared expenses visibility."}\n'
    )
    sensor = AutoWorkflowStatusSensor(base_url='http://aw.local', http_client=FakeHttpClient({
        'http://aw.local/api/review-queue': [],
        'http://aw.local/api/workflows': [],
    }))

    result = sensor.collect(
        SensorContext(
            domain='code_projects',
            metadata={
                'locator': 'autoworkflow://embarka/competitor-gap-issues',
                'workspace': str(workspace),
                'candidates_path': str(workspace / 'candidates.json'),
                'discovered_path': str(workspace / 'discovered.jsonl'),
            },
        )
    )

    signal_types = [signal.signal_type for signal in result.signals]
    assert 'competitor_collaboration_feature_threat' in signal_types
    assert 'competitor_budget_visibility_threat' in signal_types
    assert 'competitor_trip_change_management_threat' in signal_types
    collaboration_signal = next(
        signal for signal in result.signals
        if signal.signal_type == 'competitor_collaboration_feature_threat'
    )
    assert collaboration_signal.evidence['candidate_keys'] == [
        'shared-trip-link',
        'trip-plan-budget-rollup',
        'trip-plan-version-history',
    ]
    collaboration_matches = collaboration_signal.evidence['matches']
    assert collaboration_matches
    assert any(
        match['source_type'] == 'candidates'
        and match['candidate_key'] == 'shared-trip-link'
        and match['matched_keys'] == ['shared-trip-link']
        and match['source_path'].endswith('candidates.json')
        and match['snippet']
        for match in collaboration_matches
    )
    assert any(
        match['source_type'] == 'discovered'
        and match['title'] == 'Group travel collaboration'
        and 'shared itinerary' in match['matched_keywords']
        and match['source_path'].endswith('discovered.jsonl')
        and match['snippet']
        for match in collaboration_matches
    )

    budget_signal = next(
        signal for signal in result.signals
        if signal.signal_type == 'competitor_budget_visibility_threat'
    )
    assert budget_signal.evidence['matches']
    assert all(
        match.get('candidate_key') != 'shared-trip-link'
        for match in budget_signal.evidence['matches']
    )


def test_autoworkflow_status_sensor_reads_feedback_artifacts_for_structured_gaps(tmp_path):
    workspace = tmp_path / 'embarka-intake'
    workspace.mkdir()
    (workspace / 'discovered.jsonl').write_text(
        '{"title":"Mobile issue","body":"The floating menu overlaps content on mobile and scrolling is awkward."}\n'
        '{"title":"Trust issue","body":"Users do not trust the generated itinerary because details look wrong and unreliable."}\n'
        '{"title":"Editing issue","body":"Need to edit itinerary changes with version history and updated plan tracking.","canonical_key":"trip-plan-version-history"}\n'
        '{"title":"Family profile issue","body":"Need better family profile capture for kids ages and travel party setup.","canonical_key":"family-profile-capture","implementation_hint":"Improve family profile capture before generating the plan."}\n'
        '{"title":"Booking issue","body":"Need booking readiness with reservation links and tickets in one place.","canonical_key":"booking-readiness"}\n'
        '{"title":"Family logistics issue","body":"Need better planning for families traveling with kids and stroller constraints.","canonical_key":"family-logistics-gap"}\n'
        '{"title":"Trip memory issue","body":"Please remember what our family liked on the last trip.","canonical_key":"trip-memory-gap"}\n'
        '{"title":"Collaboration issue","body":"Need a shared trip link so my partner can collaborate.","canonical_key":"shared-trip-link"}\n'
        '{"title":"Booking confidence issue","body":"I need more confidence before I book this trip.","canonical_key":"booking-confidence-gap"}\n'
    )
    (workspace / 'draft-remediation-proposal.md').write_text(
        'Fix mobile responsive overlap and improve trust in generated output.'
    )
    (workspace / 'weekly-product-risks.md').write_text(
        '# Embarka weekly product risks\n\nShared trip link and booking confidence stay hot.'
    )
    sensor = AutoWorkflowStatusSensor(base_url='http://aw.local', http_client=FakeHttpClient({
        'http://aw.local/api/review-queue': [],
        'http://aw.local/api/workflows': [],
    }))

    result = sensor.collect(
        SensorContext(
            domain='code_projects',
            metadata={
                'locator': 'autoworkflow://embarka/feedback',
                'workspace': str(workspace),
                'discovered_path': str(workspace / 'discovered.jsonl'),
                'proposal_path': str(workspace / 'draft-remediation-proposal.md'),
                'review_packet_path': str(workspace / 'weekly-product-risks.md'),
            },
        )
    )

    signal_types = [signal.signal_type for signal in result.signals]
    assert 'feedback_mobile_usability_gap' in signal_types
    assert 'feedback_trip_output_trust_gap' in signal_types
    assert 'feedback_itinerary_editing_gap' in signal_types
    assert 'feedback_family_profile_capture_gap' in signal_types
    assert 'feedback_booking_readiness_gap' in signal_types
    assert 'feedback_family_logistics_gap' in signal_types
    assert 'feedback_trip_memory_gap' in signal_types
    assert 'feedback_collaboration_gap' in signal_types
    assert 'feedback_booking_confidence_gap' in signal_types
    collaboration_signal = next(signal for signal in result.signals if signal.signal_type == 'feedback_collaboration_gap')
    assert collaboration_signal.evidence['artifact_paths']['review_packet'].endswith('weekly-product-risks.md')


def test_autoworkflow_status_sensor_reads_feedback_candidate_keys_from_candidates_json(tmp_path):
    workspace = tmp_path / 'embarka-intake'
    workspace.mkdir()
    (workspace / 'candidates.json').write_text(
        '[{"candidate_key":"shared-trip-link","title":"Shared trip collaboration"},'
        '{"candidate_key":"family-logistics-gap","title":"Family logistics planning"}]'
    )
    (workspace / 'discovered.jsonl').write_text(
        '{"title":"Booking confidence","body":"Users need confidence before booking.","canonical_key":"booking-confidence-gap"}\n'
    )
    sensor = AutoWorkflowStatusSensor(base_url='http://aw.local', http_client=FakeHttpClient({
        'http://aw.local/api/review-queue': [],
        'http://aw.local/api/workflows': [],
    }))

    result = sensor.collect(
        SensorContext(
            domain='code_projects',
            metadata={
                'locator': 'autoworkflow://embarka/feedback',
                'workspace': str(workspace),
                'candidates_path': str(workspace / 'candidates.json'),
                'discovered_path': str(workspace / 'discovered.jsonl'),
            },
        )
    )

    signal_types = [signal.signal_type for signal in result.signals]
    assert 'feedback_collaboration_gap' in signal_types
    assert 'feedback_family_logistics_gap' in signal_types
    assert 'feedback_booking_confidence_gap' in signal_types

    collaboration_signal = next(
        signal for signal in result.signals
        if signal.signal_type == 'feedback_collaboration_gap'
    )
    assert collaboration_signal.evidence['candidate_keys'] == [
        'family-logistics-gap',
        'shared-trip-link',
    ]
    assert collaboration_signal.evidence['canonical_keys'] == ['booking-confidence-gap']
    assert any(
        match['source_type'] == 'candidates'
        and match['candidate_key'] == 'shared-trip-link'
        and match['matched_keys'] == ['shared-trip-link']
        for match in collaboration_signal.evidence['matches']
    )
