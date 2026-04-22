"""Tests for remote Fuelio payload decoding."""

from __future__ import annotations

import importlib.util
from io import BytesIO
from pathlib import Path
import sys
import unittest
from zipfile import ZipFile


PROJECT_ROOT = Path(__file__).resolve().parent.parent
REMOTE_PATH = PROJECT_ROOT / "custom_components" / "fuelio" / "remote.py"
SAMPLE_EXPORT = PROJECT_ROOT / "tests" / "fixtures" / "sample_fuelio_export.csv"


def load_remote_module():
    """Load the remote helper module without importing Home Assistant package code."""
    spec = importlib.util.spec_from_file_location("fuelio_remote_test", REMOTE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class FuelioRemoteTests(unittest.TestCase):
    """Regression tests for remote CSV/ZIP decoding."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.remote = load_remote_module()
        cls.sample_text = SAMPLE_EXPORT.read_text(encoding="utf-8")

    def test_plain_csv_payload_is_decoded(self) -> None:
        decoded = self.remote.decode_remote_vehicle_text(
            "https://www.dropbox.com/scl/fi/example/vehicle-1-sync.csv?dl=0",
            self.sample_text.encode("utf-8"),
            "text/csv",
        )
        self.assertIn("## Vehicle", decoded)
        self.assertEqual(decoded.strip(), self.sample_text.strip())

    def test_zip_payload_is_unpacked(self) -> None:
        buffer = BytesIO()
        with ZipFile(buffer, "w") as archive:
            archive.writestr("vehicle-1-sync.csv", self.sample_text.encode("utf-8"))

        decoded = self.remote.decode_remote_vehicle_text(
            "https://www.dropbox.com/scl/fi/example/vehicle-1-sync.csv.zip?dl=0",
            buffer.getvalue(),
            "application/zip",
        )
        self.assertIn("## Log", decoded)
        self.assertEqual(decoded.strip(), self.sample_text.strip())


if __name__ == "__main__":
    unittest.main()
