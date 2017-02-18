from flask import Flask
from flask_json import FlaskJSON
from piggy_store.controller import blueprint

def create_app(config):
    app = Flask(__name__)
    app.config['TRAP_HTTP_EXCEPTIONS'] = True
    app.config['MAX_CONTENT_LENGTH'] = config['uploads']['max_content_length']
    app.config['UPLOAD_FOLDER'] = config['uploads']['folder']
    app.register_blueprint(blueprint)

    FlaskJSON(app)
    return app

