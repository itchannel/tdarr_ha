"""Config flow for Tdarr integration."""
from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant import config_entries, core
from homeassistant.core import callback

from .const import (
    APIKEY,
    DOMAIN,
    LIBRARY_SCAN_INTERVAL,
    LIBRARY_SCAN_INTERVAL_DEFAULT,
    SERVERIP,
    SERVERPORT,
    UPDATE_INTERVAL,
    UPDATE_INTERVAL_DEFAULT,
    VERIFY_SSL,
)
from .tdarr import Server, TdarrAuthError, TdarrError

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(SERVERIP): str,
        vol.Optional(SERVERPORT, default="8265"): str,
        vol.Optional(APIKEY, default=""): str,
        vol.Optional(VERIFY_SSL, default=True): bool,
    }
)


async def validate_input(hass: core.HomeAssistant, data):
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    tdarr = Server(
        data[SERVERIP],
        data.get(SERVERPORT, ""),
        data.get(APIKEY, ""),
        data.get(VERIFY_SSL, True),
    )
    await hass.async_add_executor_job(tdarr.getSettings)

    # Return info that you want to store in the config entry.
    return {"title": f"Tdarr Server ({data[SERVERIP]})"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tdarr."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            user_input[SERVERIP] = user_input[SERVERIP].strip().rstrip("/")
            user_input[SERVERPORT] = user_input.get(SERVERPORT, "").strip()
            user_input[APIKEY] = user_input.get(APIKEY, "").strip()

            await self.async_set_unique_id(
                f"{user_input[SERVERIP]}:{user_input[SERVERPORT]}"
            )
            self._abort_if_unique_id_configured()

            try:
                info = await validate_input(self.hass, user_input)
            except TdarrAuthError:
                if user_input[APIKEY]:
                    errors["base"] = "invalid_apikey"
                else:
                    errors["base"] = "auth_required"
            except TdarrError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    async def async_step_reauth(self, entry_data):
        """Handle reauthentication when the API key is rejected."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        """Ask the user for a new API key."""
        errors = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            data = {**reauth_entry.data, APIKEY: user_input[APIKEY].strip()}
            try:
                await validate_input(self.hass, data)
            except TdarrAuthError:
                errors["base"] = "invalid_apikey"
            except TdarrError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(reauth_entry, data=data)

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(APIKEY): str}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlow()


class OptionsFlow(config_entries.OptionsFlow):
    """Handle the options flow for Tdarr."""

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            apikey = user_input.pop(APIKEY, "").strip()
            if apikey != self.config_entry.data.get(APIKEY, ""):
                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={**self.config_entry.data, APIKEY: apikey},
                )
            return self.async_create_entry(title="", data=user_input)

        options = {
            vol.Optional(
                UPDATE_INTERVAL,
                default=self.config_entry.options.get(
                    UPDATE_INTERVAL,
                    self.config_entry.data.get(
                        UPDATE_INTERVAL, UPDATE_INTERVAL_DEFAULT
                    ),
                ),
            ): vol.All(vol.Coerce(int), vol.Range(min=5)),
            vol.Optional(
                LIBRARY_SCAN_INTERVAL,
                default=self.config_entry.options.get(
                    LIBRARY_SCAN_INTERVAL, LIBRARY_SCAN_INTERVAL_DEFAULT
                ),
            ): vol.All(vol.Coerce(int), vol.Range(min=60)),
            vol.Optional(
                APIKEY,
                default=self.config_entry.data.get(APIKEY, ""),
            ): str,
        }

        return self.async_show_form(step_id="init", data_schema=vol.Schema(options))
