"""Sensor platform for the Tdarr integration."""
import logging

from homeassistant.components.sensor import SensorEntity

from . import TdarrEntity
from .const import COORDINATOR, DOMAIN, SENSORS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add the Entities from the config."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
    options = config_entry.options

    async_add_entities(
        TdarrSensor(coordinator, None, options, key)
        for key, value in SENSORS.items()
        if value.get("type", "") == "single"
    )

    known: set[str] = set()

    def _async_add_dynamic_entities() -> None:
        """Add entities for nodes/libraries discovered after setup."""
        new_sensors = []
        for library in coordinator.data.get("libraries", []):
            key = "library_" + library["name"]
            if key not in known:
                known.add(key)
                new_sensors.append(TdarrSensor(coordinator, library, options, "library"))
        for node in coordinator.data.get("nodes", {}).values():
            key = "node_" + node.get("nodeName", node.get("_id", ""))
            if key not in known:
                known.add(key)
                new_sensors.append(TdarrSensor(coordinator, node, options, "node"))
                new_sensors.append(TdarrSensor(coordinator, node, options, "nodefps"))
        if new_sensors:
            async_add_entities(new_sensors)

    _async_add_dynamic_entities()
    config_entry.async_on_unload(
        coordinator.async_add_listener(_async_add_dynamic_entities)
    )


class TdarrSensor(TdarrEntity, SensorEntity):
    """Representation of a Tdarr sensor."""

    def __init__(self, coordinator, sensor, options, sensor_type):
        """Initialize the sensor."""
        self.sensor = sensor
        self.tdarroptions = options
        self.type = sensor_type

        if self.type == "server":
            device_id = "tdarr_server"
        elif self.type == "node":
            device_id = "tdarr_node_" + self.sensor.get("nodeName", self.sensor.get("_id", ""))
        elif self.type == "nodefps":
            device_id = "tdarr_node_" + self.sensor.get("nodeName", self.sensor.get("_id", "")) + "_fps"
        elif self.type == "library":
            device_id = "tdarr_library_" + self.sensor["name"]
        else:
            device_id = "tdarr_" + self.type

        super().__init__(device_id=device_id, name=device_id, coordinator=coordinator)

    def _find_node(self):
        """Find this sensor's node in the current coordinator data.

        Nodes are matched by name where possible as the internal ID changes
        when a node reconnects.
        """
        nodes = self.coordinator.data.get("nodes", {})
        node_name = self.sensor.get("nodeName")
        if node_name is not None:
            for node in nodes.values():
                if node.get("nodeName") == node_name:
                    return node
            return None
        return nodes.get(self.sensor.get("_id"))

    @staticmethod
    def _current_files(node):
        """Summarise what a node's workers are currently processing."""
        current = []
        for worker in node.get("workers", {}).values():
            if not isinstance(worker, dict):
                continue
            file_path = worker.get("file", "")
            if not file_path:
                continue
            current.append(
                {
                    "file": file_path.replace("\\", "/").rsplit("/", 1)[-1],
                    "type": worker.get("workerType"),
                    "status": worker.get("status"),
                    "percentage": worker.get("percentage"),
                    "eta": worker.get("ETA"),
                    "fps": worker.get("fps"),
                }
            )
        return current

    def _find_library(self):
        """Find this sensor's library in the current coordinator data."""
        for library in self.coordinator.data.get("libraries", []):
            if library["name"] == self.sensor["name"]:
                return library
        return None

    def get_value(self, ftype):
        """Return the state or attributes for this sensor from coordinator data."""
        if ftype == "state":
            if self.type == "server":
                return self.coordinator.data.get("server", {}).get("status")
            if self.type == "node":
                return "Online" if self._find_node() is not None else "Offline"
            if self.type == "nodefps":
                node = self._find_node()
                if node is None:
                    return None
                return sum(
                    worker.get("fps", 0) for worker in node.get("workers", {}).values()
                )
            if self.type == "stats_spacesaved":
                return round(self.coordinator.data.get("stats", {}).get("sizeDiff", 0), 2)
            if self.type == "stats_transcodefilesremaining":
                return self.coordinator.data.get("stats", {}).get("table1Count", 0)
            if self.type == "stats_transcodedcount":
                return self.coordinator.data.get("stats", {}).get("table2Count", 0)
            if self.type == "stats_stagedcount":
                return self.coordinator.data.get("staged", {}).get("totalCount", 0)
            if self.type == "stats_healthcount":
                return self.coordinator.data.get("stats", {}).get("table4Count", 0)
            if self.type == "stats_transcodeerrorcount":
                return self.coordinator.data.get("stats", {}).get("table3Count", 0)
            if self.type == "stats_healtherrorcount":
                return self.coordinator.data.get("stats", {}).get("table6Count", 0)
            if self.type == "library":
                library = self._find_library()
                return library.get("totalFiles") if library else None
            if self.type == "stats_totalfps":
                fps = 0
                for node in self.coordinator.data.get("nodes", {}).values():
                    for worker in node.get("workers", {}).values():
                        fps += worker.get("fps", 0)
                return fps

        if ftype == "attributes":
            if self.type == "server":
                return self.coordinator.data.get("server", {})
            if self.type == "node":
                node = self._find_node()
                if node is None:
                    return {}
                attributes = dict(node)
                attributes["current_files"] = self._current_files(node)
                return attributes
            if self.type == "stats_spacesaved":
                return self.coordinator.data.get("stats", {})
            if self.type == "library":
                library = self._find_library()
                if library is None:
                    return None
                data = {}
                data["Total Files"] = library.get("totalFiles")
                data["Number of Transcodes"] = library.get("totalTranscodeCount")
                data["Space Saved (GB)"] = round(library.get("sizeDiff", 0), 0)
                data["Number of Health Checks"] = library.get("totalHealthCheckCount")
                data["Codecs"] = {
                    codec["name"]: codec["value"]
                    for codec in library.get("video", {}).get("codecs", [])
                }
                data["Containers"] = {
                    container["name"]: container["value"]
                    for container in library.get("video", {}).get("containers", [])
                }
                data["Resolutions"] = {
                    quality["name"]: quality["value"]
                    for quality in library.get("video", {}).get("resolutions", [])
                }
                return data

        return None

    @property
    def native_value(self):
        return self.get_value("state")

    @property
    def extra_state_attributes(self):
        return self.get_value("attributes")

    @property
    def native_unit_of_measurement(self):
        return SENSORS.get(self.type, {}).get("unit_of_measurement")

    @property
    def device_class(self):
        return SENSORS.get(self.type, {}).get("device_class")

    @property
    def state_class(self):
        return SENSORS.get(self.type, {}).get("state_class")

    @property
    def icon(self):
        return SENSORS.get(self.type, {}).get("icon")
