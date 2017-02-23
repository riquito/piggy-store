from io import BytesIO

from minio import Minio
from minio.error import ResponseError

from piggy_store.exceptions import FileExistsError, FileDoesNotExistError
from piggy_store.storage.files.file_entity import FileDTO
from piggy_store.storage.files.storage import Storage
from piggy_store.helper import hash_checksum
from piggy_store.config import config

class S3Storage(Storage):
    def __init__(self, options):
        self.opts = options
        self.client = None
        self.user_dir = options['user_dir']
        self.bucket = options['bucket']

    def init(self):
        try:
            self.client = Minio(
                self.opts['host'],
                access_key = self.opts['access_key'],
                secret_key = self.opts['secret_key'],
                secure = self.opts['secure'],
                region = self.opts['region']
            )
            self.client.make_bucket(self.opts['bucket'])
        except ResponseError as e:
            if e.code != 'BucketAlreadyOwnedByYou':
                raise e

    def _get_object_name(self, filename):
        return '{}/{}'.format(self.user_dir, filename)

    def _get_basename(self, object_name):
        return object_name.lstrip(self.user_dir + '/')

    def _get_temporary_url(self, object_name):
        return self.client.presigned_get_object(
            self.bucket,
            object_name,
            self.opts['url_expire_after']
        )

    def add_file(self, f):
        object_name = self._get_object_name(f.filename)

        try:
            self.client.stat_object(self.bucket, object_name)
        except ResponseError as e:
            if e.code == 'NoSuchKey':
                content_stream = BytesIO(f.content)
                etag = self.client.put_object(self.bucket, object_name, content_stream, f.size)
                url = self._get_temporary_url(object_name)

                raw_file = f.as_dict()
                raw_file['checksum'] = etag
                raw_file['url'] = url

                return FileDTO(**raw_file)
            else: 
                raise e # XXX should I encapsulate the exception in PiggyStoreError?
        else:
            raise FileExistsError()
    
    def find_file_by_filename(self, filename, ignore_cache=True):
        object_name = self._get_object_name(filename)
        try:
            obj = self.client.stat_object(self.bucket, object_name)
        except ResponseError as e:
            if e.code == 'NoSuchKey':
                raise FileDoesNotExistError()
            else:
                raise e  # XXX should I encapsulate the exception in PiggyStoreError?

        else:
            return FileDTO(
                filename = self._get_basename(obj.object_name),
                size = obj.size,
                checksum = obj.etag,
                url = self._get_temporary_url(obj.object_name)
            )

    def get_files_list(self):
        # XXX self.client list may fail, as list_objects and temprary url
        for obj in self.client.list_objects_v2(self.bucket, self.user_dir, recursive=True):
            if not obj.etag:
                # e.g. minio without 'erasure'
                obj.etag = self.client.stat_object(self.bucket, obj.object_name).etag

            yield FileDTO(
                filename = self._get_basename(obj.object_name),
                size = obj.size,
                checksum = obj.etag,
                url = self._get_temporary_url(obj.object_name)
            )

