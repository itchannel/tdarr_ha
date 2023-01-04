import requests


class Server(object):
    # Class representing a tdarr server
    def __init__(self, url, port):
        self.url = url
        self.baseurl = 'http://' + self.url + ':' + port + '/api/v2/'
        
    def getNodes(self):
        r = requests.get(self.baseurl + 'get-nodes')
        if r.status_code == 200:
            result = r.json()
            return result
        else:
            return "ERROR"

    def getStatus(self):
        r = requests.get(self.baseurl + 'status')
        if r.status_code == 200:
            result = r.json()
            return result
        else:
            return "ERROR"
        
        
    def pauseNode(self, nodeID, status):
        
        data = {
            "data": {
                "nodeID": nodeID,
                "nodeUpdates": {
                    "nodePaused": status
                }
            }
        }
        
        r = requests.post(self.baseurl + 'update-node', json=data)
        if r.status_code == 200:
            return r.text
        else:
            return "ERROR"