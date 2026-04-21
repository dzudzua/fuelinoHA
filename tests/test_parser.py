"""Tests for the Fuelio CSV parser."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PARSER_PATH = PROJECT_ROOT / "custom_components" / "fuelio" / "parser.py"
SAMPLE_EXPORT = PROJECT_ROOT / "tests" / "fixtures" / "sample_fuelio_export.csv"


def load_parser_module():
    """Load the parser module without importing Home Assistant package code."""
    spec = importlib.util.spec_from_file_location("fuelio_parser_test", PARSER_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FuelioParserTests(unittest.TestCase):
    """Parser regression tests backed by a real Fuelio export."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load the parser and parse the sample file once."""
        cls.parser = load_parser_module()
        cls.parsed = cls.parser.parse_vehicle_file(SAMPLE_EXPORT)

    def test_vehicle_metadata_is_parsed(self) -> None:
        """Vehicle section metadata should be extracted from the export."""
        self.assertIsNotNone(self.parsed)
        self.assertEqual(self.parsed.name, "Hyundai i30")
        self.assertEqual(self.parsed.key, "hyundai_i30")
        self.assertEqual(self.parsed.fuel_unit, "L")
        self.assertEqual(self.parsed.distance_unit, "km")
        self.assertEqual(self.parsed.make, "Hyundai")
        self.assertEqual(self.parsed.model, "i30")
        self.assertEqual(self.parsed.year, 2009)

    def test_latest_record_is_parsed_correctly(self) -> None:
        """Newest log entry should expose the expected values."""
        latest = self.parsed.records[-1]
        self.assertEqual(str(latest.occurred_on), "2026-04-09")
        self.assertEqual(latest.odometer, 183098.0)
        self.assertEqual(latest.volume, 37.52)
        self.assertEqual(latest.cost, 1497.0)
        self.assertEqual(latest.price_per_unit, 39.9)
        self.assertEqual(latest.consumption, 7.92)
        self.assertFalse(latest.is_partial)

    def test_partial_fill_is_interpreted_from_full_flag(self) -> None:
        """Fuelio Full=0 entries should be treated as partial fills."""
        partial_record = next(
            record
            for record in self.parsed.records
            if str(record.occurred_on) == "2025-07-25"
        )
        self.assertTrue(partial_record.is_partial)

    def test_record_count_matches_export(self) -> None:
        """The parser should read all log rows from the sample export."""
        self.assertEqual(len(self.parsed.records), 2)

    def test_expense_sections_are_parsed(self) -> None:
        """Fuelio cost/category sections should become expense records."""
        self.assertEqual(len(self.parsed.expenses), 2)
        latest_expense = self.parsed.expenses[-1]
        self.assertEqual(str(latest_expense.occurred_on), "2026-03-24")
        self.assertEqual(latest_expense.title, "Wax wash")
        self.assertEqual(latest_expense.category_name, "Car wash")
        self.assertEqual(latest_expense.cost, 299.0)

    def test_triplog_sections_are_parsed(self) -> None:
        """Fuelio trip log sections should become trip records."""
        self.assertEqual(len(self.parsed.trips), 2)
        latest_trip = self.parsed.trips[-1]
        self.assertEqual(str(latest_trip.started_on), "2024-01-14")
        self.assertEqual(latest_trip.title, "Afternoon drive")
        self.assertEqual(latest_trip.end_name, "Prague")
        self.assertAlmostEqual(latest_trip.distance_km, 95.114, places=3)
        self.assertAlmostEqual(latest_trip.trip_cost, 462.04438, places=5)

    def test_parse_vehicle_text_matches_file_parser(self) -> None:
        """Parsing raw CSV text should match file-based parsing."""
        text = SAMPLE_EXPORT.read_text(encoding="utf-8")
        parsed = self.parser.parse_vehicle_text("dropbox://vehicle-1-sync.csv", text)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.name, self.parsed.name)
        self.assertEqual(parsed.key, self.parsed.key)
        self.assertEqual(len(parsed.records), len(self.parsed.records))
        self.assertEqual(len(parsed.expenses), len(self.parsed.expenses))
        self.assertEqual(len(parsed.trips), len(self.parsed.trips))


if __name__ == "__main__":
    unittest.main()
