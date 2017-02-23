from datetime import datetime, timedelta
import jwt

from piggy_store.config import config
from piggy_store.exceptions import (
    TokenExpiredError,
    TokenInvalidError
)

class UploadToken:
    def __init__(self, username, filename):
        self.username = username
        self.filename = filename

def generate_upload_token(username, filename):
    exp_after_n_minutes = 85
    now = datetime.utcnow()
    return jwt.encode(
        {
            'username': username,
            'filename': filename,
            'exp': now + timedelta(minutes=exp_after_n_minutes),
            'iat': now
        },
        config['secret'],
        algorithm='HS256'
    ).decode('utf-8')

def decode_upload_token(raw_token):
    try:
        token_payload = jwt.decode(
            raw_token,
            config['secret'],
            algorithms=['HS256']
        )

        return UploadToken(
            username = token_payload['username'],
            filename = token_payload['filename']
        )

    except jwt.ExpiredSignatureError:
        raise TokenExpiredError()
    except jwt.exceptions.DecodeError:
        raise TokenInvalidError()
    except KeyError:
        raise TokenInvalidError()

