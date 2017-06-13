from abc import ABCMeta, abstractmethod


class Storage(metaclass=ABCMeta):
    def init(self, user_dir, options):
        pass

    @abstractmethod
    def add_file(self, file_instance):
        raise NotImplementedError()

    @abstractmethod
    def get_files_list(self):
        raise NotImplementedError()

    @abstractmethod
    def get_presigned_upload_url(self):
        raise NotImplementedError()

    @abstractmethod
    def remove_file(self, file_instance):
        raise NotImplementedError

    @abstractmethod
    def remove_multiple(self, files_iterator):
        raise NotImplementedError
