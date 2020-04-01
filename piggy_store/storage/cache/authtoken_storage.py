import os
import json
from datetime import datetime, timedelta
import base64

from cryptography import fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import redis

from piggy_store.exceptions import (
    TokenInvalidError
)

kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    iterations=100000,
    salt=b'not important in this use case',
    backend=default_backend()
)

class AuthTokenStorage:
    __instance = None
    prefix = 'token-'

    def __new__(cls, options, **kwargs):
        if not cls.__instance:
            cls.__instance = object.__new__(cls)

            if options['host'].startswith('redis://'):
                cls.__instance.conn = redis.from_url(
                    options['host'],
                    db=options['database'],
                    decode_responses=True
                )
            else:
                cls.__instance.conn = redis.Redis(
                    host=options['host'],
                    port=options['port'],
                    db=options['database'],
                    decode_responses=True
                )

            cls.__instance.timeout = options['timeout']
            cls.__instance.key = base64.urlsafe_b64encode(kdf.derive(options['secret'].encode('utf-8')))

        return cls.__instance

    def generate_token(self, dataBag):
        return fernet.Fernet(self.key).encrypt(json.dumps(dataBag).encode('utf-8')).decode('utf-8')

    def decode_token(self, token):
        try:
            return json.loads(fernet.Fernet(self.key).decrypt(token.encode('utf-8')).decode('utf-8'))
        except fernet.InvalidToken:
            raise TokenInvalidError()

    def refresh_user_token(self, username, token):
        return self.conn.setex(self.prefix + username, self.timeout, token)

    def remove_user_token(self, username):
        return self.conn.delete(self.prefix + username)

    def has_user_token(self, username, token):
        return self.conn.get(self.prefix + username) == token
