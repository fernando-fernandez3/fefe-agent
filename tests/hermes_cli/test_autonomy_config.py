from unittest.mock import patch

from hermes_cli.config import DEFAULT_CONFIG, load_config, save_config


def test_autonomy_config_defaults_present(tmp_path):
    with patch.dict('os.environ', {'HERMES_HOME': str(tmp_path)}):
        config = load_config()

    assert config['autonomy']['enabled'] is False
    assert config['autonomy']['mode'] == 'desired_state'
    assert config['autonomy']['tick_interval_minutes'] == 15
    assert config['autonomy']['max_actions_per_tick'] == 3
    assert config['autonomy']['allowed_domains'] == ['code_projects']
    assert config['autonomy']['telegram_reviews_enabled'] is True
    assert config['autonomy']['daily_digest']['enabled'] is False
    assert config['autonomy']['daily_digest']['delivery_time'] == '08:00'
    assert config['autonomy']['daily_digest']['channel'] == 'telegram'
    assert DEFAULT_CONFIG['_config_version'] == 19


def test_autonomy_config_roundtrips(tmp_path):
    with patch.dict('os.environ', {'HERMES_HOME': str(tmp_path)}):
        config = load_config()
        config['autonomy']['enabled'] = True
        config['autonomy']['mode'] = 'legacy_domain'
        config['autonomy']['tick_interval_minutes'] = 5
        config['autonomy']['max_actions_per_tick'] = 2
        config['autonomy']['allowed_domains'] = ['code_projects', 'lab']
        config['autonomy']['telegram_reviews_enabled'] = False
        config['autonomy']['daily_digest']['enabled'] = True
        config['autonomy']['daily_digest']['delivery_time'] = '09:30'
        config['autonomy']['daily_digest']['channel'] = 'telegram'
        save_config(config)

        reloaded = load_config()

    assert reloaded['autonomy']['enabled'] is True
    assert reloaded['autonomy']['mode'] == 'legacy_domain'
    assert reloaded['autonomy']['tick_interval_minutes'] == 5
    assert reloaded['autonomy']['max_actions_per_tick'] == 2
    assert reloaded['autonomy']['allowed_domains'] == ['code_projects', 'lab']
    assert reloaded['autonomy']['telegram_reviews_enabled'] is False
    assert reloaded['autonomy']['daily_digest']['enabled'] is True
    assert reloaded['autonomy']['daily_digest']['delivery_time'] == '09:30'
    assert reloaded['autonomy']['daily_digest']['channel'] == 'telegram'
