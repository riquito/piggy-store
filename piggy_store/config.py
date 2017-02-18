import yaml
import re

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
        

def load(config_path):
    global config

    if config:
        raise Error('Loading configuration twice may lead to unexpected behaviour')

    with open(config_path) as fp:
        config.update(yaml.load(fp))

    config['uploads']['max_content_length'] = _size_from_human_to_bytes(
        config['uploads']['max_content_length']
    )
    
    return config
