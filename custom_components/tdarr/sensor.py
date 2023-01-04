import logging
import re

from homeassistant.helpers.entity import Entity

from . import TdarrEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add the Entities from the config."""
    entry = hass.data[DOMAIN][config_entry.entry_id]


    sensor = TdarrSensor(entry, entry.data["server"], config_entry.options, "server")
    async_add_entities([sensor], True)
    for key, value in entry.data["nodes"].items():
        sensor = TdarrSensor(entry, value, config_entry.options, "node")
        async_add_entities([sensor], True)
        fps = 0
        for key1, value1 in value["workers"].items():
            fps += value1["fps"]
        value["fps"] = fps
        sensor = TdarrSensor(entry, value, config_entry.options, "nodefps")
        async_add_entities([sensor], True)


class TdarrSensor(
    TdarrEntity,
    Entity,
):
    def __init__(self, coordinator, sensor, options, type):

        self.sensor = sensor
        self.options = options
        self.type = type
        self._attr = {}
        self.coordinator = coordinator
        _LOGGER.debug(self.sensor)
        if self.type == "server":
            self._device_id = "tdarr_server"
        elif self.type == "node":
            self._device_id = "tdarr_node_" + self.sensor["_id"]
        elif self.type == "nodefps":
            self._device_id = "tdarr_node_" + self.sensor["_id"] + "_fps"
        # Required for HA 2022.7
        self.coordinator_context = object()

    def get_value(self, ftype):
        if ftype == "state":
            if self.type == "server":
                return self.sensor["status"]
            elif self.type == "node":
                return "Online"
            elif self.type == "nodefps":
                return self.sensor["fps"]

        if ftype == "attributes":
            if self.type == "server":
                return self.sensor
            elif self.type == "node":
                return self.sensor
            elif self.type == "nodefps":
                return None

    @property
    def name(self):
        if self.type == "server":
            return "tdarr_server"
        elif self.type == "node":
            return "tdarr_node_" + self.sensor["_id"]
        elif self.type == "nodefps":
            return "tdarr_node_" + self.sensor["_id"] + "_fps"

    @property
    def state(self):
        return self.get_value("state")

    @property
    def device_id(self):
        return self.device_id

    @property
    def extra_state_attributes(self):
        return self.get_value("attributes")

    @property
    def unit_of_measurement(self):
        return None

    @property
    def icon(self):
        return None