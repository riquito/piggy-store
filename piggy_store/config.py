import yaml
import re
from datetime import timedelta

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
        }[match.group(2)]
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

    kwargs = { time_resolution: value }
    return timedelta(**kwargs)


def load(config_path):
    global config

    if config:
        raise Error('Loading configuration twice may lead to unexpected behaviour')

    with open(config_path) as fp:
        config.update(yaml.load(fp))

    config['uploads']['max_content_length'] = _size_from_human_to_bytes(
        config['uploads']['max_content_length']
    )

    config['files']['download_url_expire_after'] = _time_delta_from_human_to_timedelta(
        config['files']['download_url_expire_after']
    )

    return config
