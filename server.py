import json, time, unittest, os, sys
from uuid import uuid4
from yadapy.db.mongodb.node import Node
from yadapy.db.mongodb.manager import YadaServer
from yadapy.nodecommunicator import NodeCommunicator
from yadapy.lib.crypt import decrypt
from twisted.web import server, resource
from twisted.internet import reactor
from mongoapi import MongoApi


class TestResource(resource.Resource):
    isLeaf = True
    numberRequests = 0
    def __init__(self, nodeComm, mongoapi):
        self.nodeComm = nodeComm
        self.mongoapi = mongoapi
    
    def render_GET(self, request):
        if request.args.get('nolink', '0') == ['1']:
            return json.dumps(self.nodeComm.node.get())
        else:
            returnLinks = ''
            for hostElement in self.nodeComm.node.get('data/identity/ip_address'):
                returnLinks += '<a style="text-decoration:none;" href="http://jsonviewer.stack.hu/#http://' + hostElement['address'] + ':' +  hostElement['port']  + '?nolink=1">' + json.dumps(self.nodeComm.node.get()) + "</a>"
            return returnLinks

    def render_POST(self, request):
        print "initialize server"
        response = ""
        for i, x in request.args.items():
            try:
                print "getting the params"
                inbound = json.loads(x[0])
                print "inbound : %s" % x[0]
                break
            except:
                raise
        if request.path == '/':
            print "calling handlePacket"
            response = self.nodeComm.handlePacket(inbound)
        else:
            splitPath = request.path.split('/')
            method = splitPath[2]
            friend = self.mongoapi.getProfileFromInbound(inbound)
            data = decrypt(friend['private_key'], friend['private_key'], inbound['data'])
            data = json.loads(data)
            response = getattr(self.mongoapi, method)(friend, data)
        print "response : %s" % response
        request.setHeader("content-type", "text/plain")
        return json.dumps(response)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        exit()
    argSplit = sys.argv[1].split(':')
    if len(argSplit) < 2:
        exit()
    host = argSplit[0]
    port = argSplit[1]
    try:
        if sys.argv[3] == 'manager':
            node1 = YadaServer({}, {"name" : "node 2"})
        else:
            node1 = Node({}, {"name" : "node 2"})
    except:
        node1 = Node({}, {"name" : "node 2"})
    node1.addIPAddress(host, port)
    node1.save()
    nodeComm1 = NodeCommunicator(node1)
    reactor.listenTCP(int(port), server.Site(TestResource(nodeComm1, MongoApi())))
    reactor.run()