from hmac import compare_digest
from datetime import datetime, timedelta
import jwt

from piggy_store.exceptions import ChallengeMismatchError

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

