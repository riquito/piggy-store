from hmac import compare_digest
from datetime import datetime, timedelta
import jwt

from piggy_store.exceptions import ChallengeMismatchError

def assert_user_challenge_match(user, challenge):
    if not compare_digest(user.challenge, challenge):
        raise ChallengeMismatchError()

def generate_auth_token(username, challenge):
    exp_after_n_hours = 1
    now = datetime.utcnow()
    return jwt.encode(
        {
            'username': username,
            'exp': now + timedelta(hours=exp_after_n_hours),
            'iat': now
        },
        'XXX FIXME secret to load from config file', 
        algorithm='HS256'
    ).decode('utf-8')

