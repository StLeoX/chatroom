# 一、应用层通信设计

## 1、数据交换形式

client->server: json.dumps(msg:dict).encode(); server->client: (msg:str).encode();   
json序列充当负载 ：json作为通信载体，存放在 json就可以视为dict序列化的结果。

## 2、命令动词列举（详细含义看pdf文档）

method arg_list

- login = Command('login', 'login <username> <password>', 2)
- logout = Command('logout', 'logout', 0)
- message = Command('message', 'message <username> <message>', 2)
- broadcast = Command('broadcast', 'broadcast <message>', 1)
- whoami = Command('whoami', 'whoami', 0)
- whoelse = Command('whoelse', 'whoelse', 0)
- whoelsesince = Command('whoelsesince', 'whoelsesince <time>', 1)
- block = Command('block', 'block <user>', 1)
- unblock = Command('unblock', 'unblock <user>', 1)
- help = Command('help', 'help', 0)
- debug = Command('debug', 'debug {server|client}', 1)

## 3、记录会话

1. uuid生成会话id
2. 在client存在结构： self.session = types.SimpleNamespace(connid=self.uuid, messages=list(), # msg buffer,fifo msg_total=0,
   recv_total=0, outb=b'')
3. 在server存在结构： session = types.SimpleNamespace(connid=uuid_, addr=addr, inb=b'', outb=b'')  # separate session
4. 但是注意到client的session可以通过self.session存取，是全局的。 但是server的session通过selecter进行切换并存取（也就是所谓的context），是局部的。

# 二、并发模型设计

## 1、多线程实现客户端数据异步控制

起因：鉴于select不能注册sys.stdin。  
解决：client需要开启多个线程。 一个线程用来跑REPL用来处理用户交互，另一个线程用来跑run用来收发消息。

## 2、并发控制的启发

1. 在windows上缺少原生的select的实现。
   windows下处理c10k问题虽然有IOCP服务的支持，但是可以确定的是python的selectors库在windows平台上并没有调用IOCP服务（通过管理工具可以查看），应该是重写的轮询逻辑。
   所以在windows上运行该server脚本，对CPU的占用是很高的。这也就是为什么没什么人用win做服务主机。

2. 但是unix上存在原生的select调用的实现。 推断python的selector库也应该是调用的这个so（未测试）。

3. 但总的来说，轮询的消耗还是很高的，适用于高频的短连接。  
   针对低频的长连接，还是linux的epoll调用比较有优势，或者是自己实现一个event-loop库。 实际上，python有实现平台无关的event-loop库，在asyncio里面，下一阶段的目标就是使用asyncio
   lib重写软件。

4. 终端也是资源，需要引入并发控制来避免输入输出乱序。 我的代码是在REPL使用bool变量来实现mutex锁，效果还行。 但是远远比不上异步的控件的效果。   
   所以引用控件库来处理异步的数据是很有必要的，最基本的就是需要一个控件充当editing-buffer。

# 三、程序改进方向

1. 方向一：使用asyncore的dispatcher和ioloop重写IO复用的部分。
2. 方向二：使用asyncio的更高级的封装重写async handler的部分，希望引入session实体作为会话封装，并实现session的切换。
3. 方向三：使用go的channel和select重写server的IO复用部分，并保留python版本的client体验一下跨语言调用。

