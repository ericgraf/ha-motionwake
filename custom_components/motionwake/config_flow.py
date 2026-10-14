"""Config flow for MotionWake."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigEntry, OptionsFlow
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .client import MotionWakeAuthError, MotionWakeClient, MotionWakeError
from .const import CONF_HOST, CONF_PORT, CONF_TOKEN, DEFAULT_PORT, DOMAIN

_LOGGER = logging.getLogger(__package__)

USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_TOKEN): str,
    }
)


class MotionWakeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MotionWake."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial user config step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = int(user_input[CONF_PORT])
            token = user_input[CONF_TOKEN].strip()

            # Reject a duplicate tablet in this instance.
            await self.async_set_unique_id(f"{host}:{port}")
            self._abort_if_unique_id_configured()

            try:
                async with aiohttp.ClientSession() as session:
                    client = MotionWakeClient(session, host, port, token)
                    data = await client.get_status()
            except MotionWakeAuthError:
                errors["base"] = "invalid_auth"
            except MotionWakeError:
                errors["base"] = "cannot_connect"
            else:
                _LOGGER.debug("MotionWake validated: %r", data.get("version"))
                return self.async_create_entry(
                    title=f"{host}:{port}",
                    data={
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_TOKEN: token,
                    },
                )

        return self.async_show_form(
            step_id="user", data_schema=USER_SCHEMA, errors=errors
        )

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> MotionWakeOptionsFlow:
        """Return the options flow."""
        return MotionWakeOptionsFlow()


class MotionWakeOptionsFlow(OptionsFlow):
    """Handle options (host / port / token)."""

    async def async_step_init(self, user_input=None) -> FlowResult:
        """Handle the options flow."""
        errors: dict[str, str] = {}
        entry = self.config_entry
        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            port = int(user_input[CONF_PORT])
            token = user_input[CONF_TOKEN].strip()
            try:
                async with aiohttp.ClientSession() as session:
                    client = MotionWakeClient(session, host, port, token)
                    await client.get_status()
            except MotionWakeAuthError:
                errors["base"] = "invalid_auth"
            except MotionWakeError:
                errors["base"] = "cannot_connect"
            else:
                await self._async_update_flow(
                    {
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_TOKEN: token,
                    }
                )
                return self.async_create_entry(title="", data={})
        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=entry.data.get(CONF_HOST, "")): str,
                vol.Required(
                    CONF_PORT, default=int(entry.data.get(CONF_PORT, DEFAULT_PORT))
                ): int,
                vol.Required(CONF_TOKEN, default=entry.data.get(CONF_TOKEN, "")): str,
            }
        )
        return self.async_show_form(
            step_id="init", data_schema=schema, errors=errors
        )

    async def _async_update_flow(self, updates: dict[str, Any]) -> None:
        """Update entry + reload (delegated to the flow helper)."""
        entry = self.config_entry
        data = {**entry.data, **updates}
        self.hass.config_entries.async_update_entry(entry, data=data)
        await self.hass.config_entries.async_reload(entry.entry_id)
