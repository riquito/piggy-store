from flask import Blueprint, abort, request
from flask_json import FlaskJSON, as_json

from piggy_store.storage.users import user_storage, User
from piggy_store.validators import (
    new_user_validator,
    auth_user_validator,
    list_user_files_validator,
    request_upload_url_validator,
    file_delete_validator
)
from piggy_store.authentication import generate_auth_token, assert_user_challenge_match, decode_auth_token
from piggy_store.storage.files import access_file_storage
from piggy_store.exceptions import UserExistsError

bp = blueprint = Blueprint('controller', __name__)

@bp.after_request
def add_preflight_request_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Max-Age'] = '86400'
    response.headers['Access-Control-Allow-Methods'] = 'HEAD, OPTIONS, GET, POST, PUT, DELETE'
    return response

@bp.route('/user/', methods=['GET'])
@as_json
def list_user_files():
    unsafe_payload = request.get_json() or {}
    payload = list_user_files_validator(unsafe_payload)
    token = decode_auth_token(payload['jwt'])
    user = user_storage.find_user_by_username(token.username)
    file_storage = access_file_storage({'user_dir': user.username})
    files = file_storage.get_files_list()

    return {
        'list': [f.as_dict() for f in files]
    }

@bp.route('/user/', methods=['POST'])
@as_json
def new_user():
    unsafe_payload = request.get_json() or {}
    payload = new_user_validator(unsafe_payload)
    try:
        user = User(payload['username'], payload['challenge'])
        user_storage.add_user(user)
    except UserExistsError:
        # Sacrifice route purity for practicality. If the user exists
        # check the challenge and return the token
        user = user_storage.find_user_by_username(payload['username'])
        assert_user_challenge_match(user, payload['challenge'])

    return {
        'token': generate_auth_token(user)
    }

@bp.route('/user/auth', methods=['POST'])
@as_json
def auth_user():
    unsafe_payload = request.get_json() or {}
    payload = auth_user_validator(unsafe_payload)
    user = user_storage.find_user_by_username(payload['username'])
    assert_user_challenge_match(user, payload['challenge'])

    return {
        "token": generate_auth_token(user)
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
        'url': file_storage.get_presigned_upload_url(payload['filename'])
    }

