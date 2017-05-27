import redis

from piggy_store.exceptions import UserExistsError, UserDoesNotExistError
from piggy_store.storage.users.user_entity import User
from piggy_store.storage.users.storage import Storage as BaseStorage
from piggy_store.storage.files import access_admin_storage

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
            self.conn.hmset(user.username, {
                'challenge': user.challenge,
                'answer': user.answer
            })

    def _get_challenge_file(self, username):
        file_storage = access_admin_storage()
        filename_prefix = 'challenge_{}_'.format(username)
        challenge_file = None

        for challenge_file in file_storage.get_files_list(prefix=filename_prefix):
            break

        return challenge_file

    def _get_answer_from_filename(self, filename):
        return filename.split('_', 2)[-1]

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
                challenge = file_storage.get_file_content(challenge_file.filename).decode('utf-8')
                answer = self._get_answer_from_filename(challenge_file.filename)
                user = User(username, challenge, answer)
                self.add_user(user)

        if user is None:
            raise UserDoesNotExistError()

        return user

    def get_answer_to_challenge(self, user):
        answer = None

        # Do we have the user data already cached?
        data = self.conn.hgetall(user.username)
        if data:
            answer = data['answer']
        else:
            file_storage = access_admin_storage()
            challenge_file = self._get_challenge_file(username)
            if challenge_file:
                answer = self._get_answer_from_filename(challenge_file.filename)

        return answer
