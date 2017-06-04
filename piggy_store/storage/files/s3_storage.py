from io import BytesIO
from datetime import timedelta

from minio import Minio
from minio.error import ResponseError

from piggy_store.exceptions import FileExistsError, MultipleFilesRemoveError
from piggy_store.storage.files.file_entity import FileDTO
from piggy_store.storage.files.storage import Storage as BaseStorage


class Storage(BaseStorage):
    def __init__(self, user_dir, options):
        self.client = None
        self.user_dir = user_dir
        self.bucket = options['bucket']
        self.opts = options

    def init(self):
        self.client = Minio(
            self.opts['host'],
            access_key=self.opts['access_key'],
            secret_key=self.opts['secret_key'],
            secure=self.opts['secure'],
            region=self.opts['region']
        )

    def _get_object_name(self, filename):
        return '{}{}'.format(self.user_dir, filename)

    def _get_basename(self, object_name):
        return object_name[len(self.user_dir):]

    def _get_temporary_url(self, object_name):
        return self.client.presigned_get_object(
            self.bucket,
            object_name,
            self.opts['download_url_expire_after']
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
                raise e  # XXX should I encapsulate the exception in PiggyStoreError?
        else:
            raise FileExistsError()

    def get_files_list(self, prefix=''):
        # XXX self.client list may fail, as list_objects and temprary url
        for obj in self.client.list_objects_v2(self.bucket, self.user_dir + prefix, recursive=True):
            if not obj.etag:
                # e.g. minio without 'erasure'
                obj.etag = self.client.stat_object(self.bucket, obj.object_name).etag

            yield FileDTO(
                filename=self._get_basename(obj.object_name),
                size=obj.size,
                checksum=obj.etag,
                url=self._get_temporary_url(obj.object_name)
            )

    def get_presigned_upload_url(self, filename):
        # presigned Put object URL for an object name, expires in 3 days.
        try:
            return self.client.presigned_put_object(
                self.bucket,
                self._get_object_name(filename),
                expires=timedelta(days=3)
            )
        # Response error is still possible since internally presigned does get
        # bucket location.
        except ResponseError as e:
            raise e

    def remove_by_filename(self, filename):
        self.client.remove_object(
            self.bucket,
            self._get_object_name(filename)
        )

    def remove_multiple(self, files):
        errors = []
        for error in self.client.remove_objects(
            self.bucket,
            (self._get_object_name(f.filename) for f in files)
        ):
            errors.append((f, error))

        if errors:
            raise MultipleFilesRemoveError(errors)

    def get_file_content(self, filename):
        data = self.client.get_object(self.bucket, self._get_object_name(filename))
        content = BytesIO()
        for d in data.stream(32 * 1024):
            content.write(d)
        content.seek(0)
        return content.read()
