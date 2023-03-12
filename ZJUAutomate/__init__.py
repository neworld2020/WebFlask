import json

import requests
from bs4 import BeautifulSoup


class HomeworkAutomate:
    def __init__(self, username: str, passowrd: str):
        self.username = username
        self.password = passowrd
        self.session = requests.Session()
        self.session.headers = {
            "Cache-Control": "max-age=0",
            "Sec-Ch-Ua": 'Not A(Brand"; v="24", "Chromium"; v="110',
            "Sec-Ch-Ua-Mobile": '?0',
            "Sec-Ch-Ua-Platform": "Windows",
            "Upgrade-Insecure-Requests": "1",
            "Origin": "https://zjuam.zju.edu.cn",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-User": "?1",
            "Sec-Fetch-Dest": "document",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "close",
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36',
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": "https://zjuam.zju.edu.cn/cas/login?service=http%3A%2F%2Fzjuam.zju.edu.cn%2Fcas%2Foauth2.0%2FcallbackAuthorize"
        }

    def get(self) -> dict:
        homework_req = self.session.get("https://courses.zju.edu.cn/api/todos?no-intercept=true")
        try:
            homework_json = json.loads(homework_req.text)
        except json.JSONDecodeError:
            if not self._connect_():
                raise ConnectionRefusedError("账户名或密码错误")
            homework_req = self.session.get("https://courses.zju.edu.cn/api/todos?no-intercept=true")
            try:
                homework_json = json.loads(homework_req.text)
            except json.JSONDecodeError:
                raise RuntimeError("Internal Server May Refuse Your Request")
        return homework_json

    def _connect_(self) -> bool:
        res = self.session.get(
            "http://zjuam.zju.edu.cn/cas/oauth2.0/authorize?response_type=code&client_id=RKC5F6GbNhA00enbNx&redirect_uri=http://course.zju.edu.cn/callback/")
        # process html, get execution, get cookie: JSESSIONID
        soup = BeautifulSoup(res.text, features="html.parser")
        execution = soup.find(id="fm1").contents[9]['value']
        # get pubkey
        res = self.session.get("https://zjuam.zju.edu.cn/cas/v2/getPubKey")
        pubKey = json.loads(res.content)
        modulus = int(pubKey['modulus'], base=16)
        exponent = int(pubKey['exponent'], base=16)
        # encrypt and login

        password_bytes = bytes(self.password, 'ascii')
        password_int = int.from_bytes(password_bytes, 'big')
        result_int = pow(password_int, exponent, modulus)
        encrypted_pwd = hex(result_int)[2:].rjust(128, '0')

        data = {
            "username": self.username,
            "password": encrypted_pwd,
            "authcode": "",
            "execution": execution,
            "_eventId": "submit"
        }

        res = self.session.post(
            "https://zjuam.zju.edu.cn/cas/login?service=http%3A%2F%2Fzjuam.zju.edu.cn%2Fcas%2Foauth2.0%2FcallbackAuthorize",
            data)
        if res.history[0].status_code == 302:
            return True
        else:
            return False


if __name__ == "__main__":
    # test
    homeworkGetter = HomeworkAutomate("3200105210", "zjdx774225688")
    print(homeworkGetter.get())
