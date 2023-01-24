import ast
from datetime import datetime, timedelta

import bcrypt
from flask import Flask, request, send_file

from mysql.Base import BaseMysqlClient, random_str
from response_models import *

app = Flask(__name__)
base_db_client = BaseMysqlClient('rm-bp1712iyj3s1906i92o.mysql.rds.aliyuncs.com', 'account_admin', 'account@123456',
                                 'memo-app-db')


@app.route('/')
def index():
    # 返回主页
    return send_file("index/index.html")


"""
用户登录及注册相关接口
"""


@app.route('/user/salt', methods=['GET'])
def get_salt():
    args = request.args
    username = args.get('username')
    # 2. find if user has registered
    find_user_cmd = f"""SELECT salt FROM userinfo WHERE username='{username}';"""
    result = base_db_client.select(find_user_cmd)
    salt = None
    if len(result) == 0:
        # not registered -- generate salt
        salt = bcrypt.gensalt().decode('utf8')
    else:
        salt = result[0][0]
    return {"salt": salt}, 200, {'ContentType': 'application/json'}


@app.route('/user/login', methods=['POST'])
def login():
    """
    {
        "username": "...",
        "password": "..."
    }
    :return
    {
        "userkey": ...,
        "token": ...
    }
    """
    username = request.json.get("username").strip()  # 用户名
    password = request.json.get("password").strip()  # 密码

    login_cmd = f"""SELECT * FROM userinfo WHERE username='{username}' AND password='{password}';"""
    result = base_db_client.select(login_cmd)
    if len(result) > 0:
        # allocate token
        check_token_stored_cmd = f"""SELECT token FROM user_token WHERE username='{username}';"""
        token_result = base_db_client.select(check_token_stored_cmd)
        token = random_str(64)
        if len(token_result) > 0:
            # update token
            update_token_cmd = f"""UPDATE user_token SET token='{token}' WHERE username='{username}';"""
            base_db_client.run(update_token_cmd)
        else:
            # insert token
            new_token_cmd = f"""INSERT INTO user_token (username, token) 
                                VALUES ('{username}', '{token}');"""
            base_db_client.run(new_token_cmd)
        # login success, allocate userkey
        session_activate_cmd = f"""SELECT userkey, update_time FROM usersession WHERE username='{username}';"""
        session_result = base_db_client.select(session_activate_cmd)
        user_key = random_str(64)
        if len(session_result) == 0:
            # store in database
            update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_session_cmd = f"""INSERT INTO usersession VALUES ('{username}', '{user_key}', '{update_time}');"""
            base_db_client.run(new_session_cmd)
        else:
            # update userkey -- 10 minutes
            update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            update_session_cmd = f"""UPDATE usersession 
                                     SET userkey='{user_key}', update_time='{update_time}' 
                                     WHERE username='{username}';"""
            base_db_client.run(update_session_cmd)
        ret_json = {
            "userkey": user_key,
            "token": token
        }
        return ret_json, 200, {'ContentType': 'application/json'}
    else:
        # login fail
        return {'error': 'login fail'}, 400, {'ContentType': 'application/json'}


@app.route("/user/register", methods=['POST'])
def register():
    """
    use to register for user
    RequestJson:
    {
        "username": ...,
        "password": ...,
        "salt": ...
    }
    :return: 200 for success, 400 for failure
    """
    username = request.json.get("username").strip()
    password = request.json.get("password").strip()
    salt = request.json.get("salt").strip()
    # find whether the username has been used
    duplicate_check_cmd = f"""SELECT username FROM userinfo WHERE username='{username}';"""
    result = base_db_client.select(duplicate_check_cmd)
    if len(result) > 0:
        return {'error': 'username exists'}, 400, {'ContentType': 'application/json'}
    else:
        # add to database and return 200
        insert_cmd = f"""INSERT INTO userinfo (username, password, salt) 
                         VALUES ('{username}', '{password}', '{salt}');"""
        base_db_client.run(insert_cmd)
        return {"status": "OK"}, 200, {'ContentType': 'application/json'}


@app.route("/user/update-userkey", methods=['GET'])
def UpdateUserkeyWithToken():
    """
    Path: /user/update-userkey?token=...
    :return:
    {
        "token": ...(new token)
        "userkey": ...(new userkey)
    }
    """
    args = request.args
    token = args.get('token')
    get_user_by_token_cmd = f"""SELECT username FROM user_token WHERE token='{token}';"""
    result = base_db_client.select(get_user_by_token_cmd)
    if len(result) == 0:
        return {'error': 'token not found'}, 400, {'ContentType': 'application/json'}
    username = result[0][0]
    # update userkey and token
    new_token = random_str(64)
    new_userkey = random_str(64)
    update_time = datetime.now()
    update_token_cmd = f"""UPDATE user_token SET token='{new_token}' WHERE username='{username}';"""
    update_userkey_cmd = f"""UPDATE usersession 
                             SET userkey='{new_userkey}', update_time='{update_time}' 
                             WHERE username='{username}';"""
    base_db_client.run(update_userkey_cmd)
    base_db_client.run(update_token_cmd)
    # return result
    result = {
        "token": new_token,
        "userkey": new_userkey
    }
    return result, 200, {'ContentType': 'application/json'}


"""
语料库获取相关，需要用户已登录并已获得userkey，以后所有数据库获取都需要userkey
"""


def get_user_by_key(userkey: str):
    get_user_cmd = f"""SELECT * FROM usersession WHERE userkey='{userkey}';"""
    result = base_db_client.select(get_user_cmd)
    if len(result) == 0 or datetime.now() - result[0][2] > timedelta(days=1):
        # userkey not found or expired -- one day
        return None
    else:
        return result[0][0]


def get_vocabulary_for_user(user: str, voca_num: int = 20) -> Vocabulary:
    search_cmd = f"""SELECT word FROM uservoca WHERE username='{user}';"""
    result = base_db_client.select(search_cmd)
    if len(result) > 0:
        word = result[0][0]
        new_voca_cmd = f"""INSERT INTO static_vocabulary(%s) VALUES(%s)"""
    else:
        search_cmd = """SELECT word FROM static_vocabulary LIMIT 0, 1;"""
        result = base_db_client.select(search_cmd)
        word = result[0][0]

    find_row_num_cmd = f"""
    SELECT * from (
    SELECT word,(@rowno:=@rowno+1) as rowno
    FROM static_vocabulary,(SELECT (@rowno:=-1)) b) t
    WHERE word = '{word}';
    """
    result = base_db_client.select(find_row_num_cmd)
    row_num = int(result[0][1])

    find_vocabulary_cmd = f"""SELECT word FROM static_vocabulary LIMIT {row_num}, {voca_num};"""
    result = base_db_client.select(find_vocabulary_cmd)

    word_list = []
    for i in range(voca_num):
        w = Word(result[i][0], 0)
        word_list.append(w)
    v = Vocabulary(word_list)
    return v


@app.route('/corpus/vocabulary', methods=['GET'])
def get_vocabulary():
    args = request.args
    # get userkey from args
    user_key = args.get('userkey')
    user = get_user_by_key(user_key)
    if user is None:
        return {'error': 'userkey not found or expired'}, 400, {'ContentType': 'application/json'}
    # # get suitable vocabulary for user
    vocabulary = get_vocabulary_for_user(user)
    # return vocabulary
    return vocabulary.to_dict(), 200, {'ContentType': 'application/json'}


def get_word_details_for_user(user: str, voca_num: int = 20) -> WordDetails:
    search_cmd = f"""SELECT word FROM uservoca WHERE username='{user}';"""
    result = base_db_client.select(search_cmd)
    if len(result) > 0:
        word = result[0][0]

    else:
        search_cmd = """SELECT word FROM static_vocabulary LIMIT 0, 1;"""
        result = base_db_client.select(search_cmd)
        word = result[0][0]

    find_row_num_cmd = f"""
    SELECT * from (
    SELECT word,(@rowno:=@rowno+1) as rowno
    FROM static_vocabulary,(SELECT (@rowno:=-1)) b) t
    WHERE word = '{word}';
    """
    result = base_db_client.select(find_row_num_cmd)
    row_num = int(result[0][1])

    find_word_details_cmd = f"""SELECT * FROM static_vocabulary LIMIT {row_num}, {voca_num};"""
    result = base_db_client.select(find_word_details_cmd)

    update_word_cmd = f"""SELECT word FROM static_vocabulary LIMIT {row_num + voca_num}, 1;"""
    update_result = base_db_client.select(update_word_cmd)
    update_word = update_result[0][0]

    WordDetails_list = []
    for i in range(voca_num):
        contents_list = ast.literal_eval(result[i][2])
        to_contents_list = []
        for content in contents_list:
            c = Content(content["speaker"], content["speakerColor"], content["content"], content["translation"])
            to_contents_list.append(c)
        cs = Contents(to_contents_list)
        wd = WordDetail(result[i][0], result[i][1], cs)
        WordDetails_list.append(wd)
    wds = WordDetails(WordDetails_list)

    search_cmd = f"""SELECT word FROM uservoca WHERE username='{user}';"""
    result = base_db_client.select(search_cmd)
    if len(result) > 0:
        update_voca_cmd = f"""UPDATE uservoca SET word='{update_word}' WHERE username='{user}';"""
        base_db_client.run(update_voca_cmd)
    else:
        new_voca_cmd = f"""INSERT INTO uservoca VALUES('{user}', '{update_word}')"""
        base_db_client.run(new_voca_cmd)

    return wds


@app.route('/corpus/word-details', methods=['GET'])
def get_word_details():
    args = request.args
    # get userkey from args
    user_key = args.get('userkey')
    user = get_user_by_key(user_key)
    if user is None:
        return {'error': 'userkey not found or expired'}, 400, {'ContentType': 'application/json'}
    # # get suitable vocabulary for user
    word_details = get_word_details_for_user(user)
    # return word_details
    return word_details.to_dict(), 200, {'ContentType': 'application/json'}


@app.route('/corpus/vocabulary-and-details', methods=['GET'])
def get_vocabulary_and_details():
    # 更新后的API -- 同时获取vocabulary和details
    args = request.args
    user_key = args.get('userkey')
    try:
        count = int(args.get('count'))
    except ValueError:
        return {"error": "count type error"}, 400, {'ContentType': 'application/json'}
    user = get_user_by_key(user_key)
    if user is None:
        return {'error': 'userkey not found or expired'}, 400, {'ContentType': 'application/json'}
    vocabulary = get_vocabulary_for_user(user, count).to_dict()
    word_details = get_word_details_for_user(user, count).to_dict()
    return {"vocabulary": vocabulary, "word_details": word_details}, 200, \
        {'ContentType': 'application/json'}


if __name__ == '__main__':
    app.run()
