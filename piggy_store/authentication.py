from hmac import compare_digest
from datetime import datetime, timedelta
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
    exp_after_n_hours = 1
    now = datetime.utcnow()
    return jwt.encode(
        {
            'username': user.username,
            'exp': now + timedelta(hours=exp_after_n_hours),
            'iat': now
        },
        config['secret'],
        algorithm='HS256'
    ).decode('utf-8')

def decode_auth_token(raw_token):
    try:
        token_payload = jwt.decode(
            raw_token,
            config['secret'],
            algorithms=['HS256']
        )

        return Token(
            username = token_payload['username']
        )

    except jwt.ExpiredSignatureError:
        raise TokenExpiredError()
    except jwt.exceptions.DecodeError:
        raise TokenInvalidError()
    except KeyError:
        raise TokenInvalidError()
