from piggy_store.storage.user_entity import User
from piggy_store.exceptions import (
    UserExistsError,
    UserDoesNotExistError,
    FileExistsError
)
from piggy_store.storage import EasyStorage, EasyStorageABC

import redis


class Storage(EasyStorageABC):
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
        self._add_user_to_cache(user)

        try:
            return self.es.add_user(user)
        except FileExistsError:
            # e.g. redis restarted, client try to create an existing user

            # We could delete the just created cache entry, and let the client
            # either try to login (and so refresh the cache), or have him retry
            # for some reason again to create the user. To avoid having someone
            # trigger on purpose write/delete continuosly we choose to refresh
            # the cache here now, so that new add_user requests won't write
            # anything anymore.
            self._update_user_cache(self.es.find_user_by_username(user.username))
            raise UserExistsError()

    def _add_user_to_cache(self, user):
        """add the user to the cache atomically"""

        fields_created = self.conn.hsetnx(user.username, 'challenge', user.challenge)
        if fields_created == 0:
            raise UserExistsError()

        self.conn.hset(user.username, 'answer', user.answer)

    def _update_user_cache(self, user):
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
