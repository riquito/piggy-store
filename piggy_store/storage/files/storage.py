from abc import ABCMeta, abstractmethod

class Storage(metaclass=ABCMeta):
    def init(self, user_dir, options):
        pass

    @abstractmethod
    def add_file(self, file_instance):
        raise NotImplementedError()

    @abstractmethod
    def find_file_by_filename(self, filename):
        raise NotImplementedError()

    @abstractmethod
    def get_files_list(self):
        raise NotImplementedError()

    @abstractmethod
    def get_presigned_upload_url(self):
        raise NotImplementedError()

    @abstractmethod
    def remove_by_filename(self, filename):
        raise NotImplementedError
