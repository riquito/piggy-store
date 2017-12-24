from importlib import import_module

from piggy_store.config import config
from piggy_store.storage.cache.authtoken_storage import AuthTokenStorage


def get_cache_storage():
    cache_storage_module = import_module(config['storage']['cache']['module'])
    return cache_storage_module.Storage(config['storage']['cache']['params'])


def get_token_storage():
    return AuthTokenStorage({
        **config['storage']['cache']['params'],
        'timeout': config['auth_token_expire_after'],
        'secret': config['secret']
    })
