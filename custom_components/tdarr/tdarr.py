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
    
    def getLibraries(self):
        libraries = []
        library = self.getPies()
        library["name"] = "All"
        libraries.append(library)
        for lib in self.getLibraryStats():
            library2 = self.getPies(lib["_id"])
            library2["name"] = lib["name"]
            libraries.append(library2)


        return libraries

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
    
    def getLibraryStats(self):
        post = {
            "data": {
                "collection":"LibrarySettingsJSONDB",
                "mode":"getAll",
                },
            "timeout":20000
        }
        r = requests.post(self.baseurl + 'cruddb', json = post)
        if r.status_code == 200:
            return r.json()
        else:
            return
    def getPies(self, libraryID=""):
        post = {
            "data": {
                "libraryId":libraryID
                },
        }
        r = requests.post(self.baseurl + 'stats/get-pies', json = post)
        if r.status_code == 200:
            return r.json()["pieStats"]
        else:
            return "ERROR"
        
    def getStaged(self):
        post = {
            "data": {
                "filters":[],
                "start":0,
                "pageSize":10,
                "sorts":[],
                "opts":{}
                },
            "timeout":1000
        }
        r = requests.post(self.baseurl + 'client/staged', json = post)
        if r.status_code == 200:
            return r.json()
        else:
            return "ERROR"
        
    def getSettings(self):  
        post = {
            "data": {
                "collection":"SettingsGlobalJSONDB",
                "mode":"getById",
                "docID":"globalsettings",
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

        if nodeID == "pauseAll":
            data = {
                "data":{
                    "collection":"SettingsGlobalJSONDB",
                    "mode":"update",
                    "docID":"globalsettings",
                    "obj":{
                        "pauseAllNodes": status
                        }
                    },
                    "timeout":20000
                }
            r = requests.post(self.baseurl + 'cruddb', json=data)
        elif nodeID == "ignoreSchedules":
            data = {
                "data":{
                    "collection":"SettingsGlobalJSONDB",
                    "mode":"update",
                    "docID":"globalsettings",
                    "obj":{
                        "ignoreSchedules": status
                        }
                    },
                    "timeout":20000
                }
            r = requests.post(self.baseurl + 'cruddb', json=data)
        else:
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
            return "OK"
        else:
            return "ERROR"

    def refreshLibrary(self, libraryname, mode, folderpath):
        stats = self.getLibraryStats()
        libid = None
        _LOGGER.debug(mode)

        if mode == "":
            mode = "scanFindNew"
        for lib in stats:
            if libraryname in lib["name"]:
                libid = lib["_id"]

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



            
    


    

    