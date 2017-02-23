from abc import ABCMeta, abstractmethod

class Storage(metaclass=ABCMeta):
    def init(self):
        pass

    @abstractmethod
    def add_file(self, file_instance):
        raise NotImplementedError()

    @abstractmethod
    def find_file_by_filename(self, filename):
        raise NotImplementedError()
