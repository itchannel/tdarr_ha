import logging
import requests
import asyncio
import aiohttp
from functools import lru_cache
import time
from typing import Dict, List, Union, Any, Optional

_LOGGER = logging.getLogger(__name__)

class Server:
    """Class representing a tdarr server with optimized performance."""
    
    def __init__(self, url: str, port: str, apikey: str = "", timeout: int = 10):
        """Initialize the server connection with improved defaults."""
        self.url = url
        self.baseurl = f'http://{url}:{port}/api/v2/'
        self.headers = {
            'Content-Type': 'application/json',
            'x-api-key': apikey
        }
        self.timeout = timeout
        # Create persistent session for connection pooling
        self.session = requests.Session()
        # Cache to store frequently accessed data
        self._cache = {}
        self._cache_ttl = {}
        self._default_cache_ttl = 300  # 5 minutes default TTL
    
    def _clear_expired_cache(self):
        """Clear expired cache entries."""
        current_time = time.time()
        expired_keys = [k for k, v in self._cache_ttl.items() if current_time > v]
        for key in expired_keys:
            self._cache.pop(key, None)
            self._cache_ttl.pop(key, None)
    
    def _cache_get(self, key: str) -> Optional[Any]:
        """Get a value from cache if not expired."""
        self._clear_expired_cache()
        return self._cache.get(key)
    
    def _cache_set(self, key: str, value: Any, ttl: int = None) -> None:
        """Set a value in cache with TTL."""
        ttl = ttl or self._default_cache_ttl
        self._cache[key] = value
        self._cache_ttl[key] = time.time() + ttl
    
    async def _async_request(self, session, method: str, endpoint: str, json_data: Dict = None) -> Dict:
        """Make an async request to the API."""
        url = f"{self.baseurl}{endpoint}"
        try:
            if method.lower() == 'get':
                async with session.get(url, headers=self.headers, timeout=self.timeout) as response:
                    if response.status == 200:
                        try:
                            # Check if response is empty
                            text = await response.text()
                            if not text.strip():
                                return {"success": True}
                            # Parse the text instead of using response.json() with the content parameter
                            import json
                            return json.loads(text)
                        except ValueError as json_err:
                            _LOGGER.error(f"JSON parsing error for {endpoint}: {str(json_err)}")
                            return {"error": f"JSON parsing error: {str(json_err)}"}
                    else:
                        _LOGGER.error(f"API error: {endpoint} returned {response.status}")
                        response_text = await response.text()
                        return {"error": f"Status code: {response.status}", "response": response_text[:100]}
            else:  # POST
                async with session.post(url, headers=self.headers, json=json_data, timeout=self.timeout) as response:
                    if response.status == 200:
                        try:
                            # Check if response is empty
                            text = await response.text()
                            if not text.strip():
                                return {"success": True}
                            # Parse the text instead of using response.json() with the content parameter
                            import json
                            return json.loads(text)
                        except ValueError as json_err:
                            _LOGGER.error(f"JSON parsing error for {endpoint}: {str(json_err)}")
                            return {"error": f"JSON parsing error: {str(json_err)}"}
                    else:
                        _LOGGER.error(f"API error: {endpoint} returned {response.status}")
                        response_text = await response.text()
                        return {"error": f"Status code: {response.status}", "response": response_text[:100]}
        except Exception as e:
            _LOGGER.error(f"Request error for {endpoint}: {str(e)}")
            return {"error": str(e)}
    
    def _request(self, method: str, endpoint: str, json_data: Dict = None, cache_key: str = None, cache_ttl: int = None) -> Dict:
        """Make a synchronous request with caching support."""
        # Check cache first if a cache key is provided
        if cache_key:
            cached_data = self._cache_get(cache_key)
            if cached_data is not None:
                return cached_data
        
        url = f"{self.baseurl}{endpoint}"
        try:
            if method.lower() == 'get':
                response = self.session.get(url, headers=self.headers, timeout=self.timeout)
            else:  # POST
                response = self.session.post(url, headers=self.headers, json=json_data, timeout=self.timeout)
            
            if response.status_code == 200:
                try:
                    # Some endpoints might return empty or invalid JSON
                    if not response.text.strip():
                        result = {"success": True}
                    else:
                        result = response.json()
                    
                    # Cache the result if a cache key is provided
                    if cache_key:
                        self._cache_set(cache_key, result, cache_ttl)
                    return result
                except ValueError as json_err:
                    _LOGGER.error(f"JSON parsing error for {endpoint}: {str(json_err)}, Response: {response.text[:100]}")
                    return {"error": f"JSON parsing error: {str(json_err)}", "raw_response": response.text[:100]}
            else:
                _LOGGER.error(f"API error: {endpoint} returned {response.status_code}")
                return {"error": f"Status code: {response.status_code}", "response": response.text[:100]}
        except Exception as e:
            _LOGGER.error(f"Request error for {endpoint}: {str(e)}")
            return {"error": str(e)}
    
    def getNodes(self) -> Dict:
        """Get nodes with caching."""
        return self._request('get', 'get-nodes', cache_key='nodes', cache_ttl=60)

    def getStatus(self) -> Dict:
        """Get server status."""
        return self._request('get', 'status', cache_key='status', cache_ttl=30)
    
    def getLibraries(self) -> List[Dict]:
        """Get libraries with optimized parallel requests."""
        # Use the synchronous implementation
        libraries = []
        
        # Get library stats first (this is needed for both operations)
        library_stats = self.getLibraryStats()
        if isinstance(library_stats, dict) and "error" in library_stats:
            return [{"error": "Failed to get library stats", "details": library_stats}]
        
        # Get main library stats (All)
        all_library = self.getPies()
        if not isinstance(all_library, dict) or "error" in all_library:
            return [{"error": "Failed to get main library stats"}]
        
        all_library["name"] = "All"
        libraries.append(all_library)
        
        # Get individual library stats in parallel using asyncio
        async def fetch_all_libraries():
            async with aiohttp.ClientSession() as session:
                tasks = []
                for lib in library_stats:
                    lib_id = lib.get("_id", "")
                    lib_name = lib.get("name", "Unknown")
                    tasks.append(fetch_library_info(session, lib_id, lib_name))
                return await asyncio.gather(*tasks)
        
        async def fetch_library_info(session, lib_id, lib_name):
            """Helper function to get individual library info."""
            post_data = {"data": {"libraryId": lib_id}}
            result = await self._async_request(
                session, 'post', 'stats/get-pies', post_data
            )
            if isinstance(result, dict) and "pieStats" in result:
                result["pieStats"]["name"] = lib_name
                return result["pieStats"]
            return {"error": f"Failed to get stats for library {lib_name}"}
        
        # Execute async code in a sync context if needed
        try:
            additional_libraries = asyncio.run(fetch_all_libraries())
            for lib in additional_libraries:
                if "error" not in lib:
                    libraries.append(lib)
        except Exception as e:
            _LOGGER.error(f"Error fetching libraries in parallel: {str(e)}")
            # Fallback to sequential approach if async fails
            for lib in library_stats:
                library2 = self.getPies(lib.get("_id", ""))
                if isinstance(library2, dict) and "error" not in library2:
                    library2["name"] = lib.get("name", "Unknown")
                    libraries.append(library2)
        
        return libraries

    # Async version for use in async contexts
    async def getLibrariesAsync(self) -> List[Dict]:
        """Get libraries with optimized parallel async requests."""
        libraries = []
        
        async with aiohttp.ClientSession() as session:
            # Get library stats and main library stats in parallel
            library_stats_task = self._async_request(
                session, 'post', 'cruddb', 
                {"data": {"collection": "LibrarySettingsJSONDB", "mode": "getAll"}, "timeout": 20000}
            )
            all_library_task = self._async_request(
                session, 'post', 'stats/get-pies', 
                {"data": {"libraryId": ""}}
            )
            
            # Wait for both tasks to complete
            library_stats_result, all_library_result = await asyncio.gather(
                library_stats_task, all_library_task
            )
            
            # Process the main library result (All)
            if isinstance(all_library_result, dict) and "pieStats" in all_library_result:
                all_library = all_library_result["pieStats"]
                all_library["name"] = "All"
                libraries.append(all_library)
            
            # Skip individual libraries if we couldn't get library stats
            if isinstance(library_stats_result, dict) and "error" in library_stats_result:
                return libraries
            
            # Create tasks for each individual library
            library_tasks = []
            for lib in library_stats_result:
                lib_id = lib.get("_id", "")
                task = self._async_request(
                    session, 'post', 'stats/get-pies', 
                    {"data": {"libraryId": lib_id}}
                )
                library_tasks.append((task, lib.get("name", "Unknown")))
            
            # Process results as they complete
            for task, lib_name in library_tasks:
                result = await task
                if isinstance(result, dict) and "pieStats" in result:
                    result["pieStats"]["name"] = lib_name
                    libraries.append(result["pieStats"])
            
        return libraries

    def getStats(self) -> Dict:
        """Get server statistics."""
        post_data = {
            "data": {
                "collection": "StatisticsJSONDB",
                "mode": "getById",
                "docID": "statistics",
                "obj": {}
            },
            "timeout": 1000
        }
        return self._request('post', 'cruddb', post_data, cache_key='statistics', cache_ttl=60)
    
    def getLibraryStats(self) -> List[Dict]:
        """Get library statistics with caching."""
        post_data = {
            "data": {
                "collection": "LibrarySettingsJSONDB",
                "mode": "getAll",
            },
            "timeout": 20000
        }
        return self._request('post', 'cruddb', post_data, cache_key='library_stats', cache_ttl=120)
    
    def getPies(self, libraryID: str = "") -> Dict:
        """Get pie statistics for a library."""
        post_data = {
            "data": {
                "libraryId": libraryID
            }
        }
        cache_key = f'pies_{libraryID}' if libraryID else 'pies_all'
        result = self._request('post', 'stats/get-pies', post_data, cache_key=cache_key, cache_ttl=90)
        return result.get("pieStats", {"error": "No pieStats in response"}) if isinstance(result, dict) else result
    
    def getStaged(self) -> Dict:
        """Get staged items."""
        post_data = {
            "data": {
                "filters": [],
                "start": 0,
                "pageSize": 10,
                "sorts": [],
                "opts": {}
            },
            "timeout": 1000
        }
        # Don't cache this as it's likely to change frequently
        return self._request('post', 'client/staged', post_data)
    
    def getSettings(self) -> Dict:
        """Get global settings with caching."""
        post_data = {
            "data": {
                "collection": "SettingsGlobalJSONDB",
                "mode": "getById",
                "docID": "globalsettings",
                "obj": {}
            },
            "timeout": 1000
        }
        return self._request('post', 'cruddb', post_data, cache_key='settings', cache_ttl=300)
    
    def pauseNode(self, nodeID: str, status: bool) -> str:
        """Pause a node or all nodes."""
        result = None
        
        if nodeID == "pauseAll":
            data = {
                "data": {
                    "collection": "SettingsGlobalJSONDB",
                    "mode": "update",
                    "docID": "globalsettings",
                    "obj": {
                        "pauseAllNodes": status
                    }
                },
                "timeout": 20000
            }
            result = self._request('post', 'cruddb', data)
            # Clear settings cache since we modified it
            self._cache.pop('settings', None)
            self._cache_ttl.pop('settings', None)
            
        elif nodeID == "ignoreSchedules":
            data = {
                "data": {
                    "collection": "SettingsGlobalJSONDB",
                    "mode": "update",
                    "docID": "globalsettings",
                    "obj": {
                        "ignoreSchedules": status
                    }
                },
                "timeout": 20000
            }
            result = self._request('post', 'cruddb', data)
            # Clear settings cache since we modified it
            self._cache.pop('settings', None)
            self._cache_ttl.pop('settings', None)
            
        else:
            data = {
                "data": {
                    "nodeID": nodeID,
                    "nodeUpdates": {
                        "nodePaused": status
                    }
                }
            }
            result = self._request('post', 'update-node', data)
            # Clear nodes cache since we modified it
            self._cache.pop('nodes', None)
            self._cache_ttl.pop('nodes', None)
        
        if isinstance(result, dict) and "error" not in result:
            return "OK"
        else:
            return "ERROR"

    def refreshLibrary(self, libraryname: str, mode: str, folderpath: str) -> Dict:
        """Refresh a library with proper error handling."""
        stats = self.getLibraryStats()
        if isinstance(stats, dict) and "error" in stats:
            return {"error": "Failed to get library stats"}
        
        libid = None
        
        # Default mode if not specified
        if not mode:
            mode = "scanFindNew"
        
        # Find the library ID by name
        for lib in stats:
            if libraryname in lib.get("name", ""):
                libid = lib.get("_id")
                break

        if libid is None:
            return {"error": "Library name not found"}

        data = {
            "data": {
                "scanConfig": {
                    "dbID": libid,
                    "arrayOrPath": folderpath,
                    "mode": mode
                }
            }
        }

        result = self._request('post', 'scan-files', data)
        
        # Clear library-related caches since we triggered a scan
        for key in list(self._cache.keys()):
            if key.startswith('library') or key.startswith('pies'):
                self._cache.pop(key, None)
                self._cache_ttl.pop(key, None)
        
        if isinstance(result, dict) and "error" not in result:
            return {"success": True}
        else:
            return {"error": str(result)}

    def cancelWorker(self, nodeID, workerID, cause="user"):
        """
        Cancel a specific worker on a node.
        """
        data = {
            "data": {
                "nodeID": nodeID,
                "workerID": workerID,
                "cause": cause
            }
        }
        
        r = requests.post(self.baseurl + 'cancel-worker-item', json=data, headers=self.headers)
        
        if r.status_code == 200:
            return {"success": True, "message": f"Worker {workerID} on node {nodeID} cancelled successfully"}
        else:
            _LOGGER.error(f"Failed to cancel worker {workerID} on node {nodeID}: {r.text}")
            return {"error": True, "details": r.text}

    
    def cancelAllWorkersByNodeName(self, nodeName, cause="user"):
        """
        Cancel all workers running on a node identified by its name.
        """
        # First, get current node information to find all active workers
        nodes_response = self.getNodes()

        if nodes_response == "ERROR":
            return {"error": True, "message": "Failed to get node information"}

        # Find the node(s) by name
        target_nodes = []
        node_name_lower = nodeName.lower()

        # Let's debug what we're getting from getNodes
        _LOGGER.debug(f"Nodes response type: {type(nodes_response)}")
        #_LOGGER.debug(nodes_response)

        # Process based on the structure we have
        if isinstance(nodes_response, dict):
            # Process node list
            for key, node in nodes_response.items():
                if isinstance(node, dict):
                    node_name = node.get("nodeName", "")
                    if isinstance(node_name, str) and node_name.lower() == node_name_lower:
                        target_nodes.append(node)

        if not target_nodes:
            return {"error": True, "message": f"No nodes found with name '{nodeName}'"}

        # Multiple nodes might have the same name, handle all of them
        total_success_count = 0
        total_worker_count = 0
        failed_cancellations = []

        for node in target_nodes:
            node_id = node.get("_id")
            node_name = node.get("nodeName", "Unknown")
            
            # Extract worker IDs for this node
            workers = node.get("workers", [])
            worker_ids = []
            for key, worker in workers.items():
                _LOGGER.debug(worker)
                _LOGGER.debug(type(worker))
                if isinstance(worker, dict) and worker.get("_id"):
                    worker_ids.append(worker.get("_id"))
            
            total_worker_count += len(worker_ids)
            
            # Cancel each worker on this node
            for worker_id in worker_ids:
                result = self.cancelWorker(node_id, worker_id, cause)
                if isinstance(result, dict) and result.get("success"):
                    total_success_count += 1
                else:
                    failed_cancellations.append({
                        "node_name": node_name,
                        "node_id": node_id,
                        "worker_id": worker_id
                    })

        # Return summary
        if not total_worker_count:
            return {
                "success": True, 
                "message": f"No active workers found on nodes named '{nodeName}'",
                "affected_nodes": len(target_nodes),
                "cancelled_count": 0
            }

        if not failed_cancellations:
            return {
                "success": True,
                "message": f"Successfully cancelled all {total_success_count} workers on {len(target_nodes)} node(s) named '{nodeName}'",
                "affected_nodes": len(target_nodes),
                "cancelled_count": total_success_count
            }
        else:
            return {
                "partial_success": True,
                "message": f"Cancelled {total_success_count} out of {total_worker_count} workers on {len(target_nodes)} node(s) named '{nodeName}'",
                "affected_nodes": len(target_nodes),
                "cancelled_count": total_success_count,
                "failed_cancellations": failed_cancellations
            }
    
    def close(self):
        """Close the session to free resources."""
        self.session.close()
    
    def __del__(self):
        """Ensure session is closed on deletion."""
        try:
            self.session.close()
        except:
            pass