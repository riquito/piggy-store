from piggy_store.storage.users.user_entity import User
from piggy_store.config import config

if config['storage']['users'] == 'redis':
    from piggy_store.storage.users.redis_storage import RedisStorage
    user_storage = RedisStorage()
else:
    from piggy_store.storage.users.dumb_storage import DumbStorage
    user_storage = DumbStorage()

