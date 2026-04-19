"""World-state projection from immutable signals."""

from __future__ import annotations

import uuid

from autonomy.models import Signal, WorldStateRecord
from autonomy.store import AutonomyStore


class WorldStateProjector:
    """Project current repo state from append-only signals."""

    def project_signal(self, store: AutonomyStore, signal: Signal) -> WorldStateRecord:
        state = {
            'last_signal_type': signal.signal_type,
            'last_signal_strength': signal.signal_strength,
            'last_evidence': signal.evidence,
        }
        return store.upsert_world_state(
            record_id=f'ws_{uuid.uuid4().hex}',
            domain=signal.domain,
            entity_type=signal.entity_type,
            entity_key=signal.entity_key,
            state=state,
            freshness_ts=signal.created_at,
            source=signal.source_sensor,
        )
