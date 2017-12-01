import os
from piggy_store.app import create_app
from piggy_store.exceptions import PiggyStoreError

import pytest
import json
import werkzeug
from unittest.mock import patch

from piggy_store.config import config, load as load_config, ConfigError

config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.tests.yml')

if not config:
    config = load_config(config_path)

access_admin_storage_patcher = patch('piggy_store.app.access_admin_storage',
    **{'check_bucket.return_value': None}
)
access_admin_storage_patcher.start()

@pytest.mark.parametrize('content_type', [
    'application/json',
    'text/html'
])
@patch('piggy_store.exception_handlers.logger')
def test_unnamed_exceptions(mock_logger, content_type):
    app = create_app(config)

    exc = Exception('ops')
    def routeWithErrors():
        raise exc

    app.add_url_rule('/unnamed-exception', 'trigger-unnamed-exception', routeWithErrors)

    cli = app.test_client()
    r = cli.get('/unnamed-exception', content_type=content_type)
    assert r.status_code == 500

    assert json.loads(r.data.decode('utf-8')) == \
    {
        "status": 500,
        "error": {
            "code": 500,
            "message": "Internal Server Error"
        }
    }

    mock_logger.exception.assert_called_with(exc)

@pytest.mark.parametrize('content_type', [
    'application/json',
    'text/html'
])
def test_default_http_errors(content_type):
    app = create_app(config)
    cli = app.test_client()
    r = cli.get('/does-not-exist', content_type=content_type)
    assert r.status_code == 404

    assert json.loads(r.data.decode('utf-8')) == \
    {
        "status": 404,
        "error": {
            "code": 404,
            "message": "Not Found"
        }
    }

@pytest.mark.parametrize('content_type', [
    'application/json',
    'text/html'
])
@patch('piggy_store.exception_handlers.logger')
def test_unregistered_httpexception(mock_logger, content_type):
    app = create_app(config)

    exc = werkzeug.exceptions.HTTPException()
    exc.code = -1
    exc.description = 'such error'

    def route():
        raise exc

    app.add_url_rule('/unregistered-httpexception', 'unregistered-httpexception', route)

    cli = app.test_client()
    r = cli.get('/unregistered-httpexception', content_type=content_type)
    assert r.status_code == 500

    assert json.loads(r.data.decode('utf-8')) == \
    {
        "status": 500,
        "error": {
            "code": 500,
            "message": "Internal Server Error"
        }
    }

    mock_logger.exception.assert_called_with(exc)

def test_piggystore_exception_string_format():
    assert '0 Internal Error' == str(PiggyStoreError())
    assert '1 Internal Error' == str(PiggyStoreError(code=1))
    assert '0 Such error' == str(PiggyStoreError(message='Such error'))
    assert '42 Meaningful error' == str(PiggyStoreError(42, 'Meaningful error'))
