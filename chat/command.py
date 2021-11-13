class Command(object):
    def __init__(self, cmd, usage, op_count):
        """

        :param cmd: name of command
        :param usage: usage of command
        :param op_count: count of args
        """
        self.cmd = cmd
        self.usage = usage
        self.op_count = op_count

    def is_args_valid(self, argv_len):
        return self.op_count + 1 == argv_len


class CmdEnum(object):  # Enum of cmd
    login = Command('login', 'login <username> <password>', 2)
    logout = Command('logout', 'logout', 0)
    message = Command('message', 'message <username> <message>', 2)
    broadcast = Command('broadcast', 'broadcast <message>', 1)
    whoami = Command('whoami', 'whoami', 0)
    whoelse = Command('whoelse', 'whoelse', 0)
    whoelsesince = Command('whoelsesince', 'whoelsesince <time>', 1)
    block = Command('block', 'block <user>', 1)
    unblock = Command('unblock', 'unblock <user>', 1)
    help = Command('help', 'help', 0)
    # debug = Command('debug', 'debug {server|client}', 1)


def get_help():
    print('===HELP===')
    for m in CmdEnum.__dict__:
        if m[0] != '_':
            print(getattr(getattr(CmdEnum, m), 'usage'))


def check_cmd(cmd: str, argv_len: int):
    all_cmds = [m for m in CmdEnum.__dict__ if m[0] != '_']
    if cmd not in all_cmds:
        return 'command name error.\ntype \"help\" for help.'
    if not getattr(CmdEnum, cmd).is_args_valid(argv_len):
        return 'command agreements error.\ntype \"help\" for help.'
    return None


if __name__ == '__main__':
    pass
