from io import BytesIO
from datetime import timedelta

from minio import Minio
from minio.error import NoSuchKey

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

    def _get_temporary_url(self, object_name):
        return self.client.presigned_get_object(
            self.bucket,
            object_name,
            self.opts['download_url_expire_after']
        )

    def build_file(self, filename, raw_file=None):
        return FileDTO(**(raw_file or {}), object_name=self.user_dir + filename)

    def add_file(self, f):
        object_name = f.object_name

        try:
            self.client.stat_object(self.bucket, object_name)
        except NoSuchKey as e:
            content_stream = BytesIO(f.content)
            etag = self.client.put_object(self.bucket, object_name, content_stream, f.size)
            url = self._get_temporary_url(object_name)

            return f.clone(
                checksum=etag,
                url=url
            )
        else:
            raise FileExistsError()

    def get_files_list(self, prefix=''):
        # XXX self.client list may fail, as list_objects and temprary url
        for obj in self.client.list_objects_v2(self.bucket, self.user_dir + prefix, recursive=True):
            if not obj.etag:
                # e.g. minio without 'erasure'
                obj.etag = self.client.stat_object(self.bucket, obj.object_name).etag

            yield FileDTO(
                object_name=obj.object_name,
                size=obj.size,
                checksum=obj.etag,
                url=self._get_temporary_url(obj.object_name)
            )

    def get_presigned_upload_url(self, f):
        # presigned Put object URL for an object name, expires in 3 days.
        return self.client.presigned_put_object(
            self.bucket,
            f.object_name,
            expires=timedelta(days=3)
        )

    def remove_file(self, f):
        self.client.remove_object(
            self.bucket,
            f.object_name
        )

    def remove_multiple(self, files):
        errors = []
        for error in self.client.remove_objects(
            self.bucket,
            (f.object_name for f in files)
        ):
            errors.append((f, error))

        if errors:
            raise MultipleFilesRemoveError(errors)

    def get_file_content(self, f):
        data = self.client.get_object(self.bucket, f.object_name)
        content = BytesIO()
        for d in data.stream(32 * 1024):
            content.write(d)
        content.seek(0)
        return content.read()

    def get_first_matching_file(self, prefix):
        f = None

        for f in self.get_files_list(prefix=prefix):
            break

        return f
