import json

import flask_unittest
import pytest
from flask.testing import FlaskClient

from app import app


class TestApis(flask_unittest.ClientTestCase):
    app = app
    test_username = "abc"
    test_password = "111"
    test_count = 20

    def __init__(self, *args, **kwargs):
        super(TestApis, self).__init__(*args, **kwargs)
        self.salt = None
        self.userkey = None

    def test_0_index(self, client: FlaskClient):
        rv = client.get('/')
        self.assertStatus(rv, 200)

    def test_1_file(self, client: FlaskClient):
        rv = client.get('/file/beian_icon.png')
        self.assertStatus(rv, 200)

    def test_2_get_salt(self, client: FlaskClient):
        rv = client.get(f'/user/salt?username={TestApis.test_username}')
        self.assertStatus(rv, 200)
        response: dict = json.loads(rv.text)
        self.assertIn('salt', response.keys())
        self.salt = response['salt']

    def test_3_login_succeed(self, client: FlaskClient):
        if self.salt is None:
            self.test_2_get_salt(client)
        assert self.salt is not None
        encrypted_pwd = "$2b$12$VylSSIUNRsxTDbHo1.UnHuDFFv5MV7mgWS8NAsQdiqOl5yAsuGAa."
        data = {"username": TestApis.test_username, "password": encrypted_pwd}
        rv = client.post("/v2/user/login", content_type='application/json', data=json.dumps(data))
        self.assertStatus(rv, 200)
        response = json.loads(rv.text)
        self.assertIn("userkey", response.keys())
        self.userkey = response['userkey']

    def test_4_login_failed(self, client: FlaskClient):
        fail_username = "abc"
        fail_password = "fake_pwd"
        if self.salt is None:
            self.test_2_get_salt(client)
        assert self.salt is not None
        data = {"username": fail_username, "password": fail_password}
        rv = client.post("/v2/user/login", content_type='application/json', data=json.dumps(data))
        self.assertStatus(rv, 400)

    def test_5_update_userkey_succeed(self, client: FlaskClient):
        if self.userkey is None:
            self.test_3_login_succeed(client)
        assert self.userkey is not None
        rv = client.get(f"/v2/user/update-userkey?userkey={self.userkey}")
        self.assertStatus(rv, 200)
        response = json.loads(rv.text)
        self.assertIn("userkey", response.keys())
        self.userkey = response['userkey']

    def test_6_update_userkey_fail(self, client: FlaskClient):
        fake_userkey = "abcdefg"
        rv = client.get(f"/v2/user/update-userkey?userkey={fake_userkey}")
        self.assertStatus(rv, 400)

    def test_7_get_vocabulary(self, client: FlaskClient):
        if self.userkey is None:
            self.test_3_login_succeed(client)
        assert self.userkey is not None
        rv = client.get(f"/v2/corpus/vocabulary-and-details?userkey={self.userkey}&count={TestApis.test_count}")
        self.assertStatus(rv, 200)
        response = json.loads(rv.text)
        self.assertIn("vocabulary", response.keys())
        self.assertIn("word_details", response.keys())
        self.assertIsNotNone(response['vocabulary'])
        self.assertIsNotNone(response['word_details'])

    def test_8_get_review_test(self, client: FlaskClient):
        if self.userkey is None:
            self.test_3_login_succeed(client)
        assert self.userkey is not None
        rv = client.get(f"/v2/corpus/review_vocabulary_and_words?userkey={self.userkey}")
        self.assertStatus(rv, 200)
        response = json.loads(rv.text)
        self.assertIn("vocabulary", response.keys())
        self.assertIn("word_details", response.keys())
        self.assertIsNotNone(response['vocabulary'])
        self.assertIsNotNone(response['word_details'])

    def test_9_get_homework(self, client: FlaskClient):
        rv = client.get("/homework")
        self.assertStatus(rv, 200)
        response = json.loads(rv.text)
        self.assertIn("todo_list", response.keys())


if __name__ == "__main__":
    pytest.main(["test_api.py"])
