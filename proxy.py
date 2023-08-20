from socket import *
from threading import *
from datetime import *
import json
import time
import os

HOST = 'localhost'
PORT = 8000

def ClearCache(caches):
    while True:
        # Check per 30 seconds
        time.sleep(30)
        now = datetime.now()
        for file in caches:
            if now > file['time']:
                os.remove('cache/' + file['name'])
                caches.remove(file)
                
def Validate(req, config):
    # Empty req
    if not req:
        return 'Empty request'
    # Method
    method = req.decode().split()[0]
    if method not in config['method']:
        return 'Invalid method'
    # Whitelist
    hostn = req.decode().split()[4]
    if hostn not in config['whitelist']:
        return 'You are not allowed to access this page'
    # Time
    now = str(datetime.now().time())
    if now < config['time']['start'] or now > config['time']['end']:
        return 'It is time for bed'
    # Accept
    return 'Accept'

def Connect(tcpCliSock, caches):
    # Get request from browser
    req = tcpCliSock.recv(4096)

    # If using localhost
    if HOST + ':' + str(PORT) in req.decode():
        # Change localhost request to normal request
        req = req.decode()
        if 'Referer: ' not in req:
            # First request
            hostn = req.split()[1].split('/')[1].replace('www.', '')
            req = req.replace(HOST + ':' + str(PORT), hostn)
            # Change request file
            req = req.replace('/', 'http://', 1)
        else:
            # Following request
            referer = req.split('Referer: ')[1].split('\r\n')[0]
            hostn = referer.split(HOST + ':' + str(PORT) + '/')[1].split('/')[0]
            req = req.replace(HOST + ':' + str(PORT), hostn)
        req = req.encode()

    # Validate
    validateMsg = Validate(req, config)
    if validateMsg == 'Accept':
        # If accepted
        # Get requested file name
        fileName = req.decode().split()[1]
        print('Sending request for', fileName)
        fileInCache = fileName.replace('http://', '').replace('/', '_').replace('?', '_')
        try:
            # Find req file in cache
            f = open('cache/' + fileInCache, 'rb')
            print('Found', fileName, 'in cache')
            # Read data
            cacheContent = f.read()
            # Send data to browser
            res = b'HTTP/1.1 200 OK\r\nContent-Type: image\r\n\r\n' + cacheContent
            tcpCliSock.send(res)
        except IOError: # When file not found in cache
            # Get web server address
            hostn = req.decode().split()[4]
            # Create connection to web server
            webCliSock = socket(AF_INET, SOCK_STREAM)
            webCliSock.connect((hostn, 80))
            # Send request
            webCliSock.send(req)
            # Receive first data
            res = webCliSock.recv(4096)
            print('Received response for', fileName)
            # Check response type
            if b'Content-Length: ' in res:
                # Content length
                length = int(res.split(b'Content-Length: ')[1].split(b'\r\n')[0])
                splitPos = res.find(b'\r\n\r\n')

                if splitPos != -1:
                    # Split header and body
                    header = res[:splitPos + 4]
                    body = res[splitPos + 4:]

                    # Receive remaining response body data
                    while len(body) < length:
                        remaining_data = webCliSock.recv(4096)
                        body += remaining_data

                    # Send the remaining response body to the browser
                res = header + body
            elif b'Transfer-Encoding: chunked' in res:
                # Transfer-Encoding: chunked
                # Add Transfer-Encoding: chunked to response headers
                res = res.replace(b'Content-Length', b'Transfer-Encoding: chunked\r\nContent-Length')
                # Process chunk
                while True:
                    chunk_header = webCliSock.recv(4096)
                    if not chunk_header:
                        break
                    try:
                        chunk_size = int(chunk_header, 16)
                    except ValueError:
                        print("Chunk size:", chunk_header)
                        break
                            
                    if chunk_size == 0:
                        break
                    chunk = webCliSock.recv(chunk_size)
                    # Add the chunk to the res
                    res += chunk_header + chunk

                # Add the final chunk
                res += b'0\r\n\r\n'

            # Check type of file
            fileType = fileName.split('.')[-1]
            if fileType in config['cache']['types']:
                # Create cache file
                cache = open('cache/' + fileInCache, 'wb')
                # Add to cache list
                caches.append({
                    'name': fileInCache,
                    'time': datetime.now() + timedelta(minutes = int(config['cache']['time']))
                })
                # Write to cache file
                body = res.split(b'\r\n\r\n', 1)[1]
                cache.write(body)
                cache.close()

            # Send response to browser
            tcpCliSock.sendall(res)
            print('Sent response for', fileName)
            # Close connect to web sever
            webCliSock.close()
    else:
        # 403 FORBIDDEN
        # Read 403 html
        f = open('assets/403.html')
        forbiddenHTML = f.read()
        forbiddenHTML = forbiddenHTML.replace('MESSAGE_PLACEHOLDER', validateMsg)
        # Send 403 to browser
        forbiddenRes = b'HTTP/1.1 403 Forbidden\r\nContent-Type: text/html\r\n\r\n' + forbiddenHTML.encode()
        tcpCliSock.send(forbiddenRes)

    # Close connect from browser
    tcpCliSock.close()


# MAIN

# Get config from config file
configFile = open('config.json')
config = json.load(configFile)

# Reset cache folder
try :
    for file in os.listdir('cache'):
        os.remove('cache/' + file)
except:
    os.mkdir('cache')
# Cache files handle
caches = []
cacheThread = Thread(target = ClearCache, args = [caches])
cacheThread.start()

# Create sever
tcpSerSock = socket(AF_INET, SOCK_STREAM)
tcpSerSock.bind((HOST, PORT))
tcpSerSock.listen(10)
print('Proxy is listening...')

while True:
    # Accept connect form browser
    tcpCliSock, addr = tcpSerSock.accept()
    # Create new thread and run
    thread = Thread(target = Connect, args = [tcpCliSock, caches])
    thread.start()