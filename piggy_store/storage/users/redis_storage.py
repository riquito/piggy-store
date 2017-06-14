from piggy_store.storage.users import User
from piggy_store.exceptions import (
    UserExistsError,
    UserDoesNotExistError,
    FileExistsError
)
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
            try:
                result = self.es.add_user(user)
                self._add_user_to_cache(user)
                return result
            except FileExistsError:
                # somehow we lost the cached version, let's reload it
                # and fix the cache
                user = self.es.find_user_by_username(user.username)
                self._add_user_to_cache(user)
                raise UserExistsError()

    def _add_user_to_cache(self, user):
        self.conn.hmset(user.username, {
            'challenge': user.challenge,
            'answer': user.answer
        })

    def remove_user(self, user):
        # XXX it's safe to call conn.delete() even if the key is missing
        self.conn.delete(user.username)
        self.es.remove_user(user)

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
                self._add_user_to_cache(user)

        if user is None:
            raise UserDoesNotExistError()

        return user

    def get_user_files(self, user):
        return self.es.get_user_files(user)

    def remove_file_by_filename(self, user, filename):
        return self.es.remove_file_by_filename(user, filename)

    def get_presigned_upload_url(self, user, filename):
        return self.es.get_presigned_upload_url(user, filename)
