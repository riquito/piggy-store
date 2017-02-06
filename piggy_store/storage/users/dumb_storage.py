# This is a dumb memory storage, meant to be used
# for simple tests and development

from piggy_store.exceptions import UserExistsError
from piggy_store.storage.users.user_entity import User
from piggy_store.storage.users.storage import Storage


_db = {}

class DumbStorage(Storage):
    def add_user(self, user):
        if _db.get(user.username):
            raise UserExistsError()
        else:
            _db[user.username] = {
                'challenge': user.challenge
            }

    def find_user_by_username(self, username):
        data = _db.get(username)
        if not data:
            raise UserDoesNotExistError()
        else:
            return User(username, data['challenge'])
