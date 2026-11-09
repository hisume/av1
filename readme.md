# Alta Via 1 booking monitor

Python automation for monitoring summer 2027 booking openings and verified
three-person availability at 23 accommodations on the Alta Via 1.

## Project status

Phase 4 is complete and awaiting review. The repository now includes the full
hourly automation path:

- 15 accommodations have automated checkers across PHP, Bukly, Booking
  Südtirol, Scoiattoli, Nuvolau, and Dibona systems.
- 8 accommodations are explicitly `unsupported` because their official sites
  expose only contact or non-binding enquiry workflows.
- Persistent state independently tracks booking openings and three-bed
  availability transitions.
- GitHub Issues provide idempotent alerts using only the scoped `GITHUB_TOKEN`.
- An hourly and manually dispatchable GitHub Actions workflow preserves state
  and reports on a `monitor-state` branch.

See [the Phase 1 research report](docs/phase-1-research.md) for the official
booking paths and architecture. See [the Phase 2 prototype report](docs/phase-2-prototype.md)
for the first three adapters. See [the Phase 3 expansion report](docs/phase-3-expansion.md)
for the complete support matrix and live target-night findings. See [the Phase
4 automation report](docs/phase-4-automation.md) for state behavior,
notification rules, deployment, and validation evidence.

A complete GitHub-hosted live validation of all 23 accommodations and 36 nights
remains Phase 5.

## Run the prototype

Python 3.12 or newer is required.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m playwright install chromium
.venv\Scripts\python.exe -m av1_monitor check `
  --accommodation tissi `
  --date 2027-06-26 `
  --party-size 3
```

Accommodation IDs are defined in [config/accommodations.toml](config/accommodations.toml).
Add `--evidence-dir artifacts/run` to browser checks to capture a screenshot.
The checker prints one normalized JSON result and never advances to guest
details, holds inventory, or enters payment.

Scan the complete configured period for one accommodation:

```powershell
.venv\Scripts\python.exe -m av1_monitor scan `
  --accommodation coldai `
  --output-dir artifacts/latest
```

Use `--all` instead of `--accommodation` to include all 23 entries. The output
directory receives `scan.json`, `availability.csv`, and `summary.md`. The
opening status is derived independently from three-person availability: a
searchable but sold-out night still proves that bookings are open.

Run the transition pipeline locally without saving state or creating issues:

```powershell
.venv\Scripts\python.exe -m av1_monitor run `
  --accommodation coldai `
  --start-date 2027-06-26 `
  --end-date 2027-06-26 `
  --output-dir artifacts/dry-run `
  --dry-run
```

Run the safety-focused parser, registry, and scan tests with:

```powershell
.venv\Scripts\python.exe -m pytest -p no:cacheprovider
```

## GitHub Actions deployment

The [monitor workflow](.github/workflows/monitor.yml) runs at minute 17 of
every hour and supports manual execution. It declares only `contents: write`
and `issues: write`; no SMTP or personal-access-token secret is needed.

After pushing the repository:

1. Ensure GitHub Issues and Actions are enabled. Organization policy must allow
   the workflow's requested write permissions.
2. In **Actions → Alta Via 1 booking monitor → Run workflow**, first choose one
   accommodation and enable `dry_run`. A dry run creates no issue and saves no
   state.
3. Run once with `dry_run` disabled. This creates the `monitor-state` branch.
   Existing booking openings become a silent baseline, while currently
   available three-person nights remain actionable and may create issues.
4. To receive those issues by email, choose **Watch → Custom → Issues** for the
   repository and enable email delivery in GitHub notification settings. See
   [GitHub's notification documentation](https://docs.github.com/en/subscriptions-and-notifications/get-started/configuring-notifications).

Each issue includes an internal event key. If issue creation succeeds but the
state push fails, retrying the workflow detects the existing key instead of
creating a duplicate.

## Agreed deployment choices

- Run hourly and manually with GitHub Actions.
- Create GitHub Issues for alerts, using the workflow's scoped `GITHUB_TOKEN`.
- Persist state and generated reports on a dedicated `monitor-state` branch.
- Keep this repository as the final project repository.

Email via SMTP may be added later behind the same notification interface, but
it is not required for the initial deployment.
