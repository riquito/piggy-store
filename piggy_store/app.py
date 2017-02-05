from flask import Flask, abort, request
from flask_json import FlaskJSON, as_json

from piggy_store.validators import new_user_validator
from piggy_store.exceptions import PiggyStoreError

app = Flask(__name__)
FlaskJSON(app)

@app.route('/user/<username>', methods=['GET'])
def list_user_files(username):
    abort(401)

@app.route('/new-user', methods=['POST'])
@as_json
def new_user():
    unsafe_payload = request.get_json()
    payload = new_user_validator(unsafe_payload)

@app.errorhandler(401)
@as_json
def user_unauthorized(e):
    return {
        'error': {
            'code': e.code,
            'message': e.name
        }
    }, e.code

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