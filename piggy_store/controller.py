from flask import Blueprint, abort, request, url_for
from flask_json import FlaskJSON, as_json
from werkzeug.local import LocalProxy
from functools import wraps

from piggy_store.storage.user_entity import User
from piggy_store.validators import (
    new_user_validator,
    auth_user_request_challenge_validator,
    auth_user_answer_challenge_validator,
    request_upload_url_validator,
    file_delete_validator
)
from piggy_store.authentication import (
    assert_is_valid_authorization_header,
    get_access_token_from_authorization_header
)
from piggy_store.storage.cache import get_cache_storage, get_token_storage
from piggy_store.exceptions import (
    UserExistsError,
    ChallengeMismatchError,
    TokenExpiredError
)

bp = blueprint = Blueprint('controller', __name__)
db = LocalProxy(get_cache_storage)
tokenDb = LocalProxy(get_token_storage)

def authentication(func):
    @wraps(func)
    def pass_valid_token(*args, **kwargs):
        authorization_header = request.headers.get('Authorization', '')
        assert_is_valid_authorization_header(authorization_header)
        token = get_access_token_from_authorization_header(authorization_header)
        tokenBag = tokenDb.decode_token(token)
        if not tokenDb.has_user_token(tokenBag['username'], token):
            raise TokenExpiredError()
        return func(tokenBag, *args, **kwargs)
    return pass_valid_token

@bp.route('/', methods=['GET'])
@as_json
def root():
    return {
        'links': {
            **hateoas_auth_user_request_challenge(),
            **hateoas_new_user()
        }
    }


@bp.route('/files/', methods=['GET'])
@as_json
@authentication
def list_user_files(tokenBag):
    user = db.find_user_by_username(tokenBag['username'])
    files = db.get_user_files(user)

    return {
        'content': [
            {
                'content': f.as_dict(),
                'links': {
                    **hateoas_file_read(f),
                    **hateoas_file_delete()
                }
            } for f in files
        ]
    }


@bp.route('/users/', methods=['POST'])
@as_json
def new_user():
    unsafe_payload = request.get_json() or {}
    payload = new_user_validator(unsafe_payload)
    user = User(payload['username'], payload['challenge'], payload['answer'])
    stored_challenge = db.add_user(user)
    token = tokenDb.generate_token({ 'username': user.username })
    tokenDb.refresh_user_token(user.username, token)

    return {
        'content': {
            'token': token,
            'challenge': stored_challenge
        },
        'links': {
            **hateoas_list_user_files(),
            **hateoas_request_upload_url()
        }
    }


@bp.route('/users/', methods=['DELETE'])
@as_json
@authentication
def delete_user(tokenBag):
    user = db.find_user_by_username(tokenBag['username'])
    tokenDb.remove_user_token(user.username)
    db.remove_user(user)

    return {
        'links': {
            **hateoas_new_user()
        }
    }


@bp.route('/auth/request-challenge', methods=['GET'])
@as_json
def auth_user_request_challenge():
    unsafe_payload = request.args
    payload = auth_user_request_challenge_validator(unsafe_payload)
    user = db.find_user_by_username(payload['username'])

    return {
        'content': {
            'challenge': user.challenge
        },
        'links': {
            **hateoas_new_user(),
            **hateoas_auth_user_answer_challenge()
        }
    }


@bp.route('/auth/answer-challenge', methods=['POST'])
@as_json
def auth_user_answer_challenge():
    unsafe_payload = request.get_json() or {}
    payload = auth_user_answer_challenge_validator(unsafe_payload)
    user = db.find_user_by_username(payload['username'])
    correct_answer = user.answer

    if payload['answer'] != correct_answer:
        raise ChallengeMismatchError()

    token = tokenDb.generate_token({ 'username': user.username })
    tokenDb.refresh_user_token(user.username, token)

    return {
        'content': {
            'token': token
        },
        'links': {
            **hateoas_list_user_files(),
            **hateoas_request_upload_url()
        }
    }


@bp.route('/files/', methods=['DELETE'])
@as_json
@authentication
def file_delete(tokenBag):
    unsafe_payload = request.get_json() or {}
    payload = file_delete_validator(unsafe_payload)
    user = db.find_user_by_username(tokenBag['username'])
    db.remove_file_by_filename(user, payload['filename'])
    return {}


@bp.route('/files/request-upload-url', methods=['POST'])
@as_json
@authentication
def request_upload_url(tokenBag):
    unsafe_payload = request.get_json() or {}
    payload = request_upload_url_validator(unsafe_payload)
    user = db.find_user_by_username(tokenBag['username'])
    upload_url = db.get_presigned_upload_url(user, payload['filename'])

    return {
        'links': {
            'upload_url': {
                'rel': 'file',
                'href': upload_url
            }
        }
    }


def hateoas_auth_user_request_challenge():
    return {
        'request_auth_challenge': {
            'rel': 'auth',
            'href': url_for('controller.auth_user_request_challenge', _external=True)
        }
    }


def hateoas_auth_user_answer_challenge():
    return {
        'answer_auth_challenge': {
            'rel': 'auth',
            'href': url_for('controller.auth_user_answer_challenge', _external=True)
        }
    }


def hateoas_new_user():
    return {
        'create_user': {
            'rel': 'user',
            'href': url_for('controller.new_user', _external=True)
        }
    }


def hateoas_list_user_files():
    return {
        'files_list': {
            'rel': 'file',
            'href': url_for('controller.list_user_files', _external=True)
        }
    }


def hateoas_file_delete():
    return {
        'delete': {
            'rel': 'file',
            'href': url_for('controller.file_delete', _external=True)
        }
    }


def hateoas_file_read(f):
    return {
        'read': {
            'rel': 'file',
            'href': f.url
        }
    }


def hateoas_request_upload_url():
    return {
        'request_upload_url': {
            'rel': 'file',
            'href': url_for('controller.request_upload_url', _external=True)
        }
    }
