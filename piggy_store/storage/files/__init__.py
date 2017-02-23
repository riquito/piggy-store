from piggy_store.storage.files.file_entity import FileDTO
from piggy_store.config import config

if config['storage']['files'] == 's3':
    from piggy_store.storage.files.s3_storage import S3Storage
    def access_file_storage(options):
        storage = S3Storage(dict(
            url_expire_after = config['files']['download_url_expire_after'],
            **config['s3'],
            **options
        ))
        storage.init()
        return storage
else:
    from piggy_store.storage.files.dumb_storage import DumbStorage
    access_file_storage = DumbStorage

