from socket import *
from threading import Thread

def Threaded(conn):
    try:
        req = b""
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break
            req += chunk
            if b'\r\n\r\n' in req:
                break

        if not req:
            return

        req_str = req.decode()

        if 'HTTP/1.1' not in req_str or 'GET' not in req_str:
            return

        httpAddr = req_str.split()[4]

        print('Request:')
        print(req_str)

        reqSock = socket(AF_INET, SOCK_STREAM)
        reqSock.connect((httpAddr, 80))
        reqSock.send(req)

        while True:
            res = reqSock.recv(4096)
            if not res:
                break
            print('Response:')
            print(res.decode())

            if b'Transfer-Encoding: chunked' in res:
                res = decode_chunked(res)

            conn.send(res)

    except Exception as e:
        print('Error:', e)

    finally:
        conn.close()

def decode_chunked(data):
    decoded_data = b""
    while data:
        chunk_len, data = data.split(b'\r\n', 1)
        chunk_len = int(chunk_len, 16)
        
        if chunk_len == 0:
            break
        
        decoded_data += data[:chunk_len]
        data = data[chunk_len + 2:]
    
    return decoded_data

proxy = socket(AF_INET, SOCK_STREAM)
proxy.bind(('localhost', 8000))
proxy.listen()
print('Proxy is listening...')

Threads = []
while True:
    conn, addr = proxy.accept()

    thread = Thread(target=Threaded, args=[conn])
    thread.start()
    Threads.append(thread)
