"""Browser checker for Averau's Bukly booking engine."""

from __future__ import annotations

import re
from datetime import date, timedelta
from pathlib import Path
import time

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from av1_monitor.models import AvailabilityStatus, CheckResult
from av1_monitor.registry import Accommodation

BOOKING_URL = "https://rifugioaverau.bukly.com/booking"
ITALIAN_MONTHS = (
    "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
    "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre",
)


def classify_bukly_results(text: str) -> tuple[AvailabilityStatus, tuple[str, ...]]:
    normalized = " ".join(text.lower().split())
    incompatible = (
        "non abbiamo trovato" in normalized and "compatibil" in normalized
    )
    alternatives = "opzioni alternative suggerite" in normalized
    selectable = "seleziona" in normalized
    if incompatible and alternatives and selectable:
        return (
            AvailabilityStatus.OPEN_INSUFFICIENT_AVAILABILITY,
            ("Bukly returned only alternative offers, not an offer compatible with the three-person search.",),
        )
    if incompatible or "nessuna disponibilità" in normalized:
        return (
            AvailabilityStatus.FULLY_BOOKED,
            ("Bukly explicitly returned no compatible availability.",),
        )
    if selectable:
        return (
            AvailabilityStatus.AVAILABLE_FOR_THREE,
            ("Bukly returned a selectable offer compatible with the requested dates and occupancy.",),
        )
    return (
        AvailabilityStatus.CANNOT_DETERMINE,
        ("Bukly did not return a recognized search result.",),
    )


def classify_disabled_date(
    target_day: int, enabled_days_in_month: list[int]
) -> tuple[AvailabilityStatus, tuple[str, ...]]:
    """Distinguish an unreleased calendar frontier from an isolated sold-out day."""
    if any(day > target_day for day in enabled_days_in_month):
        return (
            AvailabilityStatus.FULLY_BOOKED,
            ("The requested arrival is disabled while a later date in the same released month is selectable.",),
        )
    if enabled_days_in_month:
        return (
            AvailabilityStatus.BOOKINGS_NOT_OPEN,
            ("Bukly's selectable calendar dates stop before the requested arrival, indicating the target period has not been released.",),
        )
    return (
        AvailabilityStatus.CANNOT_DETERMINE,
        ("The requested arrival and all visible dates in its month are disabled; opening state is ambiguous.",),
    )


class AverauChecker:
    def __init__(self, accommodation: Accommodation | None = None) -> None:
        self.accommodation = accommodation or Accommodation(
            id="averau",
            name="Rifugio Averau",
            adapter="bukly",
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
        return self.check_many((check_in,), party_size, evidence_dir)[0]

    def check_many(
        self,
        nights: tuple[date, ...],
        party_size: int,
        evidence_dir: Path | None = None,
        delay_seconds: float = 0.5,
    ) -> tuple[CheckResult, ...]:
        """Reuse one Chromium process and page across a range scan."""
        results: list[CheckResult] = []
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 1200})
                for index, check_in in enumerate(nights):
                    if index and delay_seconds > 0:
                        time.sleep(delay_seconds)
                    try:
                        results.append(
                            self._check_on_page(
                                page, check_in, party_size, evidence_dir
                            )
                        )
                    except (PlaywrightError, OSError, RuntimeError) as exc:
                        results.append(
                            self._failure(check_in, party_size, exc)
                        )
                browser.close()
        except (PlaywrightError, OSError, RuntimeError) as exc:
            return tuple(self._failure(night, party_size, exc) for night in nights)
        return tuple(results)

    def _check_on_page(
        self,
        page,
        check_in: date,
        party_size: int,
        evidence_dir: Path | None,
    ) -> CheckResult:
        check_out = check_in + timedelta(days=1)
        screenshot: str | None = None
        page.goto(self.booking_url, wait_until="networkidle", timeout=90_000)
        page.locator("input.v-field__input").nth(0).click()

        target_label = f"{check_in.day} {ITALIAN_MONTHS[check_in.month - 1]} {check_in.year}"
        target = page.locator(f'[aria-label$="{target_label}"]:visible')
        for _ in range(25):
            if target.count():
                break
            next_button = page.locator(
                ".v-overlay--active button.rounded-lg:visible"
            ).nth(1)
            if not next_button.count() or next_button.is_disabled():
                break
            next_button.click()
            page.wait_for_timeout(150)

        if not target.count():
            return self._result(
                check_in,
                check_out,
                party_size,
                AvailabilityStatus.BOOKINGS_NOT_OPEN,
                ("The target month could not be reached in Bukly's released calendar.",),
            )

        if evidence_dir:
            evidence_dir.mkdir(parents=True, exist_ok=True)
            output = evidence_dir / f"{self.accommodation_id}-{check_in.isoformat()}-calendar.png"
            page.screenshot(path=output, full_page=False)
            screenshot = str(output)

        if target.first.is_disabled():
            month_suffix = f"{ITALIAN_MONTHS[check_in.month - 1]} {check_in.year}"
            month_days = page.locator(
                f'button.v-date-picker-month__day-btn[aria-label$="{month_suffix}"]:visible'
            )
            enabled_labels = month_days.evaluate_all(
                "buttons => buttons.filter(button => !button.disabled).map(button => button.getAttribute('aria-label'))"
            )
            enabled_days = []
            for label in enabled_labels:
                match = re.search(rf"(\d+) {re.escape(month_suffix)}$", label or "")
                if match:
                    enabled_days.append(int(match.group(1)))
            status, evidence = classify_disabled_date(check_in.day, enabled_days)
            return self._result(
                check_in,
                check_out,
                party_size,
                status,
                evidence + ("No search or reservation was submitted.",),
                screenshot,
            )

        target.first.click()
        checkout_label = f"{check_out.day} {ITALIAN_MONTHS[check_out.month - 1]} {check_out.year}"
        checkout = page.locator(f'[aria-label$="{checkout_label}"]:visible')
        if not checkout.count() or checkout.first.is_disabled():
            return self._result(
                check_in,
                check_out,
                party_size,
                AvailabilityStatus.FULLY_BOOKED,
                ("The requested checkout boundary is not selectable in Bukly.",),
                screenshot,
            )
        checkout.first.click()

        page.locator("input.v-field__input").nth(1).click()
        guest_overlay = page.locator(".v-overlay--active")
        current_text = page.locator("input.v-field__input").nth(1).input_value()
        current_match = re.search(r"(\d+)", current_text)
        current_adults = int(current_match.group(1)) if current_match else 2
        adult_plus = guest_overlay.locator("button.rounded-full:visible").nth(1)
        for _ in range(max(0, party_size - current_adults)):
            adult_plus.click()
        guest_overlay.get_by_role("button", name="Conferma", exact=True).click()

        page.get_by_role("button", name="Cerca", exact=True).click()
        page.wait_for_load_state("networkidle", timeout=90_000)
        page.wait_for_timeout(500)
        text = page.locator("body").inner_text()
        status, evidence = classify_bukly_results(text)
        if evidence_dir:
            output = evidence_dir / f"{self.accommodation_id}-{check_in.isoformat()}-result.png"
            page.screenshot(path=output, full_page=True)
            screenshot = str(output)
        return self._result(
            check_in, check_out, party_size, status, evidence, screenshot
        )

    def _failure(
        self, check_in: date, party_size: int, exc: Exception
    ) -> CheckResult:
        return self._result(
            check_in,
            check_in + timedelta(days=1),
            party_size,
            AvailabilityStatus.CANNOT_DETERMINE,
            ("The Bukly browser check failed before a conclusive result.",),
            error=f"{type(exc).__name__}: {exc}",
        )

    def _result(
        self,
        check_in: date,
        check_out: date,
        party_size: int,
        status: AvailabilityStatus,
        evidence: tuple[str, ...],
        screenshot: str | None = None,
        error: str | None = None,
    ) -> CheckResult:
        return CheckResult(
            accommodation_id=self.accommodation_id,
            accommodation_name=self.accommodation_name,
            check_in=check_in,
            check_out=check_out,
            party_size=party_size,
            status=status,
            booking_url=self.booking_url,
            evidence=evidence,
            screenshot=screenshot,
            error=error,
        )


BuklyChecker = AverauChecker

