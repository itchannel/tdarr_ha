"""API client for a Tdarr server."""
import logging

import requests

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30

AUTH_ERROR_SNIPPETS = ("Invalid API key", "No auth token provided")


class TdarrError(Exception):
    """Base exception for Tdarr API errors."""


class TdarrConnectionError(TdarrError):
    """Raised when the Tdarr server cannot be reached or returns an error."""


class TdarrAuthError(TdarrError):
    """Raised when the Tdarr server rejects the API key."""


class Server:
    """Class representing a Tdarr server."""

    def __init__(self, url, port, apikey=""):
        self.url = url
        self.baseurl = f"http://{url}:{port}/api/v2/"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "x-api-key": apikey or "",
            }
        )

    def _request(self, method, endpoint, payload=None):
        try:
            response = self.session.request(
                method,
                self.baseurl + endpoint,
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )
        except requests.exceptions.RequestException as ex:
            raise TdarrConnectionError(
                f"Error connecting to Tdarr server at {self.url}: {ex}"
            ) from ex

        if response.status_code in (401, 403) or (
            response.status_code != 200
            and any(snippet in response.text for snippet in AUTH_ERROR_SNIPPETS)
        ):
            raise TdarrAuthError(
                f"Tdarr server rejected the request: {response.text}"
            )
        if response.status_code != 200:
            raise TdarrConnectionError(
                f"Tdarr server returned HTTP {response.status_code}: {response.text}"
            )
        return response

    def _get(self, endpoint):
        return self._request("GET", endpoint).json()

    def _post(self, endpoint, payload):
        return self._request("POST", endpoint, payload)

    def getNodes(self):
        return self._get("get-nodes")

    def getStatus(self):
        return self._get("status")

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
                "collection": "StatisticsJSONDB",
                "mode": "getById",
                "docID": "statistics",
                "obj": {},
            },
            "timeout": 1000,
        }
        return self._post("cruddb", post).json()

    def getLibraryStats(self):
        post = {
            "data": {
                "collection": "LibrarySettingsJSONDB",
                "mode": "getAll",
            },
            "timeout": 20000,
        }
        result = self._post("cruddb", post).json()
        return result if isinstance(result, list) else []

    def getPies(self, libraryID=""):
        post = {
            "data": {
                "libraryId": libraryID,
            },
        }
        return self._post("stats/get-pies", post).json()["pieStats"]

    def getStaged(self):
        post = {
            "data": {
                "filters": [],
                "start": 0,
                "pageSize": 10,
                "sorts": [],
                "opts": {},
            },
            "timeout": 1000,
        }
        return self._post("client/staged", post).json()

    def getSettings(self):
        post = {
            "data": {
                "collection": "SettingsGlobalJSONDB",
                "mode": "getById",
                "docID": "globalsettings",
                "obj": {},
            },
            "timeout": 1000,
        }
        return self._post("cruddb", post).json()

    def pauseNode(self, nodeID, status):
        if nodeID in ("pauseAll", "ignoreSchedules"):
            setting = "pauseAllNodes" if nodeID == "pauseAll" else "ignoreSchedules"
            data = {
                "data": {
                    "collection": "SettingsGlobalJSONDB",
                    "mode": "update",
                    "docID": "globalsettings",
                    "obj": {setting: status},
                },
                "timeout": 20000,
            }
            self._post("cruddb", data)
        else:
            data = {
                "data": {
                    "nodeID": nodeID,
                    "nodeUpdates": {"nodePaused": status},
                }
            }
            self._post("update-node", data)

    def cancelWorker(self, nodeID, workerID, cause="user"):
        """Cancel a specific worker on a node."""
        data = {
            "data": {
                "nodeID": nodeID,
                "workerID": workerID,
                "cause": cause,
            }
        }
        self._post("cancel-worker-item", data)

    def cancelAllWorkersByNodeName(self, nodeName, cause="user"):
        """Cancel all workers running on nodes with the given name.

        Returns the number of workers cancelled.
        """
        nodes = self.getNodes()
        target_nodes = [
            node
            for node in nodes.values()
            if isinstance(node, dict)
            and node.get("nodeName", "").lower() == nodeName.lower()
        ]
        if not target_nodes:
            raise TdarrError(f"No nodes found with name '{nodeName}'")

        cancelled = 0
        for node in target_nodes:
            for worker in node.get("workers", {}).values():
                if isinstance(worker, dict) and worker.get("_id"):
                    self.cancelWorker(node["_id"], worker["_id"], cause)
                    cancelled += 1
        return cancelled

    def refreshLibrary(self, libraryname, mode, folderpath):
        if not mode:
            mode = "scanFindNew"

        libid = None
        for lib in self.getLibraryStats():
            if libraryname in lib["name"]:
                libid = lib["_id"]

        if libid is None:
            raise TdarrError(f"Library '{libraryname}' not found")

        data = {
            "data": {
                "scanConfig": {
                    "dbID": libid,
                    "arrayOrPath": folderpath,
                    "mode": mode,
                }
            }
        }
        self._post("scan-files", data)
