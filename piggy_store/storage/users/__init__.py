from piggy_store.storage.users.user_entity import User
from piggy_store.config import config

if config['storage']['users'] == 'redis':
    from piggy_store.storage.users.redis_storage import RedisStorage
    user_storage = RedisStorage()
else:
    raise NotImplementedError('No such user storage: ' + config['storage']['users'])

