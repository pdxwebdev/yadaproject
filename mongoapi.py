import json
from uuid import uuid4
from yadapy.lib.crypt import decrypt, encrypt
from pymongo import Connection, code
from base64 import b64encode, b64decode
from yadapy.db.mongodb.node import Node
from yadapy.nodecommunicator import NodeCommunicator



class MongoApi:
    
    def loadInboundJson(self, request):
            jsonDict = {}
            try:
                jsonDict = json.loads(request.POST['data'])
                if type(jsonDict['data']) == type("") or type(jsonDict['data']) == type(u""):
                    jsonDict['data'] = jsonDict['data'].replace(' ', '+')
            except:
                logging.debug('loadInboundJson error in parsing json')
            return jsonDict
    
    def getProfileFromInbound(self, jsonDict):
        #first check that a user is trying to replicate
        try:
            connection = Connection('localhost',27021)
            db = connection.yadaserver
            collection = db.identities
            return collection.find({'public_key':jsonDict['public_key']},{"public_key":1,"private_key":1,"modified":1})[0]
        except:
            return None
        

    def Ping(self, data, decrypted):
        return '{"status":"ok"}' 
    
    
    def getCounts(self, data, decrypted):
        friend_requestCount=0
        messageCount=0
        try:
            latestMessageGUIDs = decrypted['latestMessageGUIDs']
            friendRequestPublicKeys = decrypted['friendRequestPublicKeys']
            connection = Connection('localhost',27021)
            db = connection.yadaserver
            friend = db.command(
                {
                    "aggregate" : "identities", "pipeline" : [
                        {
                            "$match" : {
                                "public_key" : data['public_key']
                            }
                        },
                        {
                            "$match" : {
                                "data.friends" : { "$not" : {"$size" : 0}}
                            }
                        },
                        {
                            "$project" : {
                                "friend" : "$data.friends",
                            }
                        },
                        {
                            "$unwind" : "$friend"
                         },
                        {
                            "$match" : {
                                "friend.data.routed_friend_requests" : { "$not" : {"$size" : 0}}
                            }
                        },
                        
                        {
                            "$unwind" : "$friend.data.routed_friend_requests"
                         },
                        {
                            "$project" : {
                                          "public_keym" :"$friend.public_key",
                                          "request_public_keym" : "$friend.data.routed_friend_requests.public_key",
                                          "routed_public_keym" : "$friend.data.routed_friend_requests.routed_public_key"
                                        }
                        },
                    ]
                })
            #this is a heck because aggregation framework wont support matching the public_key with routed_public_key
            for i, r in enumerate(friend['result']):
                if 'routed_public_keym' in r and r['routed_public_keym']==r['public_keym'] and not r['request_public_keym'] in friendRequestPublicKeys:
                    friend_requestCount+=1
            
            message = db.command(
                {
                    "aggregate" : "identities", "pipeline" : [
                        {
                            "$match" : {
                                "public_key" : data['public_key']
                            }
                        },
                        {
                            "$match" : {
                                "data.friends" : { "$not" : {"$size" : 0}}
                            }
                        },
                        {
                            "$project" : {
                                "friend" : "$data.friends",
                            }
                        },
                        {
                            "$unwind" : "$friend"
                         },
                        {
                            "$match" : {
                                "friend.data.messages" : { "$not" : {"$size" : 0}}
                            }
                        },
                        {
                            "$unwind" : "$friend.data.messages"
                        },
                        {
                            "$project" : {
                                          "public_keym" :"$friend.public_key",
                                          "guid" :"$friend.data.messages.guid",
                                          "message_public_keym" : "$friend.data.messages.public_key"
                                        }
                        },
                    ]
                })
            #this is a heck because aggregation framework wont support matching the public_key with routed_public_key
            for i, r in enumerate(message['result']):
                if 'message_public_keym' in r and 'public_keym' in r:
                    if r['public_keym'] in r['message_public_keym'] and not r['guid'] in latestMessageGUIDs:
                        messageCount+=1
                    
            return {"messages": messageCount, "friend_requests" : friend_requestCount, "requestType" : "getCounts"}
        except:
            raise
    
    
    
    
    def getFriends(self, data, decrypted):
        connection = Connection('localhost',27021)
        db = connection.yadaserver
        friend = db.command(
                {
                    "aggregate" : "identities", "pipeline" : [
                        {
                            "$match" : {
                                "public_key" : data['public_key']
                            }
                        },
                        {
                            "$match" : {
                                "data.friends" : { "$not" : {"$size" : 0}}
                            }
                        },
                        {
                            "$project" : {
                                "friend" : "$data.friends",
                            }
                        },
                        {
                            "$unwind" : "$friend"
                         },
                        {
                            "$project" : {
                                "public_key" : "$friend.public_key",
                                "name" : "$friend.data.identity.name",
                                "_id" : 0
                            }
                        }]
                    })
        return json.dumps({'friends' : friend['result'], 'requestType' : 'getFriends'})
    
    
    def getFriend(self, data, decrypted):
    
        connection = Connection('localhost',27021)
        db = connection.yadaserver
        friend = db.command(
                {
                    "aggregate" : "identities", "pipeline" : [
                        {
                            "$match" : {
                                "public_key" : data['public_key']
                            }
                        },
                        {
                            "$match" : {
                                "data.friends" : { "$not" : {"$size" : 0}}
                            }
                        },
                        {
                            "$project" : {
                                "friend" : "$data.friends",
                            }
                        },
                        {
                            "$unwind" : "$friend"
                         },
                        {
                            "$match" : {
                                "friend.public_key" : decrypted['public_key'],
                            }
                        }]
                    })
        if friend['result']:
            return friend['result'][0]['friend']
        else:
            return '{}'
    
    
    def getThreads(self, data, decrypted):
        connection = Connection('localhost',27021)
        db = connection.yadaserver
        posts = db.command(
                {
                    "aggregate" : "identities", "pipeline" : [
                        {
                            "$match" : {
                                "public_key" : data['public_key']
                            }
                        },
                        {
                            "$match" : {
                                "data.friends" : { "$not" : {"$size" : 0}}
                            }
                        },
                        {
                            "$project" : {
                                "friend" : "$data.friends",
                            }
                        },
                        {
                            "$unwind" : "$friend"
                         },
                        {
                            "$match" : {
                                "friend.data.messages" : { "$not" : {"$size" : 0}}
                            }
                        },
                        {
                            "$unwind" : "$friend.data.messages"
                         },
                         
                        {
                            "$match" : {
                                "friend.data.messages.thread_id" : {"$type" : 2}
                            }
                        },
                        {
                            "$project" : {
                                "public_key" : "$friend.public_key",
                                "message" : {
                                             "thread_id" : "$friend.data.messages.thread_id",
                                             "guid" : "$friend.data.messages.guid",
                                             "timestamp" : "$friend.data.messages.timestamp",
                                             "public_key" : "$friend.data.messages.public_key",
                                             "subject" : "$friend.data.messages.subject",
                                             "name" : "$friend.data.identity.name",
                                             },
                            }
                        },
                        {
                            "$group" : {
                            "_id" : "$message.thread_id",
                            "friend_public_key" : {"$first" : "$public_key"},
                             "guid" : {"$first" : "$message.guid"},
                             "timestamp" : {"$last" : "$message.timestamp"},
                             "public_key" : {"$first" : "$message.public_key"},
                            "subject" : {"$first" : "$message.subject"},
                            "name" : {"$first" : "$message.name"},
                            }
                        },]
                    })
        finalPosts = []
        for i, r in enumerate(posts['result']):
            if r['friend_public_key'] in r['public_key']:
                finalPosts.append(r)
        posts = db.command(
                {
                    "aggregate" : "identities", "pipeline" : [
                        {
                            "$match" : {
                                "public_key" : data['public_key']
                            }
                        },
                        {
                            "$match" : {
                                "data.messages" : { "$not" : {"$size" : 0}}
                            }
                        },
                        {
                            "$unwind" : "$data.messages"
                         },
                         
                        {
                            "$match" : {
                                "data.messages.thread_id" : {"$type" : 2}
                            }
                        },
                        {
                            "$project" : {
                                "public_key" : "$public_key",
                                "message" : {
                                             "thread_id" : "$data.messages.thread_id",
                                             "guid" : "$data.messages.guid",
                                             "timestamp" : "$data.messages.timestamp",
                                             "public_key" : "$data.messages.public_key",
                                             "subject" : "$data.messages.subject",
                                             "name" : "$data.identity.name",
                                             },
                            }
                        },
                        {
                            "$group" : {
                            "_id" : "$message.thread_id",
                            "friend_public_key" : {"$first" : "$public_key"},
                             "guid" : {"$first" : "$message.guid"},
                             "timestamp" : {"$last" : "$message.timestamp"},
                             "public_key" : {"$first" : "$message.public_key"},
                            "subject" : {"$first" : "$message.subject"},
                            "name" : {"$first" : "$message.name"},
                            }
                        },]
                    })
        for i, r in enumerate(posts['result']):
            finalPosts.append(r)
        return json.dumps({'threads':[{'thread_id': x['_id'], 'public_key' : x['public_key'], 'name' : x['name'], 'subject' : x['subject'], 'guid' : x['guid'], 'timestamp': float(x['timestamp'])} for i, x in enumerate(finalPosts)], 'requestType' : 'getThreads'})
        
    
    def getThread(self, data, decrypted):
        guids_added = []
        connection = Connection('localhost',27021)
        db = connection.yadaserver
        friendPosts = db.command(
                {
                    "aggregate" : "identities", "pipeline" : [
                        {
                            "$match" : {
                                "public_key" : data['public_key']
                            }
                        },
                        {
                            "$match" : {
                                "data.friends" : { "$not" : {"$size" : 0}}
                            }
                        },
                        {
                            "$project" : {
                                "friend" : "$data.friends",
                            }
                        },
                        {
                            "$unwind" : "$friend"
                         },
                        {
                            "$match" : {
                                "friend.data.messages" : { "$not" : {"$size" : 0}}
                            }
                        },
                        {
                            "$project" : {
                                "friend" : 1,
                                "message" : "$friend.data.messages",
                            }
                        },
                        {
                            "$unwind" : "$message"
                         },
                        {
                            "$match" : {
                                "message.thread_id" : decrypted['thread_id']
                            }
                        },
                        {
                            "$project" : {
                                          "message" : 1,
                                          "name" : "$friend.data.identity.name"
                                          }
                         }
                         ]
                    })['result']
        for x in friendPosts:
            x['message']['name'] = x['name']
        friendPosts = [x['message'] for x in friendPosts]
        for i, post in enumerate(friendPosts):
            post['timestamp'] = int(round(float(post['timestamp']),0))
            post['who'] = 'friend'
            guids_added.append(post['guid'])
        posts = db.command(
                {
                    "aggregate" : "identities", "pipeline" : [
                        {
                            "$match" : {
                                "public_key" : data['public_key']
                            }
                        },
                        {
                            "$match" : {
                                "data.messages" : { "$not" : {"$size" : 0}}
                            }
                        },
                        {
                            "$project" : {
                                "name" : "$data.identity.name",
                                "message" : "$data.messages",
                            }
                        },
                        {
                            "$unwind" : "$message"
                         },
                        {
                            "$match" : {
                                "message.thread_id" : decrypted['thread_id']
                            }
                        }
                         ]
                    })['result']
        for x in posts:
            x['message']['name'] = x['name']
        posts = [x['message'] for x in posts]
        for i, post in enumerate(posts):
            post['timestamp'] = int(round(float(post['timestamp']),0))
            post['who'] = 'me'
            guids_added.append(post['guid'])
        posts.extend(friendPosts)
        friendOfIndexerQuery = db.command(
                {
                    "aggregate" : "identities", "pipeline" : [
                        {
                            "$match" : {
                                "public_key" : data['public_key']
                            }
                        },
                        {
                            "$match" : {
                                "data.friends" : { "$not" : {"$size" : 0}}
                            }
                        },
                        {
                            "$project" : {
                                "friend" :"$data.friends"
                            }
                        },
                        {
                            "$unwind" : "$friend"
                         },
                         {
                            "$project" : {
                                "public_key" :"$friend.public_key",
                                "private_key" :"$friend.private_key",
                                "data" : {
                                          "type" : "$friend.data.type",
                                          "friends" : "$friend.data.friends",
                                          "identity" : "$friend.data.identity"
                                          },
                            }
                        },
                         ]
                    })['result']
        
        
        thread_id = decrypted['thread_id']
        for friend in friendOfIndexerQuery:
            if 'type' in friend['data']:
                dataToSend = '{"method" : "GET", "public_key" : "%s", "data" : "%s"}' %(friend['public_key'], encrypt(friend['private_key'], friend['private_key'], json.dumps({'query':'messages', 'thread_id':thread_id,'data':{'friends':[{'public_key':x['public_key']} for x in friendOfIndexerQuery]}}, cls=JSONEncoder)))
                responseDecoded = self.queryIndexer(dataToSend, friend, data)
                for post in responseDecoded:
                    post['timestamp'] = int(round(float(post['timestamp']),0))
                    post['who'] = 'friend'
                    if not post['guid'] in guids_added:
                        posts.extend(post)
                        guids_added.append(post['guid'])
        return json.dumps({'thread':posts})
    
    
    def getStatus(self, data, decrypted):
        posts = []
        connection = Connection('localhost',27021)
        db = connection.yadaserver
        
        for friend in data['data']['friends']:
            if 'status' in friend['data']:
                if friend['data']['status']:
                    dict = {}
                    dict['blob'] = sorted(friend['data']['status'], key=lambda k: k['timestamp'],reverse=True)[0]
                    dict['name'] = friend['data']['identity']['name']
                    dict['public_key'] = friend['public_key']
                    posts.append(dict)
        
        return json.dumps({'status':posts[0:10], 'requestType':'getStatus'})
    
    
    def getFriendRequests(self, data, decrypted):
        posts = []
        connection = Connection('localhost',27021)
        db = connection.yadaserver
        ignoredRequests = decrypted['ignoredRequests']
        friend = db.command(
                {
                    "aggregate" : "identities", "pipeline" : [
                        {
                            "$match" : {
                                "public_key" : data['public_key']
                            }
                        },
                        {
                            "$match" : {
                                "data.friends" : { "$not" : {"$size" : 0}}
                            }
                        },
                        {
                            "$project" : {
                                "friend" : "$data.friends",
                            }
                        },
                        {
                            "$unwind" : "$friend"
                         },
                        {
                            "$match" : {
                                "friend.data.routed_friend_requests" : { "$not" : {"$size" : 0}}
                            }
                        },
                        {
                            "$unwind" : "$friend.data.routed_friend_requests"
                        },
                        {
                            "$project" : {
                                          "public_key" : "$friend.public_key",
                                          "routed_public_key" :"$friend.data.routed_friend_requests.routed_public_key",
                                          "request_public_key" :"$friend.data.routed_friend_requests.public_key",
                                          "name" : "$friend.data.routed_friend_requests.data.identity.name"
                                        }
                        },
                    ]
                })['result']
         
        for request in friend:
            if 'routed_public_key' in request and request['routed_public_key']==request['public_key'] and not request['request_public_key'] in ignoredRequests:
                posts.append({'public_key' : request['request_public_key'], 'name' : request['name']})
        return {'friend_requests':posts, 'requestType':'getFriendRequests'}
    
    
    def getFriendRequest(self, data, decrypted):
        posts = []
        connection = Connection('localhost',27021)
        db = connection.yadaserver
        
        friend = db.command(
                {
                    "aggregate" : "identities", "pipeline" : [
                        {
                            "$match" : {
                                "public_key" : data['public_key']
                            }
                        },
                        {
                            "$match" : {
                                "data.friends" : { "$not" : {"$size" : 0}}
                            }
                        },
                        {
                            "$project" : {
                                "friend" : "$data.friends",
                            }
                        },
                        {
                            "$unwind" : "$friend"
                         },
                        {
                            "$match" : {
                                "friend.data.routed_friend_requests" : { "$not" : {"$size" : 0}}
                            }
                        },
                        {
                            "$unwind" : "$friend.data.routed_friend_requests"
                        },
                        {
                            "$match" : {
                                "friend.data.routed_friend_requests.public_key" : decrypted['public_key']
                            }
                        },
                        {
                            "$project" : {
                                          "routed_public_key" :"$friend.data.routed_friend_requests.routed_public_key",
                                          "friendRequest" : "$friend.data.routed_friend_requests"
                                        }
                        },
                    ]
                })['result'][0]
        self.stripIdentityAndFriendsForProtocolV1(friend['friendRequest'])
        return json.dumps(friend['friendRequest'])
        
        return "{}"
    
    
    def getIdentity(self, data, decrypted):
        node = Node(public_key=data['public_key'], host='localhost', port=27017)
        return {'identity':node.get('data/identity'), 'requestType':'getIdentity'}
    
    
    def postMessage(self, data, decrypted):
        node = Node(public_key = data['public_key'])
        node.addMessage(decrypted)
        node.save()
        friends_indexed = []
        connection = Connection('localhost',27021)
        db = connection.yadaserver
        data = Node(public_key = data['public_key'])
        nodeComm = NodeCommunicator(data)
        nodeComm.sendMessage(pub_keys=decrypted['public_key'], subject=decrypted['subject'], message=decrypted['message'], thread_id=decrypted['thread_id'])
        
        """
        selectedFriends = {}
        for i, friend in enumerate(data['data']['friends']):
            if friend['public_key'] in decrypted['public_key']:
                selectedFriends[friend['public_key']] = friend
        for i, friend in enumerate(decrypted['public_key']):
            data['public_key'] = selectedFriends[friend]['public_key']
            data['private_key'] = selectedFriends[friend]['private_key']
            hostedUserUpdate({"method" : "POST", "public_key" :friend, "data" : encrypt(selectedFriends[friend]['private_key'], selectedFriends[friend]['private_key'], json.dumps(data, cls=MongoEncoder))})
        """
        return "{}"
    
    
    def postStatus(self, data, decrypted):
        data['data']['status'].append(decrypted)
        data['modified'] = self.getTimeStamp()
        self.saveDataForProfile(data)
        """
        selectedFriends = {}
        stripIdentityAndFriendsForProtocolV1(data)
        replaceIdentityOfFriendsWithPubKeysKeepPrivateKeys(data)
        for i, friend in enumerate(data['data']['friends']):
            data['public_key'] = friend['public_key']
            data['private_key'] = friend['private_key']
            try:
                encryptedDataToSend = encrypt(friend['private_key'], friend['private_key'], json.dumps(data, cls=MongoEncoder))
                hostedUserUpdate({"method" : "POST", "public_key" :friend['public_key'], "data" : encryptedDataToSend})
            except:
                pass
        """
        return "{}"
        
    
    def postFriend(self, data, decrypted):
        node = Node(public_key = data['public_key'])
        node.addFriend(decrypted)
        node.save()
        return "{}"
    
    
    def postIdentity(self, data, decrypted):
        connection = Connection('localhost',27021)
        db = connection.yadaserver
        collection = db.identities
        node = Node(public_key = data['public_key'])
        node.sync(decrypted)
        node.save()
        return "{}"