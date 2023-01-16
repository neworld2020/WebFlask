import ast
from datetime import datetime, timedelta

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
        salt = random_str(64)
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
    """
    username = request.json.get("username").strip()  # 用户名
    password = request.json.get("password").strip()  # 密码

    login_cmd = f"""SELECT * FROM userinfo WHERE username='{username}' AND password='{password}';"""
    result = base_db_client.select(login_cmd)
    if len(result) > 0:
        # login success, allocate userkey
        session_activate_cmd = f"""SELECT userkey, update_time FROM usersession WHERE username='{username}';"""
        session_result = base_db_client.select(session_activate_cmd)
        user_key = random_str(64)
        if len(session_result) == 0:
            # store in database
            update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            new_session_cmd = f"""INSERT INTO usersession VALUES ('{username}', '{user_key}', '{update_time}');"""
            base_db_client.run(new_session_cmd)
            return {'userkey': user_key}, 200, {'ContentType': 'application/json'}
        else:
            # update userkey -- 10 minutes
            update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            update_session_cmd = f"""UPDATE usersession SET userkey='{user_key}', update_time='{update_time}' 
                                     WHERE username='{username}';"""
            base_db_client.run(update_session_cmd)
            return {'userkey': user_key}, 200, {'ContentType': 'application/json'}
    else:
        # login fail
        return {'error': 'login fail'}, 400, {'ContentType': 'application/json'}


"""
语料库获取相关，需要用户已登录并已获得userkey，以后所有数据库获取都需要userkey
"""
voca_num = 20


def get_user_by_key(userkey: str):
    get_user_cmd = f"""SELECT * FROM usersession WHERE userkey='{userkey}';"""
    result = base_db_client.select(get_user_cmd)
    if len(result) == 0 or datetime.now() - result[0][2] > timedelta(days=1):
        # userkey not found or expired -- one day
        return None
    else:
        return result[0][0]


def get_vocabulary_for_user(user: str) -> Vocabulary:
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


def get_word_details_for_user(user: str) -> WordDetails:
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


if __name__ == '__main__':
    app.run()
