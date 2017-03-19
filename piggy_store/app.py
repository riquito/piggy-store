from flask import Flask
from flask_json import FlaskJSON

from piggy_store.controller import blueprint
from piggy_store.exception_handlers import register_default_exceptions

def create_app(config):
    app = Flask(__name__)
    app.config['TRAP_HTTP_EXCEPTIONS'] = True
    app.config['MAX_CONTENT_LENGTH'] = config['uploads']['max_content_length']

    port_in_hostname = str(config['server']['port']) not in ('443', '80')
    app.config['SERVER_NAME'] = config['server']['name'] + \
            (port_in_hostname and (':' + str(config['server']['port'])))

    app.register_blueprint(blueprint)

    # 404 and 500 can be register just to the default app, so we register
    # those and the rest here
    register_default_exceptions(app)

    FlaskJSON(app)
    return app

