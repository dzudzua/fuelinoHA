"""Config flow for Fuelio."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_SCAN_INTERVAL, CONF_SOURCE_PATH, DEFAULT_SCAN_INTERVAL, DOMAIN


def _build_schema(
    default_path: str = "",
    default_scan_interval: int = DEFAULT_SCAN_INTERVAL,
) -> vol.Schema:
    """Build the config schema."""
    return vol.Schema(
        {
            vol.Required(CONF_SOURCE_PATH, default=default_path): str,
            vol.Optional(
                CONF_SCAN_INTERVAL, default=default_scan_interval
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=1440)),
        }
    )


class FuelioConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Fuelio."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._errors: dict[str, str] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            return await self._async_create_or_update_entry(user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=_build_schema(),
            errors=self._errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reconfiguration."""
        entry = self._get_reconfigure_entry()

        if user_input is not None:
            source_path = Path(user_input[CONF_SOURCE_PATH]).expanduser()
            if not _is_valid_source_path(source_path):
                return self.async_show_form(
                    step_id="reconfigure",
                    data_schema=_build_schema(
                        default_path=user_input[CONF_SOURCE_PATH],
                        default_scan_interval=user_input.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ),
                    errors={"base": "invalid_folder"},
                )

            normalized_path = str(source_path)
            await self.async_set_unique_id(normalized_path.lower())
            self._abort_if_unique_id_mismatch()

            return self.async_update_reload_and_abort(
                entry,
                data_updates={
                    CONF_SOURCE_PATH: normalized_path,
                    CONF_SCAN_INTERVAL: user_input.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                },
                reason="reconfigured",
            )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_build_schema(
                default_path=entry.data[CONF_SOURCE_PATH],
                default_scan_interval=entry.data.get(
                    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                ),
            ),
            errors=self._errors,
        )

    async def _async_create_or_update_entry(
        self, user_input: dict[str, Any], current_entry_id: str | None = None
    ) -> FlowResult:
        """Validate input and create the entry."""
        source_path = Path(user_input[CONF_SOURCE_PATH]).expanduser()
        if not _is_valid_source_path(source_path):
            return self.async_show_form(
                step_id="user" if current_entry_id is None else "reconfigure",
                data_schema=_build_schema(
                    default_path=user_input[CONF_SOURCE_PATH],
                    default_scan_interval=user_input.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                ),
                errors={"base": "invalid_folder"},
            )

        normalized_path = str(source_path)
        await self.async_set_unique_id(normalized_path.lower())

        if current_entry_id is None:
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=source_path.name or normalized_path,
                data={
                    CONF_SOURCE_PATH: normalized_path,
                    CONF_SCAN_INTERVAL: user_input.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                },
            )

        self._abort_if_unique_id_mismatch()
        return self.async_create_entry(title="", data={})

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow."""
        return FuelioOptionsFlow(config_entry)


class FuelioOptionsFlow(config_entries.OptionsFlow):
    """Handle Fuelio options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            source_path = Path(user_input[CONF_SOURCE_PATH]).expanduser()
            if not _is_valid_source_path(source_path):
                return self.async_show_form(
                    step_id="init",
                    data_schema=_build_schema(
                        default_path=user_input[CONF_SOURCE_PATH],
                        default_scan_interval=user_input.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ),
                    errors={"base": "invalid_folder"},
                )
            return self.async_create_entry(title="", data=user_input)

        current_path = self._config_entry.options.get(
            CONF_SOURCE_PATH, self._config_entry.data[CONF_SOURCE_PATH]
        )
        current_scan_interval = self._config_entry.options.get(
            CONF_SCAN_INTERVAL,
            self._config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )

        return self.async_show_form(
            step_id="init",
            data_schema=_build_schema(
                default_path=current_path,
                default_scan_interval=current_scan_interval,
            ),
        )


def _is_valid_source_path(path: Path) -> bool:
    """Validate configured source path."""
    if not path.exists():
        return False
    if path.is_dir():
        return True
    return path.is_file() and path.suffix.lower() == ".csv"
