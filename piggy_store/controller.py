from flask import Blueprint, abort, request, url_for
from flask_json import FlaskJSON, as_json

from piggy_store.storage.users import user_storage, User
from piggy_store.validators import (
    new_user_validator,
    auth_user_request_challenge_validator,
    auth_user_answer_challenge_validator,
    list_user_files_validator,
    request_upload_url_validator,
    file_delete_validator
)
from piggy_store.authentication import generate_auth_token, assert_user_challenge_match, decode_auth_token
from piggy_store.storage.files import access_file_storage
from piggy_store.storage.files.file_entity import FileDTO
from piggy_store.exceptions import UserExistsError, FileDoesNotExistError, ChallengeMismatchError

bp = blueprint = Blueprint('controller', __name__)

@bp.route('/', methods=['GET'])
@as_json
def root():
    return {
        'links': {
            **hateoas_auth(),
            **hateoas_new_user()
        }
    }

@bp.route('/files/', methods=['GET'])
@as_json
def list_user_files():
    unsafe_payload = request.args
    payload = list_user_files_validator(unsafe_payload)
    token = decode_auth_token(payload['jwt'])
    user = user_storage.find_user_by_username(token.username)
    file_storage = access_file_storage({'user_dir': user.username})
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
    user = User(payload['username'], payload['challenge'])
    user_storage.add_user(user)
    file_storage = access_file_storage({'user_dir': 'admin$'})
    filename = 'challenge_{}_{}'.format(user.username, payload['answer'])
    challenge_file = FileDTO(
        filename = filename,
        content = payload['challenge']
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

@bp.route('/user/auth/request-challenge', methods=['GET'])
@as_json
def auth_user_request_challenge():
    unsafe_payload = request.args
    payload = auth_user_request_challenge_validator(unsafe_payload)
    user = user_storage.find_user_by_username(payload['username'])
    file_storage = access_file_storage({'user_dir': 'admin$'})
    filename_prefix = 'challenge_{}_'.format(user.username)
    challenge_files = list(file_storage.get_files_list(prefix = filename_prefix))

    status = 200

    if len(challenge_files) > 1:
        raise Exception('XXX wrong number of challenge files')
    elif len(challenge_files) == 0:
        status = 401

    json_content= {
        'links': {
            **hateoas_new_user(),
            **hateoas_auth_user_answer_challenge(),
        }
    }
    
    if status == 200:
        challenge_file = challenge_files[0]
        json_content['content'] = {
            'challenge': file_storage.get_file_content(challenge_file.filename).decode('utf-8')
        }
        json_content['links']['challenge'] = {
            'rel': 'file',
            'href': challenge_file.url
        }

    return json_content, status


@bp.route('/user/auth/answer-challenge', methods=['POST'])
@as_json
def auth_user_answer_challenge():
    unsafe_payload = request.get_json() or {}
    payload = auth_user_answer_challenge_validator(unsafe_payload)
    user = user_storage.find_user_by_username(payload['username'])
    file_storage = access_file_storage({'user_dir': 'admin$'})
    filename = 'challenge_{}_{}'.format(user.username, payload['answer'])

    try:
        file_storage.find_file_by_filename(filename)
    except FileDoesNotExistError:
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
    user = user_storage.find_user_by_username(token.username)

    file_storage = access_file_storage({'user_dir': user.username})
    file_storage.remove_by_filename(payload['filename'])
    return {}

@bp.route('/file/request-upload-url', methods=['POST'])
@as_json
def request_upload_url():
    unsafe_payload = request.get_json() or {}
    payload = request_upload_url_validator(unsafe_payload)
    token = decode_auth_token(payload['jwt'])
    user = user_storage.find_user_by_username(token.username)

    file_storage = access_file_storage({'user_dir': user.username})
    return {
        'links': {
            'upload_url': {
                'rel': 'file',
                'href': file_storage.get_presigned_upload_url(payload['filename'])
            }
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
