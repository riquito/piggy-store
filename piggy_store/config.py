import yaml
import re
from datetime import timedelta


class ConfigError(Exception):
    pass


config = {}


def _size_from_human_to_bytes(humansize):
    match = re.match(r'\s*(\d+)\s*(MB|M|B|BYTES|KB)\s*$', humansize, re.I)
    if match:
        return int(match.group(1)) * {
            'MB': 1024**2,
            'M': 1024**2,
            'B': 1,
            'BYTES': 1,
            'KB': 1024
        }[match.group(2).upper()]
    else:
        # default to kilobytes
        return int(humansize) * 1024


def _time_delta_from_human_to_timedelta(humandelta):
    match = re.match(r'\s*(\d+)\s*(d|h|m|s|days?|hours?|minutes?|seconds?)\s*$', humandelta, re.I)
    time_resolution = 'minutes'
    if match:
        value = int(match.group(1))
        time_resolution = {
            'd': 'days',
            'h': 'hours',
            'm': 'minutes',
            's': 'seconds'
        }[match.group(2)[0].lower()]
    else:
        value = int(humandelta)

    kwargs = {time_resolution: value}
    return timedelta(**kwargs)


def load(config_path):
    global config

    if config:
        raise ConfigError('Loading configuration twice may lead to unexpected behaviour')

    with open(config_path) as fp:
        config.update(yaml.load(fp,Loader=yaml.SafeLoader))

    config.update(_sanitize_config(config))
    return config


def _sanitize_config(config):
    '''Sanitize in-place a config dictionary'''

    config.setdefault('debug', False)
    config.setdefault('uploads', {})
    config.setdefault('users_whitelist', [])
    config.setdefault('auth_token_expire_after', '2 hours')
    config['uploads'].setdefault('max_content_length', '1M')

    try:
        config['debug']
        config['secret']
        config['auth_token_expire_after']
        config['uploads']
        config['uploads']['max_content_length']
        config['server']
        config['server']['host']
        config['server']['port']
        config['server']['name']
        config['users_whitelist']
        config['sentry']
        config['sentry']['dsn']
        config['storage']
        config['storage']['cache']
        config['storage']['cache']['module']
        config['storage']['cache']['params']
        config['storage']['files']
        config['storage']['files']['module']
        config['storage']['files']['params']
    except KeyError as e:
        raise ConfigError('A config key is missing: {}'.format(e.args[0]))

    config['uploads']['max_content_length'] = _size_from_human_to_bytes(
        config['uploads']['max_content_length']
    )

    config['storage']['files']['params']['download_url_expire_after'] = _time_delta_from_human_to_timedelta(
        config['storage']['files']['params'].get('download_url_expire_after', '1 day')
    )

    config['auth_token_expire_after'] = _time_delta_from_human_to_timedelta(
        config['auth_token_expire_after']
    )

    return config
