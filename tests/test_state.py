from datetime import date, datetime, timedelta, timezone

from av1_monitor.models import AvailabilityStatus, CheckResult
from av1_monitor.registry import Accommodation
from av1_monitor.scan import AccommodationScan, BookingOpeningStatus
from av1_monitor.state import EventType, reduce_scans


HUT = Accommodation(
    id="test-hut",
    name="Test Hut",
    adapter="php",
    booking_url="https://example.test/booking",
    search_url="https://example.test/search",
)
NIGHT = date(2027, 6, 26)
NOW = datetime(2026, 11, 9, 16, 0, tzinfo=timezone.utc)


def make_result(status: AvailabilityStatus, night: date = NIGHT) -> CheckResult:
    return CheckResult(
        accommodation_id=HUT.id,
        accommodation_name=HUT.name,
        check_in=night,
        check_out=night + timedelta(days=1),
        party_size=3,
        status=status,
        booking_url=HUT.booking_url,
        error="temporary failure" if status is AvailabilityStatus.CANNOT_DETERMINE else None,
        checked_at=NOW,
    )


def make_scan(
    status: AvailabilityStatus,
    opening: BookingOpeningStatus,
) -> AccommodationScan:
    return AccommodationScan(HUT, opening, (make_result(status),))


def test_first_open_run_suppresses_opening_but_alerts_current_availability() -> None:
    state, events = reduce_scans(
        None,
        (make_scan(AvailabilityStatus.AVAILABLE_FOR_THREE, BookingOpeningStatus.OPEN),),
        NOW,
    )

    assert [event.event_type for event in events] == [EventType.THREE_BEDS_AVAILABLE]
    assert state["accommodations"][HUT.id]["opening"]["baseline_suppressed"]
    assert state["accommodations"][HUT.id]["nights"][NIGHT.isoformat()][
        "availability_generation"
    ] == 1


def test_unchanged_availability_does_not_repeat_alert() -> None:
    state, _ = reduce_scans(
        None,
        (make_scan(AvailabilityStatus.AVAILABLE_FOR_THREE, BookingOpeningStatus.OPEN),),
        NOW,
    )
    _, events = reduce_scans(
        state,
        (make_scan(AvailabilityStatus.AVAILABLE_FOR_THREE, BookingOpeningStatus.OPEN),),
        NOW + timedelta(hours=1),
    )
    assert not events


def test_availability_reappearance_increments_generation_and_alerts_again() -> None:
    state, _ = reduce_scans(
        None,
        (make_scan(AvailabilityStatus.AVAILABLE_FOR_THREE, BookingOpeningStatus.OPEN),),
        NOW,
    )
    state, _ = reduce_scans(
        state,
        (make_scan(AvailabilityStatus.FULLY_BOOKED, BookingOpeningStatus.OPEN),),
        NOW + timedelta(hours=1),
    )
    state, events = reduce_scans(
        state,
        (make_scan(AvailabilityStatus.AVAILABLE_FOR_THREE, BookingOpeningStatus.OPEN),),
        NOW + timedelta(hours=2),
    )

    assert [event.event_type for event in events] == [EventType.THREE_BEDS_AVAILABLE]
    assert events[0].generations == ((NIGHT.isoformat(), 2),)
    assert state["accommodations"][HUT.id]["nights"][NIGHT.isoformat()][
        "availability_generation"
    ] == 2


def test_new_opening_after_not_open_alerts_only_once() -> None:
    state, events = reduce_scans(
        None,
        (make_scan(AvailabilityStatus.BOOKINGS_NOT_OPEN, BookingOpeningStatus.NOT_OPEN),),
        NOW,
    )
    assert not events

    state, events = reduce_scans(
        state,
        (make_scan(AvailabilityStatus.FULLY_BOOKED, BookingOpeningStatus.OPEN),),
        NOW + timedelta(hours=1),
    )
    assert [event.event_type for event in events] == [EventType.BOOKINGS_OPEN]

    _, events = reduce_scans(
        state,
        (make_scan(AvailabilityStatus.FULLY_BOOKED, BookingOpeningStatus.OPEN),),
        NOW + timedelta(hours=2),
    )
    assert not events


def test_failed_check_preserves_last_success_and_availability_state() -> None:
    state, _ = reduce_scans(
        None,
        (make_scan(AvailabilityStatus.AVAILABLE_FOR_THREE, BookingOpeningStatus.OPEN),),
        NOW,
    )
    state, events = reduce_scans(
        state,
        (make_scan(AvailabilityStatus.CANNOT_DETERMINE, BookingOpeningStatus.UNKNOWN),),
        NOW + timedelta(hours=1),
    )
    night = state["accommodations"][HUT.id]["nights"][NIGHT.isoformat()]

    assert not events
    assert night["available"] is True
    assert night["last_successful_status"] == "available_for_three"
    assert night["last_attempt_status"] == "cannot_determine"
    assert state["accommodations"][HUT.id]["opening"]["current"] == "open"


def test_event_key_is_stable_for_retry_but_changes_for_reappearance() -> None:
    state, first_events = reduce_scans(
        None,
        (make_scan(AvailabilityStatus.AVAILABLE_FOR_THREE, BookingOpeningStatus.OPEN),),
        NOW,
    )
    _, retry_events = reduce_scans(
        None,
        (make_scan(AvailabilityStatus.AVAILABLE_FOR_THREE, BookingOpeningStatus.OPEN),),
        NOW + timedelta(hours=1),
    )
    assert first_events[0].event_key == retry_events[0].event_key

    state, _ = reduce_scans(
        state,
        (make_scan(AvailabilityStatus.FULLY_BOOKED, BookingOpeningStatus.OPEN),),
        NOW + timedelta(hours=1),
    )
    _, second_events = reduce_scans(
        state,
        (make_scan(AvailabilityStatus.AVAILABLE_FOR_THREE, BookingOpeningStatus.OPEN),),
        NOW + timedelta(hours=2),
    )
    assert first_events[0].event_key != second_events[0].event_key

