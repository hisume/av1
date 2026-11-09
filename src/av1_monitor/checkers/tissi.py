"""Read-only checker for Tissi's server-rendered booking search."""

from __future__ import annotations

import re
from datetime import date, timedelta
from html import unescape
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from av1_monitor.models import AvailabilityStatus, CheckResult, Offer
from av1_monitor.registry import Accommodation

BOOKING_URL = "https://www.rifugiotissi.com/EN/disponibilita.php"
SEARCH_URL = "https://www.rifugiotissi.com/EN/prenotazione1.php"


def _plain_text(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value)
    return " ".join(unescape(without_tags).split())


def parse_php_search(html: str, party_size: int) -> tuple[AvailabilityStatus, tuple[Offer, ...], tuple[str, ...]]:
    """Classify a shared PHP-family response without entering step two."""
    next_step = bool(
        re.search(r"<form\b[^>]*action=[\"'][^\"']*prenotazione2\.php", html, re.I)
    )
    offers: list[Offer] = []
    selects = re.finditer(
        r"<select\b[^>]*name=[\"']nAlloggi\d+[\"'][^>]*>(.*?)</select>",
        html,
        re.I | re.S,
    )
    for select in selects:
        values = [
            int(value)
            for value in re.findall(
                r"<option\b[^>]*value=[\"']?(\d+)", select.group(1), re.I
            )
        ]
        prefix = html[max(0, select.start() - 2_000) : select.start()]
        block_start = max(
            prefix.lower().rfind('class="quadrocamere'),
            prefix.lower().rfind("class='quadrocamere"),
        )
        context = prefix[block_start:] if block_start >= 0 else prefix
        descriptions = re.findall(
            r"<p\b[^>]*>(.*?)(?:<br\b|</p>)", context, re.I | re.S
        )
        # The first paragraph in each room block is the room name; later
        # paragraphs contain the generic "Select number of beds" label.
        description_match = descriptions[0] if descriptions else None
        description = _plain_text(description_match) if description_match else "Selectable accommodation"
        offers.append(Offer(description=description, max_selectable=max(values, default=0)))

    selectable_capacity = sum(offer.max_selectable or 0 for offer in offers)
    if next_step and selectable_capacity >= party_size:
        evidence = (
            f"Official search returned selectable capacity for {party_size} people across {len(offers)} offer(s).",
            "The checker stopped before prenotazione2.php; no room was held.",
        )
        return AvailabilityStatus.AVAILABLE_FOR_THREE, tuple(offers), evidence

    normalized = _plain_text(html).lower()
    no_inventory_phrases = (
        "no availability",
        "no accommodation available",
        "do not have any room available",
        "not have any room available",
        "non ci sono disponibilità",
        "nessuna disponibilità",
        "abbiamo esaurito i posti letto",
        "posti letto esauriti",
    )
    if any(phrase in normalized for phrase in no_inventory_phrases):
        return (
            AvailabilityStatus.FULLY_BOOKED,
            tuple(),
            ("The official search explicitly returned no availability.",),
        )
    if next_step and offers:
        return (
            AvailabilityStatus.OPEN_INSUFFICIENT_AVAILABILITY,
            tuple(offers),
            (f"Offers were returned, but none allowed {party_size} people.",),
        )
    not_open_phrases = (
        "bookings are not open",
        "reservations are not open",
        "prenotazioni non sono aperte",
        "prenotazioni apriranno",
        "booking non ancora aperto",
    )
    if any(phrase in normalized for phrase in not_open_phrases):
        return (
            AvailabilityStatus.BOOKINGS_NOT_OPEN,
            tuple(),
            ("The official search states that bookings are not open.",),
        )
    return (
        AvailabilityStatus.CANNOT_DETERMINE,
        tuple(offers),
        ("The response did not contain a recognized availability result.",),
    )


# Backwards-compatible name used by the Phase 2 fixtures.
parse_tissi_search = parse_php_search


class TissiChecker:
    def __init__(self, accommodation: Accommodation | None = None) -> None:
        self.accommodation = accommodation or Accommodation(
            id="tissi",
            name="Rifugio Tissi",
            adapter="php",
            booking_url=BOOKING_URL,
            search_url=SEARCH_URL,
        )
        self.accommodation_id = self.accommodation.id
        self.accommodation_name = self.accommodation.name
        self.booking_url = self.accommodation.booking_url
        self.search_url = self.accommodation.search_url or SEARCH_URL

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
            return CheckResult(
                accommodation_id=self.accommodation_id,
                accommodation_name=self.accommodation_name,
                check_in=check_in,
                check_out=check_out,
                party_size=party_size,
                status=AvailabilityStatus.BOOKINGS_NOT_OPEN,
                booking_url=self.booking_url,
                evidence=(
                    "The official announcement places the opening in "
                    f"{self.accommodation.season_open_date.strftime('%B %Y')}; "
                    "the booking system's placeholder no-inventory response is not treated as sold out.",
                ),
            )
        data = urlencode(
            {
                "codAgenzia": "0",
                "arrivo": check_in.strftime("%d/%m/%Y"),
                "partenza": check_out.strftime("%d/%m/%Y"),
                "persone": str(party_size),
            }
        ).encode("ascii")
        request = Request(
            self.search_url,
            data=data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "av1-booking-monitor/0.1 (read-only availability check)",
            },
        )
        try:
            with urlopen(request, timeout=30) as response:
                html = response.read().decode("utf-8", errors="replace")
            status, offers, evidence = parse_php_search(html, party_size)
            return CheckResult(
                accommodation_id=self.accommodation_id,
                accommodation_name=self.accommodation_name,
                check_in=check_in,
                check_out=check_out,
                party_size=party_size,
                status=status,
                booking_url=self.booking_url,
                offers=offers,
                evidence=evidence,
            )
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            return CheckResult(
                accommodation_id=self.accommodation_id,
                accommodation_name=self.accommodation_name,
                check_in=check_in,
                check_out=check_out,
                party_size=party_size,
                status=AvailabilityStatus.CANNOT_DETERMINE,
                booking_url=self.booking_url,
                evidence=("The official search could not be loaded.",),
                error=f"{type(exc).__name__}: {exc}",
            )


PhpChecker = TissiChecker

