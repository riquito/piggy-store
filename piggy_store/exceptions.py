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

class FileDoesNotExistError(PiggyStoreError):
    CODE = 1010
    MESSAGE = 'A file with that name does not exist'

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

