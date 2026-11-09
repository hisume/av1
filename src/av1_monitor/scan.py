"""Date-range scanning, opening-state derivation, throttling, and reports."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, timedelta
from enum import Enum
import json
from pathlib import Path
import time
from urllib.parse import urlparse

from av1_monitor.checkers.factory import create_checker
from av1_monitor.models import AvailabilityStatus, CheckResult
from av1_monitor.registry import Accommodation


class BookingOpeningStatus(str, Enum):
    OPEN = "open"
    NOT_OPEN = "not_open"
    UNKNOWN = "unknown"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class AccommodationScan:
    accommodation: Accommodation
    opening_status: BookingOpeningStatus
    results: tuple[CheckResult, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "accommodation_id": self.accommodation.id,
            "accommodation_name": self.accommodation.name,
            "adapter": self.accommodation.adapter,
            "opening_status": self.opening_status.value,
            "results": [result.to_dict() for result in self.results],
        }


def monitored_dates(start_date: date, end_date: date) -> tuple[date, ...]:
    if end_date < start_date:
        raise ValueError("end date must not precede start date")
    return tuple(
        start_date + timedelta(days=offset)
        for offset in range((end_date - start_date).days + 1)
    )


def derive_opening_status(results: tuple[CheckResult, ...]) -> BookingOpeningStatus:
    statuses = {result.status for result in results}
    open_evidence = {
        AvailabilityStatus.AVAILABLE_FOR_THREE,
        AvailabilityStatus.OPEN_INSUFFICIENT_AVAILABILITY,
        AvailabilityStatus.FULLY_BOOKED,
    }
    if statuses & open_evidence:
        return BookingOpeningStatus.OPEN
    if statuses == {AvailabilityStatus.UNSUPPORTED}:
        return BookingOpeningStatus.UNSUPPORTED
    if AvailabilityStatus.BOOKINGS_NOT_OPEN in statuses and not (
        statuses & {AvailabilityStatus.CANNOT_DETERMINE, AvailabilityStatus.UNSUPPORTED}
    ):
        return BookingOpeningStatus.NOT_OPEN
    return BookingOpeningStatus.UNKNOWN


class HostThrottler:
    def __init__(self, delay_seconds: float) -> None:
        self.delay_seconds = max(0.0, delay_seconds)
        self._last_request: dict[str, float] = {}

    def wait(self, url: str) -> None:
        host = urlparse(url).netloc.lower()
        now = time.monotonic()
        remaining = self.delay_seconds - (now - self._last_request.get(host, 0.0))
        if remaining > 0:
            time.sleep(remaining)
        self._last_request[host] = time.monotonic()


def scan_accommodation(
    accommodation: Accommodation,
    start_date: date,
    end_date: date,
    party_size: int,
    host_delay_seconds: float = 0.5,
    evidence_dir: Path | None = None,
) -> AccommodationScan:
    checker = create_checker(accommodation)
    throttler = HostThrottler(host_delay_seconds)
    nights = monitored_dates(start_date, end_date)
    check_many = getattr(checker, "check_many", None)
    if check_many is not None:
        finalized = tuple(
            check_many(nights, party_size, evidence_dir, host_delay_seconds)
        )
        return AccommodationScan(
            accommodation=accommodation,
            opening_status=derive_opening_status(finalized),
            results=finalized,
        )
    results: list[CheckResult] = []
    for night in nights:
        if accommodation.adapter != "unsupported":
            throttler.wait(accommodation.search_url or accommodation.booking_url)
        result = checker.check(night, party_size, evidence_dir)
        results.append(result)
    finalized = tuple(results)
    return AccommodationScan(
        accommodation=accommodation,
        opening_status=derive_opening_status(finalized),
        results=finalized,
    )


def write_reports(scans: tuple[AccommodationScan, ...], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "scan.json").write_text(
        json.dumps([scan.to_dict() for scan in scans], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    all_dates = sorted(
        {result.check_in for scan in scans for result in scan.results}
    )
    with (output_dir / "availability.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(["date", *(scan.accommodation.id for scan in scans)])
        by_scan = {
            scan.accommodation.id: {
                result.check_in: result.status.value for result in scan.results
            }
            for scan in scans
        }
        for night in all_dates:
            writer.writerow(
                [
                    night.isoformat(),
                    *(by_scan[scan.accommodation.id].get(night, "") for scan in scans),
                ]
            )

    lines = [
        "# AV1 monitor scan",
        "",
        "| Accommodation | Adapter | Booking opening | Available nights | Errors |",
        "|---|---|---|---:|---:|",
    ]
    for scan in scans:
        available = sum(
            result.status is AvailabilityStatus.AVAILABLE_FOR_THREE
            for result in scan.results
        )
        errors = sum(bool(result.error) for result in scan.results)
        lines.append(
            f"| {scan.accommodation.name} | `{scan.accommodation.adapter}` | "
            f"`{scan.opening_status.value}` | {available} | {errors} |"
        )
    (output_dir / "summary.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

