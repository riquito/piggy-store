from flask import Flask
from flask_json import FlaskJSON
from raven.contrib.flask import Sentry
import logging

from piggy_store.controller import blueprint
from piggy_store.exception_handlers import register_default_exceptions
from piggy_store.storage.files import access_admin_storage

sentry = Sentry()


def add_preflight_request_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Max-Age'] = '86400'
    response.headers['Access-Control-Allow-Methods'] = 'HEAD, OPTIONS, GET, POST, PUT, DELETE'
    return response

def create_app(config):
    access_admin_storage().check_bucket()

    app = Flask(__name__)
    app.config['TRAP_HTTP_EXCEPTIONS'] = True
    app.config['MAX_CONTENT_LENGTH'] = config['uploads']['max_content_length']
    app.config['DEBUG'] = config['debug']
    app.config['SENTRY_CONFIG'] = config['sentry']

    app.register_blueprint(blueprint)
    app.after_request(add_preflight_request_headers)

    # 404 and 500 can be register just to the default app, so we register
    # those and the rest here
    register_default_exceptions(app)

    FlaskJSON(app)

    sentry.init_app(app,
                    dsn=config['sentry']['dsn'],
                    logging=config['sentry']['dsn'] and not config['debug'],
                    level=logging.ERROR
    )

    return app
