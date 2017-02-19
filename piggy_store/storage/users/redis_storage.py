from piggy_store.exceptions import UserExistsError, UserDoesNotExistError
from piggy_store.storage.users.user_entity import User
from piggy_store.storage.users.storage import Storage
from piggy_store.redis_connect import conn

class RedisStorage(Storage):
    def add_user(self, user):
        if conn.exists(user.username):
            raise UserExistsError()
        else:
            conn.hset(user.username, 'challenge', user.challenge)

    def find_user_by_username(self, username):
        data = conn.hgetall(username)
        if not data:
            raise UserDoesNotExistError()
        else:
            return User(username, data['challenge'])

