# Phase 4: automation, persistence, and notifications

Implementation date: 2026-11-09 (America/New_York)

## Outcome

The monitor now has an end-to-end scheduled execution path. It scans official
booking systems, derives the two independent monitor states, reduces them
against a durable snapshot, creates idempotent GitHub Issues for new events,
generates reports, and saves the next snapshot on a dedicated branch.

```text
official booking systems
          |
          v
  36-night normalized scans -----> JSON / CSV / Markdown reports
          |
          v
 previous state + transition reducer
          |
          +-----> booking-opening events ----+
          |                                  |
          +-----> availability events -------+--> GitHub Issues
          |
          v
  next state on monitor-state branch
```

The workflow is [`.github/workflows/monitor.yml`](../.github/workflows/monitor.yml).

## Transition behavior

| Situation | State behavior | Notification behavior |
|---|---|---|
| First observation is already open | Stored as the opening baseline | No retroactive booking-opening issue |
| Previously not open, now conclusively searchable | Opening becomes `open` | One `bookings-open` issue |
| First observation has three-person availability | Night becomes active, generation 1 | One availability issue because it is actionable |
| Availability remains unchanged | Active state remains true | No duplicate issue |
| Available → conclusively unavailable | Active state becomes false | No issue |
| Unavailable → available again | Generation increments | A fresh availability issue |
| Timeout, CAPTCHA, inaccessible page, or unknown markup | Last attempt and error are recorded | Last successful status and active availability are preserved |

Booking-opening alerts are permanently one-time per accommodation. Availability
alerts use a generation counter per night so a genuine reappearance can alert
again without making retries noisy.

## GitHub Issue notifications

The notifier creates and uses these labels:

- `av1-alert`;
- `bookings-open`; and
- `three-beds-available`.

Availability issues group all newly available nights for one accommodation and
include room/bed arrangements, displayed prices, the official booking URL,
verification evidence, timestamp, and workflow-run link.

Every issue embeds a deterministic event-key marker. Before creating an issue,
the notifier checks existing `av1-alert` issues, including closed issues. This
prevents a duplicate if an issue was created successfully but the subsequent
state-branch push failed. A later availability generation has a different key
and is therefore allowed to create a new issue.

GitHub documents that workflow token access can be limited through the
`permissions` key; this workflow requests only `contents: write` and
`issues: write`: [Workflow syntax and token permissions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax).

GitHub Issues also provide email delivery without SMTP credentials. The user
must watch the repository's Issues category and enable email as a delivery
method: [Configuring notifications](https://docs.github.com/en/subscriptions-and-notifications/get-started/configuring-notifications).

## Persistence and reporting

The workflow restores `state/monitor-state.json` from the `monitor-state`
branch. After successful notification handling it commits:

- the updated state snapshot;
- the normalized scan;
- the availability CSV matrix;
- the Markdown summary;
- transition events; and
- notification outcomes.

State is written only after notifications succeed. A dry run prints proposed
issues but deliberately writes no state. Unknown checks never overwrite a last
successful observation.

The workflow concurrency group is `av1-monitor-state` with cancellation
disabled, preventing overlapping runs from racing the state branch. Commits
made with the repository `GITHUB_TOKEN` do not recursively trigger ordinary
workflow events, as documented by GitHub: [Triggering a workflow](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow).

## Browser batching and request control

Bukly checks now launch one Chromium process per accommodation range and reuse
the same page for every night. A live two-night Averau scan returned two
`bookings_not_open` results from one browser session. Booking Südtirol's current
system-level widget failure is probed once per range rather than 36 times.

HTTP adapters remain serialized and subject to the configured per-host delay.
Nuvolau reuses cached monthly inventory, requiring at most two calendar requests
for the monitored period.

## Workflow behavior

The hourly cron is `17 * * * *`, intentionally offset from the top of the hour.
Manual dispatch supports:

- an optional single accommodation ID;
- non-mutating dry-run notification mode; and
- optional browser screenshots.

The workflow caches Chromium, installs its Linux dependencies, uploads run
reports/evidence for 14 days, and has a 55-minute timeout. It creates the
`monitor-state` branch automatically on the first non-dry run.

## Validation performed

Two local end-to-end validations were performed without external mutations:

1. A Coldai dry run generated the expected availability issue body and reports,
   while confirming that no state file was written.
2. Two consecutive persistent Coldai runs stored generation 1 on the first run
   and emitted zero transition events on the unchanged second run.

The generated summaries, events, and sample state remain local runtime
artifacts rather than repository files. Hosted runs upload the same evidence
and persist the latest reports on `monitor-state`.

The automated suite now contains 37 tests covering parsers, all registry
entries, the 36-night range, browser batching selection, transition rules,
failure atomicity, generation behavior, event-key stability, issue formatting,
and GitHub duplicate suppression.

```text
37 passed in 0.11s
```

## Phase 5 boundary

No GitHub Issue or remote branch was created during local Phase 4 validation.
Phase 5 must push the repository, run the workflow first in manual dry-run mode,
then perform a real GitHub-hosted baseline run. It should confirm runner timing,
write permissions, `monitor-state` branch creation, issue delivery, email
settings, and behavior differences caused by GitHub-hosted IP addresses.

