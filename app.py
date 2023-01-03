from flask import Flask

app = Flask(__name__)


@app.route('/')
def hello_world():  # put application's code here
    return 'Hello World!'


"""
用户登录及注册相关接口
"""

"""
语料库获取相关，需要用户已登录并已获得UserKey，以后所有数据库获取都需要UserKey
"""


@app.route('/corpus/vocabulary', methods=['GET'])
def get_vocabulary():
    # args = request.args
    # # get UserKey from args
    # user_key = args.get('UserKey')
    # user = get_user_by_key(user_key)
    # # get suitable vocabulary for user
    # vocabulary = get_vocabulary_for_user(user)
    # return vocabulary
    return {'type': 'vocabulary'}, 200, {'ContentType': 'application/json'}


@app.route('/corpus/word-details', methods=['GET'])
def get_word_details():
    # args = request.args
    # # get UserKey from args
    # user_key = args.get('UserKey')
    # user = get_user_by_key(user_key)
    # # get suitable vocabulary for user
    # vocabulary = get_word_details_for_user(user)
    # return vocabulary
    return {'type': 'word-details'}, 200, {'ContentType': 'application/json'}


if __name__ == '__main__':
    app.run()
