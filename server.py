import json, time, unittest, os, sys
from uuid import uuid4
from pymongo import Connection
from yadapy.db.mongodb.node import Node
from yadapy.db.mongodb.manager import YadaServer
from yadapy.nodecommunicator import NodeCommunicator
from yadapy.lib.crypt import decrypt
from twisted.web import server, resource
from twisted.web.util import redirectTo
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
            return redirectTo('/?friendRequestSuccess=1', request)
        else:
            returnLinks = '<pre>'
            for hostElement in self.nodeComm.node.get('data/identity/ip_address'):
                returnLinks += '<iframe height="800" width="800" style="text-decoration:none;" src="http://jsonviewer.stack.hu/#http://' + hostElement['address'] + ':' +  hostElement['port']  + '?nolink=1"></iframe>'
            returnLinks += '</pre>Send Friend Request to another manager: <form action="" method="GET"><input type="text" name="hostandport" />(ie. 192.168.1.100:42000 or manager.website.com:42000<br><input type="submit" value="send request" /></form>'
            return str(returnLinks)

    def render_POST(self, request):
        print "initialize server"
        response = ""
        for i, x in request.args.items():
            try:
                print "getting the params"
                inbound = json.loads(x[0])
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
            if friend:
                data = decrypt(friend['private_key'], friend['private_key'], inbound['data'])
                data = json.loads(data)
                response = getattr(self.mongoapi, method)(friend, data)
            else:
                response = ""
        request.setHeader("content-type", "text/plain")
        return json.dumps(response)
    
    def search(self, term=None, public_key=None):
        results = []
        excludeKeys = []
        results = self.performSearch(term, source_indexer_key=public_key)
        return results
    
    def performSearch(self, term, excludeKeys=[], source_indexer_key=""):
        results = []
        keys = []
        for x in self.nodeComm.node.get('data/friends'):
            if 'name' in x['data']['identity']:
                if x['data']['identity']['name'].lower() in term.lower() or term.lower() in x['data']['identity']['name'].lower():
                    if x['data']['identity']['name'].lower()!="":
                        if x['public_key'] not in keys:
                            keys.append(x['public_key'])
                            x['source_indexer_key'] = source_indexer_key
                            results.append(x)
            for z in x['data']['friends']:
                if 'data' in z:
                    if 'identity' in z['data']:
                        if 'name' in z['data']['identity']:
                            if z['data']['identity']['name'].lower() in term.lower() or term.lower() in z['data']['identity']['name'].lower():
                                if z['data']['identity']['name'].lower()!="":
                                    if z['public_key'] not in keys:
                                        keys.append(z['public_key'])
                                        results.append(z)
        return results
    def syncAllFriends(self):
        for x in self.nodeComm.node.get('data/friends'):
            try:
                self.nodeComm.updateRelationship(Node(x))
            except:
                pass
            print time.time()
        reactor.callLater(60, self.syncAllFriends)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        exit()
    argSplit = sys.argv[1].split(':')
    if len(argSplit) < 2:
        exit()
    host = argSplit[0]
    port = argSplit[1]
    connection = Connection('localhost',27021)
    db = connection.yadaserver
    manager = db.command(
        {
            "aggregate" : "identities", "pipeline" : [
                {
                    "$match" : {
                        "data.identity.ip_address.address" : host,
                        "data.identity.ip_address.port" : port,
                        "data.type" : "manager"
                    }
                },
            ]
        })['result']
    
    if len(manager):
        manager[0]['_id'] = str(manager[0]['_id'])
        node1 = manager[0]
        node1 = YadaServer(node1)
    else:
        node1 = YadaServer({}, {"name" : "node"})
        node1.addIPAddress(host, port)
        node1.save()
        
    node1.save()
    nodeComm1 = NodeCommunicator(node1)
    tr = TestResource(nodeComm1, MongoApi(nodeComm1))
    reactor.callInThread(tr.syncAllFriends)
    reactor.listenTCP(int(port), server.Site(tr))
    reactor.run()