"""Editable accommodation registry backed by standard-library TOML."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Accommodation:
    id: str
    name: str
    adapter: str
    booking_url: str
    search_url: str | None = None
    limitation: str | None = None
    season_open_date: date | None = None


@dataclass(frozen=True)
class MonitorConfig:
    start_date: date
    end_date: date
    party_size: int
    host_delay_seconds: float


@dataclass(frozen=True)
class Registry:
    monitor: MonitorConfig
    accommodations: tuple[Accommodation, ...]

    def get(self, accommodation_id: str) -> Accommodation:
        for accommodation in self.accommodations:
            if accommodation.id == accommodation_id:
                return accommodation
        raise KeyError(accommodation_id)


def _date(value: Any) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def load_registry(path: Path = Path("config/accommodations.toml")) -> Registry:
    with path.open("rb") as handle:
        raw = tomllib.load(handle)
    monitor = raw["monitor"]
    accommodations = tuple(
        Accommodation(
            id=item["id"],
            name=item["name"],
            adapter=item["adapter"],
            booking_url=item["booking_url"],
            search_url=item.get("search_url"),
            limitation=item.get("limitation"),
            season_open_date=(
                _date(item["season_open_date"])
                if item.get("season_open_date")
                else None
            ),
        )
        for item in raw["accommodations"]
    )
    identifiers = [item.id for item in accommodations]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("accommodation IDs must be unique")
    return Registry(
        monitor=MonitorConfig(
            start_date=_date(monitor["start_date"]),
            end_date=_date(monitor["end_date"]),
            party_size=int(monitor["party_size"]),
            host_delay_seconds=float(monitor["host_delay_seconds"]),
        ),
        accommodations=accommodations,
    )

