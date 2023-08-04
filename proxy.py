from socket import *
from threading import *
from datetime import *
import json

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

def Connect(tcpCliSock):
# Get request from browser
    req = tcpCliSock.recv(2 ** 20)
    # Validate
    message = ['']
    if Validate(req, config, message):
        # If accepted
        print('Request:')
        print(req.decode(errors = 'ignore'))
        # Get requested file name
        fileName = req.decode().split()[1]
        try:
            # Find req file in cache
            f = open(fileName)
        except IOError: # When file not found in cache
            # Get web server address
            hostn = req.decode().split()[4]
            print('HOST', hostn)
            # Create connection to web server
            webCliSock = socket(AF_INET, SOCK_STREAM)
            webCliSock.connect((hostn, 80))
            # Send request
            webCliSock.send(req)
            # Receive response and send back to browser
            print('Response:')
            while True:
                res = webCliSock.recv(2 ** 20)
                if not res:
                    break
                print(res.decode(errors = 'ignore'))
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

# Create sever
tcpSerSock = socket(AF_INET, SOCK_STREAM)
tcpSerSock.bind(('', 8000))
tcpSerSock.listen()
print('Proxy is listening...')

while True:
    # Accept connect form browser
    tcpCliSock, addr = tcpSerSock.accept()
    print('Received a connection from:', addr)
    # Create new thread and run
    thread = Thread(target = Connect, args = [tcpCliSock])
    thread.start()
