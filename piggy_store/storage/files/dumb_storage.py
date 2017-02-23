# This is a dumb file storage, meant to be used
# for simple tests and development

from base64 import standard_b64encode

from piggy_store.exceptions import FileExistsError, FileDoesNotExistError
from piggy_store.storage.files.file_entity import FileDTO
from piggy_store.storage.files.storage import Storage
from piggy_store.helper import hash_checksum

_db = {}

class DumbStorage(Storage):
    def __init__(self, options):
        user_dir = options['user_dir']

        if not _db.get(user_dir):
            _db[user_dir] = {}

        self.user_db = _db[user_dir]

    def add_file(self, file_instance):
        if self.user_db.get(file_instance.filename):
            raise FileExistsError()
        else:
            raw_file = file_instance.as_dict()
            if file_instance.content:
                if not raw_file['url']:
                    b64data = standard_b64encode(file_instance.content).decode('ascii')
                    raw_file['url'] = 'data:text/plain;base64,' + b64data

                raw_file['checksum'] = hash_checksum(file_instance.content).hexdigest()

            self.user_db[file_instance.filename] = FileDTO(**raw_file)
            return file_instance
    
    def find_file_by_filename(self, filename, ignore_cache=True):
        file_instance = self.user_db.get(filename)
        if not file_instance:
            raise FileDoesNotExistError()
        else:
            return file_instance

    def get_files(self):
        return self.user_db.values()

