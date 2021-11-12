#!/usr/bin/python3
import sys
import socket
import selectors
import uuid
import types
import json
from random import randint, random
import time
#
import server_config
import command

#
_PROMPT_INPUT = 'INPUT: '  # client pull
_PROMPT_OUTPUT = 'OUTPUT: '  # client pull
_PROMPT_INFO = 'INFO: '  # server push
_DFT_TIMEOUT = 60  # client timeout, if server is busy.


class Client(object):
    def __init__(self, srv_host: str, srv_port: int):
        self.uuid = str(uuid.uuid1())
        self.username = None
        self.hangup = False  # user is inputting
        self.srv_sock_addr = (srv_host, srv_port)
        self.srv_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # allow server push msg
        self.srv_socket.setblocking(False)
        # IO design
        # session is the msg carrier
        self.session = types.SimpleNamespace(connid=self.uuid,
                                             messages=list(),  # msg buffer,fifo
                                             msg_total=0,
                                             recv_total=0,
                                             outb=b'')
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.srv_socket, selectors.EVENT_READ | selectors.EVENT_WRITE, data=self.session)

    def run(self):
        # establish, actually these two statements should be atomic
        self.srv_socket.connect_ex(self.srv_sock_addr)
        self.srv_socket.send(self.uuid.encode())
        try:
            while True:
                # req
                self.REPL()
                # res
                events = self.selector.select(timeout=_DFT_TIMEOUT)
                for key, mask in events:
                    self.serve_connection(key, mask)
        except KeyboardInterrupt:
            print("client stopping.")
        finally:
            self.selector.close()

    # send single msg
    def add_msg(self, msg: dict):
        self.session.messages.append(json.dumps(msg).encode())

    def serve_connection(self, key, mask):
        sock = key.fileobj
        data = key.data
        if mask & selectors.EVENT_WRITE:
            if not data.outb and data.messages:
                data.outb = data.messages.pop(0)  # fifo
            if data.outb:
                # print('sending', repr(data.outb), 'via connection', data.connid)
                sent = sock.send(data.outb)  # Should be ready to write
                data.outb = data.outb[sent:]
        if mask & selectors.EVENT_READ:
            recv_data = sock.recv(1024)  # Should be ready to read
            if recv_data:
                # print('received', repr(recv_data), 'via connection', data.connid)
                self.async_info(recv_data.decode())
                data.recv_total += len(recv_data)
            if not recv_data or data.recv_total == data.msg_total:
                print('closing connection', data.connid)
                self.selector.unregister(sock)
                sock.close()

    def parser(self, raw: str) -> tuple:
        """

        deal user input
        :param raw: user input
        :return: (ok,tokens), ok means output immediately
        """
        tokens = raw.strip().split(' ')
        if tokens[0] == 'help':
            return True, command.get_help()
        check = command.check_cmd(tokens[0], len(tokens))
        if check:
            return True, check
        return False, tokens

    # main user loop
    # msg_dict format: {user:str, cmd_type:str, cmd_args:list}
    def REPL(self):
        user_input = input(_PROMPT_INPUT)
        ok, ret = self.parser(user_input)
        if ok:  # ok means output immediately
            print(_PROMPT_OUTPUT, ret)
            self.hangup = True
            return None
        else:
            if ret[0] == 'login' or ret[0] == 'logout':
                if ret[0] == 'login':
                    self.username = ret[1]
                msg = {'user': self.username, 'cmd_type': ret[0], 'cmd_args': ret[1:] + [self.uuid]}
            else:
                msg = {'user': self.username, 'cmd_type': ret[0], 'cmd_args': ret[1:]}
            self.add_msg(msg)

    # async msg display
    def async_info(self, msg: str):
        if self.hangup:
            print('\r')
        print(_PROMPT_INFO, msg)

    ##
    # constructed from cli args
    @staticmethod
    def get_customized_client():
        args = sys.argv
        assert len(args) == 3, "usage: ./client.py <host> <port>."
        return Client(args[1], int(args[2]))

    # do not need cli args
    @staticmethod
    def get_default_client():
        return Client(server_config.host_default, server_config.port_default)


if __name__ == '__main__':
    if len(sys.argv) == 1:
        # test
        client = Client.get_default_client()
        client.run()
    else:
        client = Client.get_customized_client()
        client.run()
