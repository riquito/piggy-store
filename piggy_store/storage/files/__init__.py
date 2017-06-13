from importlib import import_module
from piggy_store.config import config

# hereon I write "directory" but I mean "prefix" in an S3 context

# The $ symbol is not allowed as username, so even if USERS_DIR
# were empty a malicious user could not access that directory
ADMIN_DIR = 'admin$/'
USERS_DIR = 'users/'


def access_user_storage(username):
    file_storage_module = import_module(config['storage']['files']['module'])

    # add a pending / to avoid that a username can be the prefix of another one
    directory = USERS_DIR + username + '/'

    storage = file_storage_module.Storage(directory, config['storage']['files']['params'])
    storage.init()

    return storage


def access_admin_storage():
    file_storage_module = import_module(config['storage']['files']['module'])
    storage = file_storage_module.Storage(ADMIN_DIR, config['storage']['files']['params'])
    storage.init()

    return storage
