"""Constants for the Fuelio integration."""

from __future__ import annotations

DOMAIN = "fuelio"

CONF_SOURCE_PATH = "source_path"
CONF_SOURCE_TYPE = "source_type"
CONF_REMOTE_CSV_URL = "remote_csv_url"
CONF_SCAN_INTERVAL = "scan_interval"
SERVICE_RELOAD = "reload"

SOURCE_TYPE_LOCAL = "local"
SOURCE_TYPE_REMOTE_URL = "remote_csv_url"

DEFAULT_SCAN_INTERVAL = 60
PLATFORMS = ["sensor", "button"]
DEFAULT_UPLOAD_FOLDER = "fuelino"
PANEL_URL_PATH = "fuelio-upload"
