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


def _source_type_schema(default_source_type: str = SOURCE_TYPE_LOCAL) -> vol.Schema:
    """Return the source-type selection schema."""
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
            )
        }
    )


def _local_schema(
    default_path: str = "",
    default_scan_interval: int = DEFAULT_SCAN_INTERVAL,
) -> vol.Schema:
    """Return the local-source schema."""
    return vol.Schema(
        {
            vol.Required(CONF_SOURCE_PATH, default=default_path): str,
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=default_scan_interval,
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=1440)),
        }
    )


def _remote_schema(
    default_url: str = "",
    default_scan_interval: int = DEFAULT_SCAN_INTERVAL,
) -> vol.Schema:
    """Return the remote URL schema."""
    return vol.Schema(
        {
            vol.Required(CONF_REMOTE_CSV_URL, default=default_url): str,
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
                data_schema=_source_type_schema(),
            )

        source_type = user_input.get(CONF_SOURCE_TYPE, SOURCE_TYPE_LOCAL)
        if source_type == SOURCE_TYPE_REMOTE_URL:
            return await self.async_step_remote()
        return await self.async_step_local()

    async def async_step_local(self, user_input=None):
        """Handle local CSV path setup."""
        if user_input is None:
            return self.async_show_form(
                step_id="local",
                data_schema=_local_schema(),
            )

        source_path = user_input.get(CONF_SOURCE_PATH, "").strip()
        if not source_path:
            return self.async_show_form(
                step_id="local",
                data_schema=_local_schema(
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
                CONF_SOURCE_TYPE: SOURCE_TYPE_LOCAL,
                CONF_SOURCE_PATH: source_path,
                CONF_SCAN_INTERVAL: user_input.get(
                    CONF_SCAN_INTERVAL,
                    DEFAULT_SCAN_INTERVAL,
                ),
            },
        )

    async def async_step_remote(self, user_input=None):
        """Handle remote CSV URL setup."""
        if user_input is None:
            return self.async_show_form(
                step_id="remote",
                data_schema=_remote_schema(),
            )

        remote_url = user_input.get(CONF_REMOTE_CSV_URL, "").strip()
        if not remote_url or not remote_url.lower().startswith(("http://", "https://")):
            return self.async_show_form(
                step_id="remote",
                data_schema=_remote_schema(
                    default_url=user_input.get(CONF_REMOTE_CSV_URL, ""),
                    default_scan_interval=user_input.get(
                        CONF_SCAN_INTERVAL,
                        DEFAULT_SCAN_INTERVAL,
                    ),
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
                CONF_SCAN_INTERVAL: user_input.get(
                    CONF_SCAN_INTERVAL,
                    DEFAULT_SCAN_INTERVAL,
                ),
            },
        )
