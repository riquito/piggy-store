from piggy_store.storage.users import User
from piggy_store.exceptions import UserExistsError, UserDoesNotExistError
from piggy_store.storage import EasyStorage

import redis


class Storage():
    __instance = None

    def __new__(cls, options, **kwargs):
        if not cls.__instance:
            cls.__instance = object.__new__(cls)
            cls.conn = redis.StrictRedis(
                host=options['host'],
                port=options['port'],
                db=options['database'],
                decode_responses=True
            )

        return cls.__instance

    def __init__(self, *args, **kwargs):
        self.es = EasyStorage()

    def add_user(self, user):
        if self.conn.exists(user.username):
            raise UserExistsError()
        else:
            self.conn.hmset(user.username, {
                'challenge': user.challenge,
                'answer': user.answer
            })

    def delete_user(self, user):
        if not self.conn.exists(user.username):
            raise UserDoesNotExistError()
        else:
            self.conn.delete(user.username)

    def find_user_by_username(self, username):
        user = None

        # Do we have the user data already cached?
        data = self.conn.hgetall(username)

        if data:
            user = User(username, data['challenge'], data['answer'])
        else:
            # Do we have the user data at all?
            user = self.es.find_user_by_username(username)
            if user:
                # found, let's cache it
                self.add_user(user)

        if user is None:
            raise UserDoesNotExistError()

        return user

    def remove_user_by_username(self, username):
        user = self.find_user_by_username(username)
        if user:
            self.es.remove_user(user)
            self.delete_user(user)
