"""Config flow for Fuelio."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries

from .const import CONF_SCAN_INTERVAL, CONF_SOURCE_PATH, DEFAULT_SCAN_INTERVAL, DOMAIN


def _user_schema(
    default_path: str = "",
    default_scan_interval: int = DEFAULT_SCAN_INTERVAL,
) -> vol.Schema:
    """Return the user step schema."""
    return vol.Schema(
        {
            vol.Required(CONF_SOURCE_PATH, default=default_path): str,
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=default_scan_interval,
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=1440)),
        }
    )


class FuelioConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Fuelio."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=_user_schema(),
            )

        source_path = user_input.get(CONF_SOURCE_PATH, "").strip()
        if not source_path:
            return self.async_show_form(
                step_id="user",
                data_schema=_user_schema(
                    default_path=user_input.get(CONF_SOURCE_PATH, ""),
                    default_scan_interval=user_input.get(
                        CONF_SCAN_INTERVAL,
                        DEFAULT_SCAN_INTERVAL,
                    ),
                ),
                errors={"base": "invalid_source_path"},
            )

        await self.async_set_unique_id(source_path.lower())
        self._abort_if_unique_id_configured()

        title = source_path.replace("\\", "/").rstrip("/").split("/")[-1] or source_path
        return self.async_create_entry(
            title=title,
            data={
                CONF_SOURCE_PATH: source_path,
                CONF_SCAN_INTERVAL: user_input.get(
                    CONF_SCAN_INTERVAL,
                    DEFAULT_SCAN_INTERVAL,
                ),
            },
        )
