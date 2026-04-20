"""Diagnostics support for Fuelio."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .coordinator import FuelioDataUpdateCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict:
    """Return diagnostics for a config entry."""
    coordinator: FuelioDataUpdateCoordinator = entry.runtime_data

    vehicles: dict[str, dict] = {}
    for key, vehicle in coordinator.data.vehicles.items():
        latest_fill = vehicle.records[-1] if vehicle.records else None
        latest_expense = vehicle.expenses[-1] if vehicle.expenses else None
        latest_trip = vehicle.trips[-1] if vehicle.trips else None
        vehicles[key] = {
            "name": vehicle.name,
            "source_file": vehicle.source_file,
            "record_count": len(vehicle.records),
            "expense_count": len(vehicle.expenses),
            "trip_count": len(vehicle.trips),
            "currency": vehicle.currency,
            "fuel_unit": vehicle.fuel_unit,
            "distance_unit": vehicle.distance_unit,
            "make": vehicle.make,
            "model": vehicle.model,
            "year": vehicle.year,
            "latest_fill": {
                "date": latest_fill.occurred_on.isoformat() if latest_fill else None,
                "cost": latest_fill.cost if latest_fill else None,
                "volume": latest_fill.volume if latest_fill else None,
                "odometer": latest_fill.odometer if latest_fill else None,
            },
            "latest_expense": {
                "date": latest_expense.occurred_on.isoformat()
                if latest_expense
                else None,
                "title": latest_expense.title if latest_expense else None,
                "category": latest_expense.category_name if latest_expense else None,
                "cost": latest_expense.cost if latest_expense else None,
            },
            "latest_trip": {
                "date": latest_trip.started_on.isoformat() if latest_trip else None,
                "title": latest_trip.title if latest_trip else None,
                "distance_km": latest_trip.distance_km if latest_trip else None,
                "trip_cost": latest_trip.trip_cost if latest_trip else None,
            },
            "cost_categories": vehicle.cost_categories,
        }

    return {
        "entry": {
            "entry_id": entry.entry_id,
            "title": entry.title,
            "data": dict(entry.data),
            "options": dict(entry.options),
        },
        "resolved_source_path": str(coordinator.source_path),
        "source_files": coordinator.data.source_files,
        "vehicle_count": len(coordinator.data.vehicles),
        "vehicles": vehicles,
    }
