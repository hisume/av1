# Phase 2: booking-system prototypes

Verification date: 2026-11-09 (America/New_York)

Prototype stay: 2027-06-26 through 2027-06-27, one night, three adults.

## Outcome

Three adapters now return the normalized Phase 1 result model without entering
guest details, holding inventory, or reaching payment.

| Accommodation | Official system | Live result | Evidence and interpretation |
|---|---|---|---|
| Rifugio Tissi | Server-rendered PHP search | `available_for_three` | The official search returned three selectable accommodation categories, each allowing three beds: Room with 4 beds, Dormitory, and the separate 16-bed dormitory. The checker stopped before `prenotazione2.php`. This is evidence for this one target night only. |
| Rifugio Averau | Bukly | `bookings_not_open` | Bukly's selectable dates ended before June 26. June 13 was selectable while the later target period was disabled, which is treated as an unreleased calendar frontier rather than sold-out inventory. A calendar screenshot was captured in the local Phase 2 runtime artifacts. |
| Rifugio Lavarella | Booking Südtirol | `cannot_determine` | The official widget displayed its own loading-error message. Its request to `api.widgets.bookingsuedtirol.com/v6/widgets?propertyId=13004&source=widget&type=booking` failed in the browser because the response lacked the required CORS permission. This is an integration failure, not evidence of no beds. A widget screenshot was captured in the local Phase 2 runtime artifacts. |

These observations are time-specific and can change. Only Tissi produced a
positive three-person offer for the tested night.

## Implemented boundaries

- `CheckResult`, `Offer`, and `AvailabilityStatus` provide one JSON-serializable
  result format across booking systems.
- The Tissi adapter submits only the initial date-and-party search over HTTP.
  It accepts availability only when the response contains a next-stage form
  and a selectable quantity that fits the entire party.
- The Averau adapter opens the official Bukly calendar, navigates to the target
  month, and distinguishes a release frontier from an isolated disabled date.
  If dates are selectable, it can run the three-adult search and rejects
  "alternative suggested options" as positive availability.
- The Lavarella adapter records the Booking Südtirol widget and API failure as
  `cannot_determine`. It does not bypass the browser's CORS policy or infer
  inventory from an error page.
- The command-line interface runs one accommodation/night check and prints the
  complete result as JSON. Screenshots are optional evidence.

## Safety tests

Eleven fixture-based tests cover:

- a selectable Tissi offer that fits all three adults;
- insufficient Tissi quantities, explicit no-inventory text, and unknown
  markup;
- compatible Bukly results versus suggested alternatives;
- a Bukly calendar release frontier versus an isolated sold-out day; and
- Booking Südtirol errors and unknown widget markup.

The suite passes under Python 3.13 with Playwright 1.64 and pytest 9.2:

```text
11 passed in 0.07s
```

Live website checks are deliberately not part of the deterministic test suite.

## Known limitations

- The Bukly UI uses Italian accessible labels and undocumented markup. A markup
  or localization change will return `cannot_determine` until the adapter is
  updated.
- A disabled Bukly date is labeled `fully_booked` only when a later day in the
  same month is already selectable. If selectable dates merely stop before the
  target, the result is `bookings_not_open`; if the evidence is ambiguous, it
  is `cannot_determine`.
- Lavarella cannot currently be searched through its own embedded widget. The
  prototype preserves this failure honestly instead of using an unverified
  third-party path.
- The Tissi parser is site-specific even though several huts use similar PHP
  flows. Phase 3 should extract shared configuration only after validating a
  second member of that family.
- There is no retry policy, host throttling, multi-night scan, saved state,
  notification reducer, or GitHub Actions workflow yet.

## Phase 3 recommendation

Expand the registry and adapters conservatively: validate one additional PHP
site and the other two Bukly sites, then implement the 36-night scan with
host-level throttling. Booking-opening state and availability state should stay
independent so a newly released but already-unavailable date is represented
correctly.

