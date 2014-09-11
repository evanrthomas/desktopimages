#!/usr/bin/python
import socket
import sys
import os
from subprocess import Popen

socket_address = ('localhost', 8888)
#TODO get freedback

def sendMessage(message):
    # Create a UDS socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect the socket to the port where the server is listening
    print 'connecting to %s, %s' % socket_address
    try:
        sock.connect(socket_address)
    except socket.error, msg:
        print msg
        sys.exit(1)

    try:
        # Send data
        print 'sending "%s"' % message
        sock.sendall(message)
        s = sock.recv(1024)
        while s != "":
            print s
            s = sock.recv(1024)
    finally:
        sock.close()

def handle(command):
    #TODO: check if client already started
    #TODO: figure out why you have to press enter every time for new line
    if command == "start":
        from daemon import asynch_start
        asynch_start()
    else:
        sendMessage(command)
def main():
    handle(sys.argv[1])

if __name__ == "__main__":
    main()
