#!/usr/bin/env python

import os
from piggy_store.config import load as load_config

# load the config before doing anything else
config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.yml')
config = load_config(config_path)

from piggy_store.app import create_app

application = create_app(config)

if __name__ == "__main__":
    application.run(
        host = config['server']['host'],
        port = config['server']['port'],
        debug = config['debug'],
        use_evalex = False
    )
