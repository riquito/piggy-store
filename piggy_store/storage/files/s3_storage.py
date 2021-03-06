from io import BytesIO
from datetime import datetime, timedelta

from minio import Minio, PostPolicy
from minio.error import NoSuchKey, AccessDenied
from urllib3.exceptions import MaxRetryError

from piggy_store.exceptions import (
    FileExistsError,
    MultipleFilesRemoveError,
    BucketAccessTimeoutError,
    BucketAccessDeniedError,
    BucketDoesNotExistError,
    BucketWriteError
)
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

    def check_bucket(self):
        try:
            if not self.client.bucket_exists(self.bucket):
                raise BucketDoesNotExistError(self.bucket)
        except AccessDenied:
            raise BucketAccessDeniedError()
        except MaxRetryError:
            raise BucketAccessTimeoutError()

        f = self.build_file('.check-bucket-permissions')

        try:
            try: self.add_file(f)
            except FileExistsError: pass
            self.remove_file(f)
        except Error:
            raise BucketWriteError()

    def build_file(self, filename, raw_file=None):
        return FileDTO(**(raw_file or {}), object_name=self.user_dir + filename)

    def add_file(self, f):
        object_name = f.object_name

        try:
            self.client.stat_object(self.bucket, object_name)
        except NoSuchKey as e:
            content_stream = BytesIO(f.content)
            etag = self.client.put_object(self.bucket, object_name, content_stream, f.size)
            url = self.get_presigned_retrieve_url(f)

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
                url=self.get_presigned_retrieve_url(obj)
            )

    def get_presigned_post_policy(self, f):
        # presigned POST formdata for an object name, expires in 5 minutes.
        # Use POST policy instead of the simpler presigned_put_object because
        # it allows to set an upper limit on the uploaded file size.

        post_policy = PostPolicy()
        post_policy.set_bucket_name(self.bucket)
        post_policy.set_key(f.object_name)
        # content length accepted range, in bytes
        post_policy.set_content_length_range(10, 1024 * 1024)

        expires_date = datetime.utcnow() + timedelta(minutes=5)
        post_policy.set_expires(expires_date)

        url_str, signed_form_data = self.client.presigned_post_policy(post_policy)
        return url_str, signed_form_data

    def get_presigned_retrieve_url(self, f):
        # presigned GET object URL for an object name.
        return self.client.presigned_get_object(
            self.bucket,
            f.object_name,
            self.opts['download_url_expire_after']
        )

    def remove_file(self, f):
        self.client.remove_object(
            self.bucket,
            f.object_name
        )

    def remove_multiple(self, files):
        errors = []
        files = [f for f in files]
        for i, error in enumerate(self.client.remove_objects(
            self.bucket,
            (f.object_name for f in files)
        )):
            errors.append((files[i], error))

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
