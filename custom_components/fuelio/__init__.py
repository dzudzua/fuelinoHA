"""The Fuelio integration."""

from __future__ import annotations

from pathlib import Path

from aiohttp import web

from homeassistant.components.frontend import async_register_built_in_panel
from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DEFAULT_UPLOAD_FOLDER, DOMAIN, PANEL_MODULE_URL, PANEL_URL_PATH, PLATFORMS

_PANEL_JS_PATH = Path(__file__).with_name("panel.js")


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Fuelio integration."""
    hass.data.setdefault(DOMAIN, {})
    hass.http.register_view(FuelioUploadPanelJsView(hass))
    hass.http.register_view(FuelioUploadView(hass))
    async_register_built_in_panel(
        hass,
        component_name="custom",
        frontend_url_path=PANEL_URL_PATH,
        module_url=PANEL_MODULE_URL,
        sidebar_title="Fuelio Upload",
        sidebar_icon="mdi:file-upload-outline",
        require_admin=True,
        config={"upload_folder": hass.config.path(DEFAULT_UPLOAD_FOLDER)},
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Fuelio from a config entry."""
    from .coordinator import FuelioDataUpdateCoordinator

    coordinator = FuelioDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    hass.data[DOMAIN][entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded


class FuelioUploadPanelJsView(HomeAssistantView):
    """Serve the Fuelio upload panel JavaScript."""

    url = PANEL_MODULE_URL
    name = "api:fuelio:upload_panel_js"
    requires_auth = True

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the panel JS view."""
        self.hass = hass

    async def get(self, request: web.Request) -> web.Response:
        """Return the panel JavaScript."""
        content = await self.hass.async_add_executor_job(
            _PANEL_JS_PATH.read_text,
            "utf-8",
        )
        return web.Response(text=content, content_type="text/javascript")


class FuelioUploadView(HomeAssistantView):
    """Handle CSV uploads for Fuelio."""

    url = "/api/fuelio/upload"
    name = "api:fuelio:upload"
    requires_auth = True

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the upload view."""
        self.hass = hass

    async def post(self, request: web.Request) -> web.Response:
        """Save an uploaded CSV file into the HA config folder."""
        data = await request.post()
        uploaded = data.get("file")
        if uploaded is None or not getattr(uploaded, "filename", ""):
            return web.json_response({"error": "missing_file"}, status=400)

        filename = Path(uploaded.filename).name
        if not filename.lower().endswith(".csv"):
            return web.json_response({"error": "invalid_extension"}, status=400)

        file_bytes = uploaded.file.read()
        saved_path = await self.hass.async_add_executor_job(
            _save_uploaded_csv,
            self.hass.config.path(DEFAULT_UPLOAD_FOLDER),
            filename,
            file_bytes,
        )

        for coordinator in self.hass.data.get(DOMAIN, {}).values():
            await coordinator.async_request_refresh()

        return web.json_response(
            {
                "filename": filename,
                "saved_path": saved_path,
            }
        )


def _save_uploaded_csv(upload_folder: str, filename: str, file_bytes: bytes) -> str:
    """Persist an uploaded CSV file to the HA config folder."""
    folder_path = Path(upload_folder)
    folder_path.mkdir(parents=True, exist_ok=True)
    destination = folder_path / filename
    destination.write_bytes(file_bytes)
    return str(destination)
