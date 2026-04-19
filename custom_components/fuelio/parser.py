"""Fuelio CSV parsing helpers."""

from __future__ import annotations

from csv import DictReader, Sniffer, reader as csv_reader
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
import re


@dataclass(slots=True)
class FillRecord:
    """Normalized fill-up record."""

    occurred_on: date
    odometer: float | None
    volume: float | None
    cost: float | None
    price_per_unit: float | None
    consumption: float | None
    is_partial: bool | None
    raw: dict[str, str]


@dataclass(slots=True)
class ParsedVehicle:
    """Parsed data for a single vehicle."""

    key: str
    name: str
    source_file: str
    records: list[FillRecord]
    currency: str | None
    fuel_unit: str | None
    distance_unit: str | None
    make: str | None
    model: str | None
    year: int | None


HEADER_ALIASES = {
    "date": ("date", "datum", "time", "created", "datetime"),
    "odometer": ("odometer", "tachometer", "mileage", "distance", "km"),
    "volume": ("fuel", "volume", "liters", "litres", "l", "kwh"),
    "cost": ("price", "cost", "amount", "total"),
    "price_per_unit": (
        "price per volume",
        "price/l",
        "price per liter",
        "price per litre",
        "fuel price",
        "price per kwh",
        "unit price",
    ),
    "consumption": ("l/100km", "consumption", "avg consumption", "kwh/100km"),
    "partial": ("partial", "missed", "full tank", "tank full"),
    "vehicle": ("vehicle", "car", "name"),
    "currency": ("currency",),
}

DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%d.%m.%Y",
    "%d.%m.%Y %H:%M",
    "%m/%d/%Y",
    "%m/%d/%Y %H:%M",
)

FUEL_UNIT_MAP = {
    "0": "L",
    "1": "gal",
    "2": "kWh",
}

DISTANCE_UNIT_MAP = {
    "0": "km",
    "1": "mi",
}


def parse_vehicle_file(path: Path) -> ParsedVehicle | None:
    """Parse a single Fuelio CSV file."""
    text = path.read_text(encoding="utf-8-sig", errors="ignore")
    if not text.strip():
        return None

    if "## Vehicle" in text and "## Log" in text:
        parsed = _parse_sectioned_fuelio_file(path, text)
        if parsed is not None:
            return parsed

    return _parse_generic_csv_file(path, text)


def _parse_sectioned_fuelio_file(path: Path, text: str) -> ParsedVehicle | None:
    """Parse Fuelio's native multi-section CSV export."""
    rows = list(csv_reader(text.splitlines()))
    sections: dict[str, list[list[str]]] = {}
    current_section: str | None = None

    for row in rows:
        if not row:
            continue
        first = (row[0] or "").strip()
        if first.startswith("## "):
            current_section = first[3:].strip().lower()
            sections[current_section] = []
            continue
        if current_section is not None:
            sections[current_section].append(row)

    vehicle_rows = sections.get("vehicle", [])
    log_rows = sections.get("log", [])
    if len(vehicle_rows) < 2 or len(log_rows) < 2:
        return None

    vehicle_info = _row_to_dict(vehicle_rows[0], vehicle_rows[1])
    records: list[FillRecord] = []

    for row in log_rows[1:]:
        log_entry = _row_to_dict(log_rows[0], row)
        occurred_on = _parse_date(log_entry.get("Data"))
        if occurred_on is None:
            continue

        record = FillRecord(
            occurred_on=occurred_on,
            odometer=_parse_number(log_entry.get("Odo (km)") or log_entry.get("Odo")),
            volume=_parse_number(log_entry.get("Fuel (litres)") or log_entry.get("Fuel")),
            cost=_parse_number(log_entry.get("Price (optional)") or log_entry.get("Price")),
            price_per_unit=_parse_number(log_entry.get("VolumePrice")),
            consumption=_parse_number(log_entry.get("l/100km (optional)")),
            is_partial=_fuelio_partial_value(
                log_entry.get("Full"),
                log_entry.get("Missed"),
            ),
            raw=log_entry,
        )
        if record.volume is None and record.cost is None and record.odometer is None:
            continue
        records.append(record)

    if not records:
        return None

    records.sort(key=lambda item: item.occurred_on)
    base_name = vehicle_info.get("Name") or path.stem
    make = _clean_text(vehicle_info.get("Make"))
    model = _clean_text(vehicle_info.get("Model"))
    year = _parse_int(vehicle_info.get("Year"))
    pretty_name = _build_vehicle_name(base_name, make, model)

    return ParsedVehicle(
        key=_slugify(pretty_name),
        name=pretty_name,
        source_file=str(path),
        records=records,
        currency=_clean_text(vehicle_info.get("Currency")),
        fuel_unit=FUEL_UNIT_MAP.get((vehicle_info.get("FuelUnit") or "").strip()),
        distance_unit=DISTANCE_UNIT_MAP.get((vehicle_info.get("DistUnit") or "").strip()),
        make=make,
        model=model,
        year=year,
    )


def _parse_generic_csv_file(path: Path, text: str) -> ParsedVehicle | None:
    """Fallback parser for simpler CSV shapes."""
    sample = "\n".join(text.splitlines()[:5])
    try:
        dialect = Sniffer().sniff(sample, delimiters=",;|\t")
    except Exception:
        class _FallbackDialect:
            delimiter = ","

        dialect = _FallbackDialect()

    reader = DictReader(text.splitlines(), delimiter=dialect.delimiter)
    if not reader.fieldnames:
        return None

    header_map = _match_headers(reader.fieldnames)
    vehicle_name = _slug_to_title(path.stem)
    currency: str | None = None
    records: list[FillRecord] = []

    for row in reader:
        normalized_row = {key.strip(): (value or "").strip() for key, value in row.items()}
        if not any(normalized_row.values()):
            continue

        vehicle_name = (
            _first_non_empty(normalized_row, header_map.get("vehicle")) or vehicle_name
        )
        currency = _first_non_empty(normalized_row, header_map.get("currency")) or currency

        occurred_on = _parse_date(_first_non_empty(normalized_row, header_map.get("date")))
        if occurred_on is None:
            continue

        record = FillRecord(
            occurred_on=occurred_on,
            odometer=_parse_number(
                _first_non_empty(normalized_row, header_map.get("odometer"))
            ),
            volume=_parse_number(_first_non_empty(normalized_row, header_map.get("volume"))),
            cost=_parse_number(_first_non_empty(normalized_row, header_map.get("cost"))),
            price_per_unit=_parse_number(
                _first_non_empty(normalized_row, header_map.get("price_per_unit"))
            ),
            consumption=_parse_number(
                _first_non_empty(normalized_row, header_map.get("consumption"))
            ),
            is_partial=_parse_bool(
                _first_non_empty(normalized_row, header_map.get("partial"))
            ),
            raw=normalized_row,
        )
        if record.volume is None and record.cost is None and record.odometer is None:
            continue
        records.append(record)

    if not records:
        return None

    records.sort(key=lambda item: item.occurred_on)
    key = _slugify(vehicle_name or path.stem)
    return ParsedVehicle(
        key=key,
        name=vehicle_name or path.stem,
        source_file=str(path),
        records=records,
        currency=currency,
        fuel_unit=None,
        distance_unit=None,
        make=None,
        model=None,
        year=None,
    )


def _match_headers(fieldnames: list[str]) -> dict[str, list[str]]:
    """Match source headers to normalized field groups."""
    normalized_fields = {field: _normalize_header(field) for field in fieldnames}
    matched: dict[str, list[str]] = {}

    for target, aliases in HEADER_ALIASES.items():
        matched[target] = [
            field
            for field, normalized in normalized_fields.items()
            if any(alias in normalized for alias in aliases)
        ]

    return matched


def _normalize_header(value: str) -> str:
    """Normalize header names for fuzzy matching."""
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _parse_date(value: str | None) -> date | None:
    """Parse a date value."""
    if not value:
        return None

    cleaned = value.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(cleaned.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _parse_number(value: str | None) -> float | None:
    """Parse a localized number."""
    if not value:
        return None

    cleaned = value.strip().replace("\xa0", "").replace(" ", "")
    cleaned = re.sub(r"[^0-9,.\-]", "", cleaned)
    if not cleaned:
        return None

    if cleaned.count(",") > 0 and cleaned.count(".") > 0:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif cleaned.count(",") == 1 and cleaned.count(".") == 0:
        cleaned = cleaned.replace(",", ".")
    elif cleaned.count(",") > 1 and cleaned.count(".") == 0:
        cleaned = cleaned.replace(",", "")

    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_bool(value: str | None) -> bool | None:
    """Parse a boolean-ish value."""
    if not value:
        return None

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "full", "filled"}:
        return True
    if normalized in {"0", "false", "no", "n", "partial", "missed"}:
        return False
    return None


def _fuelio_partial_value(full_value: str | None, missed_value: str | None) -> bool | None:
    """Interpret Fuelio full/missed values as a partial-fill flag."""
    missed = _parse_bool(missed_value)
    if missed is True:
        return True

    full = _parse_bool(full_value)
    if full is True:
        return False
    if full is False:
        return True
    return None


def _first_non_empty(row: dict[str, str], keys: list[str] | None) -> str | None:
    """Return the first non-empty value for matching headers."""
    if not keys:
        return None

    for key in keys:
        value = row.get(key)
        if value:
            return value
    return None


def _slugify(value: str) -> str:
    """Create a Home Assistant friendly slug."""
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "vehicle"


def _slug_to_title(value: str) -> str:
    """Turn a filename stem into a human-readable name."""
    return re.sub(r"[_-]+", " ", value).strip().title()


def _row_to_dict(headers: list[str], row: list[str]) -> dict[str, str]:
    """Convert a CSV row to a dictionary with padded cells."""
    padded = list(row) + [""] * max(0, len(headers) - len(row))
    return {
        (header or "").strip(): (padded[index] or "").strip()
        for index, header in enumerate(headers)
        if header
    }


def _clean_text(value: str | None) -> str | None:
    """Normalize optional text fields."""
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _parse_int(value: str | None) -> int | None:
    """Parse an integer-ish value."""
    number = _parse_number(value)
    if number is None:
        return None
    return int(number)


def _build_vehicle_name(base_name: str, make: str | None, model: str | None) -> str:
    """Create a friendly vehicle name."""
    if make or model:
        combined = " ".join(part for part in (make, model) if part)
        if combined:
            return combined
    return _clean_text(base_name) or _slug_to_title(base_name)
