from piggy_store.storage.users import User
from piggy_store.storage.files import (
    access_admin_storage,
    access_user_storage,
    compose_challenge_file_filename,
    parse_challenge_file_filename
)


class EasyStorage:
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
