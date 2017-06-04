from abc import ABCMeta, abstractmethod


class Storage(metaclass=ABCMeta):
    @abstractmethod
    def __init__(self, options):
        raise NotImplementedError()

    @abstractmethod
    def add_user(self, user):
        raise NotImplementedError()

    @abstractmethod
    def find_user_by_username(self, username):
        raise NotImplementedError()
