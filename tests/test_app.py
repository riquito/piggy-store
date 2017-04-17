# load the config before doing anything else
import os
from piggy_store.config import load as load_config
config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config.tests.yml')
config = load_config(config_path)

import unittest
from unittest.mock import patch
import base64
import json
import urllib
from datetime import datetime
from hashlib import md5

from minio import Minio
from minio.error import ResponseError
import redis
import jwt

from piggy_store.app import create_app

FOO_USERNAME = 'foo'
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

    def request_upload_url(self, jwt, filename=DEFAULT_FILENAME):
        return self.cli.post('/file/request-upload-url', data=json.dumps({
            'jwt': jwt,
            'filename': filename,
        }), content_type='application/json')

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

    def upload_file_to_user_foo(self, token, filename, file_content):
        r = self.request_upload_url(token, filename)
        assert r.status_code == 200
        decoded_data = json.loads(r.data.decode('utf-8'))
        upload_url = decoded_data['links']['upload_url']['href']

        req = self.get_upload_file_request(upload_url, file_content)

        with urllib.request.urlopen(req) as f:
            assert f.getcode() == 200
            f.read()

    def list_files(self, token):
        return self.cli.get('/files/', query_string = {
            'jwt': token
        }, content_type='application/json')

    def delete_file(self, token, filename):
        return self.cli.delete('/file/delete', data=json.dumps({
            'jwt': token,
            'filename': filename
        }), content_type='application/json')

class PiggyStoreTestCase(unittest.TestCase):
    DUMMY_TOKEN = 'a.dummy.token'

    @classmethod
    def setUpClass(cls):
        cls._miniocli = Minio(
            config['s3']['host'],
            access_key = config['s3']['access_key'],
            secret_key = config['s3']['secret_key'],
            secure = config['s3']['secure'],
            region = config['s3']['region']
        )

        cls._rediscli = redis.StrictRedis(
            host = config['redis']['host'],
            port = config['redis']['port'],
            db = config['redis']['database'],
            decode_responses = True
        )

    def setUp(self):
        self.cli = Navigator(create_app(config).test_client())

        try:
            self.__class__._miniocli.make_bucket(config['s3']['bucket'])
        except ResponseError as e:
            if e.code != 'BucketAlreadyOwnedByYou':
                raise e

    def tearDown(self):
        self.__class__._rediscli.flushdb()
        miniocli = self.__class__._miniocli
        
        for bucket in miniocli.list_buckets():
            bucket_name = bucket.name
            errors = miniocli.remove_objects(bucket_name, (x.object_name for x in miniocli.list_objects_v2(bucket_name, '', recursive=True)))
            for i in errors:
                pass # you need to force evaluation
            miniocli.remove_bucket(bucket_name)

    def _test_cors(self, r):
        assert r.headers.get('Content-Type') == 'application/json'
        assert r.headers.get('Access-Control-Allow-Origin') == '*'
        assert r.headers.get('Access-Control-Max-Age') == '86400'
        
        allowed_methods_string = r.headers.get('Access-Control-Allow-Methods', '')
        allowed_methods = set(x.strip() for x in allowed_methods_string.split(','))
        assert allowed_methods == set(('HEAD', 'OPTIONS', 'GET', 'POST', 'PUT', 'DELETE'))

    def test_404(self):
        r = self.cli.get_unexistent_page()
        assert r.status_code == 404
        self._test_cors(r)

    def test_root(self):
        r = self.cli.get_root()
        assert r.status_code == 200
        self._test_cors(r)
        assert json.loads(r.data.decode('utf-8')) == \
        {
            "status": 200,
            "links":  {
                "create_user": {
                    "href": "http://localhost:5000/user/",
                    "rel": "user"
                },
                "request_auth_challenge":  {
                    "href": "http://localhost:5000/user/auth/answer-challenge",
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

    def test_create_new_user(self):
        r = self.cli.create_user_foo()
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
                    "href": "http://localhost:5000/files/",
                    "rel": "file"
                },
                "request_upload_url": {
                    "href": "http://localhost:5000/file/request-upload-url",
                    "rel": "file"
                }
            },
            "status": 200
        }

    def test_try_to_create_new_user_but_the_user_already_exists(self):
        r = self.cli.create_user_foo()
        assert r.status_code == 200
        r = self.cli.create_user_foo()
        assert r.status_code == 409
        assert json.loads(r.data.decode('utf-8')) == \
        {
            "status": 409,
            "error": {
                "code": 1000,
                "message": "User already exists"
            }
        }

    def test_get_auth_challenge_no_username_provided(self):
        r = self.cli.get_auth_challenge()
        assert r.status_code == 409
        assert json.loads(r.data.decode('utf-8')) == \
        {
            "status": 409,
            "error": {
                "code": 1002,
                "message": "This field is required: username"
            }
        }
        
    def test_get_auth_challenge_username_not_found(self):
        r = self.cli.get_auth_challenge('user1')
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
                    "href": "http://localhost:5000/user/",
                    "rel": "user"
                }
            }
        }

    def test_get_auth_challenge_succeed(self):
        r = self.cli.create_user_foo()
        assert r.status_code == 200
        r = self.cli.get_auth_challenge(FOO_USERNAME)
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
                    'href': 'http://localhost:5000/user/auth/answer-challenge'
                },
                'create_user': {
                    'rel': 'user',
                    'href': 'http://localhost:5000/user/'
                }
            }
        }

    def test_auth_user_answer_challenge_succeed(self):
        r = self.cli.create_user_foo()
        assert r.status_code == 200
        r = self.cli.answer_auth_challenge(FOO_USERNAME, FOO_ANSWER)
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
                    'href': 'http://localhost:5000/file/request-upload-url'
                },
                'files_list': {
                    'rel': 'file',
                    'href': 'http://localhost:5000/files/'
                }
            }
        }

    def test_auth_user_answer_challenge_wrong_answer(self):
        r = self.cli.create_user_foo()
        assert r.status_code == 200
        r = self.cli.answer_auth_challenge(FOO_USERNAME, 'wrong answer')
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

    def test_request_upload_url(self):
        r = self.cli.create_user_foo()
        assert r.status_code == 200
        decoded_data = json.loads(r.data.decode('utf-8'))
        token = decoded_data['content']['token']

        r = self.cli.request_upload_url(token)
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
                    'href': 'http://localhost:9000/bucket-test/users/foo/default-filename'
                }
            }
        }

    def test_upload_file(self):
        r = self.cli.create_user_foo()
        assert r.status_code == 200
        decoded_data = json.loads(r.data.decode('utf-8'))
        token = decoded_data['content']['token']

        r = self.cli.request_upload_url(token)
        assert r.status_code == 200
        decoded_data = json.loads(r.data.decode('utf-8'))
        upload_url = decoded_data['links']['upload_url']['href']

        file_content = b'this is a test'
        req = self.cli.get_upload_file_request(upload_url, file_content)

        with urllib.request.urlopen(req) as f:
            assert f.getcode() == 200
            assert f.info().get('Etag').strip('"') == md5(file_content).hexdigest()

    def test_list_files(self):
        r = self.cli.create_user_foo()
        assert r.status_code == 200
        decoded_data = json.loads(r.data.decode('utf-8'))
        token = decoded_data['content']['token']

        self.cli.upload_file_to_user_foo(token, 'file1', b'content 1')
        self.cli.upload_file_to_user_foo(token, 'file2', b'content 2')

        r = self.cli.list_files(token)
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
                            'href': 'http://localhost:9000/bucket-test/users/foo/file1'
                        },
                        'delete': {
                            'rel': 'file',
                            'href': 'http://localhost:5000/file/delete'
                        }
                    },
                    'content': {
                        'checksum': '9297ab3fbd56b42f6566284119238125',
                        'filename': 'file1',
                        'size': 9,
                        'url': 'http://localhost:9000/bucket-test/users/foo/file1'
                    }
                },
                {
                    'links': {
                        'read': {
                            'rel': 'file',
                            'href': 'http://localhost:9000/bucket-test/users/foo/file2'
                        },
                        'delete': {
                            'rel': 'file',
                            'href': 'http://localhost:5000/file/delete'
                        }
                    },
                    'content': {
                        'checksum': '6685cd62b95f2c58818cb20e7292168b',
                        'filename': 'file2',
                        'size': 9,
                        'url': 'http://localhost:9000/bucket-test/users/foo/file2'
                    }
                }
            ]
        }

    def test_delete_file(self):
        r = self.cli.create_user_foo()
        assert r.status_code == 200
        decoded_data = json.loads(r.data.decode('utf-8'))
        token = decoded_data['content']['token']

        self.cli.upload_file_to_user_foo(token, 'file1', b'content 1')
        self.cli.upload_file_to_user_foo(token, 'file2', b'content 2')

        r = self.cli.delete_file(token, 'file1')
        assert r.status_code == 200

        r = self.cli.list_files(token)
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
                            'href': 'http://localhost:9000/bucket-test/users/foo/file2'
                        },
                        'delete': {
                            'rel': 'file',
                            'href': 'http://localhost:5000/file/delete'
                        }
                    },
                    'content': {
                        'checksum': '6685cd62b95f2c58818cb20e7292168b',
                        'filename': 'file2',
                        'size': 9,
                        'url': 'http://localhost:9000/bucket-test/users/foo/file2'
                    }
                }
            ]
        }

    def test_token_expired(self):
        with patch('piggy_store.authentication.datetime') as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2017, 1, 1)

            r = self.cli.create_user_foo()
            assert r.status_code == 200
            decoded_data = json.loads(r.data.decode('utf-8'))
            expired_token = decoded_data['content']['token']

            r = self.cli.list_files(expired_token)
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



if __name__ == '__main__':
    unittest.main()