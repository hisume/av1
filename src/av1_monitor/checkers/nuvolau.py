"""Monthly inventory parser for Nuvolau's official VikBooking calendar."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from av1_monitor.models import AvailabilityStatus, CheckResult, Offer
from av1_monitor.registry import Accommodation


def parse_nuvolau_month(html: str) -> dict[date, int]:
    totals: dict[date, int] = defaultdict(int)
    pattern = re.compile(
        r'<td\b[^>]*data-cell-date=["\'](\d{2}/\d{2}/\d{4})["\'][^>]*>'
        r'.*?data-units-left=["\'](\d+)["\']',
        re.I | re.S,
    )
    for raw_date, units in pattern.findall(html):
        day = datetime.strptime(raw_date, "%d/%m/%Y").date()
        totals[day] += int(units)
    return dict(totals)


class NuvolauChecker:
    def __init__(self, accommodation: Accommodation) -> None:
        self.accommodation = accommodation
        self._months: dict[tuple[int, int], dict[date, int]] = {}

    def _load_month(self, check_in: date) -> dict[date, int]:
        key = (check_in.year, check_in.month)
        if key in self._months:
            return self._months[key]
        timestamp = int(
            datetime(check_in.year, check_in.month, 1, tzinfo=timezone.utc).timestamp()
        )
        data = urlencode(
            [
                ("month", str(timestamp)),
                ("room_ids[]", "4"),
                ("room_ids[]", "6"),
                ("room_ids[]", "8"),
                ("room_ids[]", "5"),
                ("room_ids[]", "7"),
                ("showtype", "2"),
            ]
        ).encode("ascii")
        request = Request(
            self.accommodation.booking_url,
            data=data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "av1-booking-monitor/0.1 (read-only availability check)",
            },
        )
        with urlopen(request, timeout=30) as response:
            month = parse_nuvolau_month(
                response.read().decode("utf-8", errors="replace")
            )
        self._months[key] = month
        return month

    def check(
        self,
        check_in: date,
        party_size: int,
        evidence_dir: Path | None = None,
    ) -> CheckResult:
        check_out = check_in + timedelta(days=1)
        if (
            self.accommodation.season_open_date
            and date.today() < self.accommodation.season_open_date
        ):
            return self._result(
                check_in,
                check_out,
                party_size,
                AvailabilityStatus.BOOKINGS_NOT_OPEN,
                (
                    f"The official published opening date is {self.accommodation.season_open_date.isoformat()}.",
                ),
            )
        try:
            month = self._load_month(check_in)
            if check_in not in month:
                return self._result(
                    check_in,
                    check_out,
                    party_size,
                    AvailabilityStatus.CANNOT_DETERMINE,
                    ("The requested day was missing from Nuvolau's official monthly calendar.",),
                )
            units = month[check_in]
            if units >= party_size:
                status = AvailabilityStatus.AVAILABLE_FOR_THREE
            elif units > 0:
                status = AvailabilityStatus.OPEN_INSUFFICIENT_AVAILABILITY
            else:
                status = AvailabilityStatus.FULLY_BOOKED
            offers = (
                Offer(
                    description="Bookable bed units across Nuvolau dormitory types",
                    max_selectable=units,
                ),
            ) if units else tuple()
            return CheckResult(
                accommodation_id=self.accommodation.id,
                accommodation_name=self.accommodation.name,
                check_in=check_in,
                check_out=check_out,
                party_size=party_size,
                status=status,
                booking_url=self.accommodation.booking_url,
                evidence=(f"Nuvolau's official calendar reports {units} bed unit(s) left across its bed-based room types.",),
                offers=offers,
            )
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            return self._result(
                check_in,
                check_out,
                party_size,
                AvailabilityStatus.CANNOT_DETERMINE,
                ("Nuvolau's official monthly calendar could not be loaded.",),
                f"{type(exc).__name__}: {exc}",
            )

    def _result(
        self,
        check_in: date,
        check_out: date,
        party_size: int,
        status: AvailabilityStatus,
        evidence: tuple[str, ...],
        error: str | None = None,
    ) -> CheckResult:
        return CheckResult(
            accommodation_id=self.accommodation.id,
            accommodation_name=self.accommodation.name,
            check_in=check_in,
            check_out=check_out,
            party_size=party_size,
            status=status,
            booking_url=self.accommodation.booking_url,
            evidence=evidence,
            error=error,
        )

