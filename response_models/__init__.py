from marshmallow import Schema, fields

from response_models.TypeRestrictList import TypeRestrictList


class Word:
    """
    {
        "word": "abandon",
        "familiar_degree": 0(0-5)
    }
    """

    familiar_degree_min = 0
    familiar_degree_max = 5

    def __init__(self, word: str, familiar_degree: int):
        self.word = word
        if Word.familiar_degree_min <= familiar_degree <= Word.familiar_degree_max:
            self.familiar_degree = familiar_degree
        else:
            raise ValueError("familiar_degree只能是0-5的整数")

    def __str__(self):
        class WordSchema(Schema):
            word = fields.String()
            familiar_degree = fields.Integer()

        ws = WordSchema()
        return ws.dumps(self)


class Vocabulary(TypeRestrictList):
    # 创建一个只能储存Word类型的数组 -- 只需更改check方法
    def check(self, item):
        if isinstance(item, Word):
            return True
        else:
            raise TypeError("Vocabulary中储存的数据只能是Word")


class Content:
    def __init__(self, speaker: str, speakerColor: str,
                 content: str, translation: str):
        self.speaker = speaker
        self.speakerColor = speakerColor
        self.content = content
        self.translation = translation

    def __str__(self):
        class ContentSchema(Schema):
            speaker = fields.String()
            speakerColor = fields.String()
            content = fields.String()
            translation = fields.String()

        cs = ContentSchema()
        return cs.dumps(self)


class Contents(TypeRestrictList):
    # list[Content]
    def check(self, item):
        if not isinstance(item, Content):
            raise TypeError("Contents的元素只能是Content")
        else:
            return True


class WordDetail:
    """{
        "word": "abandon",
        "word_translation": "v.抛弃...",
        "contents": [
            {
                "speaker": "Jack",
                "speakerColor": "Black",
                "content": "...",
                "translation": "..."
            },
            ...
        ]
    }"""

    def __init__(self, word: str, word_translation: str, contents: Contents):
        self.word = word
        self.word_translation = word_translation
        self.contents = [content.__dict__ for content in contents]

    def __str__(self):
        class WordDetailSchema(Schema):
            word = fields.String()
            word_translation = fields.String()
            contents = fields.List(fields.Dict())

        wds = WordDetailSchema()
        return wds.dumps(self)


class WordDetails(TypeRestrictList):
    # 创建一个只能储存WordDetail类型的数组 -- 只需更改check方法
    def check(self, item):
        if isinstance(item, WordDetail):
            return True
        else:
            raise TypeError("Vocabulary中储存的数据只能是Word")


if __name__ == "__main__":
    # 测试用
    w1 = Word("hello", 0)
    w2 = Word("world", 1)
    try:
        w_err = Word("hello", -1)
    except ValueError:
        print("Word异常测试通过")
    print(str(w1))

    v = Vocabulary([w1, w2])
    try:
        v_err = Vocabulary([1, 2])
    except TypeError:
        print("Vocabulary类型异常测试通过")
    print(str(v))

    c1 = Content("I", "Yellow", "Goodbye!", "再见了！")
    c2 = Content("You", "Green", "OK, Goodbye!", "好的，再见了！")
    cs = Contents([c1, c2])
    wd = WordDetail("goodbye", "再见", cs)
    print(str(wd))
