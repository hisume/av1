from av1_monitor.checkers.factory import create_checker
from av1_monitor.registry import load_registry


def test_registry_contains_all_23_unique_accommodations() -> None:
    registry = load_registry()

    assert len(registry.accommodations) == 23
    assert len({item.id for item in registry.accommodations}) == 23
    assert registry.monitor.start_date.isoformat() == "2027-06-26"
    assert registry.monitor.end_date.isoformat() == "2027-07-31"


def test_every_registry_adapter_has_a_checker() -> None:
    registry = load_registry()
    assert all(create_checker(item) for item in registry.accommodations)


def test_supported_http_family_entries_have_search_urls() -> None:
    registry = load_registry()
    entries = [
        item
        for item in registry.accommodations
        if item.adapter in {"php", "dibona"}
    ]
    assert entries
    assert all(item.search_url for item in entries)

