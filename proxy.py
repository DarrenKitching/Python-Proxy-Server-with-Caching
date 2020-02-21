import socket
import signal
import threading
import ssl
import pickle # file format for saving cache dict
import atexit # used to save cache before program exit
import time

BUFFER_LENGTH = 1048576 # buffer size = 2^20
cacheDict = {}

def saveDict():
  with open('cache' + '.pkl', 'wb') as f:
    pickle.dump(cacheDict, f, pickle.HIGHEST_PROTOCOL)

def readDict():
    with open('cache' + '.pkl', 'rb') as f:
        cacheDict = pickle.load(f)

def exit_handler():
  saveDict()
  print("Cache saved")

def readBlocked():
  listBlocked = open("blocked.txt").read()
  print(listBlocked)

def writeToBlocked(block):
  f = open("blocked.txt", "a")
  f.write(block + "\n")
  f.close

def removeBlocked(blocked):
  lines = open("blocked.txt").read().splitlines()
  f = open("blocked.txt", "w")
  for line in lines:
    if (str(line) != (blocked)):
      f.write(str(line + "\n"))
  f.close

def isBlocked(blocked):
  lines = open("blocked.txt").read().splitlines()
  for line in lines:
    if (str(line) in (blocked)):
      return True
  return False

def inputLoop():
  while True:
    choice = int(input("Type 1 to start proxy server, 2 to block a url, 3 to unblock a url, 4 to list all blocked urls, 5 to clear cache: "))
    if choice == 1:
      port = int(input("Choose a port: "))
      server = Server(port)
    elif choice == 2:
      blockUrl = str(input("Type url to block: "))
      writeToBlocked(blockUrl)
      print("Url blocked")
    elif choice == 3:
      unblockUrl = str(input("Type url to unblock: "))
      removeBlocked(unblockUrl)
      print("Url unblocked")
    elif choice == 4:
      readBlocked()
    elif choice == 5:
    	cacheDict = {}
    	saveDict()
    else:
    	print("Command not recognised")

def main():
  atexit.register(exit_handler) # set up cache save at exit
  readDict() # read cache from cache.pkl
  inputLoop() # begin IO


class Server:
  def __init__(self, port): 
    self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # socket creation
    self.serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    self.serverSocket.bind(('', port)) # bind localhost and port provided with our new socket
    self.serverSocket.listen(10) # queue up as many as 10 connect requests before refusing more
    while True:
      (proxySocket, proxy_address) = self.serverSocket.accept()
      threadListener = threading.Thread(target = self.requestReceived, args=(proxySocket, proxy_address)) # ready to create a new thread for any request made and run requestReceived
      threadListener.setDaemon(True)
      threadListener.start()

  def getPort(self, request, url):
    http_pos = url.find("://")
    if (http_pos==-1):
        temp = url
    else:
        temp = url[(http_pos+3):]
    port_pos = temp.find(":")
    webserver_pos = temp.find("/")
    if webserver_pos == -1:
        webserver_pos = len(temp)
    webserver = ""
    port = -1
    if (port_pos==-1 or webserver_pos < port_pos): 

        port = 80 
        webserver = temp[:webserver_pos] 
    else:
        port = int((temp[(port_pos+1):])[:webserver_pos-port_pos-1])
        webserver = temp[:port_pos]
    return port

  def getUrl(self, request):
    first_line = str(request).split('\n')[0]
    url = first_line.split(' ')[1]
    return url

  def getWebserver(self, request, url):
    http_pos = url.find("://")
    if (http_pos==-1):
        temp = url
    else:
        temp = url[(http_pos+3):]
    port_pos = temp.find(":")
    webserver_pos = temp.find("/")
    if webserver_pos == -1:
        webserver_pos = len(temp)
    webserver = ""
    port = -1
    if (port_pos==-1 or webserver_pos < port_pos): 

        port = 80 
        webserver = temp[:webserver_pos] 
    else:
        port = int((temp[(port_pos+1):])[:webserver_pos-port_pos-1])
        webserver = temp[:port_pos]
    return webserver



  def requestReceived(self, proxySocket, proxy_address):
    print()
    try:
      request = proxySocket.recv(BUFFER_LENGTH)
      if (str(request).split('\n')[0] == "b''"):
      	print("Empty request")
      	proxySocket.close()
      	return
      url = self.getUrl(request) # find url
      webserver = self.getWebserver(request, url) # find webserver
      port = self.getPort(request, url) # find port
      print("Request for website: " + url + " at Port: " + str(port))
      if (isBlocked(url)):
        print("Url is blocked")
        proxySocket.close() # if website is on the blocked list then close socket
      elif (request in cacheDict):
        print("Cache hit, fetching from cache")
        start = time.time()
        data = cacheDict[request]
        while 1:
          if (len(data) > 0):
              proxySocket.send(data) # send data to browser
          else:
              break
          break
        end = time.time()
        timeElapsed = (end - start) * 1000
        print("Request for " + webserver + " handled from cache in " + str(timeElapsed) + "ms") 
        proxySocket.close()
      else:
        start = time.time()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        s.connect((webserver, port))
        s.send(request) # send request to server
        while 1:
          data = s.recv(BUFFER_LENGTH) # receive data from server
          #saveDict()
          cacheDict[request] = data
          #print(data)
          if (len(data) > 0):
              proxySocket.send(data) # send data to browser
          else:
              break
          break
        end = time.time()
        timeElapsed = (end - start) * 1000
        print("Request completed in " + str(timeElapsed) + "ms")
        s.close()
        proxySocket.close()
    except OSError:
      #print("Socket Error")
      pass
    except IOError:
      #print("Pipe Error")
      pass

if __name__== "__main__":
  main()
