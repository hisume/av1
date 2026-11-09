# Phase 5 — GitHub-hosted validation

Phase 5 deployed commit `5126025c21a039f67d9c99fbe37271ab19853168`
to `main` and validated the complete automation path on GitHub-hosted Linux
runners on 2026-11-09. No checker advanced to guest details, held inventory,
or entered payment information.

## Hosted run sequence

| Check | Workflow run | Duration | Result |
|---|---|---:|---|
| Coldai dry run | [42661005488](https://github.com/hisume/av1/actions/runs/42661005488) | 4m 21s | 36 nights available, no errors, no state saved, no issue created |
| Full production baseline | [42706515802](https://github.com/hisume/av1/actions/runs/42706515802) | 23m 43s | All 23 accommodations and 36 nights scanned; state, reports, artifacts, and seven issues created |
| Coldai production repeat | [42710474785](https://github.com/hisume/av1/actions/runs/42710474785) | 4m 28s | State restored; zero transition events and zero notifications |

All setup, Chromium installation, scan, persistence, and artifact-upload steps
completed successfully. The full run remained comfortably below the workflow's
55-minute timeout and the hourly schedule interval.

The dry run did not create `monitor-state`. The first production run created
the branch and commit `5c8d5d6`; the focused repeat advanced it to `8b7dd21`.
The repeat artifact retained state for all 23 accommodations while updating
only Coldai's observation timestamps.

## Full baseline findings

The baseline evaluated 828 accommodation-night combinations. Opening status
was:

- 9 open: Lagazuoi, Coldai, Carestiato, Col Gallina, Scoiattoli, Scotoni,
  Tissi, Passo Duran, and Vazzoler;
- 3 not open: Croda da Lago, Nuvolau, and Angelo Dibona;
- 3 unknown: Lavarella, Averau, and Fanes; and
- 8 explicitly unsupported contact/enquiry-only entries.

Seven grouped availability transitions represented 141 nights and created
these GitHub Issues:

| Accommodation | Available nights | Alert |
|---|---:|---|
| Rifugio Coldai | 36 | [#1](https://github.com/hisume/av1/issues/1) |
| Rifugio Carestiato | 9 | [#2](https://github.com/hisume/av1/issues/2) |
| Rifugio Col Gallina | 6 | [#3](https://github.com/hisume/av1/issues/3) |
| Rifugio Scotoni | 1 | [#4](https://github.com/hisume/av1/issues/4) |
| Rifugio Tissi | 34 | [#5](https://github.com/hisume/av1/issues/5) |
| Rifugio Passo Duran (C. Tomè) | 28 | [#6](https://github.com/hisume/av1/issues/6) |
| Rifugio Vazzoler | 27 | [#7](https://github.com/hisume/av1/issues/7) |

Existing open-season detections were stored as a silent opening baseline. The
availability transitions remained actionable, as designed. A second real run
against unchanged Coldai availability produced `events: []` and
`notifications: []`; the repository still contained exactly seven
`av1-alert` issues afterward.

## Hosted-only limitations observed

Lavarella and Fanes each returned 36 `cannot_determine` results because the
Booking Südtirol widget API failed with `net::ERR_FAILED` from the hosted
browser. These failures do not erase the last successful observation, and the
hourly workflow will retry them.

Averau returned five `bookings_not_open` nights and 31 indeterminate nights,
so its overall opening state correctly remained `unknown`. The system did not
turn those uncertain results into false availability alerts.

The runner also emitted GitHub's compatibility warning that the pinned action
majors target Node.js 20 and are currently forced onto Node.js 24. It did not
affect any step in these runs, but updating the action majors should be part of
future dependency maintenance.

## Final verification

The local suite was rerun after the hosted checks:

```text
37 passed in 0.11s
```

Issue creation, scoped write permissions, state-branch creation, report and
artifact persistence, and duplicate suppression are all verified. GitHub email
delivery is an account preference rather than a repository automation setting;
the remaining user-side step is **Watch → Custom → Issues** plus enabled email
delivery in GitHub notification settings.
