import os
from hmac import compare_digest
from datetime import datetime, timedelta
import re
import jwt

from piggy_store.config import config
from piggy_store.exceptions import (
    TokenExpiredError,
    TokenInvalidError
)


class Token:
    def __init__(self, username):
        self.username = username


def generate_auth_token(user):
    return os.urandom(32).hex()


def assert_is_valid_authorization_header(header):
    if not re.match('^Bearer [a-zA-Z0-9/+~_.-]+=*$', header):
        raise TokenInvalidError()

def get_access_token_from_authorization_header(header):
    return header.split(' ')[1]
