import logging
import re

from homeassistant.helpers.entity import Entity

from . import TdarrEntity
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add the Entities from the config."""
    entry = hass.data[DOMAIN][config_entry.entry_id]
    sensors = []
    # Server Status Sensor
    sensors.append(TdarrSensor(entry, entry.data["server"], config_entry.options, "server"))
    # Server Stats Sensors
    sensors.append(TdarrSensor(entry, entry.data["stats"], config_entry.options, "stats_spacesaved"))
    sensors.append(TdarrSensor(entry, entry.data["stats"], config_entry.options, "stats_transcodefilesremaining"))
    sensors.append(TdarrSensor(entry, entry.data["stats"], config_entry.options, "stats_transcodedcount"))
    for key, value in entry.data["nodes"].items():
        sensors.append(TdarrSensor(entry, value, config_entry.options, "node"))
        sensors.append(TdarrSensor(entry, value, config_entry.options, "nodefps"))
    async_add_entities(sensors, True)


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
        if self.type == "server":
            self._device_id = "tdarr_server"
        elif self.type == "node":
            self._device_id = "tdarr_node_" + self.sensor["_id"]
        elif self.type == "nodefps":
            self._device_id = "tdarr_node_" + self.sensor["_id"] + "_fps"
        else:
            self._device_id = "tdarr_" + self.type
        # Required for HA 2022.7
        self.coordinator_context = object()

    def get_value(self, ftype):
        if ftype == "state":
            if self.type == "server":
                return self.coordinator.data["server"]["status"]
            elif self.type == "node":
                return "Online"
            elif self.type == "nodefps":
                fps = 0
                for key1, value in self.coordinator.data["nodes"][self.sensor["_id"]]["workers"].items():
                    fps += value["fps"]
                return fps
            elif self.type == "stats_spacesaved":
                return round(self.coordinator.data["stats"]["sizeDiff"], 2)
            elif self.type == "stats_transcodefilesremaining":
                return self.coordinator.data["stats"]["table1Count"]
            elif self.type == "stats_transcodedcount":
                return self.coordinator.data["stats"]["table2Count"]

        if ftype == "attributes":
            if self.type == "server":
                return self.coordinator.data["server"]
            elif self.type == "node":
                return self.coordinator.data["nodes"][self.sensor["_id"]]
            elif self.type == "stats_spacesaved":
                return self.coordinator.data["stats"]
            else:
                return None

    @property
    def name(self):
        if self.type == "server":
            return "tdarr_server"
        elif self.type == "node":
            return "tdarr_node_" + self.sensor["_id"]
        elif self.type == "nodefps":
            return "tdarr_node_" + self.sensor["_id"] + "_fps"
        else:
            return "tdarr_" + self.type

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
        if self.type == "nodefps":
            return "FPS"
        elif self.type == "stats_spacesaved":
            return "GB"
        elif self.type == "stats_transcodefilesremaining":
            return "Files"
        elif self.type == "stats_transcodedcount":
            return "Files"
        else:
            return None

    @property
    def icon(self):
        return None