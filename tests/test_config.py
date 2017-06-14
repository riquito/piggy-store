import os
import importlib
import pytest
from datetime import timedelta

import piggy_store.config
from piggy_store.config import config, load as load_config, ConfigError

config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.tests.yml')


def get_minimal_loadable_config():
    return {
        'debug': False,
        'secret': '',
        'uploads': {
            'max_content_length': '1MB'
        },
        'server': {
            'host': '',
            'port': 443,
            'name': '',
        },
        'sentry': {
            'dsn':  ''
        },
        'storage': {
            'cache': {
                'module': '',
                'params': {}
            },
            'files': {
                'module': '',
                'params': {}
            }
        }
    }

@pytest.fixture(name='config_mod')
def reload_config_module():
    importlib.reload(piggy_store.config)
    return piggy_store.config

def test_cannot_load_config_twice(config_mod):
    config = config_mod.load(config_path)
    with pytest.raises(config_mod.ConfigError) as exc_info:
        piggy_store.config.load(config_path)

    exc_info.match('twice') # it raises AssertionError on failure


@pytest.mark.parametrize('required_key', [
    'secret',
    'server',
    'server.host',
    'server.port',
    'server.name',
    'sentry',
    'sentry.dsn',
    'storage',
    'storage.cache',
    'storage.cache.module',
    'storage.cache.params',
    'storage.files',
    'storage.files.module',
    'storage.files.params',
])
def test_error_on_missing_keys(config_mod, required_key):
    # check that it doesn't trigger an error
    config_mod._sanitize_config(get_minimal_loadable_config())

    # remove a key and check that an error is triggered
    config = get_minimal_loadable_config()
    key_parts = required_key.split('.')

    parent = config
    for key in key_parts[:-1]:
        parent = parent[key]
    del(parent[key_parts[-1]])

    with pytest.raises(piggy_store.config.ConfigError) as exc_info:
        config_mod._sanitize_config(config)

    # match() raises AssertionError on failure
    exc_info.match('A config key is missing: {}'.format(key_parts[-1]))

@pytest.mark.parametrize('defaulted_key', [
    'debug',
    'uploads.max_content_length',
])
def test_config_keys_with_defaults(config_mod, defaulted_key):
    # remove a key and check that it comes back with a default value
    config = get_minimal_loadable_config()

    parent = config
    key_parts = defaulted_key.split('.')
    for key in key_parts[:-1]:
        parent = parent[key]
    del(parent[key_parts[-1]])

    config = config_mod._sanitize_config(config)

    assert key_parts[0] in config
    v = config[key_parts[0]]

    for key in key_parts[1:]:
        assert key in v
        v = v[key]

@pytest.mark.parametrize('humansize,expected', [
    ('2', 2048),
    ('2b', 2),
    ('2B', 2),
    ('2 b', 2),
    ('2 B', 2),
    ('2 bytes', 2),
    ('2 BYTES', 2),
    ('2kb', 2 * 1024),
    ('2KB', 2 * 1024),
    ('2 kb', 2 * 1024),
    ('2 KB', 2 * 1024),
    ('2mb', 2 * 1024 * 1024),
    ('2MB', 2 * 1024 * 1024),
    ('2 mb', 2 * 1024 * 1024),
    ('2 MB', 2 * 1024 * 1024),
])
def test_size_from_human_to_bytes(config_mod, humansize, expected):
    assert expected == config_mod._size_from_human_to_bytes(humansize)

@pytest.mark.parametrize('humandelta,expected', [
    ('2', timedelta(minutes=2)),
    ('1 day', timedelta(days=1)),
    ('2 days', timedelta(days=2)),
    ('1 hour', timedelta(hours=1)),
    ('2 hours', timedelta(hours=2)),
    ('1 minute', timedelta(minutes=1)),
    ('2 minutes', timedelta(minutes=2)),
    ('1 second', timedelta(seconds=1)),
    ('2 seconds', timedelta(seconds=2)),
])
def test_time_delta_from_human_to_timedelta(config_mod, humandelta, expected):
    assert expected == config_mod._time_delta_from_human_to_timedelta(humandelta)
