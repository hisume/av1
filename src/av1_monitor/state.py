"""Persistent monitor state and transition reduction."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Any

from av1_monitor.models import AvailabilityStatus, CheckResult
from av1_monitor.scan import AccommodationScan, BookingOpeningStatus

SCHEMA_VERSION = 1


class EventType(str, Enum):
    BOOKINGS_OPEN = "bookings_open"
    THREE_BEDS_AVAILABLE = "three_beds_available"


@dataclass(frozen=True)
class MonitorEvent:
    event_type: EventType
    accommodation_id: str
    accommodation_name: str
    booking_url: str
    verified_at: str
    results: tuple[CheckResult, ...]
    generations: tuple[tuple[str, int], ...] = tuple()

    @property
    def event_key(self) -> str:
        if self.event_type is EventType.BOOKINGS_OPEN:
            raw = f"{self.event_type.value}:{self.accommodation_id}"
        else:
            transitions = ",".join(
                f"{night}:{generation}" for night, generation in self.generations
            )
            raw = f"{self.event_type.value}:{self.accommodation_id}:{transitions}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "event_key": self.event_key,
            "accommodation_id": self.accommodation_id,
            "accommodation_name": self.accommodation_name,
            "booking_url": self.booking_url,
            "verified_at": self.verified_at,
            "results": [result.to_dict() for result in self.results],
            "generations": dict(self.generations),
        }


def empty_state(now: datetime | None = None) -> dict[str, Any]:
    timestamp = (now or datetime.now(timezone.utc)).isoformat()
    return {
        "schema_version": SCHEMA_VERSION,
        "initialized_at": timestamp,
        "last_run_at": timestamp,
        "accommodations": {},
    }


def load_state(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(
            f"unsupported state schema {state.get('schema_version')!r}; "
            f"expected {SCHEMA_VERSION}"
        )
    if not isinstance(state.get("accommodations"), dict):
        raise ValueError("state accommodations must be an object")
    return state


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def reduce_scans(
    previous: dict[str, Any] | None,
    scans: tuple[AccommodationScan, ...],
    now: datetime | None = None,
) -> tuple[dict[str, Any], tuple[MonitorEvent, ...]]:
    current_time = now or datetime.now(timezone.utc)
    verified_at = current_time.isoformat()
    state = deepcopy(previous) if previous is not None else empty_state(current_time)
    state["last_run_at"] = verified_at
    accommodations: dict[str, Any] = state["accommodations"]
    events: list[MonitorEvent] = []

    for scan in scans:
        identifier = scan.accommodation.id
        is_new = identifier not in accommodations
        record = accommodations.setdefault(
            identifier,
            {
                "name": scan.accommodation.name,
                "booking_url": scan.accommodation.booking_url,
                "opening": {
                    "current": BookingOpeningStatus.UNKNOWN.value,
                    "alerted": False,
                    "first_verified_at": None,
                    "last_observed_at": None,
                },
                "nights": {},
            },
        )
        record["name"] = scan.accommodation.name
        record["booking_url"] = scan.accommodation.booking_url
        opening = record["opening"]
        prior_opening = opening.get("current", BookingOpeningStatus.UNKNOWN.value)
        observed_opening = scan.opening_status.value
        opening["last_observation"] = observed_opening
        opening["last_observed_at"] = verified_at

        if scan.opening_status is BookingOpeningStatus.OPEN:
            if opening.get("first_verified_at") is None:
                opening["first_verified_at"] = verified_at
            if is_new:
                # Existing openings form the initial baseline and must not
                # produce retroactive Monitor A alerts.
                opening["alerted"] = True
                opening["baseline_suppressed"] = True
            elif prior_opening != BookingOpeningStatus.OPEN.value and not opening.get(
                "alerted", False
            ):
                conclusive = tuple(
                    result
                    for result in scan.results
                    if result.status
                    in {
                        AvailabilityStatus.AVAILABLE_FOR_THREE,
                        AvailabilityStatus.OPEN_INSUFFICIENT_AVAILABILITY,
                        AvailabilityStatus.FULLY_BOOKED,
                    }
                )
                events.append(
                    MonitorEvent(
                        event_type=EventType.BOOKINGS_OPEN,
                        accommodation_id=identifier,
                        accommodation_name=scan.accommodation.name,
                        booking_url=scan.accommodation.booking_url,
                        verified_at=verified_at,
                        results=conclusive,
                    )
                )
                opening["alerted"] = True
            opening["current"] = BookingOpeningStatus.OPEN.value
        elif scan.opening_status in {
            BookingOpeningStatus.NOT_OPEN,
            BookingOpeningStatus.UNSUPPORTED,
        }:
            opening["current"] = observed_opening
        # UNKNOWN is an observation failure and does not erase the last
        # conclusive opening state.

        newly_available: list[CheckResult] = []
        generations: list[tuple[str, int]] = []
        nights: dict[str, Any] = record["nights"]
        for result in scan.results:
            night = result.check_in.isoformat()
            night_record = nights.setdefault(
                night,
                {
                    "available": False,
                    "availability_generation": 0,
                    "last_successful_status": None,
                    "last_successful_at": None,
                },
            )
            night_record["last_attempt_status"] = result.status.value
            night_record["last_attempt_at"] = result.checked_at.isoformat()
            night_record["last_error"] = result.error

            if result.status is AvailabilityStatus.CANNOT_DETERMINE:
                continue

            was_available = bool(night_record.get("available", False))
            is_available = result.status is AvailabilityStatus.AVAILABLE_FOR_THREE
            if is_available and not was_available:
                generation = int(
                    night_record.get("availability_generation", 0)
                ) + 1
                night_record["availability_generation"] = generation
                newly_available.append(result)
                generations.append((night, generation))
            night_record["available"] = is_available
            night_record["last_successful_status"] = result.status.value
            night_record["last_successful_at"] = result.checked_at.isoformat()
            night_record["last_evidence"] = list(result.evidence)
            night_record["last_offers"] = [
                {
                    "description": offer.description,
                    "max_selectable": offer.max_selectable,
                    "price": offer.price,
                }
                for offer in result.offers
            ]

        if newly_available:
            events.append(
                MonitorEvent(
                    event_type=EventType.THREE_BEDS_AVAILABLE,
                    accommodation_id=identifier,
                    accommodation_name=scan.accommodation.name,
                    booking_url=scan.accommodation.booking_url,
                    verified_at=verified_at,
                    results=tuple(newly_available),
                    generations=tuple(generations),
                )
            )

    return state, tuple(events)

