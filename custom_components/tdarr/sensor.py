import logging
import re

from homeassistant.helpers.entity import Entity

from . import TdarrEntity
from .const import DOMAIN, COORDINATOR

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add the Entities from the config."""
    entry = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
    sensors = []
    # Server Status Sensor
    #_LOGGER.debug(entry.data)
    sensors.append(TdarrSensor(entry, entry.data["server"], config_entry.options, "server"))
    # Server Stats Sensors
    sensors.append(TdarrSensor(entry, entry.data["stats"], config_entry.options, "stats_spacesaved"))
    sensors.append(TdarrSensor(entry, entry.data["stats"], config_entry.options, "stats_transcodefilesremaining"))
    sensors.append(TdarrSensor(entry, entry.data["stats"], config_entry.options, "stats_transcodedcount"))
    sensors.append(TdarrSensor(entry, entry.data["stats"], config_entry.options, "stats_healthcount"))
    # Server Stage Count
    sensors.append(TdarrSensor(entry, entry.data["staged"], config_entry.options, "stats_stagedcount"))
    # Server Library Sensors
    id = 0
    for value in entry.data["stats"]["pies"]:
        value.insert(0, id)
        #_LOGGER.debug(value)
        sensors.append(TdarrSensor(entry, value, config_entry.options, "library"))
        id += 1
    # Server Node Sensors
    fps_count = 0
    for key, value in entry.data["nodes"].items():
        sensors.append(TdarrSensor(entry, value, config_entry.options, "node"))
        sensors.append(TdarrSensor(entry, value, config_entry.options, "nodefps"))
    
    #Calculate total fps
    sensors.append(TdarrSensor(entry, entry.data["nodes"], config_entry.options, "stats_totalfps"))
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
            if "nodeName" in self.sensor:
                self._device_id = "tdarr_node_" + self.sensor.get("nodeName", "")
            else:
                self._device_id = "tdarr_node_" + self.sensor.get("_id", "")
        elif self.type == "nodefps":
            if "nodeName" in self.sensor:
                self._device_id = "tdarr_node_" + self.sensor.get("nodeName","") + "_fps"
            else:
                self._device_id = "tdarr_node_" + self.sensor.get("_id", "") + "_fps"
        elif self.type == "library":
            self._device_id = "tdarr_library_" + self.sensor[1]
        else:
            self._device_id = "tdarr_" + self.type
        # Required for HA 2022.7
        self.coordinator_context = object()


    def get_value(self, ftype):
        if ftype == "state":
            if self.type == "server":
                return self.coordinator.data.get("server", {}).get("status")
            elif self.type == "node":
                return "Online"
            elif self.type == "nodefps":
                fps = 0
                for key1, value in self.coordinator.data.get("nodes", {}).get(self.sensor["_id"], {}).get("workers", {}).items():
                    fps += value.get("fps", 0)
                return fps
            elif self.type == "stats_spacesaved":
                return round(self.coordinator.data.get("stats",{}).get("sizeDiff", 0), 2)
            elif self.type == "stats_transcodefilesremaining":
                return self.coordinator.data.get("stats",{}).get("table1Count", 0)
            elif self.type == "stats_transcodedcount":
                return self.coordinator.data.get("stats",{}).get("table2Count", 0)
            elif self.type == "stats_stagedcount":
                return self.coordinator.data.get("staged",{}).get("totalCount", 0)
            elif self.type == "stats_healthcount":
                return self.coordinator.data.get("stats",{}).get("table4Count", 0)
            elif self.type == "library":
                return self.coordinator.data.get("stats",{}).get("pies",[])[self.sensor[0]][2]
            elif self.type == "stats_totalfps":
                fps = 0
                for key1, value1 in self.coordinator.data["nodes"].items():
                    for key2, value2 in value1.get("workers", {}).items():
                        fps += value2.get("fps", 0)
                return fps

        if ftype == "attributes":
            if self.type == "server":
                return self.coordinator.data.get("server", {})
            elif self.type == "node":
                return self.coordinator.data.get("nodes",{}).get(self.sensor["_id"], {})
            elif self.type == "stats_spacesaved":
                return self.coordinator.data.get("stats", {})
            elif self.type == "library":
                library = self.coordinator.data.get("stats",{}).get("pies", [])[self.sensor[0]]
                data = {}
                data["Total Files"] = library[2]
                data["Number of Transcodes"] = library[3]
                data["Space Saved (GB)"] = round(library[4], 0)
                data["Number of Health Checks"] = library[5]
                codecs = {}
                for codec in library[8]:
                    codecs[codec["name"]] = codec["value"]
                data["Codecs"] = codecs
                containers = {}
                for container in library[9]:
                    containers[container["name"]] = container["value"]
                data["Containers"] = containers
                qualities = {}
                for quality in library[10]:
                    qualities[quality["name"]] = quality["value"]
                data["Resolutions"] = qualities
                return data
            else:
                return None

    @property
    def name(self):
        if self.type == "server":
            return "tdarr_server"
        elif self.type == "node":
            if "nodeName" in self.sensor:
                return "tdarr_node_" + self.sensor.get("nodeName", "Unknown")
            else:
                return "tdarr_node_" + self.sensor.get("_id", "Unknown")
        elif self.type == "nodefps":
            if "nodeName" in self.sensor:
                return "tdarr_node_" + self.sensor.get("nodeName", "Unknown") + "_fps"
            else:
                return "tdarr_node_" + self.sensor.get("_id", "Unknown") + "_fps"
        elif self.type == "library":
            return "tdarr_library_" + self.sensor[1]
        else:
            return "tdarr_" + self.type

    @property
    def state(self):
        try:
            return self.get_value("state")
        except Exception as e:
            _LOGGER.error(f"Error getting state for {self.name}: {e}")
            return None

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
        elif self.type == "stats_stagedcount":
            return "Files"
        elif self.type == "stats_healthcount":
            return "Files"
        elif self.type == "library":
            return "Total Files"
        elif self.type == "stats_totalfps":
            return "FPS"
        else:
            return None

    @property
    def icon(self):
        return None