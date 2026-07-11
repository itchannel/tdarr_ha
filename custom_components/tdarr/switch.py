"""Switch platform for the Tdarr integration."""
import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.exceptions import HomeAssistantError

from . import TdarrEntity
from .const import COORDINATOR, DOMAIN, SWITCHES
from .tdarr import TdarrError

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Add the Switch from the config."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id][COORDINATOR]
    options = config_entry.options

    async_add_entities(
        Switch(coordinator, coordinator.data.get("globalsettings", {}), value["name"], options)
        for value in SWITCHES.values()
    )

    known: set[str] = set()

    def _async_add_dynamic_entities() -> None:
        """Add pause switches for nodes discovered after setup."""
        new_switches = []
        for node in coordinator.data.get("nodes", {}).values():
            key = "node_" + node.get("nodeName", node.get("_id", ""))
            if key not in known:
                known.add(key)
                new_switches.append(Switch(coordinator, node, node["_id"], options))
        if new_switches:
            async_add_entities(new_switches)

    _async_add_dynamic_entities()
    config_entry.async_on_unload(
        coordinator.async_add_listener(_async_add_dynamic_entities)
    )


class Switch(TdarrEntity, SwitchEntity):
    """Switch to pause a Tdarr node or toggle a global setting."""

    def __init__(self, coordinator, switch, name, options):
        """Initialize the switch."""
        if "nodeName" in switch:
            device_id = "tdarr_node_" + switch["nodeName"] + "_paused"
        elif name == "pauseAll":
            device_id = "tdarr_pause_all"
        elif name == "ignoreSchedules":
            device_id = "tdarr_ignore_schedules"
        else:
            device_id = "tdarr_node_" + switch["_id"] + "_paused"

        self.switch = switch
        self.object_name = name
        self._optimistic_state = None

        super().__init__(device_id=device_id, name=device_id, coordinator=coordinator)

    def _is_global(self) -> bool:
        """Return True if this is a global settings switch rather than a node."""
        return self.object_name in SWITCHES

    def _find_node(self):
        """Find this switch's node in the current coordinator data.

        Nodes are matched by name where possible as the internal ID changes
        when a node reconnects.
        """
        nodes = self.coordinator.data.get("nodes", {})
        node_name = self.switch.get("nodeName")
        if node_name is not None:
            for node in nodes.values():
                if node.get("nodeName") == node_name:
                    return node
            return None
        return nodes.get(self.switch.get("_id"))

    async def _async_set_state(self, state: bool) -> None:
        """Send the new state to the Tdarr server."""
        if self._is_global():
            target = self.object_name
        else:
            node = self._find_node()
            if node is None:
                raise HomeAssistantError(
                    f"Cannot update {self.name}: node is offline"
                )
            target = node["_id"]

        try:
            await self.coordinator.hass.async_add_executor_job(
                self.coordinator.tdarr.pauseNode, target, state
            )
        except TdarrError as ex:
            raise HomeAssistantError(
                f"Failed to update {self.name}: {ex}"
            ) from ex

        # The Tdarr API can lag behind; show the new state until the next poll
        self._optimistic_state = state
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs):
        await self._async_set_state(True)

    async def async_turn_off(self, **kwargs):
        await self._async_set_state(False)

    def _handle_coordinator_update(self) -> None:
        self._optimistic_state = None
        super()._handle_coordinator_update()

    @property
    def available(self):
        if not super().available:
            return False
        if self._is_global():
            return True
        return self._find_node() is not None

    @property
    def is_on(self):
        if self._optimistic_state is not None:
            return self._optimistic_state
        if self.object_name == "pauseAll":
            return self.coordinator.data.get("globalsettings", {}).get("pauseAllNodes", False)
        if self.object_name == "ignoreSchedules":
            return self.coordinator.data.get("globalsettings", {}).get("ignoreSchedules", False)
        node = self._find_node()
        if node is not None:
            return node.get("nodePaused", False)
        return None

    @property
    def icon(self):
        return SWITCHES.get(self.object_name, {}).get("icon")
