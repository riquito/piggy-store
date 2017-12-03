class PiggyStoreError(Exception):
    CODE = 0
    MESSAGE = 'Internal Error'

    def __init__(self, code=None, message=None):
        self.code = code or self.CODE
        self.message = message or self.MESSAGE

    def __str__(self):
        return '{} {}'.format(self.code, self.message)


class UserExistsError(PiggyStoreError):
    CODE = 1000
    MESSAGE = 'User already exists'


class UsernameError(PiggyStoreError):
    CODE = 1001
    MESSAGE = 'Username is not valid'


class FieldRequiredError(PiggyStoreError):
    CODE = 1002
    MESSAGE = 'This field is required: {}'

    def __init__(self, field_name):
        super().__init__(self.CODE, self.MESSAGE.format(field_name))


class FieldTypeError(PiggyStoreError):
    CODE = 1003
    MESSAGE = 'Expected {} to be a {}'

    def __init__(self, field_name, type_expected):
        super().__init__(self.CODE, self.MESSAGE.format(field_name, type_expected))


class FieldEmptyError(PiggyStoreError):
    CODE = 1004
    MESSAGE = 'Expected {} to not be empty'

    def __init__(self, field_name):
        super().__init__(self.CODE, self.MESSAGE.format(field_name))


class UserDoesNotExistError(PiggyStoreError):
    CODE = 1005
    MESSAGE = 'The user does not exist'


class ChallengeMismatchError(PiggyStoreError):
    CODE = 1006
    MESSAGE = 'The challenge does not match'


class TokenExpiredError(PiggyStoreError):
    CODE = 1007
    MESSAGE = 'The token has expired'


class TokenInvalidError(PiggyStoreError):
    CODE = 1008
    MESSAGE = 'The token is not valid'


class FileExistsError(PiggyStoreError):
    CODE = 1009
    MESSAGE = 'A file with that name already exists'


class FieldLengthError(PiggyStoreError):
    CODE = 1011
    MESSAGE = 'Expected {} to be {} characters long'

    def __init__(self, field_name, length):
        super().__init__(self.CODE, self.MESSAGE.format(field_name, length))


class FieldHexError(PiggyStoreError):
    CODE = 1012
    MESSAGE = 'This field is not in hex format: {}'

    def __init__(self, field_name):
        super().__init__(self.CODE, self.MESSAGE.format(field_name))


class MultipleFilesRemoveError(PiggyStoreError):
    CODE = 1013
    MESSAGE = 'There was an error deleting some files: {}'

    def __init__(self, pairs_file_error):
        super().__init__(
            self.CODE,
            self.MESSAGE.format(
                ', '.join(
                    '%s [%s:%s]' %
                    (error.object_name,
                     error.error_code,
                     error.error_message) for f,
                    error in pairs_file_error)))


class UserNotAllowedError(PiggyStoreError):
    CODE = 1014
    MESSAGE = 'The user is not allowed: {}'

    def __init__(self, username):
        super().__init__(self.CODE, self.MESSAGE.format(username))


class BucketDoesNotExistError(PiggyStoreError):
    CODE = 1015
    MESSAGE = 'The configured bucket does not exist: {}'

    def __init__(self, bucketname):
        super().__init__(self.CODE, self.MESSAGE.format(bucketname))


class BucketPolicyError(PiggyStoreError):
    CODE = 1016
    MESSAGE = 'The configured bucket does not allow either upload or download'

class BucketAccessDeniedError(PiggyStoreError):
    CODE = 1017
    MESSAGE = 'The access to the bucket is denied'

class BucketAccessTimeoutError(PiggyStoreError):
    CODE = 1018
    MESSAGE = 'Request timed out when trying to access the bucket'
