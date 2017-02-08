from flask import Flask, abort, request
from flask_json import FlaskJSON, as_json

from piggy_store.storage.users import user_storage, User
from piggy_store.validators import new_user_validator, auth_user_validator
from piggy_store.exceptions import PiggyStoreError, UserDoesNotExistError, ChallengeMismatchError
from piggy_store.authentication import generate_auth_token, assert_user_challenge_match

app = Flask(__name__)
FlaskJSON(app)

@app.route('/user/<username>', methods=['GET'])
def list_user_files(username):
    abort(401)

@app.route('/new-user', methods=['POST'])
@as_json
def new_user():
    unsafe_payload = request.get_json() or {}
    payload = new_user_validator(unsafe_payload)
    user = User(payload['username'], payload['challenge'])
    user_storage.add_user(user)

@app.route('/user/<username>/auth', methods=['POST'])
@as_json
def auth_user(username):
    unsafe_payload = request.get_json() or {}
    payload = auth_user_validator(unsafe_payload)

    user = user_storage.find_user_by_username(username)
    try:
        assert_user_challenge_match(user, payload['challenge'])
    except ChallengeMismatchError:
        abort(404)

    return {
        "token": generate_auth_token(username, payload['challenge'])
    }


@app.errorhandler(401)
@as_json
def user_unauthorized(e):
    return {
        'error': {
            'code': e.code,
            'message': e.name
        }
    }, e.code

@app.errorhandler(UserDoesNotExistError)
@as_json
def handle_user_does_not_exist_error(e):
    return {
        'error': {
            'code': e.code,
            'message': e.message
        }
    }, 404

@app.errorhandler(PiggyStoreError)
@as_json
def handle_piggy_store_errors(e):
    return {
        'error': {
            'code': e.code,
            'message': e.message
        }
    }, 409

if __name__ == "__main__":
    app.run(host='0.0.0.0')