from flask import Flask, abort, make_response
from flask_json import FlaskJSON, JsonError, json_response, as_json

app = Flask(__name__)
FlaskJSON(app)

@app.route('/user/<username>', methods=['GET'])
def list_user_files(username):
    abort(401)

@app.errorhandler(401)
@as_json
def user_unauthorized(e):
    return {
        'error': {
            'code': e.code,
            'message': e.name
        }
    }, e.code

if __name__ == "__main__":
    app.run(host='0.0.0.0')