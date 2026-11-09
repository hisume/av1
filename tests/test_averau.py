from av1_monitor.checkers.averau import classify_bukly_results, classify_disabled_date
from av1_monitor.models import AvailabilityStatus


def test_compatible_selectable_offer_is_available() -> None:
    status, _ = classify_bukly_results("Camera compatibile con la ricerca Seleziona")
    assert status is AvailabilityStatus.AVAILABLE_FOR_THREE


def test_alternatives_are_not_positive_availability() -> None:
    text = (
        "Non abbiamo trovato Camera(i) compatibile con la tua ricerca. "
        "Opzioni alternative suggerite Dormitorio Seleziona"
    )
    status, _ = classify_bukly_results(text)
    assert status is AvailabilityStatus.OPEN_INSUFFICIENT_AVAILABILITY


def test_unrecognized_page_is_ambiguous() -> None:
    status, _ = classify_bukly_results("Benvenuto al Rifugio Averau")
    assert status is AvailabilityStatus.CANNOT_DETERMINE


def test_calendar_frontier_means_bookings_not_open() -> None:
    status, _ = classify_disabled_date(target_day=26, enabled_days_in_month=[13])
    assert status is AvailabilityStatus.BOOKINGS_NOT_OPEN


def test_disabled_day_between_released_days_is_fully_booked() -> None:
    status, _ = classify_disabled_date(target_day=26, enabled_days_in_month=[13, 27])
    assert status is AvailabilityStatus.FULLY_BOOKED

