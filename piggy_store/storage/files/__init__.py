from importlib import import_module
from piggy_store.config import config
from piggy_store.storage.files.file_entity import FileDTO

def access_file_storage(user_dir):
    file_storage_module = import_module(config['storage']['files']['module'])

    if user_dir != 'admin$':
        user_dir = 'users/' + user_dir

    storage = file_storage_module.Storage(user_dir, config['storage']['files']['params'])
    storage.init()

    return storage
