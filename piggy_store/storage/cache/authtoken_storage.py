import json
from datetime import datetime, timedelta

from cryptography import fernet
import redis

from piggy_store.exceptions import (
    TokenInvalidError
)

class AuthTokenStorage:
    __instance = None
    prefix = 'token-'
    key = fernet.Fernet.generate_key()

    def __new__(cls, options, **kwargs):
        if not cls.__instance:
            cls.__instance = object.__new__(cls)
            cls.__instance.conn = redis.StrictRedis(
                host=options['host'],
                port=options['port'],
                db=options['database'],
                decode_responses=True
            )
            cls.__instance.timeout = options['timeout']

        return cls.__instance

    def generate_token(self, dataBag):
        return fernet.Fernet(self.key).encrypt(json.dumps(dataBag).encode('utf-8')).decode('utf-8')

    def decode_token(self, token):
        try:
            return json.loads(fernet.Fernet(self.key).decrypt(token.encode('utf-8')).decode('utf-8'))
        except fernet.InvalidToken:
            raise TokenInvalidError()

    def refresh_user_token(self, username, token):
        #exp_after_n_hours = 1
        #now = datetime.utcnow()
        #timeout = timedelta(hours = exp_after_n_hours)
        return self.conn.setex(self.prefix + username, self.timeout, token)

    def remove_user_token(self, username):
        return self.conn.delete(self.prefix + username)

    def has_user_token(self, username, token):
        return self.conn.get(self.prefix + username) == token
