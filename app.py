import random
from datetime import datetime, timedelta

from flask import Flask, request

from DB_Client import DB_Client

app = Flask(__name__)


def random_str(length: int) -> str:
    # generate a string randomly
    source_str = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    source_str_len = len(source_str)
    result_str = ""
    for i in range(0, length):
        result_str += random.choice(source_str)
    return result_str


@app.route('/')
def hello_world():  # put application's code here
    return 'Hello World!'


"""
用户登录及注册相关接口
"""


@app.route('/salt', methods=['GET'])
def get_salt():
    args = request.args
    username = args.get('username')
    # 1. connect to database
    db_client = DB_Client()
    # 2. find if user has registered
    find_user_cmd = f"""SELECT salt FROM UserInfo WHERE username='{username}';"""
    result = db_client.select(find_user_cmd)
    salt = None
    if len(result) == 0:
        # not registered -- generate salt
        salt = random_str(64)
    else:
        salt = result[0][0]
    return {"salt": salt}, 200, {'ContentType': 'application/json'}


@app.route('/login', methods=['POST'])
def login():
    """
    {
        "username": "...",
        "password": "..."
    }
    """
    username = request.json.get("username").strip()  # 用户名
    password = request.json.get("password").strip()  # 密码

    db_client = DB_Client()
    login_cmd = f"""SELECT * FROM UserInfo WHERE username='{username}' AND password='{password}';"""
    result = db_client.select(login_cmd)
    if len(result) > 0:
        # login success, allocate UserKey
        session_activate_cmd = f"""SELECT UserKey, update_time FROM UserSession WHERE username='{username}';"""
        session_result = db_client.select(session_activate_cmd)
        user_key = random_str(64)
        if len(session_result) == 0:
            # store in database
            update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_session_cmd = f"""INSERT INTO UserSession VALUES ('{username}', '{user_key}', '{update_time}');"""
            db_client.run(new_session_cmd)
            return {'UserKey': user_key}, 200, {'ContentType': 'application/json'}
        else:
            # update UserKey -- 10 minutes
            update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            update_session_cmd = f"""UPDATE UserSession SET UserKey='{user_key}', update_time='{update_time}' 
                                     WHERE username='{username}';"""
            db_client.run(update_session_cmd)
            return {'UserKey': user_key}, 200, {'ContentType': 'application/json'}
    else:
        # login fail
        return {'error': 'login fail'}, 400, {'ContentType': 'application/json'}


"""
语料库获取相关，需要用户已登录并已获得UserKey，以后所有数据库获取都需要UserKey
"""


def get_user_by_key(UserKey: str):
    db_client = DB_Client()
    get_user_cmd = f"""SELECT * FROM UserSession WHERE UserKey='{UserKey}';"""
    result = db_client.select(get_user_cmd)
    if len(result) == 0 or datetime.now() - result[0][2] > timedelta(days=1):
        # UserKey not found or expired -- one day
        return None
    else:
        return result[0][0]


@app.route('/vocabulary', methods=['GET'])
def get_vocabulary():
    args = request.args
    # get UserKey from args
    user_key = args.get('UserKey')
    user = get_user_by_key(user_key)
    if user is None:
        return {'error': 'UserKey not found or expired'}, 400, {'ContentType': 'application/json'}
    # # get suitable vocabulary for user
    # vocabulary = get_vocabulary_for_user(user)
    # return vocabulary
    return {'type': 'vocabulary'}, 200, {'ContentType': 'application/json'}


@app.route('/word-details', methods=['GET'])
def get_word_details():
    args = request.args
    # get UserKey from args
    user_key = args.get('UserKey')
    user = get_user_by_key(user_key)
    if user is None:
        return {'error': 'UserKey not found or expired'}, 400, {'ContentType': 'application/json'}
    # # get suitable vocabulary for user
    # word_details = get_word_details_for_user(user)
    # return word_details
    return {'type': 'word-details'}, 200, {'ContentType': 'application/json'}


if __name__ == '__main__':
    app.run()
