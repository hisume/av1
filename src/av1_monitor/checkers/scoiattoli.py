"""Read-only checker for Scoiattoli's custom GET booking search."""

from __future__ import annotations

from datetime import date, timedelta
from html import unescape
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from av1_monitor.models import AvailabilityStatus, CheckResult, Offer
from av1_monitor.registry import Accommodation


def _text(html: str) -> str:
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", html)).split()).lower()


def parse_scoiattoli_search(
    html: str, party_size: int
) -> tuple[AvailabilityStatus, tuple[Offer, ...], tuple[str, ...]]:
    text = _text(html)
    if "not enough beds available for the selected dates" in text:
        return (
            AvailabilityStatus.OPEN_INSUFFICIENT_AVAILABILITY,
            tuple(),
            (
                "The official search reported too few beds for the requested party on the selected dates.",
                "Suggested alternative dates were ignored.",
            ),
        )
    if "enough beds available for the selected dates" in text:
        return (
            AvailabilityStatus.AVAILABLE_FOR_THREE,
            (Offer(description=f"Beds for {party_size} adults", max_selectable=party_size),),
            ("The official search explicitly reported enough beds for the requested party and dates.",),
        )
    if "no beds available for the selected dates" in text:
        return (
            AvailabilityStatus.FULLY_BOOKED,
            tuple(),
            ("The official search explicitly reported no beds for the selected dates.",),
        )
    if "dates are wrong" in text:
        return (
            AvailabilityStatus.CANNOT_DETERMINE,
            tuple(),
            ("Scoiattoli rejected the submitted dates.",),
        )
    return (
        AvailabilityStatus.CANNOT_DETERMINE,
        tuple(),
        ("Scoiattoli did not return a recognized target-date result.",),
    )


class ScoiattoliChecker:
    def __init__(self, accommodation: Accommodation) -> None:
        self.accommodation = accommodation

    def check(
        self,
        check_in: date,
        party_size: int,
        evidence_dir: Path | None = None,
    ) -> CheckResult:
        check_out = check_in + timedelta(days=1)
        query = urlencode(
            {
                "action": "invia",
                "arrivo": f"{check_in.day} {check_in.strftime('%B')}, {check_in.year}",
                "arrivo_insert": check_in.isoformat(),
                "partenza": f"{check_out.day} {check_out.strftime('%B')}, {check_out.year}",
                "partenza_insert": check_out.isoformat(),
                "nadulti": str(party_size),
                "nbambini_3_12": "0",
            }
        )
        request = Request(
            f"{self.accommodation.booking_url}?{query}",
            headers={"User-Agent": "av1-booking-monitor/0.1 (read-only availability check)"},
        )
        try:
            with urlopen(request, timeout=30) as response:
                html = response.read().decode("utf-8", errors="replace")
            status, offers, evidence = parse_scoiattoli_search(html, party_size)
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
        except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
            return CheckResult(
                accommodation_id=self.accommodation.id,
                accommodation_name=self.accommodation.name,
                check_in=check_in,
                check_out=check_out,
                party_size=party_size,
                status=AvailabilityStatus.CANNOT_DETERMINE,
                booking_url=self.accommodation.booking_url,
                evidence=("Scoiattoli's official search could not be loaded.",),
                error=f"{type(exc).__name__}: {exc}",
            )

