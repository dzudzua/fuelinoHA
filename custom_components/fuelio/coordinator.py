"""Coordinator for Fuelio data updates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import CONF_SCAN_INTERVAL, CONF_SOURCE_PATH, DEFAULT_SCAN_INTERVAL, DOMAIN
from .parser import ParsedVehicle, parse_vehicle_file

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
    def source_path(self) -> Path:
        """Return the configured source path."""
        configured = self.config_entry.options.get(
            CONF_SOURCE_PATH, self.config_entry.data[CONF_SOURCE_PATH]
        )
        return Path(configured).expanduser()

    async def _async_update_data(self) -> FuelioData:
        """Read and parse the configured CSV files."""
        source_path = self.source_path
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
