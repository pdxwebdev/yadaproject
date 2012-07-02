import json, time, unittest, os, sys
from uuid import uuid4
from yadapy.sqlite.nodesqlite import Node
from yadapy.sqlite.yadasqliteserver import YadaServer
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
            
        print "calling handlePacket"
        response = self.nodeComm.handlePacket(inbound)
            
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
            node1 = YadaServer({}, {"name" : "node 1"}, location=sys.argv[2])
        else:
            node1 = Node({}, {"name" : "node 1"}, location=sys.argv[2])
    except:
        node1 = Node({}, {"name" : "node 1"}, location=sys.argv[2])
    node1.addIPAddress(host, port)
    node1.save()
    nodeComm1 = NodeCommunicator(node1)
    reactor.listenTCP(int(port), server.Site(TestResource(nodeComm1)))
    reactor.run()