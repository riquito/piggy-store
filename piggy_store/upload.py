from datetime import datetime, timedelta
import jwt

from piggy_store.exceptions import (
    TokenExpiredError,
    TokenInvalidError
)

class UploadToken:
    def __init__(self, username, filename, checksum):
        self.username = username
        self.filename = filename
        self.checksum = checksum

def generate_upload_token(user, filename, checksum):
    exp_after_n_minutes = 85
    now = datetime.utcnow()
    return jwt.encode(
        {
            'username': user.username,
            'filename': filename,
            'checksum': checksum,
            'exp': now + timedelta(minutes=exp_after_n_minutes),
            'iat': now
        },
        'XXX FIXME secret to load from config file', 
        algorithm='HS256'
    ).decode('utf-8')

def decode_upload_token(raw_token):
    try:
        token_payload = jwt.decode(
            raw_token,
            'XXX FIXME secret to load from config file',
            algorithms=['HS256']
        )

        return UploadToken(
            username = token_payload['username'],
            filename = token_payload['filename'],
            checksum = token_payload['checksum']
        )

    except jwt.ExpiredSignatureError:
        raise TokenExpiredError()
    except jwt.exceptions.DecodeError:
        raise TokenInvalidError()
    except KeyError:
        raise TokenInvalidError()

