"""The Tdarr integration."""
from __future__ import annotations

import logging
from datetime import timedelta

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    APIKEY,
    COORDINATOR,
    DOMAIN,
    MANUFACTURER,
    SERVERIP,
    SERVERPORT,
    UPDATE_INTERVAL,
    UPDATE_INTERVAL_DEFAULT,
)
from .tdarr import Server, TdarrAuthError, TdarrError

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS = [Platform.SENSOR, Platform.SWITCH]

SERVICE_REFRESH_LIBRARY = "refresh_library"
SERVICE_REFRESH_LIBRARY_SCHEMA = vol.Schema(
    {
        vol.Required("library"): cv.string,
        vol.Optional("folderpath", default=""): cv.string,
        vol.Optional("mode", default="scanFindNew"): vol.In(
            ["scanFindNew", "scanFresh"]
        ),
    }
)

SERVICE_CANCEL_WORKERS = "cancel_workers_by_node_name"
SERVICE_CANCEL_WORKERS_SCHEMA = vol.Schema(
    {
        vol.Required("node_name"): cv.string,
        vol.Optional("cause", default="user"): cv.string,
    }
)

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Tdarr component."""
    hass.data.setdefault(DOMAIN, {})

    async def async_refresh_library_service(service_call: ServiceCall) -> None:
        await hass.async_add_executor_job(refresh_library, hass, service_call)

    async def async_cancel_workers_service(service_call: ServiceCall) -> None:
        await hass.async_add_executor_job(cancel_workers, hass, service_call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH_LIBRARY,
        async_refresh_library_service,
        schema=SERVICE_REFRESH_LIBRARY_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CANCEL_WORKERS,
        async_cancel_workers_service,
        schema=SERVICE_CANCEL_WORKERS_SCHEMA,
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tdarr Server from a config entry."""
    # Older versions stored the update interval in entry.data, so fall back to it
    update_interval = entry.options.get(
        UPDATE_INTERVAL, entry.data.get(UPDATE_INTERVAL, UPDATE_INTERVAL_DEFAULT)
    )

    coordinator = TdarrDataUpdateCoordinator(hass, entry, update_interval)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {COORDINATOR: coordinator}

    entry.async_on_unload(entry.add_update_listener(options_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


def _get_coordinators(hass: HomeAssistant) -> list["TdarrDataUpdateCoordinator"]:
    """Return the coordinators for all configured Tdarr servers."""
    return [
        entry_data[COORDINATOR]
        for entry_data in hass.data.get(DOMAIN, {}).values()
        if isinstance(entry_data, dict) and COORDINATOR in entry_data
    ]


def refresh_library(hass: HomeAssistant, service: ServiceCall) -> None:
    """Handle the refresh_library service call against all configured servers."""
    library = service.data["library"]
    mode = service.data.get("mode", "scanFindNew")
    folderpath = service.data.get("folderpath", "")

    coordinators = _get_coordinators(hass)
    if not coordinators:
        raise HomeAssistantError("No Tdarr servers are configured")

    errors = []
    for coordinator in coordinators:
        try:
            coordinator.tdarr.refreshLibrary(library, mode, folderpath)
            return
        except TdarrError as ex:
            errors.append(str(ex))

    raise HomeAssistantError("; ".join(errors))


def cancel_workers(hass: HomeAssistant, service: ServiceCall) -> None:
    """Cancel all workers on nodes matching the given name."""
    node_name = service.data["node_name"]
    cause = service.data.get("cause", "user")

    coordinators = _get_coordinators(hass)
    if not coordinators:
        raise HomeAssistantError("No Tdarr servers are configured")

    errors = []
    for coordinator in coordinators:
        try:
            cancelled = coordinator.tdarr.cancelAllWorkersByNodeName(node_name, cause)
            _LOGGER.info(
                "Cancelled %s worker(s) on node '%s'", cancelled, node_name
            )
            return
        except TdarrError as ex:
            errors.append(str(ex))

    raise HomeAssistantError("; ".join(errors))


async def options_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when options change."""
    _LOGGER.debug("Options updated, reloading Tdarr entry")
    await hass.config_entries.async_reload(entry.entry_id)


class TdarrDataUpdateCoordinator(DataUpdateCoordinator):
    """DataUpdateCoordinator to handle fetching new data about the Tdarr server."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, update_interval: int):
        """Initialize the coordinator and set up the Server object."""
        self.serverip = entry.data[SERVERIP]
        self.serverport = entry.data[SERVERPORT]
        self.tdarr = Server(
            self.serverip, self.serverport, entry.data.get(APIKEY, "")
        )

        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )

    def _fetch_data(self) -> dict:
        """Fetch all data from the Tdarr server (runs in the executor)."""
        return {
            "server": self.tdarr.getStatus(),
            "nodes": self.tdarr.getNodes(),
            "stats": self.tdarr.getStats(),
            "staged": self.tdarr.getStaged(),
            "libraries": self.tdarr.getLibraries(),
            "globalsettings": self.tdarr.getSettings(),
        }

    async def _async_update_data(self) -> dict:
        """Fetch data from Tdarr Server."""
        try:
            data = await self.hass.async_add_executor_job(self._fetch_data)
        except TdarrAuthError as ex:
            raise ConfigEntryAuthFailed(
                f"Tdarr server rejected the API key for {self.serverip}"
            ) from ex
        except TdarrError as ex:
            raise UpdateFailed(
                f"Error communicating with Tdarr for {self.serverip}: {ex}"
            ) from ex

        return data


class TdarrEntity(CoordinatorEntity):
    """Base class for Tdarr entities."""

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

        server = self.coordinator.data.get("server", {})
        sw_version = "Unknown"
        if isinstance(server, dict):
            sw_version = server.get("version", "Unknown")

        return {
            "identifiers": {(DOMAIN, self.coordinator.serverip)},
            "name": f"Tdarr Server ({self.coordinator.serverip})",
            "sw_version": sw_version,
            "manufacturer": MANUFACTURER,
        }
