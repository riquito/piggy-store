from importlib import import_module

from piggy_store.storage.users.user_entity import User
from piggy_store.config import config

def get_user_storage():
    user_storage_module = import_module(config['storage']['users']['module'])
    return user_storage_module.Storage(config['storage']['users']['params'])
