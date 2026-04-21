"""Button platform for Fuelio."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.components.persistent_notification import async_create
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.network import NoURLAvailableError, get_url
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PANEL_URL_PATH
from .coordinator import FuelioDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class FuelioButtonDescription(ButtonEntityDescription):
    """Fuelio button entity description."""

    press_fn: Any


BUTTONS: tuple[FuelioButtonDescription, ...] = (
    FuelioButtonDescription(
        key="open_upload_page",
        translation_key="open_upload_page",
        icon="mdi:file-upload-outline",
        press_fn=lambda entity: entity.async_show_upload_help(),
    ),
    FuelioButtonDescription(
        key="reload_data",
        translation_key="reload_data",
        icon="mdi:reload",
        press_fn=lambda entity: entity.coordinator.async_request_refresh(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Fuelio buttons."""
    coordinator: FuelioDataUpdateCoordinator = entry.runtime_data
    async_add_entities(
        FuelioButton(coordinator, entry, description) for description in BUTTONS
    )


class FuelioButton(CoordinatorEntity[FuelioDataUpdateCoordinator], ButtonEntity):
    """Fuelio action button."""

    entity_description: FuelioButtonDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FuelioDataUpdateCoordinator,
        entry: ConfigEntry,
        description: FuelioButtonDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self.entity_description = description
        self._entry = entry
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_{description.key}"

    @property
    def device_info(self) -> dict[str, Any]:
        """Return integration-level device info."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id, "hub")},
            "name": "Fuelio",
            "manufacturer": "Fuelio",
            "model": "CSV Import",
        }

    async def async_press(self) -> None:
        """Handle button press."""
        result = self.entity_description.press_fn(self)
        if result is not None:
            await result

    async def async_show_upload_help(self) -> None:
        """Show upload instructions inside Home Assistant."""
        upload_path = "/api/fuelio/upload-page"
        try:
            base_url = get_url(self.hass)
            upload_url = f"{base_url}{upload_path}"
        except NoURLAvailableError:
            upload_url = upload_path
        source_path = self.coordinator.source_label
        message = (
            "Open the Fuelio upload page and upload a CSV export.\n\n"
            f"[Open Fuelio upload page]({upload_url})\n\n"
            f"Upload page: `{upload_url}`\n"
            f"Configured source: `{source_path}`\n\n"
            "If a normal click opens the Home Assistant dashboard instead, open "
            "the link in a new tab.\n\n"
            "Recommended workflow: close the setup form, then use this helper to "
            "open the upload page or use a stable Dropbox shared file link for "
            "remote CSV mode."
        )
        async_create(
            self.hass,
            message,
            title="Fuelio Upload",
            notification_id=f"{DOMAIN}_upload_help_{self._entry.entry_id}",
        )
