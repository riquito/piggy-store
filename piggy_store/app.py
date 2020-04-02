from time import time
from flask import Flask, g
from flask_json import FlaskJSON
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.redis import RedisIntegration

from piggy_store.controller import blueprint
from piggy_store.exception_handlers import register_default_exceptions
from piggy_store.storage.files import access_admin_storage


def add_preflight_request_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Max-Age'] = '86400'
    response.headers['Access-Control-Allow-Methods'] = 'HEAD, OPTIONS, GET, POST, PUT, DELETE'
    return response

def start_request_timer():
    g.start = time()

def stop_and_collect_request_timer(response):
    # time as float, in milliseconds
    diff = 1000 * (time() - g.start)
    response.headers['Server-Timing'] = 'total;dur={:.3f}'.format(diff)
    return response

def create_app(config):
    access_admin_storage().check_bucket()

    app = Flask(__name__)
    app.config['TRAP_HTTP_EXCEPTIONS'] = True
    app.config['MAX_CONTENT_LENGTH'] = config['uploads']['max_content_length']
    app.config['DEBUG'] = config['debug']

    app.register_blueprint(blueprint)
    # Note: after_requests are called in reverse order
    app.after_request(stop_and_collect_request_timer)
    app.after_request(add_preflight_request_headers)
    app.before_request(start_request_timer)

    # 404 and 500 can be register just to the default app, so we register
    # those and the rest here
    register_default_exceptions(app)

    FlaskJSON(app)

    sentry_sdk.init(
        config['sentry']['dsn'],
        integrations=[FlaskIntegration(), RedisIntegration()],
    )
    return app
