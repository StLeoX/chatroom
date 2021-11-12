import csv
import server_config
import time


class Authorizer(object):
    def __init__(self):
        self.cre_map = {}
        with open(server_config.cre_file, 'r') as f:
            lines = csv.DictReader(f, fieldnames=['name', 'pw'])
            for line in lines:
                self.cre_map[line['name']] = line['pw']

    def exist_name(self, name):
        return name in self.cre_map.keys()

    def match_pw(self, name, pw):
        return self.cre_map[name] == pw


class History(object):
    def __init__(self):
        self.his_file = server_config.login_his_file
        self.his = {}  # name:last login time
        self.writein()

    def writein(self):
        with open(self.his_file, 'r') as f:
            lines = csv.DictReader(f, fieldnames=['name', 'sec'])
            for line in lines:
                self.his[line['name']] = int(line['sec'])

    def writeback(self):
        with open(self.his_file, 'w') as f:
            for name, sec in self.his.items():
                f.write(f"{name},{sec}\n")

    def login_append(self, name):
        self.his[name] = int(time.time())
        self.writeback()

    def login_since(self, passed_sec: int):
        ret = []
        self.writein()
        for name, sec in self.his.items():
            if (int(time.time()) - self.his[name]) <= passed_sec:
                ret.append(name)
        return ret


authorizer = Authorizer()
history = History()
