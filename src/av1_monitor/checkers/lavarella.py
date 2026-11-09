"""Conservative checker for Lavarella's Booking Südtirol widget."""

from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from av1_monitor.models import AvailabilityStatus, CheckResult
from av1_monitor.registry import Accommodation

BOOKING_URL = "https://lavarella.it/en/book-online"
WIDGET_ERROR = "unexpected error occurred while loading the booking widget"


def classify_lavarella_widget(text: str) -> tuple[AvailabilityStatus, tuple[str, ...]]:
    normalized = " ".join(text.lower().split())
    if WIDGET_ERROR in normalized:
        return (
            AvailabilityStatus.CANNOT_DETERMINE,
            ("The official Booking Südtirol widget displayed a loading error before a search could be made.",),
        )
    return (
        AvailabilityStatus.CANNOT_DETERMINE,
        ("The Booking Südtirol widget loaded, but this prototype did not recognize a safe, conclusive result.",),
    )


class LavarellaChecker:
    def __init__(self, accommodation: Accommodation | None = None) -> None:
        self.accommodation = accommodation or Accommodation(
            id="lavarella",
            name="Rifugio Lavarella",
            adapter="booking_suedtirol",
            booking_url=BOOKING_URL,
        )
        self.accommodation_id = self.accommodation.id
        self.accommodation_name = self.accommodation.name
        self.booking_url = self.accommodation.booking_url

    def check(
        self,
        check_in: date,
        party_size: int,
        evidence_dir: Path | None = None,
    ) -> CheckResult:
        check_out = check_in + timedelta(days=1)
        screenshot: str | None = None
        api_failure: list[str] = []
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 1200})
                page.on(
                    "requestfailed",
                    lambda request: api_failure.append(
                        f"{request.url}: {request.failure}"
                    )
                    if "api.widgets.bookingsuedtirol.com" in request.url
                    else None,
                )
                page.goto(self.booking_url, wait_until="networkidle", timeout=90_000)
                text = page.locator("body").inner_text()
                status, evidence = classify_lavarella_widget(text)
                if api_failure:
                    evidence += (
                        "The widget's official API request failed in the browser; this is an integration failure, not proof of no inventory.",
                    )
                if evidence_dir:
                    evidence_dir.mkdir(parents=True, exist_ok=True)
                    output = evidence_dir / f"{self.accommodation_id}-{check_in.isoformat()}-widget.png"
                    widget = page.locator("#Bs-BookingWidget")
                    if widget.count():
                        widget.screenshot(path=output)
                    else:
                        page.screenshot(path=output, full_page=False)
                    screenshot = str(output)
                browser.close()
                return CheckResult(
                    accommodation_id=self.accommodation_id,
                    accommodation_name=self.accommodation_name,
                    check_in=check_in,
                    check_out=check_out,
                    party_size=party_size,
                    status=status,
                    booking_url=self.booking_url,
                    evidence=evidence,
                    error=api_failure[0] if api_failure else None,
                    screenshot=screenshot,
                )
        except (PlaywrightError, OSError, RuntimeError) as exc:
            return CheckResult(
                accommodation_id=self.accommodation_id,
                accommodation_name=self.accommodation_name,
                check_in=check_in,
                check_out=check_out,
                party_size=party_size,
                status=AvailabilityStatus.CANNOT_DETERMINE,
                booking_url=self.booking_url,
                evidence=("The Booking Südtirol browser check failed before a conclusive result.",),
                error=f"{type(exc).__name__}: {exc}",
                screenshot=screenshot,
            )

    def check_many(
        self,
        nights: tuple[date, ...],
        party_size: int,
        evidence_dir: Path | None = None,
        delay_seconds: float = 0.5,
    ) -> tuple[CheckResult, ...]:
        """Probe the system-level widget once; it currently has no date UI."""
        if not nights:
            return tuple()
        probe = self.check(nights[0], party_size, evidence_dir)
        return tuple(
            replace(
                probe,
                check_in=night,
                check_out=night + timedelta(days=1),
            )
            for night in nights
        )


BookingSuedtirolChecker = LavarellaChecker

