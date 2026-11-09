from datetime import date, timedelta

from av1_monitor.models import AvailabilityStatus, CheckResult
from av1_monitor.registry import Accommodation
from av1_monitor.scan import (
    AccommodationScan,
    BookingOpeningStatus,
    derive_opening_status,
    monitored_dates,
    scan_accommodation,
)


ACCOMMODATION = Accommodation(
    id="test-hut",
    name="Test Hut",
    adapter="unsupported",
    booking_url="https://example.test/booking",
)


def result(status: AvailabilityStatus, night: date = date(2027, 6, 26)) -> CheckResult:
    return CheckResult(
        accommodation_id=ACCOMMODATION.id,
        accommodation_name=ACCOMMODATION.name,
        check_in=night,
        check_out=night + timedelta(days=1),
        party_size=3,
        status=status,
        booking_url=ACCOMMODATION.booking_url,
    )


def test_configured_period_contains_36_nights() -> None:
    nights = monitored_dates(date(2027, 6, 26), date(2027, 7, 31))
    assert len(nights) == 36
    assert nights[0] == date(2027, 6, 26)
    assert nights[-1] == date(2027, 7, 31)


def test_opening_state_is_independent_of_three_bed_availability() -> None:
    statuses = (
        result(AvailabilityStatus.FULLY_BOOKED),
        result(AvailabilityStatus.OPEN_INSUFFICIENT_AVAILABILITY),
    )
    assert derive_opening_status(statuses) is BookingOpeningStatus.OPEN


def test_unknown_errors_do_not_become_not_open() -> None:
    statuses = (
        result(AvailabilityStatus.BOOKINGS_NOT_OPEN),
        result(AvailabilityStatus.CANNOT_DETERMINE),
    )
    assert derive_opening_status(statuses) is BookingOpeningStatus.UNKNOWN


def test_scan_serializes_statuses_for_reports() -> None:
    scan = AccommodationScan(
        accommodation=ACCOMMODATION,
        opening_status=BookingOpeningStatus.OPEN,
        results=(result(AvailabilityStatus.AVAILABLE_FOR_THREE),),
    )
    serialized = scan.to_dict()

    assert serialized["opening_status"] == "open"
    assert serialized["results"][0]["status"] == "available_for_three"


def test_range_scanner_uses_checker_batch_method(monkeypatch) -> None:
    calls = []

    class BatchChecker:
        def check_many(self, nights, party_size, evidence_dir, delay_seconds):
            calls.append((nights, party_size, delay_seconds))
            return tuple(
                result(AvailabilityStatus.FULLY_BOOKED, night) for night in nights
            )

    batch_hut = Accommodation(
        id="batch-hut",
        name="Batch Hut",
        adapter="bukly",
        booking_url="https://example.test/booking",
    )
    monkeypatch.setattr("av1_monitor.scan.create_checker", lambda _: BatchChecker())

    scan = scan_accommodation(
        batch_hut,
        date(2027, 6, 26),
        date(2027, 6, 27),
        party_size=3,
        host_delay_seconds=0.25,
    )

    assert len(calls) == 1
    assert len(calls[0][0]) == 2
    assert len(scan.results) == 2

