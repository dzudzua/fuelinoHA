"""Quick local inspector for a Fuelio CSV export."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PARSER_PATH = PROJECT_ROOT / "custom_components" / "fuelio" / "parser.py"


def load_parser_module():
    """Load the parser module without importing Home Assistant package code."""
    spec = importlib.util.spec_from_file_location("fuelio_parser_inspector", PARSER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    """Inspect a Fuelio export file and print a short summary."""
    if len(sys.argv) != 2:
        print("Usage: python tools/inspect_fuelio_export.py <path-to-export.csv>")
        return 1

    export_path = Path(sys.argv[1]).resolve()
    if not export_path.exists():
        print(f"File not found: {export_path}")
        return 1

    parser = load_parser_module()
    parsed = parser.parse_vehicle_file(export_path)
    if parsed is None:
        print("Could not parse the Fuelio export.")
        return 2

    print(f"Vehicle: {parsed.name}")
    print(f"Fuel records: {len(parsed.records)}")
    print(f"Expenses: {len(parsed.expenses)}")
    print(f"Trips: {len(parsed.trips)}")
    if parsed.records:
        latest_fill = parsed.records[-1]
        print(
            "Latest fill: "
            f"{latest_fill.occurred_on} | cost={latest_fill.cost} | volume={latest_fill.volume}"
        )
    if parsed.expenses:
        latest_expense = parsed.expenses[-1]
        print(
            "Latest expense: "
            f"{latest_expense.occurred_on} | {latest_expense.title} | cost={latest_expense.cost}"
        )
    if parsed.trips:
        latest_trip = parsed.trips[-1]
        print(
            "Latest trip: "
            f"{latest_trip.started_on} | {latest_trip.title} | distance_km={latest_trip.distance_km}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
