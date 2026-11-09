"""GitHub Issue notifications with event-key idempotency."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from av1_monitor.state import EventType, MonitorEvent


@dataclass(frozen=True)
class NotificationResult:
    event_key: str
    status: str
    url: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "event_key": self.event_key,
            "status": self.status,
            "url": self.url,
        }


def _arrangement(event: MonitorEvent, index: int) -> str:
    result = event.results[index]
    if not result.offers:
        return "Verified for the requested party"
    return "; ".join(
        offer.description
        + (f" (up to {offer.max_selectable})" if offer.max_selectable else "")
        for offer in result.offers
    )


def format_issue(event: MonitorEvent, workflow_url: str | None = None) -> dict[str, Any]:
    marker = f"<!-- av1-event-key:{event.event_key} -->"
    if event.event_type is EventType.BOOKINGS_OPEN:
        title = f"Alta Via 1 — Bookings Open: {event.accommodation_name}"
        labels = ["av1-alert", "bookings-open"]
        dates = sorted({result.check_in.isoformat() for result in event.results})
        date_text = ", ".join(dates) if dates else "At least one monitored night"
        body = "\n".join(
            [
                marker,
                f"## Bookings open: {event.accommodation_name}",
                "",
                "The official system produced a conclusive searchable result after previously being closed or unreleased.",
                "",
                f"- Verified monitored dates: {date_text}",
                f"- Official booking link: {event.booking_url}",
                f"- Verified at: {event.verified_at}",
            ]
        )
    else:
        dates = [result.check_in.isoformat() for result in event.results]
        suffix = dates[0] if len(dates) == 1 else f"{len(dates)} nights"
        title = (
            f"Alta Via 1 — 3 Beds Available: {event.accommodation_name} — {suffix}"
        )
        labels = ["av1-alert", "three-beds-available"]
        rows = ["| Night | Arrangement | Price |", "|---|---|---|"]
        for index, result in enumerate(event.results):
            prices = sorted({offer.price for offer in result.offers if offer.price})
            price = ", ".join(prices) if prices else "Not shown"
            rows.append(
                f"| {result.check_in.isoformat()} | {_arrangement(event, index)} | {price} |"
            )
        evidence = []
        for result in event.results:
            evidence.extend(result.evidence)
        body = "\n".join(
            [
                marker,
                f"## Three-person availability: {event.accommodation_name}",
                "",
                *rows,
                "",
                f"Official booking link: {event.booking_url}",
                "",
                "### Verification evidence",
                "",
                *(f"- {item}" for item in dict.fromkeys(evidence)),
                "",
                f"Verified at: {event.verified_at}",
            ]
        )
    if workflow_url:
        body += f"\n- Workflow run: {workflow_url}"
    return {"title": title, "body": body + "\n", "labels": labels}


class GitHubIssueNotifier:
    def __init__(
        self,
        token: str,
        repository: str,
        api_url: str = "https://api.github.com",
        workflow_url: str | None = None,
    ) -> None:
        if "/" not in repository:
            raise ValueError("repository must be in owner/name form")
        self.token = token
        self.repository = repository
        self.api_url = api_url.rstrip("/")
        self.workflow_url = workflow_url

    @classmethod
    def from_environment(cls) -> "GitHubIssueNotifier":
        token = os.environ.get("GITHUB_TOKEN")
        repository = os.environ.get("GITHUB_REPOSITORY")
        if not token or not repository:
            raise RuntimeError(
                "GITHUB_TOKEN and GITHUB_REPOSITORY are required for issue notifications"
            )
        server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
        run_id = os.environ.get("GITHUB_RUN_ID")
        workflow_url = (
            f"{server}/{repository}/actions/runs/{run_id}" if run_id else None
        )
        return cls(
            token=token,
            repository=repository,
            api_url=os.environ.get("GITHUB_API_URL", "https://api.github.com"),
            workflow_url=workflow_url,
        )

    def _request(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> Any:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = Request(
            f"{self.api_url}{path}",
            data=data,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "User-Agent": "av1-booking-monitor/0.1",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        with urlopen(request, timeout=30) as response:
            content = response.read()
        return json.loads(content) if content else None

    def _ensure_labels(self) -> None:
        labels = {
            "av1-alert": ("5319e7", "Verified Alta Via 1 booking monitor alert"),
            "bookings-open": ("1d76db", "Summer 2027 reservations newly opened"),
            "three-beds-available": ("0e8a16", "Verified availability for three people"),
        }
        for name, (color, description) in labels.items():
            try:
                self._request(
                    "POST",
                    f"/repos/{self.repository}/labels",
                    {"name": name, "color": color, "description": description},
                )
            except HTTPError as exc:
                if exc.code != 422:
                    raise

    def _existing_markers(self) -> set[str]:
        query = urlencode(
            {
                "state": "all",
                "labels": "av1-alert",
                "per_page": "100",
                "sort": "created",
                "direction": "desc",
            }
        )
        issues = self._request(
            "GET", f"/repos/{self.repository}/issues?{query}"
        )
        markers: set[str] = set()
        for issue in issues or []:
            body = issue.get("body") or ""
            prefix = "<!-- av1-event-key:"
            start = body.find(prefix)
            if start >= 0:
                end = body.find(" -->", start)
                if end >= 0:
                    markers.add(body[start + len(prefix) : end])
        return markers

    def notify(
        self, events: tuple[MonitorEvent, ...]
    ) -> tuple[NotificationResult, ...]:
        if not events:
            return tuple()
        self._ensure_labels()
        existing = self._existing_markers()
        results: list[NotificationResult] = []
        for event in events:
            if event.event_key in existing:
                results.append(
                    NotificationResult(event.event_key, "duplicate_skipped")
                )
                continue
            issue = self._request(
                "POST",
                f"/repos/{self.repository}/issues",
                format_issue(event, self.workflow_url),
            )
            results.append(
                NotificationResult(
                    event.event_key,
                    "created",
                    issue.get("html_url") if issue else None,
                )
            )
            existing.add(event.event_key)
        return tuple(results)


def print_notifications(
    events: tuple[MonitorEvent, ...]
) -> tuple[NotificationResult, ...]:
    results: list[NotificationResult] = []
    for event in events:
        issue = format_issue(event)
        print(f"\n--- {issue['title']} ---\n{issue['body']}")
        results.append(NotificationResult(event.event_key, "printed"))
    return tuple(results)

