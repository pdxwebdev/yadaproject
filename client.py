import logging, os, json, time, copy, time, datetime, re, urllib, httplib, sys
from base64 import b64encode, b64decode
from uuid import uuid4
from yadapy.lib.crypt import encrypt, decrypt
from yadapy.sqlite.nodesqlite import *
from yadapy.manager import YadaServer
from yadapy.nodecommunicator import NodeCommunicator


def getTerminalSize():
    import os
    env = os.environ
    def ioctl_GWINSZ(fd):
        try:
            import fcntl, termios, struct, os
            cr = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ,
        '1234'))
        except:
            return None
        return cr
    cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_GWINSZ(fd)
            os.close(fd)
        except:
            pass
    if not cr:
        try:
            cr = (env['LINES'], env['COLUMNS'])
        except:
            cr = (25, 80)
    return int(cr[1]), int(cr[0])


node = False
nodeClient = False

logo = """

    %s
    
    yyyyyyy   yyyyyy  aaaaaa      ddddddddddddd            aaaaaa
    yyyyyy    yyyyy  aaaaaaa      dddddddddddddddd        aaaaaaa
     yyyy    yyyyy  aaaaaaaaa     dddddd        dddd     aaaaaaaaa
      yyy   yyyyy  aaaaa  aaaa    dddddd        ddddd   aaaaa  aaaa
      yyyy yyyy   aaaaa    aaaa   dddddd        ddddd  aaaaa    aaaa
       yyyyyy    aaaaaaaaaaaaaaa  dddddd       ddddd  aaaaaaaaaaaaaaa
        yyyy    aaaaaaaaaaaaaaaa  dddddd    ddddddd  aaaaaaaaaaaaaaaa
        yyyy   aaaaaaa     aaaaa  ddddddddddddddd   aaaaaaa     aaaaa
        yyyy   aaaaaaa    aaaaaaa ddddddddddddd     aaaaaaa    aaaaaaa
        
     ______   ______     ______       __     ______     ______     ______  
    /\  == \ /\  == \   /\  __ \     /\ \   /\  ___\   /\  ___\   /\__  _\ 
    \ \  _-/ \ \  __<   \ \ \/\ \   _\_\ \  \ \  __\   \ \ \____  \/_/\ \/ 
     \ \_\    \ \_\ \_\  \ \_____\ /\_____\  \ \_____\  \ \_____\    \ \_\ 
      \/_/     \/_/ /_/   \/_____/ \/_____/   \/_____/   \/_____/     \/_/
        
    %s

""" % (("\n" * (getTerminalSize()[1])), ("\n" * (getTerminalSize()[1])))

def frame(text):
    textLen = len(text)
    frameTopBottom = "*" * (textLen + 14)
    frameStr = """
    %s
    *      %s      *
    %s
    """ % (frameTopBottom, text, frameTopBottom)
    return frameStr

if __name__ == '__main__':
    clear = lambda: os.system('cls')
    #screen 1
    raw_input("""
    %s
    %s
    [Press Enter]""" % (logo, frame("Welcome to your new Social Network!")))
    clear()
    
    #screen 2
    while 1:
        var = raw_input("""
        %s
        %s
        Enter the host name and port ie.localhost:80: """ % (logo, frame("Lets check that your server is up.")))
        try:
            varSplit = var.split(":")
            host = varSplit[0]
            port = varSplit[1]
        except:
            raw_input("ERROR: You did not enter a valid host name and port number. Format: localhost:80 [Press Enter]")
            clear()
            continue
        try:
            headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "text/plain"}
            conn = httplib.HTTPConnection(host, port)
            conn.request("POST", "", "", headers)
            
            response = conn.getresponse()
            response = response.read()
            conn.close()
            break
        except:
            raw_input("ERROR: Host is inaccessible [Press Enter]")
            clear()
            continue
        
    #screen 3
    while 1:
        var = raw_input("""
        %s
        %s
        Type the absolute path to your sqlite database file: """ % (logo, frame("Good, your server responded.")))
        try:
            node = Node({}, {"name" : "NodeServer"}, location=var)
            nodeClient = NodeCommunicator(node)
        except:
            raw_input("ERROR: This is not a valid path to an sqlite database file [Press Enter]")
            clear()
            continue
        
        