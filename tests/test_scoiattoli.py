from av1_monitor.checkers.scoiattoli import parse_scoiattoli_search
from av1_monitor.models import AvailabilityStatus


def test_target_shortage_wins_over_suggested_alternative() -> None:
    html = """
    <p>There are not enough beds available for the selected dates</p>
    <p>There are enough beds available by moving the reservation:</p>
    <p>Arrival on 23/06/2027 and departure 24/06/2027</p>
    """
    status, offers, evidence = parse_scoiattoli_search(html, 3)

    assert status is AvailabilityStatus.OPEN_INSUFFICIENT_AVAILABILITY
    assert not offers
    assert "ignored" in evidence[1]


def test_explicit_target_availability_is_positive() -> None:
    status, offers, _ = parse_scoiattoli_search(
        "<p>There are enough beds available for the selected dates</p>", 3
    )

    assert status is AvailabilityStatus.AVAILABLE_FOR_THREE
    assert offers[0].max_selectable == 3


def test_rejected_dates_are_ambiguous() -> None:
    status, _, _ = parse_scoiattoli_search("<p>Dates are wrong</p>", 3)
    assert status is AvailabilityStatus.CANNOT_DETERMINE

