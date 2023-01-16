import abc
import json
import typing


class TypeRestrictList(typing.MutableSequence):
    # 限制类型的数组
    def __init__(self, *args):
        self.list = list()
        self.extend(*args)

    @abc.abstractmethod
    def check(self, item):
        # 类型检查
        return NotImplemented

    def to_dict(self) -> dict:
        json_str = str(self)
        json_dict = json.loads(json_str)
        return json_dict

    def __len__(self): return len(self.list)

    def __getitem__(self, i): return self.list[i]

    def __delitem__(self, i): del self.list[i]

    def __setitem__(self, i, v):
        self.check(v)
        self.list[i] = v

    def insert(self, i, v):
        self.check(v)
        self.list.insert(i, v)

    def __str__(self):
        inner = [str(item) for item in self.list]
        inner_str = ','.join(inner)
        return '[' + inner_str + ']'
