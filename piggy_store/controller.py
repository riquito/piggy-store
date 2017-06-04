from flask import Blueprint, abort, request, url_for
from flask_json import FlaskJSON, as_json

from piggy_store.storage.users import get_user_storage, User
from piggy_store.validators import (
    delete_user_validator,
    new_user_validator,
    auth_user_request_challenge_validator,
    auth_user_answer_challenge_validator,
    list_user_files_validator,
    request_upload_url_validator,
    file_delete_validator
)
from piggy_store.authentication import generate_auth_token, decode_auth_token
from piggy_store.storage.files import access_admin_storage, access_user_storage
from piggy_store.storage.files.file_entity import FileDTO
from piggy_store.exceptions import UserExistsError, ChallengeMismatchError

bp = blueprint = Blueprint('controller', __name__)


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
def list_user_files():
    unsafe_payload = request.args
    payload = list_user_files_validator(unsafe_payload)
    token = decode_auth_token(payload['jwt'])
    user = get_user_storage().find_user_by_username(token.username)
    file_storage = access_user_storage(user.username)
    files = file_storage.get_files_list()

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


@bp.route('/user/', methods=['POST'])
@as_json
def new_user():
    unsafe_payload = request.get_json() or {}
    payload = new_user_validator(unsafe_payload)
    user = User(payload['username'], payload['challenge'], payload['answer'])
    get_user_storage().add_user(user)
    file_storage = access_admin_storage()
    filename = 'challenge_{}_{}'.format(user.username, payload['answer'])
    challenge_file = FileDTO(
        filename=filename,
        content=payload['challenge']
    )
    file_storage.add_file(challenge_file)

    stored_challenge = file_storage.get_file_content(filename).decode('utf-8')

    if stored_challenge != payload['challenge']:
        # it would be better if we could send a checksum client side
        raise Error('XXX we wrongly stored the challenge')

    return {
        'content': {
            'token': generate_auth_token(user),
            'challenge': stored_challenge
        },
        'links': {
            **hateoas_list_user_files(),
            **hateoas_request_upload_url()
        }
    }


@bp.route('/user/', methods=['DELETE'])
@as_json
def delete_user():
    unsafe_payload = request.get_json() or {}
    payload = delete_user_validator(unsafe_payload)
    token = decode_auth_token(payload['jwt'])
    get_user_storage().remove_user_by_username(token.username)

    return {
        'links': {
            **hateoas_new_user()
        }
    }


@bp.route('/user/auth/request-challenge', methods=['GET'])
@as_json
def auth_user_request_challenge():
    unsafe_payload = request.args
    payload = auth_user_request_challenge_validator(unsafe_payload)
    user = get_user_storage().find_user_by_username(payload['username'])

    return {
        'content': {
            'challenge': user.challenge
        },
        'links': {
            **hateoas_new_user(),
            **hateoas_auth_user_answer_challenge()
        }
    }


@bp.route('/user/auth/answer-challenge', methods=['POST'])
@as_json
def auth_user_answer_challenge():
    unsafe_payload = request.get_json() or {}
    payload = auth_user_answer_challenge_validator(unsafe_payload)
    user_storage = get_user_storage()
    user = user_storage.find_user_by_username(payload['username'])
    correct_answer = user.answer

    if payload['answer'] != correct_answer:
        raise ChallengeMismatchError()

    return {
        'content': {
            'token': generate_auth_token(user)
        },
        'links': {
            **hateoas_list_user_files(),
            **hateoas_request_upload_url()
        }
    }


@bp.route('/file/delete', methods=['DELETE'])
@as_json
def file_delete():
    unsafe_payload = request.get_json() or {}
    payload = file_delete_validator(unsafe_payload)
    token = decode_auth_token(payload['jwt'])
    user = get_user_storage().find_user_by_username(token.username)

    file_storage = access_user_storage(user.username)
    file_storage.remove_by_filename(payload['filename'])
    return {}


@bp.route('/file/request-upload-url', methods=['POST'])
@as_json
def request_upload_url():
    unsafe_payload = request.get_json() or {}
    payload = request_upload_url_validator(unsafe_payload)
    token = decode_auth_token(payload['jwt'])
    user = get_user_storage().find_user_by_username(token.username)

    file_storage = access_user_storage(user.username)
    return {
        'links': {
            'upload_url': {
                'rel': 'file',
                'href': file_storage.get_presigned_upload_url(payload['filename'])
            }
        }
    }


def hateoas_auth_user_request_challenge():
    return {
        'request_auth_challenge': {
            'rel': 'user',
            'href': url_for('controller.auth_user_answer_challenge', _external=True)
        }
    }


def hateoas_auth_user_answer_challenge():
    return {
        'answer_auth_challenge': {
            'rel': 'user',
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
