from pathlib import Path

from av1_monitor.checkers.tissi import parse_tissi_search
from av1_monitor.models import AvailabilityStatus

FIXTURES = Path(__file__).parent / "fixtures"


def test_selectable_offer_supports_entire_party() -> None:
    html = (FIXTURES / "tissi_available.html").read_text(encoding="utf-8")
    status, offers, evidence = parse_tissi_search(html, party_size=3)

    assert status is AvailabilityStatus.AVAILABLE_FOR_THREE
    assert [offer.max_selectable for offer in offers] == [3, 3]
    assert offers[0].description == "Room with 4 beds"
    assert "stopped before" in evidence[1]


def test_offers_that_do_not_fit_party_are_insufficient() -> None:
    html = (FIXTURES / "tissi_insufficient.html").read_text(encoding="utf-8")
    status, offers, _ = parse_tissi_search(html, party_size=3)

    assert status is AvailabilityStatus.OPEN_INSUFFICIENT_AVAILABILITY
    assert offers[0].max_selectable == 2


def test_explicit_no_availability_is_fully_booked() -> None:
    status, offers, _ = parse_tissi_search(
        "<html><p>No accommodation available for the selected dates.</p></html>",
        party_size=3,
    )

    assert status is AvailabilityStatus.FULLY_BOOKED
    assert not offers


def test_unknown_markup_is_not_misreported_as_no_inventory() -> None:
    status, _, _ = parse_tissi_search("<html><p>Temporarily unavailable</p></html>", 3)

    assert status is AvailabilityStatus.CANNOT_DETERMINE


def test_separately_selectable_categories_can_cover_the_party() -> None:
    html = """
    <form action="prenotazione2.php">
      <div class="quadroCamere"><p>Room A<br></p>
        <select name="nAlloggi1"><option value="2">2</option></select>
      </div>
      <div class="quadroCamere"><p>Room B<br></p>
        <select name="nAlloggi2"><option value="1">1</option></select>
      </div>
    </form>
    """
    status, offers, _ = parse_tissi_search(html, 3)

    assert status is AvailabilityStatus.AVAILABLE_FOR_THREE
    assert sum(offer.max_selectable or 0 for offer in offers) == 3

