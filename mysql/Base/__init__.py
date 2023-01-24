import random
from typing import Tuple

import pymysql


def random_str(str_len: int):
    chars = []
    alphabet = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    for i in range(0, str_len):
        index = random.randint(0, len(alphabet) - 1)
        chars.append(alphabet[index])
    return ''.join(chars)


class BaseMysqlClient:
    def __init__(self, host, account, password, db_name="accounts"):
        self.host = host
        self.account = account
        self.password = password
        self.db_name = db_name
        self.db = pymysql.connect(host=host, user=account, password=password, database=db_name)
        self.cursor = self.db.cursor()

    def select(self, mysql_command: str) -> Tuple[Tuple]:
        # ping: auto reconnect to database when connection is closed
        self.db.ping(True)
        try:
            self.cursor.execute(mysql_command)
            self.db.commit()
            response = self.cursor.fetchall()
            return response
        except Exception as e:
            print(e)
            self.db.rollback()

    def run(self, mysql_command: str) -> None:
        self.db.ping(True)
        try:
            self.cursor.execute(mysql_command)
            self.db.commit()
        except Exception as e:
            print(e)
            self.db.rollback()

    def close(self):
        self.db.close()
