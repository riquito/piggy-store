import re

from piggy_store.exceptions import (
    UsernameError,
    FieldRequiredError,
    FieldTypeError,
    FieldEmptyError
)

def new_user_validator(payload):
    _validate_has_attrs(payload, ['username', 'challenge'])
    _validate_is_string('username', payload['username'])
    _validate_is_string('challenge', payload['challenge'])
    
    username = payload['username'].strip()

    _validate_is_not_empty('username', username)
    _validate_is_not_empty('challenge', payload['challenge'])

    _validate_username_format(username)

    return dict(
        username = username,
        challenge = payload['challenge']
    )

def auth_user_validator(payload):
    _validate_has_attrs(payload, ['challenge'])
    _validate_is_not_empty('challenge', payload['challenge'])
    return dict(challenge = payload['challenge'])

def _validate_has_attrs(data, attrs):
    for attr_name in attrs:
        if not data.get(attr_name):
            raise FieldRequiredError(attr_name)

def _validate_is_string(field_name, wannabetext):
    if not isinstance(wannabetext, str):
        raise FieldTypeError(field_name, 'string')

def _validate_username_format(username):
    if not re.match('^[a-zA-Z0-9][a-zA-Z0-9_-]+$', username):
        raise UsernameError()

def _validate_is_not_empty(field_name, text):
    if not len(text) > 0:
        raise FieldEmptyError(field_name)

