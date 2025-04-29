"""The Tdarr integration."""
import asyncio
import logging
from datetime import timedelta

import async_timeout
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    MANUFACTURER,
    SERVERIP,
    SERVERPORT,
    UPDATE_INTERVAL,
    UPDATE_INTERVAL_DEFAULT,
    COORDINATOR,
    APIKEY
)

from .tdarr import Server

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

PLATFORMS = ["sensor", "switch"]

_LOGGER = logging.getLogger(__name__)

# Service schema for refresh_library
REFRESH_LIBRARY_SCHEMA = vol.Schema({
    vol.Required("library"): cv.string,
    vol.Optional("mode", default="scanFindNew"): cv.string,
    vol.Optional("folderpath", default=""): cv.string,
})

# Service schema for cancel_workers_by_node_name
CANCEL_WORKERS_SCHEMA = vol.Schema({
    vol.Required("node_name"): cv.string,
    vol.Optional("cause", default="user"): cv.string,
})


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Tdarr component."""
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Tdarr Server from a config entry."""
    serverip = entry.data[SERVERIP]
    serverport= entry.data[SERVERPORT]
    if APIKEY in entry.data:
        apikey = entry.data[APIKEY]
    else:
        apikey = ""

    if UPDATE_INTERVAL in entry.options:
        update_interval = entry.options[UPDATE_INTERVAL]
    else:
        update_interval = UPDATE_INTERVAL_DEFAULT

    coordinator = TdarrDataUpdateCoordinator(hass, serverip, serverport, update_interval, apikey)

    await coordinator.async_refresh()  # Get initial data
    
    tdarr_options_listener = entry.add_update_listener(options_update_listener) 

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data[DOMAIN][entry.entry_id] = {
        COORDINATOR : coordinator,
        "tdarr_options_listener": tdarr_options_listener
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register service to refresh library - defined as a local function
    async def async_refresh_library_service(service_call):
        await hass.async_add_executor_job(
            refresh_library, hass, service_call, coordinator
        )

    # Define cancel workers service handler locally to capture coordinator
    async def handle_cancel_workers(service_call):
        """Handle cancel workers service call."""
        await hass.async_add_executor_job(
            cancel_workers_by_node_name, hass, service_call, coordinator
        )
        
        # Now that we're back in the event loop, safely refresh the coordinator
        await coordinator.async_refresh()

    # Register services with proper local handlers
    hass.services.async_register(
        DOMAIN,
        "refresh_library", 
        async_refresh_library_service,
        schema=REFRESH_LIBRARY_SCHEMA
    )

    hass.services.async_register(
        DOMAIN,
        "cancel_workers_by_node_name",
        handle_cancel_workers,  # Use the local function that captures coordinator
        schema=CANCEL_WORKERS_SCHEMA
    )

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    #_LOGGER.debug(hass.data[DOMAIN][entry.entry_id])
    hass.data[DOMAIN][entry.entry_id]["tdarr_options_listener"]()
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok

def refresh_library(hass, service, coordinator):
    libraryid = service.data.get("library", "")
    mode = service.data.get("mode", "scanFindNew")
    folderpath = service.data.get("folderpath", "")
    status = coordinator.tdarr.refreshLibrary(libraryid, mode, folderpath)
    if "ERROR" in status:
        _LOGGER.debug(status)
        raise HomeAssistantError(status["ERROR"])

def cancel_workers_by_node_name(hass, service, coordinator):
    """Cancel all workers on a node by name."""
    node_name = service.data.get("node_name", "")
    cause = service.data.get("cause", "user")
    
    if not node_name:
        _LOGGER.error("Node name is required")
        raise HomeAssistantError("Node name is required")
    
    _LOGGER.debug("Cancelling all workers on node '%s'", node_name)
    result = coordinator.tdarr.cancelAllWorkersByNodeName(node_name, cause)
    
    if "error" in result:
        _LOGGER.error("Failed to cancel workers: %s", result.get("message", "Unknown error"))
        raise HomeAssistantError(f"Failed to cancel workers: {result.get('message', 'Unknown error')}")
    
    _LOGGER.info(
        "Cancelled %s workers on %s node(s) named '%s'", 
        result.get("cancelled_count", 0),
        result.get("affected_nodes", 0),
        node_name
    )
    
    # Just return the result, don't refresh the coordinator here
    return result

async def options_update_listener(
    hass: HomeAssistant,  entry: ConfigEntry 
    ):
        _LOGGER.debug("OPTIONS CHANGE")
        await hass.config_entries.async_reload(entry.entry_id)

class TdarrDataUpdateCoordinator(DataUpdateCoordinator):
    """DataUpdateCoordinator to handle fetching new data about the Tdarr Controller."""

    def __init__(self, hass, serverip, serverport, update_interval, apikey):
        """Initialize the coordinator and set up the Controller object."""
        self._hass = hass
        self.serverip = serverip
        self.serverport = serverport
        self.tdarr = Server(serverip, serverport, apikey)
        self._available = True

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )

    async def _async_update_data(self):
        """Fetch data from Tdarr Server."""
        try:
            async with async_timeout.timeout(30):
                data = {}
                data["server"] = await self._hass.async_add_executor_job(
                    self.tdarr.getStatus  # Fetch new status
                )

                data["nodes"] = await self._hass.async_add_executor_job(
                    self.tdarr.getNodes
                )        

                data["stats"] = await self._hass.async_add_executor_job(
                    self.tdarr.getStats
                )

                data["staged"] = await self._hass.async_add_executor_job(
                    self.tdarr.getStaged
                )

                data["libraries"] = await self._hass.async_add_executor_job(
                    self.tdarr.getLibraries
                )

                data["globalsettings"] = await self._hass.async_add_executor_job(
                    self.tdarr.getSettings
                )
                #_LOGGER.debug(self.data)
                if self.data is not None:
                    #_LOGGER.debug(self.data)
                    oldnodes = len(self.data["nodes"])
                    #_LOGGER.debug(len(self.data["nodes"]))
                else:
                    oldnodes = len(data["nodes"])
                #_LOGGER.debug(len(self.data["nodes"])
                if oldnodes != len(data["nodes"]):
                    _LOGGER.debug("Node Change Detected config reload required")
                    # Reload integration to pick up new/changed nodes
                    current_entries = self._hass.config_entries.async_entries(DOMAIN)

                
                    if len(current_entries) > 0:
                        for entry in current_entries:
                            _LOGGER.debug("SHOWING ENTRY")
                            self._hass.config_entries.async_schedule_reload(entry.entry_id)


        

                return data
        except Exception as ex:
            self._available = False  # Mark as unavailable
            _LOGGER.warning(str(ex))
            _LOGGER.warning("Error communicating with Tdarr for %s", self.serverip)
            raise UpdateFailed(
                f"Error communicating with Tdarr for {self.serverip}"
            ) from ex

    async def reloadentities(self):
        _LOGGER.debug("Reloading?")
        current_entries = self._hass.config_entries.async_entries(DOMAIN)
        

        reload_tasks = [
            self._hass.config_entries.async_reload(entry.entry_id)
            for entry in current_entries
        ]

        await asyncio.gather(*reload_tasks)

class TdarrEntity(CoordinatorEntity):
    def __init__(
            self, *, device_id: str, name: str, coordinator: TdarrDataUpdateCoordinator
    ):
        """Initialize the entity."""
        super().__init__(coordinator)
        self._device_id = device_id
        self._name = name

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    @property
    def name(self):
        """Return the name of the entity."""
        #_LOGGER.debug(self._name)
        return self._name

    @property
    def unique_id(self):
        """Return the unique ID of the entity."""
        return f"{self.coordinator.serverip}-{self._device_id}"

    @property
    def device_info(self):
        """Return device information about this device."""
        if self._device_id is None:
            return None
        
        sw_version = "Unknown"

        if "version" in self.coordinator.data["server"]:
            sw_version = self.coordinator.data["server"]["version"]


        return {
            "identifiers": {(DOMAIN, self.coordinator.serverip)},
            "name": f"Tdarr Server ({self.coordinator.serverip})",
            #"hw_version": self.coordinator.data["system"]["hardware"],
            "sw_version": sw_version,
            "manufacturer": MANUFACTURER
        }