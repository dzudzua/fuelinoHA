"""The Fuelio integration."""

from __future__ import annotations

import secrets
from pathlib import Path

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DEFAULT_UPLOAD_FOLDER, DOMAIN, PANEL_URL_PATH, PLATFORMS


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Fuelio integration."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["upload_token"] = secrets.token_urlsafe(32)
    hass.http.register_view(FuelioUploadView(hass))
    hass.http.register_view(FuelioUploadPageView(hass))
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


class FuelioUploadView(HomeAssistantView):
    """Handle CSV uploads for Fuelio."""

    url = "/api/fuelio/upload"
    name = "api:fuelio:upload"
    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the upload view."""
        self.hass = hass

    async def post(self, request: web.Request) -> web.Response:
        """Save an uploaded CSV file into the HA config folder."""
        expected_token = self.hass.data.get(DOMAIN, {}).get("upload_token")
        provided_token = request.headers.get("X-Fuelio-Upload-Token")
        if not expected_token or provided_token != expected_token:
            return web.json_response({"error": "unauthorized"}, status=401)

        try:
            data = await request.post()
        except Exception as err:
            return web.json_response(
                {"error": "invalid_form_data", "detail": str(err)},
                status=400,
            )
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


class FuelioUploadPageView(HomeAssistantView):
    """Serve a simple authenticated upload page."""

    url = "/api/fuelio/upload-page"
    extra_urls = [f"/{PANEL_URL_PATH}"]
    name = "fuelio:upload_page"
    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the upload page view."""
        self.hass = hass

    async def get(self, request: web.Request) -> web.Response:
        """Return the upload page HTML."""
        upload_folder = self.hass.config.path(DEFAULT_UPLOAD_FOLDER)
        upload_token = self.hass.data.get(DOMAIN, {}).get("upload_token", "")
        html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Fuelio Upload</title>
  <style>
    body {{
      margin: 0;
      font-family: Arial, sans-serif;
      background: #111827;
      color: #f3f4f6;
    }}
    .wrap {{
      max-width: 720px;
      margin: 40px auto;
      padding: 24px;
    }}
    .card {{
      background: #1f2937;
      border-radius: 16px;
      padding: 24px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
    }}
    .path {{
      background: #0f172a;
      padding: 12px;
      border-radius: 10px;
      font-family: monospace;
      margin: 16px 0 20px;
      word-break: break-all;
    }}
    input[type=file] {{
      display: block;
      margin-bottom: 16px;
      color: #f3f4f6;
    }}
    button {{
      background: #2563eb;
      border: 0;
      color: white;
      padding: 12px 18px;
      border-radius: 10px;
      cursor: pointer;
      font-size: 16px;
    }}
    #status {{
      margin-top: 18px;
      padding: 12px;
      border-radius: 10px;
      background: #0f172a;
      white-space: pre-wrap;
    }}
    a {{
      color: #93c5fd;
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1>Fuelio CSV Upload</h1>
      <p>Nahraj CSV export z pocitace nebo telefonu primo do Home Assistantu.</p>
      <div class="path">{upload_folder}</div>
      <input id="file" type="file" accept=".csv,text/csv">
      <button id="upload">Upload CSV</button>
      <div id="status">Pripraveno k uploadu.</div>
    </div>
  </div>
  <script>
    const uploadToken = {upload_token!r};
    const status = document.getElementById("status");
    document.getElementById("upload").addEventListener("click", async () => {{
      const file = document.getElementById("file").files[0];
      if (!file) {{
        status.textContent = "Vyber CSV soubor.";
        return;
      }}
      const formData = new FormData();
      formData.append("file", file, file.name);
      status.textContent = "Nahravam...";
      try {{
        const response = await fetch("/api/fuelio/upload", {{
          method: "POST",
          body: formData,
          headers: {{
            "X-Fuelio-Upload-Token": uploadToken
          }},
        }});
        const rawText = await response.text();
        let result;
        try {{
          result = JSON.parse(rawText);
        }} catch (parseError) {{
          throw new Error("Ne-JSON odpoved: " + rawText.slice(0, 300));
        }}
        if (!response.ok) {{
          throw new Error(
            (result.error || "upload_failed") +
            (result.detail ? " - " + result.detail : "")
          );
        }}
        status.textContent = "Hotovo.\\nUlozeno do: " + result.saved_path;
      }} catch (err) {{
        status.textContent = "Upload selhal: " + err.message;
      }}
    }});
  </script>
</body>
</html>"""
        return web.Response(text=html, content_type="text/html")


def _save_uploaded_csv(upload_folder: str, filename: str, file_bytes: bytes) -> str:
    """Persist an uploaded CSV file to the HA config folder."""
    folder_path = Path(upload_folder)
    folder_path.mkdir(parents=True, exist_ok=True)
    destination = folder_path / filename
    destination.write_bytes(file_bytes)
    return str(destination)
