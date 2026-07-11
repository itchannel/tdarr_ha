"""Diagnostics support for Tdarr."""
from __future__ import annotations

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import APIKEY, COORDINATOR, DOMAIN, SERVERIP

TO_REDACT = {APIKEY, SERVERIP, "serverIP", "serverURL", "nodeIP", "ip"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict:
    """Return diagnostics for a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]

    return {
        "entry_data": async_redact_data(dict(entry.data), TO_REDACT),
        "options": dict(entry.options),
        "data": async_redact_data(coordinator.data, TO_REDACT),
    }
