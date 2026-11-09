"""Read-only API checker for Rifugio Angelo Dibona."""

from __future__ import annotations

from datetime import date, timedelta
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from av1_monitor.models import AvailabilityStatus, CheckResult, Offer
from av1_monitor.registry import Accommodation


def parse_dibona_search(
    payload: dict[str, object], party_size: int
) -> tuple[AvailabilityStatus, tuple[Offer, ...], tuple[str, ...]]:
    status = str(payload.get("status", ""))
    reason = str(payload.get("reason", ""))
    if status == "enough" and payload.get("rooms"):
        rooms = payload["rooms"]
        count = len(rooms) if isinstance(rooms, list) else 1
        return (
            AvailabilityStatus.AVAILABLE_FOR_THREE,
            (Offer(description=f"{count} compatible Dibona room/bed option(s)", max_selectable=party_size),),
            (
                "Dibona's official read-only search returned enough inventory for the requested party.",
                "The checker did not call the separate /api/booking-hold endpoint.",
            ),
        )
    if status == "sold_out":
        return (
            AvailabilityStatus.FULLY_BOOKED,
            tuple(),
            ("Dibona's official search returned sold_out.",),
        )
    if status.startswith("too_little_availability"):
        return (
            AvailabilityStatus.OPEN_INSUFFICIENT_AVAILABILITY,
            tuple(),
            ("Dibona's official search returned insufficient inventory for the requested party.",),
        )
    if payload.get("available") is False and reason == "BLOCKED_DAYS":
        return (
            AvailabilityStatus.BOOKINGS_NOT_OPEN,
            tuple(),
            ("Dibona's official search marks the requested date as blocked rather than sold out.",),
        )
    return (
        AvailabilityStatus.CANNOT_DETERMINE,
        tuple(),
        (f"Dibona returned an unrecognized result (status={status!r}, reason={reason!r}).",),
    )


class DibonaChecker:
    def __init__(self, accommodation: Accommodation) -> None:
        self.accommodation = accommodation

    def check(
        self,
        check_in: date,
        party_size: int,
        evidence_dir: Path | None = None,
    ) -> CheckResult:
        check_out = check_in + timedelta(days=1)
        guests = json.dumps([{"type": "adult", "count": party_size}], separators=(",", ":"))
        query = urlencode(
            {
                "checkIn": check_in.isoformat(),
                "checkOut": check_out.isoformat(),
                "guests": guests,
            }
        )
        request = Request(
            f"{self.accommodation.search_url}?{query}",
            headers={"User-Agent": "av1-booking-monitor/0.1 (read-only availability check)"},
        )
        try:
            with urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
            status, offers, evidence = parse_dibona_search(payload, party_size)
            return CheckResult(
                accommodation_id=self.accommodation.id,
                accommodation_name=self.accommodation.name,
                check_in=check_in,
                check_out=check_out,
                party_size=party_size,
                status=status,
                booking_url=self.accommodation.booking_url,
                evidence=evidence,
                offers=offers,
            )
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
            return CheckResult(
                accommodation_id=self.accommodation.id,
                accommodation_name=self.accommodation.name,
                check_in=check_in,
                check_out=check_out,
                party_size=party_size,
                status=AvailabilityStatus.CANNOT_DETERMINE,
                booking_url=self.accommodation.booking_url,
                evidence=("Dibona's official search API could not be read.",),
                error=f"{type(exc).__name__}: {exc}",
            )

