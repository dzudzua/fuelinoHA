"""Coordinator for Fuelio data updates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
import logging
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

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
from .parser import ParsedVehicle, parse_vehicle_file, parse_vehicle_text

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class FuelioData:
    """Coordinator payload."""

    vehicles: dict[str, ParsedVehicle]
    source_files: list[str]


class FuelioDataUpdateCoordinator(DataUpdateCoordinator[FuelioData]):
    """Fetch and cache Fuelio CSV data."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.config_entry = config_entry
        scan_interval = (
            config_entry.options.get(CONF_SCAN_INTERVAL)
            or config_entry.data.get(CONF_SCAN_INTERVAL)
            or DEFAULT_SCAN_INTERVAL
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=scan_interval),
        )

    @property
    def source_path(self) -> Path | None:
        """Return the configured local source path, if any."""
        configured = self.config_entry.options.get(
            CONF_SOURCE_PATH,
            self.config_entry.data.get(CONF_SOURCE_PATH),
        )
        if not configured:
            return None
        path = Path(configured).expanduser()
        if path.is_absolute():
            return path
        return Path(self.hass.config.path(configured))

    @property
    def source_type(self) -> str:
        """Return the configured source type."""
        return self.config_entry.options.get(
            CONF_SOURCE_TYPE,
            self.config_entry.data.get(CONF_SOURCE_TYPE, SOURCE_TYPE_LOCAL),
        )

    @property
    def remote_csv_url(self) -> str | None:
        """Return the configured remote CSV URL."""
        return self.config_entry.options.get(
            CONF_REMOTE_CSV_URL,
            self.config_entry.data.get(CONF_REMOTE_CSV_URL),
        )

    @property
    def source_label(self) -> str:
        """Return a human-readable source label."""
        if self.source_type == SOURCE_TYPE_REMOTE_URL:
            return self.remote_csv_url or "remote_csv_url"
        source_path = self.source_path
        return str(source_path) if source_path is not None else "unknown"

    async def _async_update_data(self) -> FuelioData:
        """Read and parse the configured CSV files."""
        if self.source_type == SOURCE_TYPE_REMOTE_URL:
            return await self._async_update_remote_data()

        source_path = self.source_path
        if source_path is None:
            return FuelioData(vehicles={}, source_files=[])
        if not source_path.exists():
            return FuelioData(vehicles={}, source_files=[])

        if source_path.is_file():
            csv_files = [source_path] if source_path.suffix.lower() == ".csv" else []
        else:
            csv_files = sorted(source_path.glob("vehicle-*-sync.csv"))
            if not csv_files:
                csv_files = sorted(source_path.glob("*.csv"))

        vehicles: dict[str, ParsedVehicle] = {}
        latest_mtimes: dict[str, float] = {}
        for csv_file in csv_files:
            parsed = await self.hass.async_add_executor_job(parse_vehicle_file, csv_file)
            if parsed is None:
                continue
            file_mtime = csv_file.stat().st_mtime
            previous_mtime = latest_mtimes.get(parsed.key)
            if previous_mtime is None or file_mtime >= previous_mtime:
                latest_mtimes[parsed.key] = file_mtime
                vehicles[parsed.key] = parsed

        return FuelioData(
            vehicles=vehicles,
            source_files=[str(path) for path in csv_files],
        )

    async def _async_update_remote_data(self) -> FuelioData:
        """Download and parse a remote CSV source."""
        remote_url = self.remote_csv_url
        if not remote_url:
            return FuelioData(vehicles={}, source_files=[])

        download_url = _normalize_remote_csv_url(remote_url)
        session = async_get_clientsession(self.hass)
        async with session.get(download_url, allow_redirects=True) as response:
            response.raise_for_status()
            text = await response.text(encoding="utf-8-sig", errors="ignore")

        parsed = await self.hass.async_add_executor_job(
            parse_vehicle_text,
            remote_url,
            text,
        )
        if parsed is None:
            return FuelioData(vehicles={}, source_files=[remote_url])

        return FuelioData(
            vehicles={parsed.key: parsed},
            source_files=[remote_url],
        )


def _normalize_remote_csv_url(url: str) -> str:
    """Normalize supported remote CSV URLs for direct download."""
    parsed = urlparse(url)
    if "dropbox.com" not in parsed.netloc.lower():
        return url

    query_items = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query_items["dl"] = "1"
    return urlunparse(parsed._replace(query=urlencode(query_items)))
