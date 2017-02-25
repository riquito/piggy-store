from flask import Blueprint, abort, request
from flask_json import FlaskJSON, as_json
import tempfile
from binascii import hexlify
from base64 import b64decode

from piggy_store.storage.users import user_storage, User
from piggy_store.validators import (
    new_user_validator,
    auth_user_validator,
    list_user_files_validator,
    request_upload_url_validator,
    upload_validator
)
from piggy_store.exceptions import ClientChecksumError, ServerUploadError
from piggy_store.authentication import generate_auth_token, assert_user_challenge_match, decode_auth_token
from piggy_store.storage.files import access_file_storage, FileDTO
from piggy_store.upload import decode_upload_token
from piggy_store.helper import hash_checksum

bp = blueprint = Blueprint('controller', __name__)

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
    user = User(payload['username'], payload['challenge'])
    user_storage.add_user(user)

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

@bp.route('/file/upload', methods=['PUT'])
@as_json
def upload():
    unsafe_payload = request.args.to_dict()
    payload = upload_validator(unsafe_payload)
    upload_token = decode_upload_token(payload['signed_upload_request'])
    user = user_storage.find_user_by_username(upload_token.username)

    content_as_bytes = request.stream.read()
    content_checksum = hash_checksum(content_as_bytes).hexdigest()

    # header content-MD5 is base64(md5(file) <- bytes, not hexstring)
    header_content_md5 = request.headers.get('Content-MD5', '').strip()
    header_content_md5_as_hex = hexlify(b64decode(header_content_md5)).decode('ascii')

    if not header_content_md5_as_hex == content_checksum:
        raise ClientChecksumError()

    file_storage = access_file_storage({'user_dir': user.username})
    file_to_upload = FileDTO(**{
        'filename': upload_token.filename,
        'content': content_as_bytes,
        'checksum': content_checksum
    })

    file_inserted = file_storage.add_file(file_to_upload)
    file_retrieved = file_storage.find_file_by_filename(file_inserted.filename, ignore_cache=True)

    if file_inserted != file_retrieved:
        raise ServerUploadError()

    return {
        'file': file_retrieved.as_dict()
    }

