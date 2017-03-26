from piggy_store.storage.files.file_entity import FileDTO
from piggy_store.config import config

if config['storage']['files'] == 's3':
    from piggy_store.storage.files.s3_storage import S3Storage
    def access_file_storage(options):
        if options['user_dir'] != 'admin$':
            options['user_dir'] = 'users/' + options['user_dir']
        storage = S3Storage(dict(
            url_expire_after = config['files']['download_url_expire_after'],
            **config['s3'],
            **options
        ))
        storage.init()
        return storage
else:
    raise NotImplementedError('No such file storage: ' + config['storage']['files'])

