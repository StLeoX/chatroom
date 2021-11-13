#!/usr/bin/python3
import socket
import selectors
import sys
import types
import json

#
import server_config
from logger import *
from server_utils import authorizer, history

#
_PROMPT_INFO = 'INFO: '  # server push


class Server(object):
    def __init__(self, host: str, port: int, timeout: int):
        self.timeout = timeout
        self.sock_addr = (host, port)
        self.listening_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listening_socket.bind((host, port))
        self.listening_socket.setblocking(False)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.listening_socket, selectors.EVENT_READ, data=None)
        self.map_user_status = {}  # username:status; status: online,offline,blocked
        self.map_uuid_conn = {}  # addr:conn
        self.map_uuid_user = {}  # uuid:username

    def listen(self):
        log_info(f"listening on {self.sock_addr[0]}:{self.sock_addr[1]}.")
        self.listening_socket.listen()

    def run(self):
        self.listen()
        try:
            while True:  # poll
                events = self.selector.select(timeout=self.timeout)
                for key, mask in events:
                    if key.data is None:  # new conn
                        self.init_connection(key)
                    else:  # serve established conn
                        self.serve_connection(key, mask)
        except KeyboardInterrupt:
            log_info("server stopping.")
        finally:
            self.selector.close()

    def init_connection(self, key):
        sock = key.fileobj
        conn, addr = sock.accept()  # Should be ready to read
        conn.setblocking(False)
        uuid_ = conn.recv(1024).decode()
        log_info(f"accepted connection from {addr[0]}:{addr[1]}. connid is {uuid_}.")
        self.map_uuid_conn[uuid_] = conn
        session = types.SimpleNamespace(connid=uuid_, addr=addr, inb=b'', outb=b'')  # separate session
        self.selector.register(conn, selectors.EVENT_READ | selectors.EVENT_WRITE, data=session)

    def serve_connection(self, key, mask):
        sock = key.fileobj
        session = key.data
        if mask & selectors.EVENT_READ:  # ref to client.session
            recv_data = sock.recv(1024)
            if recv_data:
                log_srv(f"VIA {session.connid} RECV: {recv_data.decode()}")
                session.outb += self.dispatch(json.loads(recv_data))
            else:  # read nothing
                log_info(f"closing connection to {session.addr[0]}:{session.addr[1]}.")
                self.selector.unregister(sock)
                sock.close()
        if mask & selectors.EVENT_WRITE:  # ref to server.session
            if len(session.outb) != 0:
                log_srv(f"VIA {session.connid} SENT: {session.outb.decode()}")
                sent = sock.send(session.outb)  # sent: count of sent data
                session.outb = session.outb[sent:]  # update buffer pointer

    # consume request msg, return response msg.
    # msg_dict format: {user:str, cmd_type:str, cmd_args:list}
    def dispatch(self, req: dict) -> bytes:  # todo: untest
        user_name = req['user']
        cmd_type = req['cmd_type']
        ok, ret = self.check_status(user_name, cmd_type)  # ok means return immediately
        if ok:
            return ret.encode()
        # python reflect
        return getattr(self, cmd_type)(*([user_name] + req['cmd_args'])).encode()

    # filter
    def check_status(self, user, cmd) -> tuple:
        status = None
        try:
            status = self.map_user_status[user]
        except:
            pass
        if status == 'online':
            if cmd == 'login':
                return True, f"you have login with name {user}."
            return False, None
        elif status == 'offline':
            return True, "login first"
        elif status == 'blocked':
            if cmd != 'logout':
                return True, "unblock first"
        else:
            return False, None

    # hanlders
    def login(self, user, name, pw, uid):
        if not authorizer.exist_name(name) or name is None:
            return "username does not exist."
        if not authorizer.match_pw(name, pw):
            return "password does not match."
        self.map_uuid_user[uid] = name
        self.map_user_status[name] = 'online'
        self.broadcast(user, f"user {user} has just login.")
        history.login_append(name)
        return "login success"

    def logout(self, user, uid):
        self.selector.unregister(self.map_uuid_conn[uid].fileno())
        self.map_user_status[self.map_uuid_user] = 'offline'
        self.broadcast(user, f"user {user} has just logout.")
        return "logout success"

    def message(self, user, target, msg):
        for uid, name in self.map_uuid_user.items():
            if name == target:
                self.map_uuid_conn[uid].send(f"{user} send to you: {msg}".encode())
                return "send message success"
        return "target_not_found"

    def broadcast(self, user, msg):
        for uid, name in self.map_uuid_user.items():
            if name != user:
                self.map_uuid_conn[uid].send(f"broadcast to you: {msg}".encode())
        return "broadcast success"

    def whoami(self, user):
        return f"your are {user}"

    def whoelse(self, user):
        res = []
        for name, status in self.map_user_status.items():
            if status == "online":
                res.append(name)
        try:
            res.remove(user)
        except:  # ignore
            pass
        ret = "current users except you are: "
        for r in res:
            ret += r
        return ret

    def whoelsesince(self, user, sec):
        res = history.login_since(int(sec))
        try:
            res.remove(user)
        except:  # ignore
            pass
        ret = f"users since {sec} seconds ago are: "
        for r in res:
            ret += r
        return ret

    def block(self, user, target):
        for name, status in self.map_user_status.items():
            if name == target:
                self.map_user_status[name] = 'blocked'
                return f"block {target} success"
        return "target_not_found"

    def unblock(self, user, target):
        for name, status in self.map_user_status.items():
            if name == target:
                self.map_user_status[name] = 'online'
                return f"unblock {target} success"
        return "target_not_found"

    def debug(self, user, _):
        return f'''
        map_user_status: {self.map_user_status}\n
        map_uuid_user: {self.map_uuid_user}\n
        '''

    ##
    # constructed from cli args
    @staticmethod
    def get_customized_server():
        args = sys.argv
        assert len(args) == 4, "usage: ./server.py <host> <port> <timeout>."
        return Server(args[1], int(args[2]), int(args[3]))

    # do not need cli args
    @staticmethod
    def get_default_server():
        return Server(server_config.host_default, server_config.port_default, server_config.timeout_default)


if __name__ == '__main__':
    if len(sys.argv) == 1:
        Server.get_default_server().run()
    elif len(sys.argv) == 4:
        Server.get_customized_server().run()
    else:
        print("usage: ./server.py <host> <port> <timeout>.")
