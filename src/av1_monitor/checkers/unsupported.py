"""Explicit result for accommodations without public real-time inventory."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from av1_monitor.models import AvailabilityStatus, CheckResult
from av1_monitor.registry import Accommodation


class UnsupportedChecker:
    def __init__(self, accommodation: Accommodation) -> None:
        self.accommodation = accommodation

    def check(
        self,
        check_in: date,
        party_size: int,
        evidence_dir: Path | None = None,
    ) -> CheckResult:
        return CheckResult(
            accommodation_id=self.accommodation.id,
            accommodation_name=self.accommodation.name,
            check_in=check_in,
            check_out=check_in + timedelta(days=1),
            party_size=party_size,
            status=AvailabilityStatus.UNSUPPORTED,
            booking_url=self.accommodation.booking_url,
            evidence=(
                self.accommodation.limitation
                or "No public real-time inventory can verify this accommodation.",
            ),
        )

