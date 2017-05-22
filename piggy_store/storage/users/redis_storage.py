import redis

from piggy_store.exceptions import UserExistsError, UserDoesNotExistError
from piggy_store.storage.users.user_entity import User
from piggy_store.storage.users.storage import Storage as BaseStorage

class Storage(BaseStorage):
    __instance = None

    def __new__(cls, options, **kwargs):
        if not cls.__instance:
            print('create instance')
            cls.__instance = object.__new__(cls)
            cls.conn = redis.StrictRedis(
                host = options['host'],
                port = options['port'],
                db = options['database'],
                decode_responses = True
            )

        return cls.__instance

    def __init__(self, *args, **kwargs):
        pass

    def add_user(self, user):
        if self.conn.exists(user.username):
            raise UserExistsError()
        else:
            self.conn.hset(user.username, 'challenge', user.challenge)

    def find_user_by_username(self, username):
        data = self.conn.hgetall(username)
        if not data:
            raise UserDoesNotExistError()
        else:
            return User(username, data['challenge'])

