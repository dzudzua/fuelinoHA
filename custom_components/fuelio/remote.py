"""Helpers for reading remote Fuelio exports."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import BadZipFile, ZipFile


def decode_remote_vehicle_text(source_url: str, payload: bytes, content_type: str | None = None) -> str:
    """Decode a remote Fuelio export payload into CSV text.

    Supports plain CSV responses as well as ZIP archives that contain one CSV file.
    """
    if _looks_like_zip(source_url, payload, content_type):
      return _decode_zip_payload(payload)
    return payload.decode("utf-8-sig", errors="ignore")


def _looks_like_zip(source_url: str, payload: bytes, content_type: str | None) -> bool:
    normalized_url = (source_url or "").lower()
    normalized_type = (content_type or "").lower()
    return (
        normalized_url.endswith(".zip")
        or "zip" in normalized_type
        or payload.startswith(b"PK\x03\x04")
    )


def _decode_zip_payload(payload: bytes) -> str:
    try:
        with ZipFile(BytesIO(payload)) as archive:
            csv_members = [
                member
                for member in archive.namelist()
                if not member.endswith("/") and Path(member).suffix.lower() == ".csv"
            ]
            if not csv_members:
                raise ValueError("zip archive does not contain a CSV file")

            preferred = next(
                (member for member in csv_members if Path(member).name.lower().endswith("-sync.csv")),
                csv_members[0],
            )
            with archive.open(preferred) as csv_file:
                return csv_file.read().decode("utf-8-sig", errors="ignore")
    except BadZipFile as err:
        raise ValueError("invalid zip archive") from err
