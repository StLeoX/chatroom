# for server, not for client
def log_info(msg):
    print(msg)


def log_srv(msg):
    print(msg)
    with open('./log.txt', 'a') as f:
        f.write(msg + '\n')
