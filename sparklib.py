#!/usr/bin/python
from json import dumps, loads
from re import match
from requests import HTTPError, post, get, delete
from difflib import SequenceMatcher
from collections import namedtuple

# {
#   "id" : "Y2lzY29zcGFyazovL3VzL01FU1NBR0UvOTJkYjNiZTAtNDNiZC0xMWU2LThhZTktZGQ1YjNkZmM1NjVk",
#   "roomId" : "Y2lzY29zcGFyazovL3VzL1JPT00vYmJjZWIxYWQtNDNmMS0zYjU4LTkxNDctZjE0YmIwYzRkMTU0",
#   "toPersonId" : "Y2lzY29zcGFyazovL3VzL1BFT1BMRS9mMDZkNzFhNS0wODMzLTRmYTUtYTcyYS1jYzg5YjI1ZWVlMmX",
#   "toPersonEmail" : "julie@example.com",
#   "text" : "PROJECT UPDATE - A new project plan has been published on Box: http://box.com/s/lf5vj. The PM for this project is Mike C. and the Engineering Manager is Jane W.",
#   "markdown" : "**PROJECT UPDATE** A new project plan has been published [on Box](http://box.com/s/lf5vj). The PM for this project is <@personEmail:mike@example.com> and the Engineering Manager is <@personEmail:jane@example.com>.",
#   "files" : [ "http://www.example.com/images/media.png" ],
#   "personId" : "Y2lzY29zcGFyazovL3VzL1BFT1BMRS9mNWIzNjE4Ny1jOGRkLTQ3MjctOGIyZi1mOWM0NDdmMjkwNDY",
#   "personEmail" : "matt@example.com",
#   "created" : "2015-10-18T14:26:16+00:00",
#   "mentionedPeople" : [ "Y2lzY29zcGFyazovL3VzL1BFT1BMRS8yNDlmNzRkOS1kYjhhLTQzY2EtODk2Yi04NzllZDI0MGFjNTM", "Y2lzY29zcGFyazovL3VzL1BFT1BMRS83YWYyZjcyYy0xZDk1LTQxZjAtYTcxNi00MjlmZmNmYmM0ZDg" ]
# }
class SparkMessage(object):
    def __init__(self,**kwargs):
        self.__dict__.update(kwargs)

class SparkLib():

    items = {}
    histLen = 50

    def __init__(self,api_key,apibase="https://api.ciscospark.com/v1/"):
        #print "Initializing SparkLib"
        self.post_message = self.postMessage
        self.api_key = api_key
        self.api = apibase
        self.msgHist = []
        self.me = self.getUser()
        try:
            self.getAllRooms()
        except:
            print("Could not authenticate!")

    def get(self,resource,params=None):
        return self.getCall("https://api.ciscospark.com/v1/" + resource, params)

    def post(self,resource,data, additional_headers={}):
        return self.postCall("https://api.ciscospark.com/v1/" + resource,data, addtional_headers=additional_headers)

    def delete(self,resource,oid):
        return self.delCall("https://api.ciscospark.com/v1/" + resource + "/" + oid)

    def getCall(self,endpoint,params=None):
        headers = { 'Authorization': 'Bearer {0}'.format(self.api_key), 'Content-type': 'application/json' }
        r = get(endpoint, headers=headers, params=params)
        r.raise_for_status()
        data = loads(r.text)
        #print json.dumps(data,indent=3)
        if "items" in data.keys():
            data = data["items"]
        return data

    def postCall(self, endpoint, data, addtional_headers={}):
        if isinstance(data, str):
            data = loads(data)
        headers = {'Authorization': 'Bearer {0}'.format(self.api_key), 'Content-Type': 'application/json'}
        headers.update(addtional_headers)
        r = post(endpoint, headers=headers, data=dumps(data))
        try:
            r.raise_for_status()
            return loads(r.text)
        except HTTPError as e:
            #print dumps(data, indent=3)
            #print dumps(headers, indent=3)
            raise e

    def delCall(self,endpoint):
        headers = { 'Authorization': 'Bearer {0}'.format(self.api_key), 'Content-Type': 'application/json' }
        r = delete(endpoint, headers=headers)
        r.raise_for_status()
        return r.text

    def getHooks(self):
        return self.get("webhooks")

    def delete_hooks(self):
        for h in self.getHooks():
            self.delete('webhooks',h['id'])

    def create_hooks(self,url, resource, event='created'):
        rooms = self.getAllRooms()
        for r in rooms:
            channel = "-".join((r['id'],resource))
            #self.createHook("-".join((r['id'],res)), res, event, url, "roomId={}".format(r['id']))
            self.createHook(channel, resource, event, url, "roomId={}".format(r['id']))

    def createHook(self,name,resource,event,targetUrl,sieve=None):
        if sieve is None:
            sieve = "roomId=" + self.room["id"]
        payload = {"name": name, "targetUrl": targetUrl, "resource": resource, "event": event, "filter": sieve}
        #print "Creating hook for {} on {}".format(resource,sieve)
        return self.postCall("https://api.ciscospark.com/v1/webhooks", dumps(payload))

    def getHook(self,needle):
        hooks = self.get("webhooks")
        for hook in hooks:
            if needle in hook:
                return hook

    def postMessage(self,message,roomId=None):
        if type(message) is str:
            params = {
                "roomId":"{0}".format(roomId),
                "html":"{0}".format(message)
            }
        elif type(message) is dict:
            params = message
        if not params.get('roomId', None):
            params['roomId'] = self.roomId
        msg = self.post("messages", dumps(params))
        self.msgHist.append(msg['id'])
        while len(self.msgHist) > self.histLen:
            del self.msgHist[0]
        return msg

    def getAllRooms(self,filter=None):
        allRooms = self.getCall('https://api.ciscospark.com/v1/rooms')
        for r in allRooms:
            room = namedtuple("SparkRoom",r.keys())(**r)
            if filter and hasattr(r,filter):
                yield getattr(r,filter)
            elif filter:
                continue
            else:
                yield r

    def getMessages(self):
        return loads(self.get("messages", self.roomId))

    def printRooms(self):
        import tabulate
        return tabulate.tabulate(self.getAllRooms(),headers="keys")

    def setRoom(self,room):
        #print "Setting up room"
        room = self.getRoom(room)
        if "id" in room.keys():
            self.room = room
            self.roomId = room["id"]
        else:
            raise Exception("Could not find room {0}".format(room))

    def getRoom(self,needle):
        fields = ["id","title","name"]
        #print "Searching for {}".format(needle)
        rooms = self.getAllRooms()
        if not rooms:
            #print "No rooms found!"
            return None
        highscore = 0
        for r in rooms:
            for f in fields:
                try:
                    if r[f] == needle:
                        return r
                    else:
                        score = SequenceMatcher(None,needle,r[f]).ratio()
                        if score > highscore:
                            highscore = score
                            bestobj = r
                except KeyError:
                    pass
        #print "Best score: {}".format(highscore)
        #print "Best match: {}".format(bestobj)
        return bestobj


    def createRoom(self,name):
        return self.post('rooms',{"title": name})

    def addUser(self,user,roomId=None):
        if not roomId:
            roomId = self.roomId
        if match('[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', user):
            qual = 'personId'
        elif match('.*@.*\..*', user):
            qual = 'personEmail'
        #print "Adding {} to {}".format(user,roomId)
        params = {qual: user, "roomId": roomId}
        return self.post('memberships',params)

    def getUser(self,userId=None,userEmail=None):
        from collections import namedtuple

        if userId == None and userEmail == None:
            userId = "me"
        if userEmail:
            params = {'email': userEmail}
            user = self.get("people/",params=params)
        else:
            user = self.get("people/" + userId)
        return namedtuple('Person',user.keys())(**user)



if __name__ == '__main__':
    import sys
    spark = SparkLib(sys.argv[1])
    print(spark.printRooms())
