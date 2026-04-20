"""Sensor platform for Fuelio."""

from __future__ import annotations

from collections import Counter
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
        icon="mdi:calendar-check",
        value_fn=lambda vehicle: vehicle.records[-1].occurred_on,
    ),
    FuelioSensorDescription(
        key="days_since_fill",
        translation_key="days_since_fill",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="d",
        icon="mdi:calendar-clock",
        value_fn=lambda vehicle: (date.today() - vehicle.records[-1].occurred_on).days,
    ),
    FuelioSensorDescription(
        key="last_fill_volume",
        translation_key="last_fill_volume",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="L",
        suggested_display_precision=2,
        icon="mdi:gas-station",
        value_fn=lambda vehicle: vehicle.records[-1].volume,
    ),
    FuelioSensorDescription(
        key="last_fill_cost",
        translation_key="last_fill_cost",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:cash",
        value_fn=lambda vehicle: vehicle.records[-1].cost,
    ),
    FuelioSensorDescription(
        key="last_price_per_unit",
        translation_key="last_price_per_unit",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        icon="mdi:currency-usd",
        value_fn=lambda vehicle: vehicle.records[-1].price_per_unit,
    ),
    FuelioSensorDescription(
        key="last_consumption",
        translation_key="last_consumption",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:chart-bell-curve-cumulative",
        value_fn=lambda vehicle: vehicle.records[-1].consumption,
    ),
    FuelioSensorDescription(
        key="last_fill_temperature",
        translation_key="last_fill_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="°C",
        icon="mdi:thermometer",
        suggested_display_precision=1,
        value_fn=lambda vehicle: _last_fill_temperature(vehicle),
    ),
    FuelioSensorDescription(
        key="last_city",
        translation_key="last_city",
        icon="mdi:map-marker",
        value_fn=lambda vehicle: vehicle.records[-1].city,
    ),
    FuelioSensorDescription(
        key="favorite_station",
        translation_key="favorite_station",
        icon="mdi:star-circle",
        value_fn=lambda vehicle: _favorite_station(vehicle),
    ),
    FuelioSensorDescription(
        key="favorite_city",
        translation_key="favorite_city",
        icon="mdi:city",
        value_fn=lambda vehicle: _favorite_city(vehicle),
    ),
    FuelioSensorDescription(
        key="favorite_station_id",
        translation_key="favorite_station_id",
        icon="mdi:pump",
        value_fn=lambda vehicle: _favorite_station_id(vehicle),
    ),
    FuelioSensorDescription(
        key="odometer",
        translation_key="odometer",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        suggested_display_precision=1,
        icon="mdi:counter",
        value_fn=lambda vehicle: vehicle.records[-1].odometer,
    ),
    FuelioSensorDescription(
        key="distance_since_previous_fill",
        translation_key="distance_since_previous_fill",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        suggested_display_precision=1,
        icon="mdi:map-marker-distance",
        value_fn=lambda vehicle: _distance_since_previous_fill(vehicle),
    ),
    FuelioSensorDescription(
        key="tracked_distance",
        translation_key="tracked_distance",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        suggested_display_precision=1,
        icon="mdi:road-variant",
        value_fn=lambda vehicle: _tracked_distance(vehicle),
    ),
    FuelioSensorDescription(
        key="fill_count",
        translation_key="fill_count",
        state_class=SensorStateClass.TOTAL,
        icon="mdi:counter",
        value_fn=lambda vehicle: len(vehicle.records),
    ),
    FuelioSensorDescription(
        key="cost_30d",
        translation_key="cost_30d",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:calendar-month",
        value_fn=lambda vehicle: _sum_cost_since_days(vehicle, 30),
    ),
    FuelioSensorDescription(
        key="fuel_cost_this_month",
        translation_key="fuel_cost_this_month",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:cash-multiple",
        value_fn=lambda vehicle: _sum_cost_current_month(vehicle),
    ),
    FuelioSensorDescription(
        key="last_expense_date",
        translation_key="last_expense_date",
        device_class=SensorDeviceClass.DATE,
        icon="mdi:calendar-star",
        value_fn=lambda vehicle: _last_expense_date(vehicle),
    ),
    FuelioSensorDescription(
        key="last_expense_cost",
        translation_key="last_expense_cost",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:receipt-text",
        value_fn=lambda vehicle: _last_expense_cost(vehicle),
    ),
    FuelioSensorDescription(
        key="expense_count",
        translation_key="expense_count",
        state_class=SensorStateClass.TOTAL,
        icon="mdi:receipt",
        value_fn=lambda vehicle: len(vehicle.expenses),
    ),
    FuelioSensorDescription(
        key="expense_cost_this_month",
        translation_key="expense_cost_this_month",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:wallet-outline",
        value_fn=lambda vehicle: _sum_expense_current_month(vehicle),
    ),
    FuelioSensorDescription(
        key="total_expense_cost",
        translation_key="total_expense_cost",
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        icon="mdi:wallet",
        value_fn=lambda vehicle: _sum_expense_values(vehicle, "cost"),
    ),
    FuelioSensorDescription(
        key="total_vehicle_cost",
        translation_key="total_vehicle_cost",
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        icon="mdi:car-wrench",
        value_fn=lambda vehicle: _total_vehicle_cost(vehicle),
    ),
    FuelioSensorDescription(
        key="fill_count_30d",
        translation_key="fill_count_30d",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:format-list-numbered",
        value_fn=lambda vehicle: _fill_count_since_days(vehicle, 30),
    ),
    FuelioSensorDescription(
        key="total_cost",
        translation_key="total_cost",
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
        icon="mdi:cash-check",
        value_fn=lambda vehicle: _sum_record_values(vehicle, "cost"),
    ),
    FuelioSensorDescription(
        key="most_expensive_fill",
        translation_key="most_expensive_fill",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:cash-plus",
        value_fn=lambda vehicle: _extreme_record_value(vehicle, "cost", max),
    ),
    FuelioSensorDescription(
        key="least_expensive_fill",
        translation_key="least_expensive_fill",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:cash-minus",
        value_fn=lambda vehicle: _extreme_record_value(vehicle, "cost", min),
    ),
    FuelioSensorDescription(
        key="total_volume",
        translation_key="total_volume",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement="L",
        suggested_display_precision=2,
        icon="mdi:gas-station-outline",
        value_fn=lambda vehicle: _sum_record_values(vehicle, "volume"),
    ),
    FuelioSensorDescription(
        key="average_price",
        translation_key="average_price",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        icon="mdi:finance",
        value_fn=lambda vehicle: _average_price(vehicle),
    ),
    FuelioSensorDescription(
        key="average_price_5_fills",
        translation_key="average_price_5_fills",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        icon="mdi:chart-line-variant",
        value_fn=lambda vehicle: _average_recent_record_values(
            vehicle, "price_per_unit", 5
        ),
    ),
    FuelioSensorDescription(
        key="average_consumption",
        translation_key="average_consumption",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:chart-line",
        value_fn=lambda vehicle: _average_record_values(vehicle, "consumption"),
    ),
    FuelioSensorDescription(
        key="best_consumption",
        translation_key="best_consumption",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:leaf",
        value_fn=lambda vehicle: _extreme_record_value(vehicle, "consumption", min),
    ),
    FuelioSensorDescription(
        key="worst_consumption",
        translation_key="worst_consumption",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:leaf-off",
        value_fn=lambda vehicle: _extreme_record_value(vehicle, "consumption", max),
    ),
    FuelioSensorDescription(
        key="average_consumption_30d",
        translation_key="average_consumption_30d",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:chart-timeline-variant",
        value_fn=lambda vehicle: _average_record_values_since_days(
            vehicle, "consumption", 30
        ),
    ),
    FuelioSensorDescription(
        key="average_cost_per_km",
        translation_key="average_cost_per_km",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        icon="mdi:currency-sign",
        value_fn=lambda vehicle: _average_cost_per_km(vehicle),
    ),
    FuelioSensorDescription(
        key="average_fill_volume",
        translation_key="average_fill_volume",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="L",
        suggested_display_precision=2,
        icon="mdi:gas-station-in-use",
        value_fn=lambda vehicle: _average_record_values(vehicle, "volume"),
    ),
    FuelioSensorDescription(
        key="average_days_between_fills",
        translation_key="average_days_between_fills",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="d",
        icon="mdi:calendar-sync",
        value_fn=lambda vehicle: _average_days_between_fills(vehicle),
    ),
    FuelioSensorDescription(
        key="average_distance_between_fills",
        translation_key="average_distance_between_fills",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        suggested_display_precision=1,
        icon="mdi:swap-horizontal-bold",
        value_fn=lambda vehicle: _average_distance_between_fills(vehicle),
    ),
    FuelioSensorDescription(
        key="distance_this_month",
        translation_key="distance_this_month",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        suggested_display_precision=1,
        icon="mdi:calendar-range",
        value_fn=lambda vehicle: _distance_current_month(vehicle),
    ),
    FuelioSensorDescription(
        key="last_month_cost",
        translation_key="last_month_cost",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:cash-clock",
        value_fn=lambda vehicle: _sum_cost_last_month(vehicle),
    ),
    FuelioSensorDescription(
        key="last_month_average_consumption",
        translation_key="last_month_average_consumption",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:chart-timeline",
        value_fn=lambda vehicle: _average_record_values_for_month(
            vehicle, "consumption", previous_month=True
        ),
    ),
    FuelioSensorDescription(
        key="last_month_fill_count",
        translation_key="last_month_fill_count",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:counter",
        value_fn=lambda vehicle: _fill_count_for_month(vehicle, previous_month=True),
    ),
    FuelioSensorDescription(
        key="last_month_average_price",
        translation_key="last_month_average_price",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        icon="mdi:currency-eur",
        value_fn=lambda vehicle: _average_record_values_for_month(
            vehicle, "price_per_unit", previous_month=True
        ),
    ),
    FuelioSensorDescription(
        key="month_over_month_cost_delta",
        translation_key="month_over_month_cost_delta",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        icon="mdi:compare",
        value_fn=lambda vehicle: _month_over_month_cost_delta(vehicle),
    ),
    FuelioSensorDescription(
        key="fuel_price_trend",
        translation_key="fuel_price_trend",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        icon="mdi:trending-up",
        value_fn=lambda vehicle: _fuel_price_trend(vehicle),
    ),
    FuelioSensorDescription(
        key="days_since_full_tank",
        translation_key="days_since_full_tank",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="d",
        icon="mdi:calendar-refresh",
        value_fn=lambda vehicle: _days_since_full_tank(vehicle),
    ),
    FuelioSensorDescription(
        key="km_since_full_tank",
        translation_key="km_since_full_tank",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        suggested_display_precision=1,
        icon="mdi:highway",
        value_fn=lambda vehicle: _km_since_full_tank(vehicle),
    ),
    FuelioSensorDescription(
        key="lowest_price_per_unit",
        translation_key="lowest_price_per_unit",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        icon="mdi:arrow-down-bold-circle",
        value_fn=lambda vehicle: _extreme_record_value(vehicle, "price_per_unit", min),
    ),
    FuelioSensorDescription(
        key="highest_price_per_unit",
        translation_key="highest_price_per_unit",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        icon="mdi:arrow-up-bold-circle",
        value_fn=lambda vehicle: _extreme_record_value(vehicle, "price_per_unit", max),
    ),
    FuelioSensorDescription(
        key="different_stations_count",
        translation_key="different_stations_count",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:pump",
        value_fn=lambda vehicle: _different_stations_count(vehicle),
    ),
    FuelioSensorDescription(
        key="different_cities_count",
        translation_key="different_cities_count",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:map-marker-multiple",
        value_fn=lambda vehicle: _different_cities_count(vehicle),
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
        device_info: dict[str, Any] = {
            "identifiers": {(DOMAIN, self._vehicle_key)},
            "name": self.vehicle.name,
            "manufacturer": "Fuelio",
            "model": self.vehicle.model or "CSV Import",
        }
        if self.vehicle.year is not None:
            device_info["sw_version"] = str(self.vehicle.year)
        return device_info

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
        if self.entity_description.key in {
            "last_fill_cost",
            "total_cost",
            "cost_30d",
            "fuel_cost_this_month",
            "last_expense_cost",
            "expense_cost_this_month",
            "total_expense_cost",
            "total_vehicle_cost",
            "most_expensive_fill",
            "least_expensive_fill",
            "last_month_cost",
            "month_over_month_cost_delta",
        }:
            return self.vehicle.currency
        if self.entity_description.key in {
            "last_price_per_unit",
            "average_price",
            "average_price_5_fills",
            "last_month_average_price",
            "fuel_price_trend",
        }:
            if self.vehicle.currency:
                unit = self.vehicle.fuel_unit or "L"
                return f"{self.vehicle.currency}/{unit}"
        if self.entity_description.key in {
            "lowest_price_per_unit",
            "highest_price_per_unit",
        }:
            if self.vehicle.currency:
                unit = self.vehicle.fuel_unit or "L"
                return f"{self.vehicle.currency}/{unit}"
        if self.entity_description.key == "average_cost_per_km":
            if self.vehicle.currency:
                distance_unit = self.vehicle.distance_unit or "km"
                return f"{self.vehicle.currency}/{distance_unit}"
        if self.entity_description.key in {
            "last_fill_volume",
            "total_volume",
            "average_fill_volume",
        }:
            return self.vehicle.fuel_unit or "L"
        if self.entity_description.key in {
            "odometer",
            "distance_since_previous_fill",
            "tracked_distance",
            "km_since_full_tank",
            "distance_this_month",
            "average_distance_between_fills",
        }:
            if self.vehicle.distance_unit == "mi":
                return UnitOfLength.MILES
            if self.vehicle.distance_unit == "km":
                return UnitOfLength.KILOMETERS
        if self.entity_description.key in {
            "last_consumption",
            "average_consumption",
            "average_consumption_30d",
            "best_consumption",
            "worst_consumption",
            "last_month_average_consumption",
        }:
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
        if latest.city is not None:
            attrs["last_city"] = latest.city
        favorite_station = _favorite_station(self.vehicle)
        if favorite_station is not None:
            attrs["favorite_station"] = favorite_station
        favorite_city = _favorite_city(self.vehicle)
        if favorite_city is not None:
            attrs["favorite_city"] = favorite_city
        favorite_station_id = _favorite_station_id(self.vehicle)
        if favorite_station_id is not None:
            attrs["favorite_station_id"] = favorite_station_id
        attrs["recent_cities"] = _recent_cities(self.vehicle, limit=3)
        if latest.fuel_type is not None:
            attrs["last_fuel_type"] = latest.fuel_type
        weather_desc = latest.weather.get("desc")
        if weather_desc:
            attrs["last_weather_description"] = weather_desc
        weather_temp = _last_fill_temperature(self.vehicle)
        if weather_temp is not None:
            attrs["last_fill_temperature"] = weather_temp
        last_expense = _last_expense(self.vehicle)
        if last_expense is not None:
            attrs["last_expense_title"] = last_expense.title
            attrs["last_expense_category"] = last_expense.category_name
        attrs["data_span_days"] = _data_span_days(self.vehicle)
        attrs["partial_fill_count"] = _partial_fill_count(self.vehicle)
        attrs["full_tank_count"] = _full_tank_count(self.vehicle)
        best_consumption = _extreme_record_value(self.vehicle, "consumption", min)
        if best_consumption is not None:
            attrs["best_consumption"] = best_consumption
        worst_consumption = _extreme_record_value(self.vehicle, "consumption", max)
        if worst_consumption is not None:
            attrs["worst_consumption"] = worst_consumption
        attrs["recent_fills"] = _recent_fills(self.vehicle, limit=5)
        attrs["monthly_summary"] = _monthly_summary(self.vehicle, limit=6)
        attrs["recent_expenses"] = _recent_expenses(self.vehicle, limit=5)
        attrs["expense_category_summary"] = _expense_category_summary(self.vehicle)
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


def _sum_expense_values(vehicle: ParsedVehicle, field: str) -> float | None:
    """Sum numeric expense values."""
    values = [
        getattr(expense, field)
        for expense in vehicle.expenses
        if getattr(expense, field) is not None and expense.is_income is not True
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


def _last_expense(vehicle: ParsedVehicle):
    """Return the newest parsed expense if available."""
    if not vehicle.expenses:
        return None
    return vehicle.expenses[-1]


def _last_expense_date(vehicle: ParsedVehicle) -> date | None:
    """Return the date of the newest expense."""
    latest = _last_expense(vehicle)
    return latest.occurred_on if latest is not None else None


def _last_expense_cost(vehicle: ParsedVehicle) -> float | None:
    """Return the cost of the newest expense."""
    latest = _last_expense(vehicle)
    if latest is None:
        return None
    return latest.cost


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


def _average_recent_record_values(
    vehicle: ParsedVehicle, field: str, limit: int
) -> float | None:
    """Calculate an average across the most recent record values."""
    values = [
        getattr(record, field)
        for record in vehicle.records[-limit:]
        if getattr(record, field) is not None
    ]
    if not values:
        return None
    return round(sum(values) / len(values), 3)


def _average_record_values_since_days(
    vehicle: ParsedVehicle, field: str, days: int
) -> float | None:
    """Calculate an average across recent available record values."""
    cutoff = date.today().toordinal() - days
    values = [
        getattr(record, field)
        for record in vehicle.records
        if record.occurred_on.toordinal() >= cutoff and getattr(record, field) is not None
    ]
    if not values:
        return None
    return round(sum(values) / len(values), 3)


def _average_record_values_for_month(
    vehicle: ParsedVehicle, field: str, previous_month: bool = False
) -> float | None:
    """Calculate an average across a calendar month."""
    year, month = _month_key(previous_month=previous_month)
    values = [
        getattr(record, field)
        for record in vehicle.records
        if record.occurred_on.year == year
        and record.occurred_on.month == month
        and getattr(record, field) is not None
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


def _sum_cost_current_month(vehicle: ParsedVehicle) -> float | None:
    """Return the sum of costs in the current calendar month."""
    today = date.today()
    values = [
        record.cost
        for record in vehicle.records
        if record.cost is not None
        and record.occurred_on.year == today.year
        and record.occurred_on.month == today.month
    ]
    if not values:
        return None
    return round(sum(values), 3)


def _sum_expense_current_month(vehicle: ParsedVehicle) -> float | None:
    """Return the sum of non-fuel costs in the current calendar month."""
    today = date.today()
    values = [
        expense.cost
        for expense in vehicle.expenses
        if expense.cost is not None
        and expense.is_income is not True
        and expense.occurred_on.year == today.year
        and expense.occurred_on.month == today.month
    ]
    if not values:
        return None
    return round(sum(values), 3)


def _fill_count_since_days(vehicle: ParsedVehicle, days: int) -> int:
    """Return the number of fills in a recent rolling window."""
    cutoff = date.today().toordinal() - days
    return sum(1 for record in vehicle.records if record.occurred_on.toordinal() >= cutoff)


def _average_cost_per_km(vehicle: ParsedVehicle) -> float | None:
    """Return average cost per tracked distance unit."""
    total_cost = _sum_record_values(vehicle, "cost")
    tracked_distance = _tracked_distance(vehicle)
    if not total_cost or not tracked_distance:
        return None
    return round(total_cost / tracked_distance, 4)


def _average_days_between_fills(vehicle: ParsedVehicle) -> float | None:
    """Return average days between consecutive fill records."""
    if len(vehicle.records) < 2:
        return None
    intervals = [
        (vehicle.records[index].occurred_on - vehicle.records[index - 1].occurred_on).days
        for index in range(1, len(vehicle.records))
    ]
    if not intervals:
        return None
    return round(sum(intervals) / len(intervals), 2)


def _average_distance_between_fills(vehicle: ParsedVehicle) -> float | None:
    """Return average odometer delta between consecutive fills."""
    deltas = []
    for index in range(1, len(vehicle.records)):
        latest = vehicle.records[index].odometer
        previous = vehicle.records[index - 1].odometer
        if latest is None or previous is None:
            continue
        deltas.append(latest - previous)
    if not deltas:
        return None
    return round(sum(deltas) / len(deltas), 3)


def _distance_current_month(vehicle: ParsedVehicle) -> float | None:
    """Return tracked distance within the current month."""
    today = date.today()
    month_records = [
        record
        for record in vehicle.records
        if record.odometer is not None
        and record.occurred_on.year == today.year
        and record.occurred_on.month == today.month
    ]
    if len(month_records) < 2:
        return None
    return round(month_records[-1].odometer - month_records[0].odometer, 3)


def _month_key(previous_month: bool = False) -> tuple[int, int]:
    """Return a calendar month key for current or previous month."""
    today = date.today()
    year = today.year
    month = today.month
    if previous_month:
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return year, month


def _sum_cost_last_month(vehicle: ParsedVehicle) -> float | None:
    """Return the sum of costs in the previous calendar month."""
    year, month = _month_key(previous_month=True)
    values = [
        record.cost
        for record in vehicle.records
        if record.cost is not None
        and record.occurred_on.year == year
        and record.occurred_on.month == month
    ]
    if not values:
        return None
    return round(sum(values), 3)


def _fill_count_for_month(vehicle: ParsedVehicle, previous_month: bool = False) -> int:
    """Return the number of fills in the selected calendar month."""
    year, month = _month_key(previous_month=previous_month)
    return sum(
        1
        for record in vehicle.records
        if record.occurred_on.year == year and record.occurred_on.month == month
    )


def _month_over_month_cost_delta(vehicle: ParsedVehicle) -> float | None:
    """Return this month cost minus previous month cost."""
    current = _sum_cost_current_month(vehicle)
    previous = _sum_cost_last_month(vehicle)
    if current is None or previous is None:
        return None
    return round(current - previous, 3)


def _total_vehicle_cost(vehicle: ParsedVehicle) -> float | None:
    """Return fuel plus non-fuel costs combined."""
    fuel_cost = _sum_record_values(vehicle, "cost") or 0.0
    expense_cost = _sum_expense_values(vehicle, "cost") or 0.0
    total = fuel_cost + expense_cost
    if total == 0:
        return None
    return round(total, 3)


def _fuel_price_trend(vehicle: ParsedVehicle) -> float | None:
    """Return recent average price minus previous recent average price."""
    recent_records = [r for r in vehicle.records if r.price_per_unit is not None]
    if len(recent_records) < 2:
        return None
    recent_values = [r.price_per_unit for r in recent_records[-5:]]
    previous_values = [r.price_per_unit for r in recent_records[-10:-5]]
    if not recent_values or not previous_values:
        return None
    recent_average = sum(recent_values) / len(recent_values)
    previous_average = sum(previous_values) / len(previous_values)
    return round(recent_average - previous_average, 3)


def _find_last_full_record(vehicle: ParsedVehicle):
    """Return the last full-tank record if available."""
    for record in reversed(vehicle.records):
        if record.is_partial is False:
            return record
    return None


def _days_since_full_tank(vehicle: ParsedVehicle) -> int | None:
    """Return days since the last full tank."""
    last_full = _find_last_full_record(vehicle)
    if last_full is None:
        return None
    return (date.today() - last_full.occurred_on).days


def _km_since_full_tank(vehicle: ParsedVehicle) -> float | None:
    """Return distance since the last full tank."""
    last_full = _find_last_full_record(vehicle)
    latest = vehicle.records[-1]
    if last_full is None or latest.odometer is None or last_full.odometer is None:
        return None
    return round(latest.odometer - last_full.odometer, 3)


def _favorite_station(vehicle: ParsedVehicle) -> str | None:
    """Return the most frequent city/station label."""
    values = [
        record.city or record.station_id
        for record in vehicle.records
        if record.city or record.station_id
    ]
    if not values:
        return None
    return Counter(values).most_common(1)[0][0]


def _favorite_city(vehicle: ParsedVehicle) -> str | None:
    """Return the most frequent city."""
    values = [record.city for record in vehicle.records if record.city]
    if not values:
        return None
    return Counter(values).most_common(1)[0][0]


def _favorite_station_id(vehicle: ParsedVehicle) -> str | None:
    """Return the most frequent station id."""
    values = [record.station_id for record in vehicle.records if record.station_id]
    if not values:
        return None
    return Counter(values).most_common(1)[0][0]


def _different_stations_count(vehicle: ParsedVehicle) -> int:
    """Return the number of unique station ids."""
    return len({record.station_id for record in vehicle.records if record.station_id})


def _different_cities_count(vehicle: ParsedVehicle) -> int:
    """Return the number of unique cities."""
    return len({record.city for record in vehicle.records if record.city})


def _recent_cities(vehicle: ParsedVehicle, limit: int = 3) -> list[str]:
    """Return the most recent non-empty fill cities."""
    values: list[str] = []
    for record in reversed(vehicle.records):
        if not record.city:
            continue
        values.append(record.city)
        if len(values) >= limit:
            break
    return values


def _data_span_days(vehicle: ParsedVehicle) -> int:
    """Return how many days of history the imported CSV covers."""
    if len(vehicle.records) < 2:
        return 0
    return (vehicle.records[-1].occurred_on - vehicle.records[0].occurred_on).days


def _partial_fill_count(vehicle: ParsedVehicle) -> int:
    """Return how many partial fills exist in the imported data."""
    return sum(1 for record in vehicle.records if record.is_partial is True)


def _full_tank_count(vehicle: ParsedVehicle) -> int:
    """Return how many full-tank fills exist in the imported data."""
    return sum(1 for record in vehicle.records if record.is_partial is False)


def _last_fill_temperature(vehicle: ParsedVehicle) -> float | None:
    """Return temperature from the latest weather payload."""
    temp_value = vehicle.records[-1].weather.get("temp")
    if not temp_value:
        return None
    try:
        return round(float(temp_value), 2)
    except ValueError:
        return None


def _extreme_record_value(vehicle: ParsedVehicle, field: str, reducer) -> float | None:
    """Return an extreme value across records for a numeric field."""
    values = [
        getattr(record, field)
        for record in vehicle.records
        if getattr(record, field) is not None
    ]
    if not values:
        return None
    return round(reducer(values), 3)


def _recent_fills(vehicle: ParsedVehicle, limit: int = 5) -> list[dict[str, Any]]:
    """Return a compact summary of the most recent fills."""
    recent = list(reversed(vehicle.records[-limit:]))
    rows: list[dict[str, Any]] = []
    for record in recent:
        rows.append(
            {
                "date": record.occurred_on.isoformat(),
                "odometer": record.odometer,
                "volume": record.volume,
                "cost": record.cost,
                "price_per_unit": record.price_per_unit,
                "consumption": record.consumption,
                "city": record.city,
                "station_id": record.station_id,
                "fuel_type": record.fuel_type,
                "is_partial": record.is_partial,
                "temperature": _safe_float(record.weather.get("temp")),
                "weather_description": record.weather.get("desc"),
            }
        )
    return rows


def _monthly_summary(vehicle: ParsedVehicle, limit: int = 6) -> list[dict[str, Any]]:
    """Return monthly rollups from parsed fill records."""
    monthly: dict[tuple[int, int], dict[str, Any]] = {}
    for record in vehicle.records:
        key = (record.occurred_on.year, record.occurred_on.month)
        summary = monthly.setdefault(
            key,
            {
                "year": record.occurred_on.year,
                "month": record.occurred_on.month,
                "fill_count": 0,
                "total_cost": 0.0,
                "total_volume": 0.0,
                "price_sum": 0.0,
                "price_count": 0,
                "odometer_min": record.odometer,
                "odometer_max": record.odometer,
            },
        )
        summary["fill_count"] += 1
        if record.cost is not None:
            summary["total_cost"] += record.cost
        if record.volume is not None:
            summary["total_volume"] += record.volume
        if record.price_per_unit is not None:
            summary["price_sum"] += record.price_per_unit
            summary["price_count"] += 1
        if record.odometer is not None:
            current_min = summary["odometer_min"]
            current_max = summary["odometer_max"]
            summary["odometer_min"] = (
                record.odometer
                if current_min is None
                else min(current_min, record.odometer)
            )
            summary["odometer_max"] = (
                record.odometer
                if current_max is None
                else max(current_max, record.odometer)
            )

    result: list[dict[str, Any]] = []
    for key in sorted(monthly.keys(), reverse=True)[:limit]:
        summary = monthly[key]
        distance = None
        if summary["odometer_min"] is not None and summary["odometer_max"] is not None:
            distance = round(summary["odometer_max"] - summary["odometer_min"], 3)
        average_price = None
        if summary["price_count"]:
            average_price = round(summary["price_sum"] / summary["price_count"], 3)
        result.append(
            {
                "year": summary["year"],
                "month": summary["month"],
                "fill_count": summary["fill_count"],
                "total_cost": round(summary["total_cost"], 2),
                "total_volume": round(summary["total_volume"], 2),
                "distance": distance,
                "average_price": average_price,
            }
        )
    return result


def _recent_expenses(vehicle: ParsedVehicle, limit: int = 5) -> list[dict[str, Any]]:
    """Return a compact summary of the most recent non-fuel expenses."""
    recent = list(reversed(vehicle.expenses[-limit:]))
    rows: list[dict[str, Any]] = []
    for expense in recent:
        rows.append(
            {
                "date": expense.occurred_on.isoformat(),
                "title": expense.title,
                "cost": expense.cost,
                "category_name": expense.category_name,
                "odometer": expense.odometer,
                "notes": expense.notes,
            }
        )
    return rows


def _expense_category_summary(vehicle: ParsedVehicle) -> list[dict[str, Any]]:
    """Return cost totals grouped by expense category."""
    grouped: dict[str, dict[str, Any]] = {}
    for expense in vehicle.expenses:
        if expense.cost is None or expense.is_income is True:
            continue
        key = expense.category_name or "Uncategorized"
        summary = grouped.setdefault(
            key,
            {"category_name": key, "count": 0, "total_cost": 0.0},
        )
        summary["count"] += 1
        summary["total_cost"] += expense.cost

    result = list(grouped.values())
    result.sort(key=lambda item: item["total_cost"], reverse=True)
    for item in result:
        item["total_cost"] = round(item["total_cost"], 2)
    return result


def _safe_float(value: Any) -> float | None:
    """Convert an optional numeric-like value to float."""
    if value in (None, ""):
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None
