from importlib import import_module

from piggy_store.config import config


def get_cache_storage():
    cache_storage_module = import_module(config['storage']['cache']['module'])
    return cache_storage_module.Storage(config['storage']['cache']['params'])
