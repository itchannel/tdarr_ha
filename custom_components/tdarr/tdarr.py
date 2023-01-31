import logging
import requests

_LOGGER = logging.getLogger(__name__)

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

    def getStats(self):
        post = {
            "data": {
                "collection":"StatisticsJSONDB",
                "mode":"getById",
                "docID":"statistics",
                "obj":{}
                },
            "timeout":1000
        }
        r = requests.post(self.baseurl + 'cruddb', json = post)
        if r.status_code == 200:
            return r.json()
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

    def refreshLibrary(self, libraryname, mode, folderpath):
        stats = self.getStats()
        libid = None
        _LOGGER.debug(mode)

        if mode == "":
            mode = "scanFindNew"
        for lib in stats["pies"]:
            if libraryname in lib:
                libid = lib[1]
                _LOGGER.debug(lib[1])

        if libid is None:
            return {"ERROR": "Library Name not found"}


        data = {
            "data": {
                "scanConfig": {
                    "dbID" : libid,
                    "arrayOrPath": folderpath,
                    "mode": mode
                }
            }
        }

        r = requests.post(self.baseurl + "scan-files", json=data)

        if r.status_code == 200:
            _LOGGER.debug(r.text)
            return {"SUCCESS"}
        else:
            return {"ERROR": r.text}



            
    


    

    