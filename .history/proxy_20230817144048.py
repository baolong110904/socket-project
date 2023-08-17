from socket import *
from threading import *
from datetime import *
import json
import time
import os

def ClearCache(caches):
    while True:
        # Check per 30 seconds
        time.sleep(30)
        now = datetime.now()
        for file in caches:
            if now > file['time']:
                os.remove('cache/' + file['name'])
                
def Validate(req, config, message):
    # Empty req
    if not req:
        return False
    # Method
    method = req.decode().split()[0]
    if method not in config['method']:
        message[0] = 'Invalid method'
        return False
    # Whitelist
    hostn = req.decode().split()[4].replace('www.', '')
    if hostn not in config['whitelist']:
        message[0] = 'You are not allowed to access this page'
        return False
    # Time
    now = str(datetime.now().time())
    if now < config['time']['start'] or now > config['time']['end']:
        message[0] = 'It is time for bed'
        return False
    # Accept
    return True

def Connect(tcpCliSock, caches):
    # Get request from browser
    req = tcpCliSock.recv(2 ** 20)
    print(req)
    # Validate
    message = ['']
    if Validate(req, config, message):
        # If accepted
        print('Sending request for', req.decode().split()[1])
        # Get requested file name
        fileName = req.decode().split()[1]
        fileInCache = fileName.replace('http://', '').replace('/', '_')
        try:
            # Find req file in cache
            f = open('cache/' + fileInCache, 'rb')
            print('Found', fileName, 'in cache')
            # Read data
            res = f.read()
            # Send data to browser
            tcpCliSock.send(res)
        except IOError: # When file not found in cache
            # Get web server address
            hostn = req.decode().split()[4]
            # Create connection to web server
            webCliSock = socket(AF_INET, SOCK_STREAM)
            webCliSock.connect((hostn, 80))
            # Send request
            webCliSock.send(req)
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
            # Receive response
            while True:
                res = webCliSock.recv(2 ** 20)
                print(res)
                if not res:
                    break
                print('Received response for', req.decode().split()[1])
                # Write to cache file
                if fileType in config['cache']['types']:
                    header, body = res.split(b'\r\n\r\n', 1)
                    cache.write(body)
                # Send response to browser
                tcpCliSock.send(res)

            # Close connect to web sever
            webCliSock.close()
    else:
        # 403 FORBIDDEN

        # Read 403 html
        f = open('assets/403.html')
        forbiddenHTML = f.read()
        forbiddenHTML = forbiddenHTML.replace('MESSAGE_PLACEHOLDER', message[0])
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
for file in os.listdir('cache'):
    os.remove('cache/' + file)
# Cache files handle
caches = []
cacheThread = Thread(target = ClearCache, args = [caches])
cacheThread.start()

# Create sever
tcpSerSock = socket(AF_INET, SOCK_STREAM)
tcpSerSock.bind(('', 8000))
tcpSerSock.listen()
print('Proxy is listening...')

while True:
    # Accept connect form browser
    tcpCliSock, addr = tcpSerSock.accept()
    # Create new thread and run
    thread = Thread(target = Connect, args = [tcpCliSock, caches])
    thread.start()