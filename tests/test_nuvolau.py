from datetime import date

from av1_monitor.checkers.nuvolau import parse_nuvolau_month


def test_month_parser_sums_bed_units_across_room_types() -> None:
    html = """
    <table data-room-table="4"><tr>
      <td data-cell-date="26/06/2027"><span data-units-left="1">1</span></td>
      <td data-cell-date="27/06/2027"><span data-units-left="0">0</span></td>
    </tr></table>
    <table data-room-table="6"><tr>
      <td data-cell-date="26/06/2027"><span data-units-left="2">2</span></td>
      <td data-cell-date="27/06/2027"><span data-units-left="1">1</span></td>
    </tr></table>
    """

    inventory = parse_nuvolau_month(html)

    assert inventory[date(2027, 6, 26)] == 3
    assert inventory[date(2027, 6, 27)] == 1

