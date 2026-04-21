"""Config flow for Fuelio."""

from __future__ import annotations

import voluptuous as vol
from homeassistant.helpers import selector

from homeassistant import config_entries

from .const import (
    CONF_REMOTE_CSV_URL,
    CONF_SCAN_INTERVAL,
    CONF_SOURCE_PATH,
    CONF_SOURCE_TYPE,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    SOURCE_TYPE_LOCAL,
    SOURCE_TYPE_REMOTE_URL,
)

def _user_schema(
    default_source_type: str = SOURCE_TYPE_LOCAL,
    default_path: str = "",
    default_url: str = "",
    default_scan_interval: int = DEFAULT_SCAN_INTERVAL,
) -> vol.Schema:
    """Return the single-step setup schema."""
    return vol.Schema(
        {
            vol.Required(CONF_SOURCE_TYPE, default=default_source_type): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        selector.SelectOptionDict(
                            value=SOURCE_TYPE_LOCAL,
                            label="Local file or folder",
                        ),
                        selector.SelectOptionDict(
                            value=SOURCE_TYPE_REMOTE_URL,
                            label="Dropbox / remote CSV URL",
                        ),
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(CONF_SOURCE_PATH, default=default_path): str,
            vol.Optional(CONF_REMOTE_CSV_URL, default=default_url): str,
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

        source_type = user_input.get(CONF_SOURCE_TYPE, SOURCE_TYPE_LOCAL)
        scan_interval = user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        remote_url = user_input.get(CONF_REMOTE_CSV_URL, "").strip()
        source_path = user_input.get(CONF_SOURCE_PATH, "").strip()

        if source_type == SOURCE_TYPE_REMOTE_URL:
            if not remote_url or not remote_url.lower().startswith(("http://", "https://")):
                return self.async_show_form(
                    step_id="user",
                    data_schema=_user_schema(
                        default_source_type=source_type,
                        default_path=source_path,
                        default_url=remote_url,
                        default_scan_interval=scan_interval,
                    ),
                    errors={"base": "invalid_remote_url"},
                )

            await self.async_set_unique_id(remote_url.lower())
            self._abort_if_unique_id_configured()

            title = remote_url.split("?")[0].rstrip("/").split("/")[-1] or "remote_csv"
            return self.async_create_entry(
                title=title,
                data={
                    CONF_SOURCE_TYPE: SOURCE_TYPE_REMOTE_URL,
                    CONF_REMOTE_CSV_URL: remote_url,
                    CONF_SCAN_INTERVAL: scan_interval,
                },
            )

        if not source_path:
            return self.async_show_form(
                step_id="user",
                data_schema=_user_schema(
                    default_source_type=source_type,
                    default_path=source_path,
                    default_url=remote_url,
                    default_scan_interval=scan_interval,
                ),
                errors={"base": "invalid_source_path"},
            )

        await self.async_set_unique_id(source_path.lower())
        self._abort_if_unique_id_configured()

        title = source_path.replace("\\", "/").rstrip("/").split("/")[-1] or source_path
        return self.async_create_entry(
            title=title,
            data={
                CONF_SOURCE_TYPE: SOURCE_TYPE_LOCAL,
                CONF_SOURCE_PATH: source_path,
                CONF_SCAN_INTERVAL: scan_interval,
            },
        )
