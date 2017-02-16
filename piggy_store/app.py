from flask import Flask, abort, request, url_for
from flask_json import FlaskJSON, as_json
import werkzeug
import logging
from hashlib import sha1
import tempfile

logger = logging.getLogger('controller')

from piggy_store.storage.users import user_storage, User
from piggy_store.validators import (
    new_user_validator,
    auth_user_validator,
    list_user_files_validator,
    request_upload_url_validator,
    upload_validator
)
from piggy_store.exceptions import PiggyStoreError, UserDoesNotExistError, ChallengeMismatchError, ClientChecksumError, ServerUploadError
from piggy_store.authentication import generate_auth_token, assert_user_challenge_match, decode_auth_token
from piggy_store.storage.files import access_file_storage, FileDTO
from piggy_store.upload import generate_upload_token, decode_upload_token

app = Flask(__name__)
app.config['TRAP_HTTP_EXCEPTIONS']=True
app.config['MAX_CONTENT_LENGTH'] = 3 * 1024 * 1024
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

FlaskJSON(app)

@app.route('/user/', methods=['GET'])
@as_json
def list_user_files():
    unsafe_payload = request.get_json() or {}
    payload = list_user_files_validator(unsafe_payload)
    token = decode_auth_token(payload['jwt'])
    user = user_storage.find_user_by_username(token.username)
    file_storage = access_file_storage({'location': user.username})
    files = file_storage.get_files()

    return {
        'list': [f.as_dict() for f in files]
    }

@app.route('/user/', methods=['POST'])
@as_json
def new_user():
    unsafe_payload = request.get_json() or {}
    payload = new_user_validator(unsafe_payload)
    user = User(payload['username'], payload['challenge'])
    user_storage.add_user(user)

    return {
        'token': generate_auth_token(user)
    }

@app.route('/user/auth', methods=['POST'])
@as_json
def auth_user():
    unsafe_payload = request.get_json() or {}
    payload = auth_user_validator(unsafe_payload)
    user = user_storage.find_user_by_username(payload['username'])
    assert_user_challenge_match(user, payload['challenge'])

    return {
        "token": generate_auth_token(user)
    }

@app.route('/file/request-upload-url', methods=['POST'])
@as_json
def request_upload_url():
    unsafe_payload = request.get_json() or {}
    payload = request_upload_url_validator(unsafe_payload)
    token = decode_auth_token(payload['jwt'])
    user = user_storage.find_user_by_username(token.username)

    return {
        'url': url_for(
            'upload', 
            username = user.username,
            signed_upload_request = generate_upload_token(
                user,
                payload['filename'],
                payload['checksum']
            )
        )
    }

@app.route('/file/upload', methods=['POST'])
@as_json
def upload():
    unsafe_payload = dict(**request.args.to_dict(), **request.files.to_dict())
    payload = upload_validator(unsafe_payload)
    upload_token = decode_upload_token(payload['signed_upload_request'])
    user = user_storage.find_user_by_username(upload_token.username)

    content_as_bytes = payload['file'].read()
    content_checksum = sha1(content_as_bytes).hexdigest()

    if not upload_token.checksum == content_checksum:
        raise ClientChecksumError()

    file_storage = access_file_storage({'location': user.username})
    file_to_upload = FileDTO(**{
        'filename': upload_token.filename,
        'content': content_as_bytes,
        'checksum': content_checksum
    })

    file_inserted = file_storage.add_file(file_to_upload)
    file_retrieved = file_storage.find_file_by_id(file_inserted.id, ignore_cache=True)

    if file_inserted != file_retrieved:
        raise ServerUploadError()

    return {
        'file': file_retrieved.as_dict()
    }



@app.errorhandler(UserDoesNotExistError)
@app.errorhandler(ChallengeMismatchError)
def handle_not_found_error(e):
    return make_error_response(404, e.code, e.message)

@app.errorhandler(ServerUploadError)
def handle_piggy_store_errors(e):
    logger.exception(e)
    return make_error_response(500, e.code, e.message)

@app.errorhandler(PiggyStoreError)
def handle_piggy_store_errors(e):
    return make_error_response(409, e.code, e.message)

def on_flask_http_exception(e):
    if isinstance(e, werkzeug.exceptions.HTTPException):
        return make_error_response(e.code, e.code, e.name)
    else:
        # happens when there was an error handling the exception
        logger.exception(e)
        return make_error_response(500, 500, 'Internal Server Error')

@app.errorhandler(Exception)
def on_error(e):
    logger.exception(e)
    return make_error_response(500, 500, 'Internal Server Error')

@as_json
def make_error_response(status, subcode, message):
    return {
        'error': {
            'code': subcode,
            'message': message
        },
        'status': status
    }, status


for werkzeugException in werkzeug.exceptions.default_exceptions:
    app.register_error_handler(werkzeugException, on_flask_http_exception)

if __name__ == "__main__":
    app.run(host='0.0.0.0')