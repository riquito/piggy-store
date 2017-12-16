import os

import unittest
from unittest.mock import patch, Mock
import base64
import json
import urllib
from datetime import datetime
from hashlib import md5

from minio import Minio
from minio.error import MinioError, BucketAlreadyOwnedByYou
from minio.policy import Policy
import redis
import pytest

from piggy_store.app import create_app

from piggy_store.config import config, load as load_config

if not config:
    config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.tests.yml')
    config = load_config(config_path)

# NOTE: foo and foobar usernames are whitelisted in test_config.py
FOO_USERNAME = 'foo'
FOOBAR_USERNAME = 'foobar'

FOO_ENC_CHALLENGE = 'assume I\'m an encrypted blob'
FOO_ANSWER = 'a'* 32 # fake 32 bytes long sha256 checksum
DEFAULT_FILENAME = 'default-filename'

class Navigator:
    def __init__(self, client):
        self.cli = client

    def get_unexistent_page(self):
        return self.cli.get('/foo')

    def get_root(self):
        return self.cli.get('/')

    def get_auth_challenge(self, username=None):
        qs = {}
        if username:
            qs['username'] = username
        return self.cli.get('/user/auth/request-challenge', query_string=qs)

    def create_new_user(self, username, challenge, answer):
        return self.cli.post('/user/', data=json.dumps({
            'username': username,
            'challenge': challenge,
            'answer': answer
        }), content_type='application/json')

    def create_user_foo(self):
        return self.create_new_user(FOO_USERNAME, FOO_ENC_CHALLENGE, FOO_ANSWER)

    def answer_auth_challenge(self, username, answer):
        return self.cli.post('/user/auth/answer-challenge', data=json.dumps({
            'username': username,
            'answer': answer
        }), content_type='application/json')

    def request_upload_url(self, token, filename=DEFAULT_FILENAME):
        return self.cli.post('/file/request-upload-url', data=json.dumps({
            'filename': filename,
        }), headers={
            'Authorization': 'Bearer ' + token
        }, content_type='application/json')

    def get_upload_file_request(self, url, file_content):
        content_md5 = base64.b64encode(md5(file_content).digest())
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Content-MD5': content_md5
        }

        return urllib.request.Request(
            url = url,
            headers = headers,
            method = 'PUT',
            data = file_content
        )

    def upload_file_to_user(self, token, filename, file_content):
        r = self.request_upload_url(token, filename)
        assert r.status_code == 200
        decoded_data = json.loads(r.data.decode('utf-8'))
        upload_url = decoded_data['links']['upload_url']['href']

        req = self.get_upload_file_request(upload_url, file_content)

        with urllib.request.urlopen(req) as f:
            assert f.getcode() == 200
            f.read()

    def list_files(self, token):
        return self.cli.get('/files/', headers = {
            'Authorization': 'Bearer ' + token
        }, content_type='application/json')

    def delete_file(self, token, filename):
        return self.cli.delete('/file/delete', data=json.dumps({
            'filename': filename
        }), headers = {
            'Authorization': 'Bearer ' + token
        },content_type='application/json')

    def delete_user(self, token):
        return self.cli.delete('/user/', headers={
            'Authorization': 'Bearer ' + token
        }, content_type='application/json')



miniocli = Minio(
    config['storage']['files']['params']['host'],
    access_key = config['storage']['files']['params']['access_key'],
    secret_key = config['storage']['files']['params']['secret_key'],
    secure = config['storage']['files']['params']['secure'],
    region = config['storage']['files']['params']['region']
)

rediscli = redis.StrictRedis(
    host = config['storage']['cache']['params']['host'],
    port = config['storage']['cache']['params']['port'],
    db = config['storage']['cache']['params']['database'],
    decode_responses = True
)

def bucket_init(bucket_name):
    try:
        miniocli.make_bucket(bucket_name)
    except MinioError as e:
        if not isinstance(e, BucketAlreadyOwnedByYou):
            raise e

    miniocli.set_bucket_policy(bucket_name, '', Policy.READ_WRITE)

def bucket_teardown():
    rediscli.flushdb()

    for bucket in miniocli.list_buckets():
        bucket_name = bucket.name
        errors = miniocli.remove_objects(bucket_name, (x.object_name for x in miniocli.list_objects_v2(bucket_name, '', recursive=True)))
        for i in errors:
            pass # you need to force evaluation
        miniocli.remove_bucket(bucket_name)


@pytest.fixture(scope='module')
def cli():
    return Navigator(create_app(config).test_client())

class TestPiggyStoreApp:
    DUMMY_TOKEN = 'a.dummy.token'

    @pytest.fixture(autouse=True)
    def bucket_fixture(self, request):
        bucket_name = config['storage']['files']['params']['bucket']
        bucket_init(bucket_name)
        request.addfinalizer(bucket_teardown)


    def _test_cors(self, r):
        assert r.headers.get('Content-Type') == 'application/json'
        assert r.headers.get('Access-Control-Allow-Origin') == '*'
        assert r.headers.get('Access-Control-Max-Age') == '86400'

        allowed_methods_string = r.headers.get('Access-Control-Allow-Methods', '')
        allowed_methods = set(x.strip() for x in allowed_methods_string.split(','))
        assert allowed_methods == set(('HEAD', 'OPTIONS', 'GET', 'POST', 'PUT', 'DELETE'))

    def test_404(self, cli):
        r = cli.get_unexistent_page()
        assert r.status_code == 404
        self._test_cors(r)

    def test_root(self, cli):
        r = cli.get_root()
        assert r.status_code == 200
        self._test_cors(r)
        assert json.loads(r.data.decode('utf-8')) == \
        {
            "status": 200,
            "links":  {
                "create_user": {
                    "href": "http://localhost/user/",
                    "rel": "user"
                },
                "request_auth_challenge":  {
                    "href": "http://localhost/user/auth/answer-challenge",
                    "rel": "user"
                }
            }
        }

    def _decode_json_response(self, data):
        response = json.loads(data.decode('utf-8'))
        if response.get('content') and response['content'].get('token'):
            token = response['content']['token']
            # try to decode the token, at least we make sure that it's valid
            jwt.decode(token, config['secret'], algorithms=['HS256'])
            response['content']['token'] = self.DUMMY_TOKEN

        return response

    def test_create_new_user(self, cli):
        r = cli.create_user_foo()
        assert r.status_code == 200

        json_response = self._decode_json_response(r.data)
        assert json_response == \
        {
            "content": {
                "challenge": FOO_ENC_CHALLENGE,
                "token": self.DUMMY_TOKEN,
            },
            "links": {
                "files_list": {
                    "href": "http://localhost/files/",
                    "rel": "file"
                },
                "request_upload_url": {
                    "href": "http://localhost/file/request-upload-url",
                    "rel": "file"
                }
            },
            "status": 200
        }

    def test_try_to_create_new_user_but_the_user_already_exists(self, cli):
        r = cli.create_user_foo()
        assert r.status_code == 200
        r = cli.create_user_foo()
        assert r.status_code == 409
        assert json.loads(r.data.decode('utf-8')) == \
        {
            "status": 409,
            "error": {
                "code": 1000,
                "message": "User already exists"
            }
        }

    def test_try_to_create_new_user_but_the_user_already_exists_and_the_cache_is_cleared_midway(self, cli):
        r = cli.create_user_foo()
        assert r.status_code == 200

        # The user's data would be read from the cache. Let's avoid that.
        assert rediscli.hgetall(FOO_USERNAME)['answer']
        rediscli.delete(FOO_USERNAME)

        r = cli.create_user_foo()
        assert r.status_code == 409
        assert json.loads(r.data.decode('utf-8')) == \
        {
            "status": 409,
            "error": {
                "code": 1000,
                "message": "User already exists"
            }
        }

    def test_get_auth_challenge_no_username_provided(self, cli):
        r = cli.get_auth_challenge()
        assert r.status_code == 409
        assert json.loads(r.data.decode('utf-8')) == \
        {
            "status": 409,
            "error": {
                "code": 1002,
                "message": "This field is required: username"
            }
        }

    def test_get_auth_challenge_username_not_found(self, cli):
        r = cli.get_auth_challenge('user1')
        assert r.status_code == 401
        assert json.loads(r.data.decode('utf-8')) == \
        {
            "status": 401,
            "error": {
                "code": 1005,
                "message": "The user does not exist"
            },
            "links": {
                "create_user": {
                    "href": "http://localhost/user/",
                    "rel": "user"
                }
            }
        }

    def test_get_auth_challenge_succeed(self, cli):
        r = cli.create_user_foo()
        assert r.status_code == 200
        r = cli.get_auth_challenge(FOO_USERNAME)
        assert r.status_code == 200

        decoded_data = json.loads(r.data.decode('utf-8'))
        try:
            # remove random X-Amz-* unpredictable items
            href = decoded_data['links']['challenge']['href']
            decoded_data['links']['challenge']['href'] = href.split('?', 1)[0]
        except KeyError:
            pass

        assert decoded_data == \
        {
            'status': 200,
            'content': {
                'challenge': FOO_ENC_CHALLENGE
            },
            'links': {
                'answer_auth_challenge': {
                    'rel': 'user',
                    'href': 'http://localhost/user/auth/answer-challenge'
                },
                'create_user': {
                    'rel': 'user',
                    'href': 'http://localhost/user/'
                }
            }
        }

    def test_auth_user_answer_challenge_succeed(self, cli):
        r = cli.create_user_foo()
        assert r.status_code == 200
        r = cli.answer_auth_challenge(FOO_USERNAME, FOO_ANSWER)
        assert r.status_code == 200

        decoded_data = self._decode_json_response(r.data)
        assert decoded_data == \
        {
            'status': 200,
            'content': {
                'token': self.DUMMY_TOKEN
            },
            'links': {
                'request_upload_url': {
                    'rel': 'file',
                    'href': 'http://localhost/file/request-upload-url'
                },
                'files_list': {
                    'rel': 'file',
                    'href': 'http://localhost/files/'
                }
            }
        }

    def test_auth_user_answer_challenge_wrong_answer(self, cli):
        r = cli.create_user_foo()
        assert r.status_code == 200
        r = cli.answer_auth_challenge(FOO_USERNAME, 'wrong answer')
        assert r.status_code == 403

        decoded_data = json.loads(r.data.decode('utf-8'))
        assert decoded_data == \
        {
            'status': 403,
            'error': {
                'code': 1006,
                'message': 'The challenge does not match'
            }
        }

    def test_auth_user_answer_challenge_succeed_if_the_cache_is_cleared_midway(self, cli):
        r = cli.create_user_foo()
        assert r.status_code == 200

        # The user's data would be read from the cache. Let's avoid that.
        assert rediscli.hgetall(FOO_USERNAME)['answer']
        rediscli.delete(FOO_USERNAME)

        r = cli.answer_auth_challenge(FOO_USERNAME, FOO_ANSWER)
        assert r.status_code == 200

    def test_request_upload_url(self, cli):
        r = cli.create_user_foo()
        assert r.status_code == 200
        decoded_data = json.loads(r.data.decode('utf-8'))
        token = decoded_data['content']['token']

        r = cli.request_upload_url(token)
        assert r.status_code == 200
        decoded_data = json.loads(r.data.decode('utf-8'))

        try:
            # remove random X-Amz-* unpredictable items
            href = decoded_data['links']['upload_url']['href']
            decoded_data['links']['upload_url']['href'] = href.split('?', 1)[0]
        except KeyError:
            pass

        assert decoded_data == \
        {
            'status': 200,
            'links': {
                'upload_url': {
                    'rel': 'file',
                    'href': 'http://s3like.com:9000/bucket-test/users/foo/default-filename'
                }
            }
        }

    def test_request_upload_url_field_filename_is_empty(self, cli):
        r = cli.create_user_foo()
        assert r.status_code == 200
        decoded_data = json.loads(r.data.decode('utf-8'))
        token = decoded_data['content']['token']

        r = cli.request_upload_url(token, filename='')
        assert r.status_code == 409
        decoded_data = json.loads(r.data.decode('utf-8'))

        assert decoded_data == \
        {
            'status': 409,
            'error': {
                'code': 1004,
                'message': 'Expected filename to not be empty'
            }
        }

    def test_upload_file(self, cli):
        r = cli.create_user_foo()
        assert r.status_code == 200
        decoded_data = json.loads(r.data.decode('utf-8'))
        token = decoded_data['content']['token']

        r = cli.request_upload_url(token)
        assert r.status_code == 200
        decoded_data = json.loads(r.data.decode('utf-8'))
        upload_url = decoded_data['links']['upload_url']['href']

        file_content = b'this is a test'
        req = cli.get_upload_file_request(upload_url, file_content)

        with urllib.request.urlopen(req) as f:
            assert f.getcode() == 200
            assert f.info().get('Etag').strip('"') == md5(file_content).hexdigest()

    def test_list_files(self, cli):
        r = cli.create_user_foo()
        assert r.status_code == 200
        decoded_data = json.loads(r.data.decode('utf-8'))
        token = decoded_data['content']['token']

        cli.upload_file_to_user(token, 'file1', b'content 1')
        cli.upload_file_to_user(token, 'file2', b'content 2')

        r = cli.list_files(token)
        assert r.status_code == 200
        decoded_data = json.loads(r.data.decode('utf-8'))

        try:
            # remove random X-Amz-* unpredictable items
            for idx, fname in enumerate(('file1', 'file2')):
                href_read = decoded_data['content'][idx]['links']['read']['href']
                decoded_data['content'][idx]['links']['read']['href'] = href_read.split('?', 1)[0]

                href_content = decoded_data['content'][idx]['content']['url']
                decoded_data['content'][idx]['content']['url'] = href_content.split('?', 1)[0]
        except KeyError:
            pass

        assert decoded_data == {
            'status': 200,
            'content': [
                {
                    'links': {
                        'read': {
                            'rel': 'file',
                            'href': 'http://s3like.com:9000/bucket-test/users/foo/file1'
                        },
                        'delete': {
                            'rel': 'file',
                            'href': 'http://localhost/file/delete'
                        }
                    },
                    'content': {
                        'checksum': '9297ab3fbd56b42f6566284119238125',
                        'filename': 'file1',
                        'size': 9,
                        'url': 'http://s3like.com:9000/bucket-test/users/foo/file1'
                    }
                },
                {
                    'links': {
                        'read': {
                            'rel': 'file',
                            'href': 'http://s3like.com:9000/bucket-test/users/foo/file2'
                        },
                        'delete': {
                            'rel': 'file',
                            'href': 'http://localhost/file/delete'
                        }
                    },
                    'content': {
                        'checksum': '6685cd62b95f2c58818cb20e7292168b',
                        'filename': 'file2',
                        'size': 9,
                        'url': 'http://s3like.com:9000/bucket-test/users/foo/file2'
                    }
                }
            ]
        }

    def test_list_files_does_not_produce_correctly_an_etag(self, cli):
        r = cli.create_user_foo()
        assert r.status_code == 200
        decoded_data = json.loads(r.data.decode('utf-8'))
        token = decoded_data['content']['token']

        cli.upload_file_to_user(token, 'filexyz', b'some content')

        from minio.definitions import Object
        from minio import Minio
        with patch('piggy_store.storage.files.s3_storage.Minio', new=Minio) as orig_minio_class:
            with patch.object(Minio, 'list_objects_v2') as mocked_list_objects_v2:
                mocked_object = Object(
                    'xxx bucket name unused here', # bucket_name
                    'users/foo/filexyz', # object_name
                    None, # last_modified
                    None, # etag
                    12 # size
                )

                mocked_list_objects_v2.return_value = [mocked_object]

                r = cli.list_files(token)
                assert mocked_list_objects_v2.called
                assert r.status_code == 200
                decoded_data = json.loads(r.data.decode('utf-8'))

                try:
                    # remove random X-Amz-* unpredictable items
                    for idx, fname in enumerate(('filexyz', )):
                        href_read = decoded_data['content'][idx]['links']['read']['href']
                        decoded_data['content'][idx]['links']['read']['href'] = href_read.split('?', 1)[0]

                        href_content = decoded_data['content'][idx]['content']['url']
                        decoded_data['content'][idx]['content']['url'] = href_content.split('?', 1)[0]
                except KeyError:
                    pass


                assert decoded_data == {
                    'status': 200,
                    'content': [
                        {
                            'links': {
                                'read': {
                                    'rel': 'file',
                                    'href': 'http://s3like.com:9000/bucket-test/users/foo/filexyz'
                                },
                                'delete': {
                                    'rel': 'file',
                                    'href': 'http://localhost/file/delete'
                                }
                            },
                            'content': {
                                'checksum': '9893532233caff98cd083a116b013c0b',
                                'filename': 'filexyz',
                                'size': 12,
                                'url': 'http://s3like.com:9000/bucket-test/users/foo/filexyz'
                            }
                        }
                    ]
                }

    def test_delete_file(self, cli):
        r = cli.create_user_foo()
        assert r.status_code == 200
        decoded_data = json.loads(r.data.decode('utf-8'))
        token = decoded_data['content']['token']

        cli.upload_file_to_user(token, 'file1', b'content 1')
        cli.upload_file_to_user(token, 'file2', b'content 2')

        r = cli.delete_file(token, 'file1')
        assert r.status_code == 200

        r = cli.list_files(token)
        assert r.status_code == 200
        decoded_data = json.loads(r.data.decode('utf-8'))

        try:
            # remove random X-Amz-* unpredictable items
            href_read = decoded_data['content'][0]['links']['read']['href']
            decoded_data['content'][0]['links']['read']['href'] = href_read.split('?', 1)[0]

            href_content = decoded_data['content'][0]['content']['url']
            decoded_data['content'][0]['content']['url'] = href_content.split('?', 1)[0]
        except KeyError:
            pass

        assert decoded_data == {
            'status': 200,
            'content': [
                {
                    'links': {
                        'read': {
                            'rel': 'file',
                            'href': 'http://s3like.com:9000/bucket-test/users/foo/file2'
                        },
                        'delete': {
                                'rel': 'file',
                                'href': 'http://localhost/file/delete'
                        }
                    },
                    'content': {
                        'checksum': '6685cd62b95f2c58818cb20e7292168b',
                        'filename': 'file2',
                        'size': 9,
                        'url': 'http://s3like.com:9000/bucket-test/users/foo/file2'
                    }
                }
            ]
        }

    def test_delete_file_field_filename_is_empty(self, cli):
        r = cli.create_user_foo()
        assert r.status_code == 200
        decoded_data = json.loads(r.data.decode('utf-8'))
        token = decoded_data['content']['token']

        r = cli.delete_file(token, '')
        assert r.status_code == 409
        decoded_data = json.loads(r.data.decode('utf-8'))

        assert decoded_data == {
            'status': 409,
            'error': {
                'code': 1004,
                'message': 'Expected filename to not be empty'
            }
        }

    def test_token_expired(self, cli):
        with patch('piggy_store.authentication.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2017, 1, 1)

            r = cli.create_user_foo()
            assert r.status_code == 200
            decoded_data = json.loads(r.data.decode('utf-8'))
            expired_token = decoded_data['content']['token']

            r = cli.list_files(expired_token)
            data = r.data
            assert r.status_code == 409
            decoded_data = json.loads(r.data.decode('utf-8'))

            assert decoded_data == \
            {
                'status': 409,
                'error': {
                    'code': 1007,
                    'message': 'The token has expired'
                }
            }

    def test_token_malformed_missing_key(self, cli):
        r = cli.create_user_foo()
        assert r.status_code == 200
        decoded_data = json.loads(r.data.decode('utf-8'))
        token = decoded_data['content']['token']

        decoded_token = jwt.decode(token, config['secret'], algorithms=['HS256'])
        malformed_token = jwt.encode({}, config['secret'], algorithm='HS256')

        r = self.cli.list_files(malformed_token.decode('utf-8'))
        data = r.data
        assert r.status_code == 409
        decoded_data = json.loads(r.data.decode('utf-8'))

        assert decoded_data == \
        {
            'status': 409,
            'error': {
                'code': 1008,
                'message': 'The token is not valid'
            }
        }

    def test_list_files_token_malformed(self, cli):
        r = cli.create_user_foo()
        assert r.status_code == 200
        decoded_data = json.loads(r.data.decode('utf-8'))

        malformed_token = 'bogus-token'

        r = cli.list_files(malformed_token)
        data = r.data
        assert r.status_code == 409
        decoded_data = json.loads(r.data.decode('utf-8'))

        assert decoded_data == \
        {
            'status': 409,
            'error': {
                'code': 1008,
                'message': 'The token is not valid'
            }
        }

    def test_create_new_user_validation_field_username_is_not_a_string(self, cli):
        username = 42
        r = cli.create_new_user(username, FOO_ENC_CHALLENGE, FOO_ANSWER)
        assert r.status_code == 409
        decoded_data = json.loads(r.data.decode('utf-8'))

        assert decoded_data == \
        {
            'status': 409,
            'error': {
                'code': 1003,
                'message': 'Expected username to be a string'
            }
        }

    def test_create_new_user_validation_field_username_cannot_be_empty(self, cli):
        username = ''
        r = cli.create_new_user(username, FOO_ENC_CHALLENGE, FOO_ANSWER)
        assert r.status_code == 409
        decoded_data = json.loads(r.data.decode('utf-8'))

        assert decoded_data == \
        {
            'status': 409,
            'error': {
                'code': 1004,
                'message': 'Expected username to not be empty'
            }
        }

    def test_create_new_user_validation_field_username_is_not_valid(self, cli):
        for username in ('_foo', '-foo', '$', 'à'):
            r = cli.create_new_user(username, FOO_ENC_CHALLENGE, FOO_ANSWER)
            assert r.status_code == 409
            decoded_data = json.loads(r.data.decode('utf-8'))

            assert decoded_data == \
            {
                'status': 409,
                'error': {
                    'code': 1001,
                    'message': 'Username is not valid'
                }
            }

    def test_create_new_user_validation_field_answer_must_be_32_bytes_long(self, cli):
        for answer in ('a', 'a' * 33):
            r = cli.create_new_user(FOO_USERNAME, FOO_ENC_CHALLENGE, answer)
            assert r.status_code == 409
            decoded_data = json.loads(r.data.decode('utf-8'))

            assert decoded_data == \
            {
                'status': 409,
                'error': {
                    'code': 1011,
                    'message': 'Expected answer to be 32 characters long'
                }
            }

        r = cli.create_new_user(FOO_USERNAME, FOO_ENC_CHALLENGE, 'a' * 32)
        assert r.status_code == 200

    def test_create_new_user_validation_field_answer_must_be_in_hex_format(self, cli):
        answer = 'g' * 32
        r = cli.create_new_user(FOO_USERNAME, FOO_ENC_CHALLENGE, answer)
        assert r.status_code == 409
        decoded_data = json.loads(r.data.decode('utf-8'))

        assert decoded_data == \
        {
            'status': 409,
            'error': {
                'code': 1012,
                'message': 'This field is not in hex format: answer'
            }
        }

    def test_create_new_user_not_whitelisted(self, cli):
        r = cli.create_new_user('nobodywhantsme', FOO_ENC_CHALLENGE, FOO_ANSWER)
        print(r.data)
        assert r.status_code == 403

        decoded_data = json.loads(r.data.decode('utf-8'))
        assert decoded_data == \
        {
            'status': 403,
            'error': {
                'code': 1014,
                'message': 'The user is not allowed: nobodywhantsme'
            }
        }

    def test_delete_user_success(self, cli):
        r = cli.create_user_foo()
        assert r.status_code == 200
        decoded_data = json.loads(r.data.decode('utf-8'))
        token_foo = decoded_data['content']['token']

        cli.upload_file_to_user(token_foo, 'file1', b'content 1')
        cli.upload_file_to_user(token_foo, 'file2', b'content 2')

        # add a user with the same prefix to check that we don't delete it too
        r = cli.create_new_user(FOOBAR_USERNAME, FOO_ENC_CHALLENGE, FOO_ANSWER)
        assert r.status_code == 200
        decoded_data = json.loads(r.data.decode('utf-8'))
        token_foobar = decoded_data['content']['token']

        cli.upload_file_to_user(token_foobar, 'file1', b'content 1')

        # remove the user and his content
        r = cli.delete_user(token_foo)
        assert r.status_code == 200
        assert json.loads(r.data.decode('utf-8')) == \
        {
            "status": 200,
            "links": {
                "create_user": {
                    "href": "http://localhost/user/",
                    "rel": "user"
                }
            }
        }

        # foobar should stll exist and have his file
        r = cli.list_files(token_foobar)
        assert r.status_code == 200
        decoded_data = json.loads(r.data.decode('utf-8'))
        assert 1 == len(decoded_data['content'])

        # foo should not exist anymore
        r = cli.get_auth_challenge(FOO_USERNAME)
        assert r.status_code == 401
        assert json.loads(r.data.decode('utf-8')) == \
        {
            "status": 401,
            "error": {
                "code": 1005,
                "message": "The user does not exist"
            },
            "links": {
                "create_user": {
                    "href": "http://localhost/user/",
                    "rel": "user"
                }
            }
        }

        # overall we should be left with just two files, the challenge
        # file for foobar and foobar's uploaded file
        num_files = 0
        for bucket in miniocli.list_buckets():
            num_files += len(list(miniocli.list_objects_v2(bucket.name, '', recursive=True)))
        assert 2 == num_files

        # the old token foo should not be valid anymore
        r = cli.list_files(token_foo)
        assert r.status_code == 409
        assert json.loads(r.data.decode('utf-8')) == \
        {
            'status': 409,
            'error': {
                'code': 1007,
                'message': 'The token has expired'
            }
        }

    def test_delete_user_fail_to_delete_multiple_files(self, cli):
        r = cli.create_user_foo()
        assert r.status_code == 200
        decoded_data = json.loads(r.data.decode('utf-8'))
        token = decoded_data['content']['token']

        cli.upload_file_to_user(token, 'file_xyz', b'some content')

        error_key = 'Dummy error key'
        error_code = 'Dummy error code'
        error_message = 'Dummy error message'

        # patch the third party library Minio so that it's more similar to an integration test:
        # if we were to mock our call to minio.remove_objects() we would not detect api
        # changes in the third party library (e.g. if they where to change the returned value
        # of minio.remove_objects). Another pitfall would be to rely on a wrongly mocked
        # returned value, thus having code that works on wrong assumptions.

        from minio.error import MultiDeleteError
        with patch('minio.api.parse_multi_object_delete_response') as mock_parse_multi_object_delete_response:
            mock_parse_multi_object_delete_response.return_value = [
                MultiDeleteError(error_key, error_code, error_message)
            ]

            # remove the user and his content
            r = cli.delete_user(token)
            assert mock_parse_multi_object_delete_response.called
            assert r.status_code == 500
            assert json.loads(r.data.decode('utf-8')) == \
            {
                "status": 500,
                "error": {
                    "code": 1013,
                    "message": "There was an error deleting some files: Dummy error key [Dummy error code:Dummy error message]",
                }
            }

    def test_delete_twice_the_user_with_the_same_token(self, cli):
        r = cli.create_user_foo()
        assert r.status_code == 200
        decoded_data = json.loads(r.data.decode('utf-8'))
        token_foo = decoded_data['content']['token']

        # remove the user and his content
        r = cli.delete_user(token_foo)
        assert r.status_code == 200

        # reuse the now obsolete token to try to delete the user again
        r = cli.delete_user(token_foo)
        assert r.status_code == 409
        assert json.loads(r.data.decode('utf-8')) == \
        {
            'status': 409,
            'error': {
                'code': 1007,
                'message': 'The token has expired'
            }
        }

    def test_delete_user_token_malformed_not_jwt(self, cli):
        r = cli.create_user_foo()
        assert r.status_code == 200
        decoded_data = json.loads(r.data.decode('utf-8'))
        token_foo = decoded_data['content']['token']

        malformed_token = 'bogus token'
        r = cli.delete_user(malformed_token)
        assert r.status_code == 409
        decoded_data = json.loads(r.data.decode('utf-8'))

        assert decoded_data == \
        {
            'status': 409,
            'error': {
                'code': 1008,
                'message': 'The token is not valid'
            }
        }


if __name__ == '__main__':
    unittest.main()