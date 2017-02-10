from hmac import compare_digest
from datetime import datetime, timedelta
import jwt

from piggy_store.exceptions import (
    ChallengeMismatchError,
    TokenExpiredError,
    TokenInvalidError
)

class Token:
    def __init__(self, username):
        self.username = username

def assert_user_challenge_match(user, challenge):
    if not compare_digest(user.challenge, challenge):
        raise ChallengeMismatchError()

def generate_auth_token(user):
    exp_after_n_hours = 1
    now = datetime.utcnow()
    return jwt.encode(
        {
            'username': user.username,
            'exp': now + timedelta(hours=exp_after_n_hours),
            'iat': now
        },
        'XXX FIXME secret to load from config file', 
        algorithm='HS256'
    ).decode('utf-8')

def decode_auth_token(raw_token):
    try:
        token_payload = jwt.decode(
            raw_token,
            'XXX FIXME secret to load from config file',
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
