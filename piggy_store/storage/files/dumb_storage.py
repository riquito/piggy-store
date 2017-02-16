# This is a dumb file storage, meant to be used
# for simple tests and development

from base64 import standard_b64encode
from hashlib import sha1

from piggy_store.exceptions import FileExistsError, FileDoesNotExistError
from piggy_store.storage.files.file_entity import FileDTO
from piggy_store.storage.files.storage import Storage

_db = {}

class DumbStorage(Storage):
    def __init__(self, options):
        location = options['location']
        self.user_db = {}
        _db[location] = self.user_db

    def add_file(self, file_instance):
        if self.user_db.get(file_instance.id):
            raise FileExistsError()
        else:
            raw_file = file_instance.as_dict()
            if file_instance.content:
                if not raw_file['url']:
                    b64data = standard_b64encode(file_instance.content).decode('ascii')
                    raw_file['url'] = 'data:text/plain;base64,' + b64data

                raw_file['checksum'] = sha1(file_instance.content).hexdigest()

            self.user_db[file_instance.id] = FileDTO(**raw_file)
            return file_instance
    
    def find_file_by_id(self, id, ignore_cache=True):
        file_instance = self.user_db.get(id)
        if not file_instance:
            raise FileDoesNotExistError()
        else:
            return file_instance

