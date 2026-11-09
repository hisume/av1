"""Normalized checker results shared by every booking-system adapter."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any


class AvailabilityStatus(str, Enum):
    BOOKINGS_NOT_OPEN = "bookings_not_open"
    AVAILABLE_FOR_THREE = "available_for_three"
    OPEN_INSUFFICIENT_AVAILABILITY = "open_insufficient_availability"
    FULLY_BOOKED = "fully_booked"
    CANNOT_DETERMINE = "cannot_determine"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class Offer:
    description: str
    max_selectable: int | None = None
    price: str | None = None


@dataclass(frozen=True)
class CheckResult:
    accommodation_id: str
    accommodation_name: str
    check_in: date
    check_out: date
    party_size: int
    status: AvailabilityStatus
    booking_url: str
    evidence: tuple[str, ...] = field(default_factory=tuple)
    offers: tuple[Offer, ...] = field(default_factory=tuple)
    error: str | None = None
    screenshot: str | None = None
    checked_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["status"] = self.status.value
        value["check_in"] = self.check_in.isoformat()
        value["check_out"] = self.check_out.isoformat()
        value["checked_at"] = self.checked_at.isoformat()
        return value

