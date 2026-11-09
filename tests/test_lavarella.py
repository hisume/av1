from av1_monitor.checkers.lavarella import classify_lavarella_widget
from av1_monitor.models import AvailabilityStatus


def test_widget_error_is_not_treated_as_no_inventory() -> None:
    status, evidence = classify_lavarella_widget(
        "Oh no! An unexpected error occurred while loading the booking widget."
    )

    assert status is AvailabilityStatus.CANNOT_DETERMINE
    assert "loading error" in evidence[0]


def test_unknown_widget_markup_is_ambiguous() -> None:
    status, _ = classify_lavarella_widget("Availability & Booking")
    assert status is AvailabilityStatus.CANNOT_DETERMINE

