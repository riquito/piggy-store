from flask import Flask, abort, request
from flask_json import FlaskJSON, as_json
import werkzeug
import logging

logger = logging.getLogger('controller')

from piggy_store.storage.users import user_storage, User
from piggy_store.validators import new_user_validator, auth_user_validator, list_user_files_validator
from piggy_store.exceptions import PiggyStoreError, UserDoesNotExistError, ChallengeMismatchError
from piggy_store.authentication import generate_auth_token, assert_user_challenge_match, decode_auth_token

app = Flask(__name__)
app.config['TRAP_HTTP_EXCEPTIONS']=True
FlaskJSON(app)

@app.route('/user/<username>', methods=['GET'])
@as_json
def list_user_files(username):
    unsafe_payload = request.get_json() or {}
    payload = list_user_files_validator(unsafe_payload)
    token = decode_auth_token(payload['jwt'])
    user = user_storage.find_user_by_username(token.username)
    return {
        'list': []
    }

@app.route('/new-user', methods=['POST'])
@as_json
def new_user():
    unsafe_payload = request.get_json() or {}
    payload = new_user_validator(unsafe_payload)
    user = User(payload['username'], payload['challenge'])
    user_storage.add_user(user)
    return {
        'token': generate_auth_token(user)
    }

@app.route('/user/<username>/auth', methods=['POST'])
@as_json
def auth_user(username):
    unsafe_payload = request.get_json() or {}
    payload = auth_user_validator(unsafe_payload)
    user = user_storage.find_user_by_username(username)
    assert_user_challenge_match(user, payload['challenge'])

    return {
        "token": generate_auth_token(user)
    }


@app.errorhandler(UserDoesNotExistError)
@app.errorhandler(ChallengeMismatchError)
def handle_not_found_error(e):
    return make_error_response(404, e.code, e.message)

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