import re

from piggy_store.exceptions import (
    TokenInvalidError,
    UsernameFormatError,
    FieldRequiredError,
    FieldTypeError,
    FieldEmptyError,
    FieldLengthError,
    FieldMaxLengthError,
    FieldHexError
)


def new_user_validator(payload):
    _validate_has_attrs(payload, ['username', 'challenge', 'answer'])

    username = _validate_username('username', payload['username'])

    _validate_is_string('challenge', payload['challenge'])
    _validate_is_string('answer', payload['answer'])
    _validate_is_exact_length('answer', payload['answer'], 32)
    _validate_is_hex_format('answer', payload['answer'])
    _validate_is_not_empty('challenge', payload['challenge'])
    _validate_is_not_empty('answer', payload['answer'])

    return dict(
        username=username,
        challenge=payload['challenge'],
        answer=payload['answer']
    )


def auth_user_request_challenge_validator(payload):
    _validate_has_attrs(payload, ['username'])
    username = _validate_username('username', payload['username'])

    return dict(
        username=username
    )


def auth_user_answer_challenge_validator(payload):
    _validate_has_attrs(payload, ['username', 'answer'])
    _validate_is_string('answer', payload['answer'])

    username = _validate_username('username', payload['username'])

    return dict(
        username=username,
        answer=payload['answer']
    )


def request_upload_url_validator(payload):
    _validate_has_attrs(payload, ['filename'])
    _validate_is_string('filename', payload['filename'])
    _validate_is_not_empty('filename', payload['filename'])

    return dict(
        filename=payload['filename']
    )


def file_delete_validator(payload):
    _validate_has_attrs(payload, ['filename'])
    _validate_is_string('filename', payload['filename'])
    _validate_is_not_empty('filename', payload['filename'])

    return dict(
        filename=payload['filename']
    )


def _validate_has_attrs(data, attrs):
    for attr_name in attrs:
        if data.get(attr_name) is None:
            raise FieldRequiredError(attr_name)


def _validate_is_string(field_name, wannabetext):
    if not isinstance(wannabetext, str):
        raise FieldTypeError(field_name, 'string')


def _validate_username_format(username):
    if not re.match('^[a-z0-9][a-z0-9_-]*$', username):
        raise UsernameFormatError()


def _validate_is_not_empty(field_name, text):
    if not len(text) > 0:
        raise FieldEmptyError(field_name)


def _validate_is_exact_length(field_name, text, length):
    if not len(text) == length:
        raise FieldLengthError(field_name, length)

def _validate_is_at_most_length(field_name, text, length):
    if len(text) > length:
        raise FieldMaxLengthError(field_name, length)

def _validate_is_hex_format(field_name, text):
    try:
        int(text, 16)
    except ValueError:
        raise FieldHexError(field_name)

def _validate_username(field_name, unclean_username):
    _validate_is_string(field_name, unclean_username)

    username = unclean_username.strip()
    username = username.lower()

    _validate_is_not_empty(field_name, username)
    _validate_is_at_most_length(field_name, username, 50)
    _validate_username_format(username)

    return username
