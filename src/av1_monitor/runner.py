"""End-to-end scan, transition, notification, and persistence orchestration."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from av1_monitor.notify import (
    GitHubIssueNotifier,
    NotificationResult,
    print_notifications,
)
from av1_monitor.registry import Accommodation
from av1_monitor.scan import AccommodationScan, scan_accommodation, write_reports
from av1_monitor.state import MonitorEvent, load_state, reduce_scans, save_state


@dataclass(frozen=True)
class RunOutcome:
    scans: tuple[AccommodationScan, ...]
    events: tuple[MonitorEvent, ...]
    notifications: tuple[NotificationResult, ...]
    state_saved: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "scans": [scan.to_dict() for scan in self.scans],
            "events": [event.to_dict() for event in self.events],
            "notifications": [item.to_dict() for item in self.notifications],
            "state_saved": self.state_saved,
        }


def run_monitor(
    accommodations: tuple[Accommodation, ...],
    start_date,
    end_date,
    party_size: int,
    host_delay_seconds: float,
    output_dir: Path,
    state_input: Path | None,
    state_output: Path,
    evidence_dir: Path | None = None,
    github_issues: bool = False,
    dry_run: bool = False,
) -> RunOutcome:
    scans = tuple(
        scan_accommodation(
            accommodation,
            start_date,
            end_date,
            party_size,
            host_delay_seconds,
            evidence_dir,
        )
        for accommodation in accommodations
    )
    write_reports(scans, output_dir)
    previous = load_state(state_input)
    next_state, events = reduce_scans(previous, scans)

    if dry_run:
        notifications = print_notifications(events)
    elif github_issues:
        notifier = GitHubIssueNotifier.from_environment()
        notifications = notifier.notify(events)
    else:
        notifications = print_notifications(events)

    state_saved = not dry_run
    if state_saved:
        save_state(state_output, next_state)

    outcome = RunOutcome(scans, events, notifications, state_saved)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "events.json").write_text(
        json.dumps([event.to_dict() for event in events], indent=2, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    (output_dir / "notifications.json").write_text(
        json.dumps(
            [notification.to_dict() for notification in notifications],
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    with (output_dir / "summary.md").open("a", encoding="utf-8") as handle:
        handle.write("\n## Changes and notifications\n\n")
        handle.write(f"- Transition events: {len(events)}\n")
        handle.write(f"- Notifications: {len(notifications)}\n")
        handle.write(f"- State saved: {'yes' if state_saved else 'no (dry run)'}\n")
    return outcome

