from av1_monitor.checkers.dibona import parse_dibona_search
from av1_monitor.models import AvailabilityStatus


def test_enough_result_is_available_without_holding_inventory() -> None:
    status, offers, evidence = parse_dibona_search(
        {"status": "enough", "rooms": [{"id": 1}]}, 3
    )

    assert status is AvailabilityStatus.AVAILABLE_FOR_THREE
    assert offers[0].max_selectable == 3
    assert "did not call" in evidence[1]


def test_blocked_future_day_is_not_called_sold_out() -> None:
    status, _, _ = parse_dibona_search(
        {"available": False, "reason": "BLOCKED_DAYS"}, 3
    )
    assert status is AvailabilityStatus.BOOKINGS_NOT_OPEN


def test_too_little_inventory_is_insufficient() -> None:
    status, _, _ = parse_dibona_search(
        {"status": "too_little_availability_2"}, 3
    )
    assert status is AvailabilityStatus.OPEN_INSUFFICIENT_AVAILABILITY

