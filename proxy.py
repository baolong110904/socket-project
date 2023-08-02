from socket import *
from threading import *

def Threaded(conn):
        req = conn.recv(2 ** 20)

        if (req.decode().find('HTTP/1.1') == -1):
            return
        if (req.decode().find('GET') == -1):
            return

        httpAddr = req.decode().split()[4]

        print('Request:')
        print(req.decode())

        reqSock = socket(AF_INET, SOCK_STREAM)
        reqSock.connect((httpAddr, 80))
        reqSock.send(req)

        while True:
            res = reqSock.recv(2 ** 20)
            if (res == b''):
                break
            print('Response:')
            print(res.decode())

            conn.send(res)


# Proxy
proxy = socket(AF_INET, SOCK_STREAM)
proxy.bind(('localhost', 8000))

proxy.listen()
print('Proxy is listening...')

Threads = []
idx = 0
while True:
    conn, addr = proxy.accept()

    Threaded(conn)
    # Threads.append(Thread(target = Threaded, args = [conn]))
    # Threads[-1].start()