import ast
from datetime import datetime, timedelta
from typing import Tuple

import bcrypt
from flasgger import Swagger
from flask import Flask, request, send_file, send_from_directory

from logs import getLogHandler
from mysql.Base import BaseMysqlClient, random_str
from response_models import *

app = Flask(__name__)
app.logger.addHandler(getLogHandler())
app.testing = True

template = {
    "swagger": "2.0",
    "info": {
        "title": "Playen APIs",
        "description": "API for Playen App",
        "version": "0.2.0"
    },
}
swagger = Swagger(app, template=template)
app.config['JSON_AS_ASCII'] = False

base_db_client = BaseMysqlClient('rm-bp1712iyj3s1906i92o.mysql.rds.aliyuncs.com', 'account_admin', 'account@123456',
                                 'memo-app-db')


@app.before_request
def log_request():
    app.logger.info('Method:{}, Path:{}, Addr:{}'.format(request.method, request.path, request.remote_addr))


@app.route('/')
def index():
    """返回网站首页
    ---
    tags:
      ['首页']
    responses:
      200:
        description: Index Page
    """
    return send_file("index/index.html")


@app.route('/file/<filename>', methods=['GET'])
def file(filename: str):
    return send_from_directory("index/file", filename, as_attachment=True)


"""
用户登录及注册相关接口
"""


@app.route('/user/salt', methods=['GET'])
def get_salt():
    """获取加密盐
    ---
    parameters:
      - name: username
        in: path
        type: string
        required: true
    tags:
      ['用户管理']
    definitions:
      SaltResponse:
        type: object
        properties:
          salt:
            type: string
    responses:
      200:
        description: 返回盐字符串
        schema:
          $ref: '#/definitions/SaltResponse'
        examples:
          {"salt": "a3fda8n380yr89..."}
    """
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


@app.route("/v2/user/login", methods=['POST'])
def v2_login():
    """
    file: api_ymls/v2_login.yml
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
        else:
            # update userkey
            update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            update_session_cmd = f"""UPDATE usersession 
                                     SET userkey='{user_key}', update_time='{update_time}' 
                                     WHERE username='{username}';"""
            base_db_client.run(update_session_cmd)
        return {"userkey": user_key}, 200, {'ContentType': 'application/json'}
    else:
        # login fail
        return {'error': 'login fail'}, 400, {'ContentType': 'application/json'}


@app.route("/user/register", methods=['POST'])
def register():
    """
    file: api_ymls/register.yml
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


@app.route('/v2/user/update-userkey', methods=['GET'])
def UpdateUserkey():
    """
    file: api_ymls/v2_update_userkey.yml
    """
    args = request.args
    userkey = args.get('userkey')
    user = get_user_by_key(userkey)
    if user is None:
        return {'error': 'wrong userkey or expired userkey'}, 400, {'ContentType': 'application/json'}
    else:
        # update userkey
        update_userkey = random_str(64)
        current_time = datetime.now()
        time_str = current_time.strftime("%Y-%m-%d %H:%M:%S")
        update_cmd = f"""UPDATE usersession 
                         SET userkey='{update_userkey}', update_time='{time_str}' 
                         WHERE userkey='{userkey}';"""
        base_db_client.run(update_cmd)
        return {"userkey": update_userkey}, 200, {'ContentType': 'application/json'}


"""
语料库获取相关，需要用户已登录并已获得userkey，以后所有数据库获取都需要userkey
"""


def get_user_by_key(userkey: str):
    find_session_cmd = f"""SELECT update_time FROM usersession WHERE userkey='{userkey}';"""
    result = base_db_client.select(find_session_cmd)
    current_time = datetime.now()
    if len(result) == 0 or current_time - result[0][0] >= timedelta(weeks=1):
        # userkey not found or expired -- one week
        return None
    else:
        return result[0][0]


def get_corpus_for_user(user: str, voca_num: int = 20) -> Tuple[Vocabulary, WordDetails]:
    # 从数据库中搜索
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

    # 返回结构组织
    WordDetails_list = []
    vocabulary = []
    for i in range(voca_num):
        contents_list = ast.literal_eval(result[i][2])
        w = Word(result[i][0], 0)
        vocabulary.append(w)
        to_contents_list = []
        for content in contents_list:
            c = Content(content["speaker"], content["speakerColor"], content["content"], content["translation"])
            to_contents_list.append(c)
        cs = Contents(to_contents_list)
        wd = WordDetail(result[i][0], result[i][1], cs)
        WordDetails_list.append(wd)
    vs = Vocabulary(vocabulary)
    wds = WordDetails(WordDetails_list)

    # 更新用户词汇表 -- 未来讲拆解至另外的函数
    search_cmd = f"""SELECT word FROM uservoca WHERE username='{user}';"""
    result = base_db_client.select(search_cmd)
    if len(result) > 0:
        update_voca_cmd = f"""UPDATE uservoca SET word='{update_word}' WHERE username='{user}';"""
        base_db_client.run(update_voca_cmd)
    else:
        new_voca_cmd = f"""INSERT INTO uservoca VALUES('{user}', '{update_word}')"""
        base_db_client.run(new_voca_cmd)

    return vs, wds


@app.route('/v2/corpus/vocabulary-and-details', methods=['GET'])
def get_vocabulary_and_details():
    """
    file: api_ymls/v2_vocabulary_and_details.yml
    """
    args = request.args
    user_key = args.get('userkey')
    try:
        count = int(args.get('count'))
    except ValueError:
        return {"error": "count type error"}, 400, {'ContentType': 'application/json'}
    user = get_user_by_key(user_key)
    if user is None:
        return {'error': 'userkey not found or expired'}, 400, {'ContentType': 'application/json'}
    corpus = get_corpus_for_user(user, count)
    vocabulary = corpus[0].to_dict()
    word_details = corpus[1].to_dict()
    return {"vocabulary": vocabulary, "word_details": word_details}, 200, \
        {'ContentType': 'application/json'}


if __name__ == '__main__':
    app.run()
