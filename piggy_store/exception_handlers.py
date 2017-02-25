import logging

from flask_json import as_json
import werkzeug

from piggy_store.exceptions import (
    PiggyStoreError,
    UserDoesNotExistError,
    ChallengeMismatchError,
    ServerUploadError
)

logger = logging.getLogger('errors')

def handle_not_found_error(e):
    return make_error_response(404, e.code, e.message)

def handle_detailed_500_errors(e):
    logger.exception(e)
    return make_error_response(500, e.code, e.message)

def handle_piggy_store_errors(e):
    return make_error_response(409, e.code, e.message)

def on_flask_http_exception(e):
    if isinstance(e, werkzeug.exceptions.HTTPException):
        return make_error_response(e.code, e.code, e.name)
    else:
        # hbpens when there was an error handling the exception
        logger.exception(e)
        return make_error_response(500, 500, 'Internal Server Error')

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

def register_default_exceptions(app):
    app.register_error_handler(Exception, on_error)

    # 404s
    for exc_class in (UserDoesNotExistError, ChallengeMismatchError):
        app.register_error_handler(exc_class, handle_not_found_error)

    # 500 whose real reason can show
    for exc_class in (ServerUploadError, ):
        app.register_error_handler(exc_class, handle_detailed_500_errors)

    # 409, generic error
    for exc_class in (PiggyStoreError, ):
        app.register_error_handler(exc_class, handle_piggy_store_errors)

    for werkzeugException in werkzeug.exceptions.default_exceptions:
        app.register_error_handler(werkzeugException, on_flask_http_exception)

