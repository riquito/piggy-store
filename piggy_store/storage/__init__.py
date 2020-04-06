from abc import ABCMeta, abstractmethod

from piggy_store.storage.user_entity import User
from piggy_store.storage.files import (
    access_admin_storage,
    access_user_storage,
    compose_challenge_file_filename,
    parse_challenge_file_filename
)
from piggy_store.exceptions import UserNotAllowedError
from piggy_store.config import config

class EasyStorageABC(metaclass=ABCMeta):
    @abstractmethod
    def find_user_by_username(self, username):
        raise NotImplementedError()

    @abstractmethod
    def remove_user(self, user):
        raise NotImplementedError()

    @abstractmethod
    def add_user(self, user):
        raise NotImplementedError()

    @abstractmethod
    def get_user_files(self, user):
        raise NotImplementedError()

    @abstractmethod
    def remove_file_by_filename(self, user, filename):
        raise NotImplementedError()

    @abstractmethod
    def get_presigned_post_policy(self, user, filename):
        raise NotImplementedError()


class EasyStorage(EasyStorageABC):
    def find_user_by_username(self, username):
        file_storage = access_admin_storage()
        challenge_file = file_storage.get_first_matching_file(compose_challenge_file_filename(username, ''))

        user = None
        if challenge_file:
            challenge = file_storage.get_file_content(challenge_file).decode('utf-8')
            answer = parse_challenge_file_filename(challenge_file.get_filename())['answer']
            user = User(username, challenge, answer)

        return user

    def remove_user(self, user):
        user_file_storage = access_user_storage(user.username)
        user_file_storage.remove_multiple((user_file_storage.get_files_list()))

        admin_file_storage = access_admin_storage()
        challenge_file_filename = compose_challenge_file_filename(user.username, user.answer)
        f = admin_file_storage.build_file(challenge_file_filename)
        admin_file_storage.remove_file(f)

    def add_user(self, user):
        if config['users_whitelist'] and not user.username in config['users_whitelist']:
            raise UserNotAllowedError(user.username)

        file_storage = access_admin_storage()
        filename = compose_challenge_file_filename(user.username, user.answer)
        challenge_file = file_storage.build_file(filename, dict(
            content=user.challenge
        ))
        file_storage.add_file(challenge_file)

        stored_challenge = file_storage.get_file_content(challenge_file).decode('utf-8')

        if stored_challenge != user.challenge:
            # it would be better if we could send a checksum client side
            raise Error('XXX we wrongly stored the challenge')

        return stored_challenge

    def get_user_files(self, user):
        return access_user_storage(user.username).get_files_list()

    def remove_file_by_filename(self, user, filename):
        file_storage = access_user_storage(user.username)
        f = file_storage.build_file(filename)
        file_storage.remove_file(f)

    def get_presigned_post_policy(self, user, filename):
        file_storage = access_user_storage(user.username)
        f = file_storage.build_file(filename)
        return file_storage.get_presigned_post_policy(f)

    def get_presigned_retrieve_url(self, user, filename):
        file_storage = access_user_storage(user.username)
        f = file_storage.build_file(filename)
        return file_storage.get_presigned_retrieve_url(f)
