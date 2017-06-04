import logging

from flask_json import as_json
import werkzeug

from piggy_store.exceptions import (
    PiggyStoreError,
    UserDoesNotExistError,
    ChallengeMismatchError
)

from piggy_store.controller import hateoas_new_user

logger = logging.getLogger('errors')


def handle_unhautorized_errors(e):
    return make_error_response(401, e.code, e.message, links=hateoas_new_user())


def handle_forbidden_errors(e):
    return make_error_response(403, e.code, e.message)


def handle_piggy_store_errors(e):
    return make_error_response(409, e.code, e.message)


def on_flask_http_exception(e):
    if isinstance(e, werkzeug.exceptions.HTTPException):
        return make_error_response(e.code, e.code, e.name)
    else:
        # XXX can't remember how to reproduce it, I swear it can happen
        logger.exception(e)
        return make_error_response(500, 500, 'Internal Server Error')


def on_error(e):
    logger.exception(e)
    return make_error_response(500, 500, 'Internal Server Error')


@as_json
def make_error_response(status, subcode, message, links=None):
    json_content = {
        'error': {
            'code': subcode,
            'message': message
        },
        'status': status
    }

    if links:
        json_content['links'] = {
            **links
        }

    return json_content, status


def register_default_exceptions(app):
    app.register_error_handler(Exception, on_error)

    # 401s
    for exc_class in (UserDoesNotExistError, ):
        app.register_error_handler(exc_class, handle_unhautorized_errors)

    # 403s
    for exc_class in (ChallengeMismatchError, ):
        app.register_error_handler(exc_class, handle_forbidden_errors)

    # 409, generic error
    for exc_class in (PiggyStoreError, ):
        app.register_error_handler(exc_class, handle_piggy_store_errors)

    for werkzeugException in werkzeug.exceptions.default_exceptions:
        app.register_error_handler(werkzeugException, on_flask_http_exception)
