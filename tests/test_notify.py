from datetime import date, datetime, timedelta, timezone

from av1_monitor.models import AvailabilityStatus, CheckResult, Offer
from av1_monitor.notify import GitHubIssueNotifier, format_issue
from av1_monitor.state import EventType, MonitorEvent


NOW = datetime(2026, 11, 9, 16, 0, tzinfo=timezone.utc)


def availability_event() -> MonitorEvent:
    night = date(2027, 7, 10)
    result = CheckResult(
        accommodation_id="test-hut",
        accommodation_name="Test Hut",
        check_in=night,
        check_out=night + timedelta(days=1),
        party_size=3,
        status=AvailabilityStatus.AVAILABLE_FOR_THREE,
        booking_url="https://example.test/booking",
        evidence=("Official search returned three selectable beds.",),
        offers=(Offer("Dormitory beds", 3, "€75 per person"),),
        checked_at=NOW,
    )
    return MonitorEvent(
        event_type=EventType.THREE_BEDS_AVAILABLE,
        accommodation_id="test-hut",
        accommodation_name="Test Hut",
        booking_url="https://example.test/booking",
        verified_at=NOW.isoformat(),
        results=(result,),
        generations=((night.isoformat(), 1),),
    )


def test_availability_issue_contains_actionable_details_and_marker() -> None:
    event = availability_event()
    issue = format_issue(event, "https://github.com/example/repo/actions/runs/1")

    assert "3 Beds Available" in issue["title"]
    assert "2027-07-10" in issue["title"]
    assert "Dormitory beds" in issue["body"]
    assert "€75 per person" in issue["body"]
    assert event.event_key in issue["body"]
    assert "actions/runs/1" in issue["body"]
    assert issue["labels"] == ["av1-alert", "three-beds-available"]


def test_booking_open_issue_uses_separate_label() -> None:
    availability = availability_event()
    event = MonitorEvent(
        event_type=EventType.BOOKINGS_OPEN,
        accommodation_id=availability.accommodation_id,
        accommodation_name=availability.accommodation_name,
        booking_url=availability.booking_url,
        verified_at=availability.verified_at,
        results=availability.results,
    )
    issue = format_issue(event)

    assert issue["title"] == "Alta Via 1 — Bookings Open: Test Hut"
    assert issue["labels"] == ["av1-alert", "bookings-open"]
    assert event.event_key in issue["body"]


def test_github_notifier_skips_an_existing_event_marker(monkeypatch) -> None:
    event = availability_event()
    notifier = GitHubIssueNotifier("token", "owner/repo")
    created_issues = []

    def request(method, path, payload=None):
        if method == "GET":
            return [{"body": f"<!-- av1-event-key:{event.event_key} -->"}]
        if path.endswith("/issues"):
            created_issues.append(payload)
        return {}

    monkeypatch.setattr(notifier, "_request", request)
    results = notifier.notify((event,))

    assert results[0].status == "duplicate_skipped"
    assert not created_issues


def test_github_notifier_creates_a_new_issue(monkeypatch) -> None:
    event = availability_event()
    notifier = GitHubIssueNotifier("token", "owner/repo")

    def request(method, path, payload=None):
        if method == "GET":
            return []
        if path.endswith("/issues"):
            return {"html_url": "https://github.com/owner/repo/issues/1"}
        return {}

    monkeypatch.setattr(notifier, "_request", request)
    results = notifier.notify((event,))

    assert results[0].status == "created"
    assert results[0].url.endswith("/issues/1")

