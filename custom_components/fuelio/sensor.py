"""Sensor platform for Fuelio."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FuelioDataUpdateCoordinator
from .parser import ParsedVehicle


@dataclass(frozen=True, kw_only=True)
class FuelioSensorDescription(SensorEntityDescription):
    """Fuelio sensor entity description."""

    value_fn: Any


SENSORS: tuple[FuelioSensorDescription, ...] = (
    FuelioSensorDescription(
        key="last_fill_date",
        translation_key="last_fill_date",
        device_class=SensorDeviceClass.DATE,
        value_fn=lambda vehicle: vehicle.records[-1].occurred_on,
    ),
    FuelioSensorDescription(
        key="days_since_fill",
        translation_key="days_since_fill",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="d",
        value_fn=lambda vehicle: (date.today() - vehicle.records[-1].occurred_on).days,
    ),
    FuelioSensorDescription(
        key="last_fill_volume",
        translation_key="last_fill_volume",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="L",
        suggested_display_precision=2,
        value_fn=lambda vehicle: vehicle.records[-1].volume,
    ),
    FuelioSensorDescription(
        key="last_fill_cost",
        translation_key="last_fill_cost",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda vehicle: vehicle.records[-1].cost,
    ),
    FuelioSensorDescription(
        key="last_price_per_unit",
        translation_key="last_price_per_unit",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda vehicle: vehicle.records[-1].price_per_unit,
    ),
    FuelioSensorDescription(
        key="last_consumption",
        translation_key="last_consumption",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda vehicle: vehicle.records[-1].consumption,
    ),
    FuelioSensorDescription(
        key="odometer",
        translation_key="odometer",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        suggested_display_precision=1,
        value_fn=lambda vehicle: vehicle.records[-1].odometer,
    ),
    FuelioSensorDescription(
        key="distance_since_previous_fill",
        translation_key="distance_since_previous_fill",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        suggested_display_precision=1,
        value_fn=lambda vehicle: _distance_since_previous_fill(vehicle),
    ),
    FuelioSensorDescription(
        key="tracked_distance",
        translation_key="tracked_distance",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        suggested_display_precision=1,
        value_fn=lambda vehicle: _tracked_distance(vehicle),
    ),
    FuelioSensorDescription(
        key="fill_count",
        translation_key="fill_count",
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda vehicle: len(vehicle.records),
    ),
    FuelioSensorDescription(
        key="cost_30d",
        translation_key="cost_30d",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda vehicle: _sum_cost_since_days(vehicle, 30),
    ),
    FuelioSensorDescription(
        key="total_cost",
        translation_key="total_cost",
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        value_fn=lambda vehicle: _sum_record_values(vehicle, "cost"),
    ),
    FuelioSensorDescription(
        key="total_volume",
        translation_key="total_volume",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement="L",
        suggested_display_precision=2,
        value_fn=lambda vehicle: _sum_record_values(vehicle, "volume"),
    ),
    FuelioSensorDescription(
        key="average_price",
        translation_key="average_price",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda vehicle: _average_price(vehicle),
    ),
    FuelioSensorDescription(
        key="average_consumption",
        translation_key="average_consumption",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=lambda vehicle: _average_record_values(vehicle, "consumption"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Fuelio sensor entities."""
    coordinator: FuelioDataUpdateCoordinator = entry.runtime_data
    known_entities: set[tuple[str, str]] = set()

    @callback
    def async_add_missing_entities() -> None:
        new_entities: list[FuelioSensor] = []
        for vehicle_key, vehicle in coordinator.data.vehicles.items():
            for description in SENSORS:
                entity_key = (vehicle_key, description.key)
                if entity_key in known_entities:
                    continue
                known_entities.add(entity_key)
                new_entities.append(FuelioSensor(coordinator, vehicle_key, description))

        if new_entities:
            async_add_entities(new_entities)

    async_add_missing_entities()
    entry.async_on_unload(coordinator.async_add_listener(async_add_missing_entities))


class FuelioSensor(CoordinatorEntity[FuelioDataUpdateCoordinator], SensorEntity):
    """Representation of a Fuelio sensor."""

    entity_description: FuelioSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FuelioDataUpdateCoordinator,
        vehicle_key: str,
        description: FuelioSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._vehicle_key = vehicle_key
        self._attr_unique_id = f"{DOMAIN}_{vehicle_key}_{description.key}"

    @property
    def vehicle(self) -> ParsedVehicle:
        """Return parsed vehicle data."""
        return self.coordinator.data.vehicles[self._vehicle_key]

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device info for the vehicle."""
        return {
            "identifiers": {(DOMAIN, self._vehicle_key)},
            "name": self.vehicle.name,
            "manufacturer": "Fuelio",
            "model": self.vehicle.model or "CSV Import",
            "model_year": self.vehicle.year,
        }

    @property
    def name(self) -> str | None:
        """Return entity name."""
        return self.entity_description.translation_key.replace("_", " ").title()

    @property
    def native_value(self) -> date | Decimal | float | int | None:
        """Return the current native value."""
        return self.entity_description.value_fn(self.vehicle)

    @property
    def available(self) -> bool:
        """Return entity availability."""
        return self._vehicle_key in self.coordinator.data.vehicles

    @property
    def suggested_unit_of_measurement(self) -> str | None:
        """Return per-vehicle currency when relevant."""
        if self.entity_description.key in {"last_fill_cost", "total_cost"}:
            return self.vehicle.currency
        if self.entity_description.key == "cost_30d":
            return self.vehicle.currency
        if self.entity_description.key in {"last_price_per_unit", "average_price"}:
            if self.vehicle.currency:
                unit = self.vehicle.fuel_unit or "L"
                return f"{self.vehicle.currency}/{unit}"
        if self.entity_description.key in {"last_fill_volume", "total_volume"}:
            return self.vehicle.fuel_unit or "L"
        if self.entity_description.key in {
            "odometer",
            "distance_since_previous_fill",
            "tracked_distance",
        }:
            if self.vehicle.distance_unit == "mi":
                return UnitOfLength.MILES
            if self.vehicle.distance_unit == "km":
                return UnitOfLength.KILOMETERS
        if self.entity_description.key in {"last_consumption", "average_consumption"}:
            fuel_unit = self.vehicle.fuel_unit or "L"
            distance_unit = self.vehicle.distance_unit or "km"
            return f"{fuel_unit}/100 {distance_unit}"
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return diagnostic attributes."""
        latest = self.vehicle.records[-1]
        attrs: dict[str, Any] = {
            "source_file": self.vehicle.source_file,
            "record_count": len(self.vehicle.records),
            "latest_record_date": latest.occurred_on.isoformat(),
            "fuel_unit": self.vehicle.fuel_unit,
            "distance_unit": self.vehicle.distance_unit,
        }
        if self.vehicle.make is not None:
            attrs["make"] = self.vehicle.make
        if self.vehicle.model is not None:
            attrs["model"] = self.vehicle.model
        if self.vehicle.year is not None:
            attrs["year"] = self.vehicle.year
        if latest.odometer is not None:
            attrs["latest_odometer"] = latest.odometer
        if latest.volume is not None:
            attrs["latest_volume"] = latest.volume
        if latest.cost is not None:
            attrs["latest_cost"] = latest.cost
        if latest.consumption is not None:
            attrs["latest_consumption"] = latest.consumption
        return attrs


def _sum_record_values(vehicle: ParsedVehicle, field: str) -> float | None:
    """Sum numeric record values."""
    values = [
        getattr(record, field)
        for record in vehicle.records
        if getattr(record, field) is not None
    ]
    if not values:
        return None
    return round(sum(values), 3)


def _average_price(vehicle: ParsedVehicle) -> float | None:
    """Calculate average price per liter from totals."""
    total_cost = _sum_record_values(vehicle, "cost")
    total_volume = _sum_record_values(vehicle, "volume")
    if not total_cost or not total_volume:
        return None
    return round(total_cost / total_volume, 3)


def _average_record_values(vehicle: ParsedVehicle, field: str) -> float | None:
    """Calculate an average across available record values."""
    values = [
        getattr(record, field)
        for record in vehicle.records
        if getattr(record, field) is not None
    ]
    if not values:
        return None
    return round(sum(values) / len(values), 3)


def _distance_since_previous_fill(vehicle: ParsedVehicle) -> float | None:
    """Return the odometer delta between the last two fill records."""
    if len(vehicle.records) < 2:
        return None

    latest = vehicle.records[-1].odometer
    previous = vehicle.records[-2].odometer
    if latest is None or previous is None:
        return None
    return round(latest - previous, 3)


def _tracked_distance(vehicle: ParsedVehicle) -> float | None:
    """Return the tracked odometer span covered by the imported records."""
    if len(vehicle.records) < 2:
        return None

    latest = vehicle.records[-1].odometer
    earliest = vehicle.records[0].odometer
    if latest is None or earliest is None:
        return None
    return round(latest - earliest, 3)


def _sum_cost_since_days(vehicle: ParsedVehicle, days: int) -> float | None:
    """Return the sum of fuel costs over a recent rolling window."""
    cutoff = date.today().toordinal() - days
    values = [
        record.cost
        for record in vehicle.records
        if record.cost is not None and record.occurred_on.toordinal() >= cutoff
    ]
    if not values:
        return None
    return round(sum(values), 3)
