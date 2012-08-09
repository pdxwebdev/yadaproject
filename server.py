import json, time, unittest, os, sys
from uuid import uuid4
from yadapy.db.mongodb.node import Node
from yadapy.db.mongodb.manager import YadaServer
from yadapy.nodecommunicator import NodeCommunicator
from yadapy.lib.crypt import decrypt
from twisted.web import server, resource
from twisted.internet import reactor, task
from mongoapi import MongoApi


class TestResource(resource.Resource):
    isLeaf = True
    numberRequests = 0
    def __init__(self, nodeComm, mongoapi):
        self.nodeComm = nodeComm
        self.mongoapi = mongoapi
    
    def render_GET(self, request):
        splitPath = request.path.split('/')
        method = False
        if len(splitPath) > 2:
            method = splitPath[2]
            if method == 'search':
                response = self.search(splitPath[3], splitPath[4])
                return json.dumps(response)
        if request.args.get('nolink', '0') == ['1']:
            return json.dumps(self.nodeComm.node.get())
        elif request.args.get('hostandport', None) != None:
            self.nodeComm.requestFriend(request.args.get('hostandport', '0')[0])
        else:
            returnLinks = ''
            for hostElement in self.nodeComm.node.get('data/identity/ip_address'):
                returnLinks += '<a style="text-decoration:none;" href="http://jsonviewer.stack.hu/#http://' + hostElement['address'] + ':' +  hostElement['port']  + '?nolink=1">' + json.dumps(self.nodeComm.node.get()) + "</a>"
            returnLinks += '<form action="" method="GET"><input type="text" name="hostandport" /><input type="submit" value="send request" /></form>'
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
    
    def search(self, term=None, public_key=None):
        results = []
        excludeKeys = []
        results = self.performSearch(term)
        if public_key:
            for index, result in enumerate(results):
                results[index]['source_indexer_key'] = public_key
        return results
    
    def performSearch(self, term, excludeKeys=[]):
        results = [];
        for x in self.nodeComm.node.get('data/friends'):
            if 'name' in x['data']['identity']:
                if x['data']['identity']['name'].lower() in term.lower() or term.lower() in x['data']['identity']['name'].lower():
                    if x['data']['identity']['name'].lower()!="":
                        results.append(x)
            for z in x['data']['friends']:
                if 'data' in z:
                    if 'identity' in z['data']:
                        if 'name' in z['data']['identity']:
                            if z['data']['identity']['name'].lower() in term.lower() or term.lower() in z['data']['identity']['name'].lower():
                                if z['data']['identity']['name'].lower()!="":
                                    results.append(z)
        return results
    def syncAllFriends(self):
        for x in self.nodeComm.node.get('data/friends'):
            self.nodeComm.updateRelationship(Node(x))

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
    tr = TestResource(nodeComm1, MongoApi(nodeComm1))
    l = task.LoopingCall(tr.syncAllFriends)
    l.start(60)
    reactor.listenTCP(int(port), server.Site(tr))
    reactor.run()