import os
import time

from autonomy.sensors.base import SensorContext
from autonomy.sensors.file_freshness import FileFreshnessSensor


def test_file_freshness_returns_recently_modified_for_fresh_file(tmp_path):
    target = tmp_path / 'fresh.md'
    target.write_text('hello')

    result = FileFreshnessSensor().collect(
        SensorContext(domain='learning', metadata={'locator': str(target)})
    )

    assert len(result.signals) == 1
    signal = result.signals[0]
    assert signal.signal_type == 'doc_recently_modified'
    assert signal.entity_key == str(target)
    assert signal.evidence['age_seconds'] < 60


def test_file_freshness_classifies_stale_between_7_and_30_days(tmp_path):
    target = tmp_path / 'stale.md'
    target.write_text('hello')
    now = time.time()
    ten_days_ago = now - (10 * 24 * 3600)
    os.utime(target, (ten_days_ago, ten_days_ago))

    result = FileFreshnessSensor().collect(
        SensorContext(domain='learning', metadata={'locator': str(target), 'now_epoch': int(now)})
    )

    signal = result.signals[0]
    assert signal.signal_type == 'doc_stale'
    assert signal.evidence['age_seconds'] >= 7 * 24 * 3600


def test_file_freshness_classifies_very_stale_beyond_30_days(tmp_path):
    target = tmp_path / 'ancient.md'
    target.write_text('hello')
    now = time.time()
    sixty_days_ago = now - (60 * 24 * 3600)
    os.utime(target, (sixty_days_ago, sixty_days_ago))

    result = FileFreshnessSensor().collect(
        SensorContext(domain='learning', metadata={'locator': str(target), 'now_epoch': int(now)})
    )

    signal = result.signals[0]
    assert signal.signal_type == 'doc_very_stale'
    assert signal.evidence['age_seconds'] >= 30 * 24 * 3600


def test_file_freshness_emits_missing_asset_when_path_does_not_exist(tmp_path):
    missing = tmp_path / 'not-there'

    result = FileFreshnessSensor().collect(
        SensorContext(domain='learning', metadata={'locator': str(missing)})
    )

    assert len(result.signals) == 1
    assert result.signals[0].signal_type == 'missing_asset'


def test_file_freshness_uses_latest_mtime_within_directory(tmp_path):
    docs_dir = tmp_path / 'docs'
    docs_dir.mkdir()
    (docs_dir / 'old.md').write_text('old')
    os.utime(docs_dir / 'old.md', (time.time() - 100 * 24 * 3600, time.time() - 100 * 24 * 3600))
    (docs_dir / 'new.md').write_text('new')

    result = FileFreshnessSensor().collect(
        SensorContext(domain='learning', metadata={'locator': str(docs_dir)})
    )

    signal = result.signals[0]
    assert signal.signal_type == 'doc_recently_modified'
    assert signal.evidence['is_dir'] is True


def test_file_freshness_no_locator_returns_empty(tmp_path):
    result = FileFreshnessSensor().collect(SensorContext(domain='learning'))
    assert result.signals == []
    assert result.metadata.get('status') == 'missing_locator'
