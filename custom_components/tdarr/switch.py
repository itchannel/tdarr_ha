import logging
import time

from homeassistant.components.switch import SwitchEntity

from . import TdarrEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add the Switch from the config."""
    entry = hass.data[DOMAIN][config_entry.entry_id]
    
    for key, value in entry.data["nodes"].items():
        sw = Switch(entry, value, config_entry.options)
        async_add_entities([sw], False)

class Switch(TdarrEntity, SwitchEntity):
    """Define the Switch for turning ignition off/on"""

    def __init__(self, coordinator, switch, options):

        self._device_id = "tdarr_node_" + switch["_id"] + "_paused"
        self.switch = switch
        self.coordinator = coordinator
        self._state = None
        # Required for HA 2022.7
        self.coordinator_context = object()

    async def async_turn_on(self, **kwargs):
        update = await self.coordinator.hass.async_add_executor_job(
            self.coordinator.tdarr.pauseNode,
            self.switch["_id"],
            True
        )

        if update == "OK":
            self._state = True
            self.switch["nodePaused"] = True
            self.async_write_ha_state()



           
    async def async_turn_off(self, **kwargs):
        update = await self.coordinator.hass.async_add_executor_job(
            self.coordinator.tdarr.pauseNode,
            self.switch["_id"],
            False
        )

        if update == "OK":
            self._state = False
            self.switch["nodePaused"] = False
            self.async_write_ha_state()


    @property
    def name(self):
        return "tdarr_node_" + self.switch["_id"] + "_paused"

    @property
    def device_id(self):
        return self.device_id

    @property
    def is_on(self):
        if self._state == True:
            self._state = None
            return True
        elif self._state == False:
            self._state = None
            return False
        for key, value in self.coordinator.data["nodes"].items():
            if value["_id"] == self.switch["_id"]:
                return value["nodePaused"]



    @property
    def icon(self):
        return None

    @property
    def extra_state_attributes(self):
        return None