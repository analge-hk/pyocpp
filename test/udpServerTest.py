import socket
import time
 
HOST = ''
PORT = 8080
ADDR = (HOST, PORT)
 
bufferSize = 1024
 
udpSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
udpSock.bind(ADDR)
 
while True:
    print("waiting for message...")
    data, addr = udpSock.recvfrom(bufferSize)
    if not data:
        break
    # data = str.upper(data)
    print(str)
    udpSock.sendto(data, addr)
    
udpSock.close()