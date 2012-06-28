import json, time, unittest, os
from uuid import uuid4
from yadapy.node import Node
from yadapy.manager import YadaServer
from yadapy.nodecommunicator import NodeCommunicator
from twisted.web import server, resource
from twisted.internet import reactor


class TestResource(resource.Resource):
    isLeaf = True
    numberRequests = 0
    def __init__(self, nodeComm):
        self.nodeComm = nodeComm
    
    def render_GET(self, request):
        request.setHeader("content-type", "text/plain")
        return "{}"

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
            
        print "calling consumePacket"
        response = self.nodeComm.handlePacket(inbound)
            
        print "response : %s" % response
        request.setHeader("content-type", "text/plain")
        return json.dumps(response)
    
node1 = Node({}, {"name" : "node 1"})
nodeComm1 = NodeCommunicator(node1)
reactor.listenTCP(int(8089), server.Site(TestResource(nodeComm1)))
reactor.callLater(2, nodeComm1.requestFriend, "localhost:8090")
reactor.run()