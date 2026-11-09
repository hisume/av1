# Phase 1 research: official booking systems

Research date: 2026-11-09 (America/New_York)

Target stay dates: 2027-06-26 through 2027-07-31, inclusive (36 nights), for
three adults.

## Outcome

The 23 accommodations do not share one reservation platform. The audit found
four reusable online-booking families plus several individual systems:

- A PHP-style real-time calendar used by Lagazuoi, Croda da Lago, Coldai,
  Carestiato, Tissi, Passo Duran, and Vazzoler.
- Bukly, used by Averau, Col Gallina, and Scotoni.
- Booking Südtirol, used by Lavarella and Fanes.
- Individual online systems for Scoiattoli, Nuvolau, Angelo Dibona, and
  possibly Berghotel Passo Giau.
- Contact or non-binding request workflows for Pian de Fontana, Rifugio 5
  Torri, Fedare, San Sebastiano, Malga Giau, Passo Valparola, and Sommariva al
  Pramperet.

Sixteen accommodations therefore have a plausible real-time integration,
although each family still requires a browser-level prototype before it is
called supported. Seven currently lack public, machine-verifiable inventory.
Those seven must be reported as `unsupported` or `cannot_determine`, never as
`fully_booked`.

This phase identified systems and verification strategies; it did not execute
all 36 three-adult searches. No row below is a claim of current availability.

## Integration matrix

| # | Accommodation | Official booking path and observed system | Proposed verification | Phase 1 assessment |
|---:|---|---|---|---|
| 1 | Rifugio Lavarella | [Official site](https://lavarella.it/en/book-online), Booking Südtirol widget, accommodation ID `13004` | Search one-night stays for three adults; for dorms follow the hut's instruction to add one bed/room per person; accept only returned bookable offers | Likely automatable with Playwright; HTTP/API investigation may reduce browser use |
| 2 | Rifugio Lagazuoi | [Official real-time availability](https://www.rifugiolagazuoi.com/EN/disponibilita.php), PHP calendar/search | Submit each one-night stay with three people and require a selectable room/bed offer, not merely a colored calendar day | Likely automatable; shared PHP adapter candidate |
| 3 | Rifugio Croda da Lago (Palmieri) | [Official booking page](https://www.crodadalago.it/Booking/index.php), PHP calendar/search | Same three-person offer verification as Lagazuoi | Likely automatable; official site says summer 2027 reservations open in December 2026 |
| 4 | Rifugio Coldai | [Official booking page](https://rifugiocoldai.com/Booking/index_en.php), PHP calendar/search | Same three-person offer verification as Lagazuoi | Likely automatable; shared PHP adapter candidate |
| 5 | Rifugio Carestiato | [Official booking page](https://www.rifugiocarestiato.com/Booking/index_en.php), PHP calendar/search | Same three-person offer verification; the hut states missing results mean no remaining places | Likely automatable; shared PHP adapter candidate |
| 6 | Rifugio Pian de Fontana | [Official CAI owner listing](https://www.cailongarone.it/rifugi-e-bivacchi/) links to a site that is HTTP-only and publishes phone/email contact | An email or phone response would be needed to prove a bed; the monitor must not submit recurring enquiries | Monitor A and B unsupported until a public inventory system appears |
| 7 | Rifugio Averau | [Official site](https://www.rifugioaverau.it/en/) links to [Bukly](https://rifugioaverau.bukly.com/booking) | Search each one-night stay for three adults and require a bookable occupancy arrangement | Likely automatable; shared Bukly adapter candidate |
| 8 | Rifugio Col Gallina | [Official rooms page](https://www.rifugiocolgallina.com/en/rifugio-rooms-falzarego-pass-cortina/) links to [Bukly](https://rifugiocolgallina.bukly.com/) | Same three-adult offer verification as Averau | Likely automatable; shared Bukly adapter candidate |
| 9 | Rifugio Scoiattoli | [Official booking form](https://www.rifugioscoiattoli.it/booking/eng/), custom GET search | Submit arrival, departure, and three adults; follow the result flow and require a selectable offer before payment details | Likely automatable; individual adapter |
| 10 | Rifugio 5 Torri | [Official rooms page](https://www.rifugio5torri.it/en/rooms.html), email only | The page can be watched for announcements, but exact opening or three-bed availability requires a reply from the hut | Monitor A and B unsupported; page currently says summer 2027 is almost full and only leftover-date requests may receive replies |
| 11 | Rifugio Nuvolau | [Official availability calendar](https://rifugionuvolau.it/en/availability/), inventory counts by dorm | Sum genuinely bookable beds across compatible offers for each night and verify the booking link accepts three adults | Likely automatable; official booking page says 2027 reservations begin January 2027 |
| 12 | Rifugio Scotoni | [Official site](https://www.scotoni.it/en/) links to [Bukly](https://scotoni.bukly.com/) | Same three-adult offer verification as Averau | Likely automatable; shared Bukly adapter candidate |
| 13 | Rifugio Fedare | [Official site](https://valfiorentinadolomiti.it/en/Rifugio-Fedare-Passo-Giau/Rifugio-Fedare/Welcome-to-the-Passo-Giau.html), explicitly non-binding request form | A form submission would only request availability and must not be sent hourly | Monitor A and B unsupported until real-time inventory is exposed |
| 14 | Rifugio Fanes | [Official booking page](https://www.rifugiofanes.com/en/booking), Booking Südtirol widget | Search one-night stays for three adults and require an actual offer; preserve minimum-stay failures as a distinct limitation | Likely automatable with Playwright; shared Booking Südtirol adapter candidate |
| 15 | Rifugio Tissi | [Official site](https://www.rifugiotissi.com/index_en.php) and [real-time calendar](https://rifugiotissi.com/IT/disponibilita.php), PHP calendar/search | Same three-person offer verification as Lagazuoi | Likely automatable; official site currently states 2027 bookings are open, but Phase 2 must still prove a reservable monitored night |
| 16 | Rifugio Passo Duran (C. Tomè) | [Official site](https://rifugiopassoduran.it/) and [booking system](https://rifugiopassoduran.it/booking/index.php), PHP calendar/search | Use the shared PHP search when restored; distinguish maintenance from no inventory | Temporarily blocked: booking system reports maintenance |
| 17 | Rifugio San Sebastiano | [Official site](https://www.passoduran.it/), direct contact/request workflow | A request response would be required to verify inventory; do not send automated requests | Monitor A and B unsupported until real-time inventory appears |
| 18 | Rifugio Vazzoler | [Official site](https://www.rifugiovazzoler.com/en/) and [booking page](https://www.rifugiovazzoler.com/Booking/index.php), PHP calendar/search | Same three-person offer verification as Lagazuoi | Likely automatable; shared PHP adapter candidate |
| 19 | Berghotel Passo Giau | [Official booking page](https://www.passogiau.it/en/booking-request/), Beddy availability-request widget plus contact form | Probe the widget after its season opens; support only if it returns an immediately bookable three-adult offer rather than sending an enquiry | Deferred/unknown; official page says summer 2027 booking starts in March 2027 |
| 20 | Malga Giau | [Official site](https://www.malgagiau.it/en/), phone/email only | Inventory requires direct contact; do not automate enquiries | Monitor A and B unsupported until real-time inventory appears |
| 21 | Rifugio Angelo Dibona | [Official site](https://www.rifugiodibona.it/) links to [its booking app](https://www.rifugiodibona.app/en) | Search each night for three guests and require three selectable beds/rooms before checkout | Likely automatable; individual app adapter |
| 22 | Rifugio Passo Valparola | Official tourism listings publish phone/email but no operator booking engine: [Dolomiti Superski listing](https://www.dolomitisuperski.com/en/experiences/services/dolomites-a-z/Arabba/Rifugio-Passo-Valparola) | Inventory requires direct contact; do not infer it from third-party hotel pages | Monitor A and B unsupported until an official real-time system appears |
| 23 | Rifugio Sommariva al Pramperet | [Official CAI record](https://www.prenotarifugi.cai.it/en/detail/?id=5925) and operator site publish contact details but no usable online inventory | Inventory requires direct contact; a CAI catalog entry is not proof of online availability | Monitor A and B unsupported until real-time inventory appears |

## What counts as verified

The monitor will use a strict result model:

- `bookings_not_open`: the target season cannot yet be searched or the system
  explicitly has not released it.
- `available_for_three`: a one-night search for three adults returns one or
  more selectable arrangements whose combined capacity is at least three.
- `open_insufficient_availability`: the date is searchable and offers exist,
  but they cannot accommodate three adults.
- `fully_booked`: the date is searchable and the official system explicitly
  returns no inventory.
- `cannot_determine`: ambiguity, maintenance, changed markup, timeout, CAPTCHA,
  or an inaccessible site.
- `unsupported`: no public workflow can verify inventory without contacting a
  person or submitting a non-binding request.

A visible calendar, published prices, a booking button, or a room description
is evidence for investigation but is not sufficient for a positive result.
Monitor A becomes positive only after at least one target night produces a
genuinely selectable offer. Monitor B independently evaluates all 36 nights.

On the first successful run, Monitor A records already-open properties as its
baseline without creating retroactive issues. Monitor B may report currently
available nights because those are actionable availability discoveries. Later
`available -> unavailable -> available` transitions create a fresh alert.

## Proposed architecture

The application will be a Python 3.12 package with these boundaries:

1. A YAML accommodation registry holds official URLs, booking-family adapter,
   target occupancy, enabled monitors, and known limitations.
2. Adapter classes implement a common `check(accommodation, date_range,
   party_size)` interface and return structured results plus evidence. HTTP is
   preferred where an official public endpoint is stable; Playwright is used
   for JavaScript widgets and as the correctness reference.
3. A normalization layer validates that offers cover exactly one requested
   night and all three adults. It never proceeds into guest details, holds a
   room, or reaches payment.
4. A state reducer compares the new snapshot with the previous snapshot and
   emits booking-opening and availability events independently.
5. A GitHub Issues notifier groups newly available nights by accommodation.
   It uses the built-in token with only `issues: write`; no mail credential is
   required. An optional SMTP notifier can implement the same interface later.
6. JSON state and CSV/Markdown reports live on a dedicated `monitor-state`
   branch. The workflow uses a concurrency group to prevent overlapping state
   commits. Evidence screenshots/HTML are captured only for changes and
   failures and uploaded as workflow artifacts to avoid repository bloat.
7. The hourly workflow also supports `workflow_dispatch` inputs for one
   accommodation, one date, dry-run notification mode, and screenshot mode.

The implementation will limit concurrency per hostname, retry transient
failures with jitter, and avoid a naive 23 x 36 browser-launch pattern. It will
reuse monthly inventory or multi-date responses where they are authoritative,
then execute one-night three-adult searches where necessary. A result is not
overwritten by a failed check; failures update error metadata while retaining
the last successful observation and its timestamp.

## GitHub Issue notifications

GitHub documents that an Actions workflow can create an issue using its
repository-scoped token when the job declares `issues: write`:
[Using `GITHUB_TOKEN` in a workflow](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token).
Email delivery is controlled by the repository watch selection and the user's
notification settings:
[Configuring notifications](https://docs.github.com/en/subscriptions-and-notifications/get-started/configuring-notifications).

Planned labels are `av1-alert`, `bookings-open`, `three-beds-available`, and
`monitor-error`. Each event issue will contain the official booking URL,
verified dates, offer/room details when visible, verification timestamp, and a
link to the workflow run and evidence artifact. Duplicate suppression remains
in state rather than relying on whether an issue is open or closed.

## Important limitations

- Public interfaces and undocumented endpoints can change. Markup changes must
  produce `cannot_determine`, not false availability.
- CAPTCHAs, anti-bot blocks, or terms that prohibit automation will not be
  bypassed. The affected integration will be disabled and reported.
- Request-only accommodations cannot satisfy the project's strict availability
  standard without human confirmation. Page-change alerts could be added, but
  they would be supplementary and must not be labeled verified bookings.
- Booking Südtirol and some huts may impose minimum stays or room-allocation
  rules. A failed one-night query is not automatically `fully_booked`; the
  adapter must distinguish policy rejection from lack of inventory.
- GitHub-hosted runners have changing IP addresses and can receive different
  treatment from local browsers. Phase 5 must validate both environments.
- Hourly checks should be respectful. Host-level throttling and reuse of
  authoritative calendar responses are mandatory.

## Recommended Phase 2 prototypes

Prototype three different families:

1. **Rifugio Tissi** for the shared PHP calendar/search family. Its official
   site says 2027 bookings are open, making it suitable for testing both
   positive and negative results.
2. **Rifugio Averau** for Bukly.
3. **Rifugio Lavarella** for Booking Südtirol, including the special dorm-bed
   allocation rule.

If a prototype cannot obtain an actual offer in the monitored date range, use
an additional non-target date only as a parser fixture and clearly label it;
the application must never convert that into a target-period availability
claim. Phase 2 should capture Playwright traces/screenshots, record network
responses, build saved HTML/JSON fixtures, and add tests for offer validation
and ambiguous failure handling.
