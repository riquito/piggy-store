import redis

from piggy_store.exceptions import UserExistsError, UserDoesNotExistError
from piggy_store.storage.users.user_entity import User
from piggy_store.storage.users.storage import Storage as BaseStorage
from piggy_store.storage.files import (
    access_admin_storage,
    access_user_storage,
    compose_challenge_file_filename,
    parse_challenge_file_filename
)


class Storage(BaseStorage):
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
        pass

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

    def _get_challenge_file(self, username):
        file_storage = access_admin_storage()
        filename_prefix = compose_challenge_file_filename(username, '')
        challenge_file = None

        for challenge_file in file_storage.get_files_list(prefix=filename_prefix):
            break

        return challenge_file

    def find_user_by_username(self, username):
        user = None

        # Do we have the user data already cached?
        data = self.conn.hgetall(username)

        if data:
            user = User(username, data['challenge'], data['answer'])
        else:
            # Do we have the user data at all?
            file_storage = access_admin_storage()
            challenge_file = self._get_challenge_file(username)
            if challenge_file:
                challenge = file_storage.get_file_content(challenge_file).decode('utf-8')
                answer = parse_challenge_file_filename(challenge_file.get_filename())['answer']
                user = User(username, challenge, answer)
                self.add_user(user)

        if user is None:
            raise UserDoesNotExistError()

        return user

    def remove_user_by_username(self, username):
        user = self.find_user_by_username(username)
        user_file_storage = access_user_storage(user.username)
        user_file_storage.remove_multiple((user_file_storage.get_files_list()))

        admin_file_storage = access_admin_storage()
        challenge_file_filename = compose_challenge_file_filename(user.username, user.answer)
        f = admin_file_storage.build_file(challenge_file_filename)
        admin_file_storage.remove_file(f)

        self.delete_user(user)
