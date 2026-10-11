# TraceLoft web navigation

This map covers every direct screen transition and its guards. Longer journeys are combinations
of these paths. Choosing another screen does not stop input or finish a drill; only End session,
confirmed Exit session, and confirmed Abandon session end the active drill.

Main navigation order: **Relay → Practice → Play → Analyze → Sessions**. Analyze has cross-session comparisons and filtered export. Play contains the course library and 2D game.

Sections: the current [map](#map), [screens](#screens-and-stable-locations),
[shared navigation](#shared-navigation) and [transitions](#detailed-transition-checklist), then
[paths by feature](#paths-by-feature) and dated [verification history](#verification-history).
A verification note is evidence for the change it names, never proof of later changes.

## Map

```mermaid
flowchart TD
    P[Practice selector] -->|Set up drill| T[Drill setup]
    T -->|Launch drill| A[Active practice session]
    T -->|Practice| P
    P -->|Return to active drill| A
    A -->|End session or final putt| F[Completed session]
    A -->|Exit: confirm end and save| P
    A -->|Abandon: confirm| P
    T -->|Manage bags| B[Bag manager dialog]
    A -->|Manage bags| B
    T -->|Add bag in empty slot| B
    A -->|Add bag in empty slot| B
    T -->|More bags| Q[All bags dialog]
    A -->|More bags| Q
    Q -->|Choose bag or Cancel/Escape| O
    B -->|Close or Escape| O[Originating setup or active full-swing session]
    B -->|Save bag or create bag| B
    F -->|Exit session| P
    F -->|Edit targets| T
    S[Sessions] -->|Review saved session| R[Session review]
    S -->|Return to active drill| A
    R -->|Exit review| S
    R -->|Practice selector| P
    R -->|Edit targets: no active drill| T
    R -->|Delete: confirm| S
    F -->|Delete: confirm| S
    S -->|Delete: confirm| D[Recently deleted]
    D -->|Restore or Undo| S
    G[Main navigation on every screen] -->|Practice or TraceLoft home| P
    G -->|Sessions| S
    G -->|Relay| C[Relay: input status, destination, data and backups]
    G -->|Play| L[Play: course library]
    G -->|Analyze| N[Analyze: filters, trends and comparisons]
    L -->|Go to practice| P
    N -->|Go to practice| P
    L -->|Return to active drill if present| A
    N -->|Review compared session| R
    L -->|Set up round: no active session| GT[Game setup]
    L -->|Import a course| CI[Course importer]
    CI -->|← Play or Cancel| L
    GT -->|Launch| GA[Active round]
    GT -->|Cancel| L
    GA -->|End / hole complete| GF[Ended round]
    GA -->|Exit or abandon: confirm| L
    GF -->|Exit round| L
    GF -->|New round| GT
    S -->|Review round| R
```

## Screens and stable locations

Routes are parsed in `web/navigation.js`; an unknown location falls back to `#practice`.

| Screen | Location | Identity in the interface |
| --- | --- | --- |
| Practice selector | `#practice` | Practice navigation selected; four collapsible categories |
| Drill setup | `#setup/<drill>` for `pace`, `line`, `combined`, `random`, `ladder`, `distance-ladder`, `iron-ladder`, `wedge-ladder`, `driving-range`, `bag-mapping`, `wedge-matrix` | Drill title and parameter form; Practice selected |
| Setup copied from saved results | `#setup/<drill>/<session-id>` | Parameters loaded from that saved session |
| Active or recently completed session | `#practice/<session-id>` | Drill runner (putting, distance ladder, range, collection); Practice selected |
| Session list | `#sessions` | Sessions navigation selected |
| Saved review | `#sessions/<session-id>` | Session review; Sessions selected; Exit review and Practice selector |
| Relay | `#relay` (old `#capture` bookmarks resolve here) | Relay selected; input readiness, simulator destination, CSV export and database backup |
| Play | `#play` | Course library and imports; active-session return and setup guard |
| Course importer | `#play/import` | Import workbench; Play selected |
| Game setup | `#setup/golf-sim` (or `#setup/golf-sim/<session-id>`) | Rules/source/equipment; Play selected |
| Game runner | `#practice/<session-id>` | Play selected; round live/ended identity |
| Analyze | `#analyze` | Trends / Explore / Compare, selections and filters, CSV |
| Recently deleted | Within Sessions | Expandable section; restore controls |
| Confirmation | Modal over its originating screen | Cancel keeps the screen and data; confirm performs the named action |
| Service unavailable | Current requested location retained | Retry screen; Try again reconnects |

## Shared navigation

On **every** main screen (selector, setup, active session, completed session, review, session
list, Relay, Play and Analyze) the following paths exist:

| Control | Destination | Effect on an active drill |
| --- | --- | --- |
| Practice | Practice selector | Keeps it active; Return to active drill remains available |
| TraceLoft home (wordmark) | Practice selector | Same as Practice |
| Sessions | Session list | Keeps it active |
| Relay | Relay | Keeps it active; input keeps recording |
| Play | Game entry/menu | Keeps it active |
| Analyze | Cross-session analysis | Keeps it active |
| Browser Back / Forward | Previous / next studio location | Reloads the screen, not a new session |
| Browser refresh or copied location | That same screen/session | Fetches current shared results; does not resume an ended session |

Setup edits are drafts until Launch drill. Back, Forward, refresh, and leaving setup reload defaults
or the saved source session's parameters; unsaved form edits are not retained.

## Detailed transition checklist

| From | Control or trigger | To | Guard / cancel behavior |
| --- | --- | --- | --- |
| Selector | Set up drill on any drill card | Setup | Another active drill must end/abandon first |
| Selector | Return to active drill | Active session | Only offered when a drill is active |
| Setup | Practice / home / navigation | Chosen main screen | Creates no session |
| Setup | Launch drill | New active session | Valid parameters; another active drill blocks launch |
| Active session | End session | Completed results | Saves first; failure keeps session active |
| Active session | Final scored shot / putt | Completed results | Red Session over warning; input may continue |
| Active session | Exit session | Confirmation → selector | Cancel keeps it active; confirm ends and saves |
| Active session | Abandon session | Confirmation → selector | Cancel keeps it active; confirm saves Abandoned results |
| Active session | Practice / home | Selector | Keeps the drill active; Return available |
| Completed session | Exit session | Selector | No confirmation; preserves results |
| Completed session | Edit targets | Setup with saved parameters | Creates a separate session only on launch |
| Completed session | Delete session | Confirmation → Sessions | Cancel preserves results; confirm moves to recoverable trash |
| Sessions | Review session | Saved review | Completed, abandoned and interrupted results stay in review mode |
| Sessions | Return to active drill | Active session | Clearly labeled as live, rather than Review |
| Sessions | Delete | Confirmation → Sessions | Active drill cannot be deleted |
| Review | Exit review (top or below log) | Sessions | Does not end another active drill |
| Review | Practice selector (top or below log) | Selector | Does not end another active drill |
| Review | Edit targets | Setup with saved parameters | Another active drill blocks setup |
| Review | Delete session | Confirmation → Sessions | Cancel stays in review; confirm keeps recoverable copy |
| Review / session | Select putt; exclude/include | Same screen | Results update; no navigation |
| Recently deleted | Restore session | Sessions | Restores results without resuming a drill |
| Deletion notice | Undo | Sessions | Same recovery as Restore |
| Relay | Choose Off / GSPro / Infinite Tees | Same screen | Saves immediately; affects only future forwards; no session change |
| Play / Analyze | Go to practice | Practice selector | No session or input changes |
| Play | Return to active drill | Active session | Only shown when a drill is active |
| Relay | Export CSV | Download; stays on Relay | SQLite snapshot export; does not change input/session state |
| Relay | Back up database | Same screen with verified local path | Creates a local snapshot; no Google Drive upload |
| Confirmation | Cancel or Escape | Originating screen | No data change |
| Confirmation | Browser Back | Previous screen | Cancels the dialog; does not execute its action |
| Unavailable service | Try again | Requested screen | Failure stays on retry screen |
| Missing/deleted review link | Load or refresh | Sessions | Explains unavailable session |
| Old live-session link | Another drill now active | Saved review of the original session | Does not switch to the newer drill |
| Invalid location | Load or Back/Forward | Selector | Replaces invalid location with `#practice` |
| Fresh launch without location | Service has active drill | Active session | No new session created |
| Fresh launch without location | Service idle or drill ended | Selector | No new session created |

Intentional limits: a browser cannot render the app's retry screen if the entire HTTP server is
unreachable on a fresh load. Start the server and reload in that case. Unsaved setup drafts are not
retained when leaving the screen. Review and practice use shared charts, with separate navigation
identity and recording status.

## Paths by feature


### Relay

Global order: **Relay → Practice → Play → Analyze → Sessions**. `#relay` opens the source/destination
screen. Old `#capture` bookmarks resolve to Relay. Active putting, ladder, range and game runners link
to Relay; global Practice/Play and Return to active session restore the runner. Visiting Relay does
not end practice. Destination selection auto-saves and affects only future forwards. No capture
start/stop, calibration or preview routes remain in this application.

### Golfer, equipment and tags

Header golfer → select/create → Practice with that golfer's equipment/history. Active practice/Play
blocks switching until end/abandon. Manage bags → Specifications/Replace → Save applies to future
shots. Range live/review → select shots → Tags → add/remove with attempt/physical-shot scope →
save → toast Undo; Cancel returns unchanged. Reviews/resume/corrections require the selected owner.
Isolated iPad 1366×1024/phone 390×844 browser review covered create/spec save/demo/tag save/Undo/end.
Physical iPad Safari remains unverified.

### Practice categories

Practice expands/collapses Full swing, Irons, Wedges and Putting in place. Expanded sections persist
in tab session storage; Return to active drill and completion warnings remain outside the groups.
Iron/Wedge ladder setup uses #setup/iron-ladder and #setup/wedge-ladder; existing distance-ladder
links still work. Both aliases use the same runner and session lifecycle. Refresh retains the preset.
Isolated UI checks passed: expand/collapse, keyboard Enter, preset setup/refresh, Back/Practice return,
1366 × 1024 and 390 × 844 with no horizontal overflow or console errors. No live capture changed.

### Distance ladder and bag picker

**Distance ladder** adds the `#setup/distance-ladder` location (and
`#setup/distance-ladder/<saved-session-id>` for Edit targets). It uses the shared
`#practice/<id>` runner and `#sessions/<id>` review locations. Practice now has six drill cards.
Wedge/iron/custom presets and preview are controls within setup, not new screens. Another active
drill blocks both setup and launch. Capture must have the selected distance column; start/launch
guards explain an incompatible profile. Full-swing runners use shots/yd terminology and the same
End/Exit/Abandon, completed-banner, review, Delete/Undo/Restore paths as putting.

Distance-ladder setup and active runner include Bag/Club controls and **Manage bags**, a modal at
the same location. Close or Escape returns to the originating screen, discarding unsaved catalog
edits; Save bag/Create bag persists immediately without launching/ending a drill. Setup parameters
stay intact while the dialog is open. Live selection applies to upcoming shots only; changing bags
clears club. Stale catalog edits, duplicate names and invalid club membership explain the guard.
Finished/review sessions display frozen tags without next-shot controls. These affected journeys
were checked separately at desktop and 390 px on 2026-10-01: launch with club, live switch, second
bag/custom club, cancel/reopen, refresh, completion, saved review and copied setup. No new route.

The compact picker replaces the bag/club dropdowns with three quick bag tabs and club circles.
**More bags** opens a modal listing all bags; Cancel/Escape retains selection, choosing a new bag
clears club and returns to the origin with that bag visible. Empty quick slots open **Manage bags**
with the new-name field focused. Clear club records future shots untagged. Shared catalog updates
refresh setup's picker without discarding other parameter drafts; removed clubs clear the draft tag.
Follow-up isolated browser checks covered More bags/fourth-bag selection, keyboard club selection,
live switching with earlier tags intact, Clear club, bag-editor Close, copied setup, remote catalog
removal, stopped warnings and End session with capture still running. Desktop/phone runner and
tablet setup layouts had no horizontal page overflow. The empty-slot focus shortcut and Escape paths
were inspected in code but not exercised in this follow-up browser pass. Healthy capture uses only
the header; warnings remain above tagging and completion keeps its red banner. No new route.

### Driving range and demo

| Origin / control | Destination / effect |
| --- | --- |
| Practice → Driving range → Set up drill | `#setup/driving-range`; blocked while another session is active |
| Setup → Launch range / Launch demo range | `#practice/<id>`; real and synthetic identities are distinct |
| Active range → Change target | Modal; Save changes future targets; Cancel/Escape preserves them |
| Range → plot/table Inspect shot → Back to latest | Same runner; linked tiles/profile; latest follow resumes |
| Shot workspace → cleanup action | Selection/reason confirmation; Apply edits exact keys; Cancel preserves them |
| Removed filter → select → Restore | Same workspace; original exclusion state retained |
| Undo last cleanup | Same runner/review; latest remaining batch reversed |
| Active range → Practice/Sessions/Capture/Play/Analyze | Session stays active; Return to active drill remains |
| End / Exit / Abandon | Existing lifecycle guards and red completed/abandoned warning |
| Saved range review → Exit review / Practice selector | Sessions / Practice respectively |
| Results/review → New range / edit setup | `#setup/driving-range/<id>` copies parameters; active-session guard applies |
| Sessions → All/Real/Demo filter | Same list; deleted sessions remain under Recently deleted |
| Delete session → Undo / Recently deleted → Restore | Recover exact saved session, without resuming |
| Browser Back during modal | Dialog closes; no unapplied cleanup is saved |

2026-10-02 range visual follow-up: Side view / Top view switches the selected-shot profile in place,
without changing the route, capture or session state. Isolated live/ended/saved-review checks confirm
shot inspection and Exit review still work. Club legend is informational; existing table filters
control membership. Desktop 1440 px and phone 390 px reviewed after this change.

2026-10-02 dispersion follow-up: no route changes. In the default Included state the table stays
included-only while the scatter retains excluded context. Excluded/Removed/All state filters apply
to both surfaces; circles always require included points. Fresh isolated checks covered exclusion,
Undo, removal/Undo, bag filtering, Carry/Total and plot-source changes, End and Saved review. Per-club
colors and circles persisted on review. iPad landscape and phone layouts were checked again.

2026-10-02 compact legend: the info button beside Shot dispersion opens contextual help in place;
no route/session change. Click/tap again, outside click, focus leaving or Escape dismisses it.
Hover/focus previews it and click/tap pins it. Fresh isolated click, keyboard, source-switch and
saved-review checks passed at large iPad landscape and phone sizes; physical touch remains unverified.

### Bag mapping

Practice → Full swing → Bag mapping uses #setup/bag-mapping, then the shared #practice/<id> runner.
Saved review uses #sessions/<id>; new collection/edit setup copies its plan. Existing active-session
guards and exits apply. Fresh isolated browser checks covered two-club demo collection, club switching,
manual finish, reload, saved review and Exit review; 1366 × 1024 and 390 × 844 stayed within viewport.
Automated checks cover invalid plans, exclusions, saved model restoration and recoverable deletion.

### Wedge matrix

Practice → Wedges → #setup/wedge-matrix → #practice/<id>. Select a cell changes the next wedge
and swing together; direct swing buttons change upcoming intent only. Targets/recommendations do not
change the route. Finish/abandon/review and new-matrix setup reuse lifecycle guards and exits.
Isolated checks cover custom-label setup, two sampled cells, target suggestion, End, review and
390 px no page overflow. Shared cleanup, delete/restore and label freezing also have API coverage.

### Play rounds

Play → setup → round uses the shared stable session routes. Setup Cancel returns to Play.
Other active drills/rounds block launch and offer Return to active session. Visiting Play/Practice/
Analyze/Sessions leaves a round active; End round stops recording without leaving. Exit round confirms
ending (Cancel keeps it active) and returns to Play; Abandon confirms, saves and returns to Play.
Completion shows the red banner; New round copies saved rules. Saved review selects Sessions,
with Exit review, Practice selector, Play menu and recoverable Delete/Undo. Top and bottom exits exist.
Browser verified setup/reset/guard, map and button aiming, bag/club tagging, automatic finish, refresh,
review and exclusion preserving score, review exit, exit Cancel, abandon and deletion/Undo.
Primary landscape/reduced-height and phone widths checked in the isolated service.

2026-10-02 score/aim follow-up: no route changes. Map tap, keyboard aim button and numeric aim
update the two distance readouts in place. Live → automatic completion → saved review preserves
par and score components. Fresh isolated checks verified yards/feet and all four target viewports.

2026-10-02 terrain follow-up: Map display expands in place in active and saved rounds. Detailed
terrain and Show scoring boundaries only change rendering, retain keyboard focus and never call
shot/aim APIs. Aiming uses map taps, Aim at pin and numeric coordinate entry; left/right buttons
are removed. Fresh isolated checks covered switches, keyboard pin aiming, green zoom, completion
and saved review, with no route or scoring changes. iPad landscape and phone layout checks pass.

Play → Load Tour demo bag stays on Play and gives completion/already-loaded feedback. Sessions
opens the two DEMO collections; their existing review/exit/cleanup paths apply. Loading while a
round is active does not take ownership or change its tags. New demo round setup can select the
reference bag, then receive total-distance suggestions. The source link opens external documentation.

### Full-course rounds

Play → Boulder Beach card → existing round setup → Launch → hole 1 of 18. Completing holes 1–17
keeps the session active and shows a red pause banner; Next hole advances the same saved round.
The previous hole cannot accept further scored shots. Hole 18 ends the round with the standard red
Session over banner. End/abandon/exit remain available between holes. Play menu leaves the round
active and Return to active session restores it; a competing launch remains blocked.

The scorecard expands in place during play. Ended round/Sessions → Review → Review a hole selects
its frozen map, distance, score and shot log without changing the current hole or stored state.
Unplayed holes remain unplayed. Exit review returns to Sessions; Play menu returns to the library.
New round / edit setup preserves the full-course choice. Legacy cards remain single-hole rounds.
Fresh isolated checks covered setup, launch, next tee, partial ending, full completion, review hole
selection and exits at iPad Pro landscape and phone sizes; see docs/PEBBLE_BOULDER.md.

### Nine-hole selection

Play → course setup → Full 18 / Front 9 / Back 9 → Launch. Front starts at hole 1 and ends at 9;
Back starts at 10 and ends at 18. Setup displays each choice's par/yardage. Switching course updates
those totals; New round / edit setup restores the saved selection. Reset settings returns Full 18.
Only selected holes appear in scorecards and review; Sessions labels Front/Back 9. Imported single
holes hide the nine-hole choices. Existing full rounds keep all eighteen holes.

Shared active-session guards/exits remain. Intermediate completion pauses until Next hole; final
selected-hole completion ends the round. Misread/Mulligan can reopen it without clearing earlier
selected-hole results. Course cameras resize with the panel; Map options & hole guide retains
scoring boundaries, and map taps still use the saved world coordinates.

Fresh isolated browser checks: both course choices/totals, Back 9 launch at 10 → complete → Next
11 → Misread back to 10 → End → selected-hole review → edit setup → Front 9 launch at 1. Reviewed
iPad landscape, reduced-height, desktop and phone layouts. API tests complete both nines on both
courses and reopen the final selected hole. Physical iPad Safari/touch remains unverified.

### Mulligan and Misread

- Active Play → header Mulligan / Misread → previous position on the same active round.
  Header order: Mulligan → Misread → End round → Play menu → Exit round.
  Counts remain visible in the collapsed scorecard; expand it for Shot correction history.
  Choose the bag in setup; the active round shows its name with a compact club-only selector.
- Hole complete → either action → reopen that hole; Next hole disappears until it is completed again.
- Next tee before another scored shot → either action → return to the preceding completed hole.
- Round ended / Sessions → saved golf review → either action → active Play route for the restored
  hole, including hole 18. Simply viewing review does not resume recording.
- Button help identifies the latest scored attempt across the round, even while reviewing
  another hole. Repeated actions rewind newest-first. Corrected and unscored attempts are skipped.
- No scored attempts, abandoned round or another active session: controls disabled with reason.
  Server also rejects stale turn/key, deleted rounds and pending saves; no concurrent session takeover.

### Course library: Sheboygan Straits, Boulder Beach, Judges Course

Play → Sheboygan Straits → Set up round preselects the Blue 18-hole package; Cancel returns to
Play. Shared round routes, active-session guards and exits apply. Hole guide expands in place.
Completion → Next hole → next tee; Misread can return to the just-completed hole. All eighteen
holes are preserved for Sessions review. The built-in library now contains Sheboygan Straits and
Boulder Beach; imported holes remain separate. Meadow One, Willow Cove, Pine Bend and Meadow Reach
are removed from Play/setup choices. Their existing sessions remain reviewable/playable.

Fresh isolated browser verification covered this selection/setup path, hole completion/Next hole,
Misread back to hole 1, Play menu active guard/Return, End, hole 18 review/Green zoom and Exit.
Viewport checks: iPad 1366×1024, desktop 1536×960, phone 390×844; no document overflow.

### Map-first Play, replay, landing rules and course versions

No route changes. The score strip expands the scorecard/history; ended/review opens it and the shot
log automatically. Review a hole switches the displayed hole/map/log while the round total remains
the original aggregate. Active Club for next shot keeps the setup bag and updates the existing
planning layer. Club dispersion expands settings below the map; collapsing it does not hide the
overlay. Map options & hole guide expands coordinate aiming, terrain/boundary controls and Relay.
Demo shot generation and Bag suggestions each expand in place. Panel openness survives shot/aim
redraws within the session. Reload starts with the default panels.

Header order remains Mulligan → Misread → End round → Play menu → Exit round. Lifecycle controls
also remain outside the lower disclosures. Completion/recording warnings are not collapsed.
Fresh isolated browser checks covered club changes, map tap/pin/numeric aim, preview modes/source,
terrain boundaries, green pace, gimme completion → Misread reopen → completion → Next hole,
End round and saved hole selection. Verified iPad landscape, reduced-height, desktop and phone
layouts; physical iPad Safari/touch remains unverified. See [design review](designs/play-map-first/README.md).

Ball replay adds no routes. Range Flight profile and the row below Play's map expose Replay ball
and Skip. New shots animate only while viewing that session; entry/reload/review do not autoplay
history. Range inspection retains the selected shot until Back to latest. Play completion, Next
hole, Misread/Mulligan and Exit remain available during playback. A new hole or correction clears
the previous animation; finishing an approach returns to the normal green camera.

Round setup adds Landing in rough / Landing out of bounds rollout sliders, separate from the
Shot from rough / Shot from sand distance settings. Demo shot input exposes optional reported
carry. No route changes. Launch saves settings; the live log/review shows landing adjustments and
original source carry/total/offline. Correction, end/review and exits keep their existing paths.

Finished-art course registration changes no routes. Play → course setup → launch now selects the
reviewed v2 packages; active/saved rounds keep their frozen versions. Start a new round to use the
revised boundaries. Fresh isolated browser verification covered Boulder setup → live map/Green →
boundary toggle → bunker shot → End/review → Play menu, then Straits setup → Back 9 → hole 10
Green/terrain toggle → End/review. Map boundaries use the same geometry with or without artwork.

The catalog now selects Boulder Beach v3 (fairways 6/16/18) and Straits v2. Prior v1/v2 rounds
retain their copies. New-round setup/review routes and guards are unchanged.

Judges Course adds a third 18-hole library choice using the same setup/launch/review paths.
Full/front/back choices keep original numbering; Provided yardages identifies the supplied
scorecard without guessing a tee color. Isolated browser verification covered Back 9 setup,
club selection, live map, Green/overview, boundary toggle, ended review and Play menu.

### Club dispersion preview

No new route. Active round → bag/club → preview source/profile/visibility controls stays in place;
preview controls do not change aim or score. Empty profile → Bag mapping/Wedge matrix setup uses
the existing guard: with a round active it returns to Practice with the End/abandon explanation
and Return to active drill. Fresh isolated browser verified that return preserves the round.
Full-swing preview hides on the green and in ended/saved review; normal exits remain available.

### Course importer and workbench

Play → Import a course → `#play/import`. Download or file input loads an unsaved draft; select a
hole → Preview → correct geometry → Save draft, or acknowledge review → Publish hole to Play. Source/settings changes invalidate
the preview acknowledgement. Publication stays in the importer and adds a version to the library without
starting or ending a round. ← Play returns to the library; imported-hole Set up this hole selects
that version in the shared round setup. Cancel returns to Play. Active sessions still block launch;
importing itself is available without taking capture ownership. Browser Back/Forward works; reload
preserves saved courses but clears an unsaved in-memory draft. Invalid routes return to Practice.
Open Jackson Park example loads the bundled, dated source in place without network access or a save.

Course workbench follow-up: Saved draft → Open draft restores source/settings/geometry with review
approval cleared; New import confirms replacing unsaved work. Export draft → file chooser opens a
separate draft copy. Save draft stays on the route; Publish saves the draft, adds a fixed library
version and stays in the workbench. Incomplete geometry may be drafted but cannot be published.
← Play → imported-hole setup → demo/live runner uses existing launch/exit guards. Applied edits
survive same-page navigation; refresh requires a saved server draft. Finish/cancel pending drawing
before navigation. Fresh isolated review covered reopen, correction/Undo, invalid pin publication
block, publish → setup → demo shot → End → Play → importer, and responsive layouts.

### Analyze

`#analyze` opens Trends / Explore / Compare in place. Selections & filters expands/collapses without
changing membership; Apply refreshes the common query. Mode/type changes reset dependent filters.
Trends → shared interval inspection → detail rows; Explore → bins/ranges → linked views/rows/CSV;
Compare → named dates/session/config/tag scopes → paired results and independent cohort CSV.
Saved views → Save/Load/Remove stores dynamic browser queries, not frozen publications.
Shot workspace or Session coverage → Review opens `#sessions/<id>`; persistent Analyze returns
to applied choices. Practice and other global tabs remain available. Empty/error states provide
reset/retry. No route changes session/input ownership. See [Analyze guide](docs/ANALYZE.md).
Isolated browser checks verified real-empty/demo, multi-club/metric selection, shared inspection,
numeric filters/clear, saved-view restore, comparison recovery, review and Analyze return, plus
expanded/collapsed iPad and phone layouts. API tests verify exact selected CSV membership.

### Analytical controls

Analyze → Metric versions, configurations and tags → choose basis/configuration/tags → Apply. Bag mapping or Wedge matrix → sampled result → Use this collection in Play. No top-level route changes; these controls are secondary disclosures/actions.

Analyze → Calculation methods and version history → choose family/method → Preview recalculation
→ inspect coverage and changed values → Publish. Saved batch → Review → Refresh preview or Resume
interrupted run → Publish. History CSV downloads owned calculation versions without changing selection.
Changing the golfer scopes all these paths. Missing/error/pending inputs or changed source, equipment,
inclusion or selected versions block publication; review/refresh remains available. Publication affects
analytical selections and future Play profiles, while session review and saved scores retain their pins.
Verified staging/publication/history review and collection publication in the isolated browser at
1366×1024; advanced controls and tables retain internal scrolling at 390×844. No top-level route changes.

## Verification history

Dated evidence for earlier changes, kept for traceability. Removed screens are noted as such.

### Capture screen (removed 2026-10-03 when acquisition moved to TraceCapture)

Capture includes AirPlay, HDMI and VDD profiles. VDD exposes an explicit secondary-display selector;
changing the profile sets the matching source. Preview is available before calibration and never
records shots. Start capture requires geometry and glyph training; VDD additionally requires a
trained calibration status. Controls lock during run/preview and Stop releases the owner before
they unlock. VDD guard errors stop capture without ending the drill. The source/display selection
does not introduce another route or alter Practice/Sessions navigation. VDD Capture/Preview/Stop and
Practice return were checked after this update; the previous 125-path audit predates these controls.

### Historical 125-check audit and distance-ladder recheck

Verification status: the screen transitions and guards below exist in the app. The isolated browser
audit passed 125 checks, including every main screen's shared navigation, session lifecycle controls,
saved-review exits, history/refresh, and service recovery. Persistence-failure guards are additionally
covered by the existing web API tests; these failures were not induced in the user's live service.

The 125-check audit predates Distance ladder. Its affected paths were separately rechecked in an
isolated service on 2026-10-01: setup/launch guard, active return and exit cancel, completion/manual
end, abandon cancel/confirm, copied setup/refresh, saved review, exclusion, Delete/Restore, both
review exits and browser Back, with desktop and 390 px layouts. See WORK_LOG.md for this update's
actual evidence; the earlier audit is not used as its verification.

### Earlier verification evidence

- Five-section update (2026-10-01): fresh browser checks verify requested order, all five tabs,
  selected identity on Play/Analyze/review, Analyze refresh, Play Back/Forward, both placeholder
  exits to Practice, and return to the original saved review. Capture and sessions were not changed.
  At 390 × 844 all five controls are 45 px high and fit without horizontal overflow; the 850 px
  tablet header also fits. JavaScript syntax and new/old route checks pass; no browser warnings/errors.
  The existing Return to active drill handler is reused; its new placeholder visibility was not
  exercised with a live active drill. This is targeted evidence, not a rerun of the historical audit.

- Distance/ladder update (2026-10-01): isolated API and fresh browser checks cover the fifth drill setup, invalid range, ladder launch/advancement, exclusion, active setup guard, cancel exit, automatic completion/banner/footer exit, saved review, Practice selector, Back, copied parameters, descending launch and abandon cancel/confirm. Fixed distance setup and manual completion are checked separately. Phone setup/runner checks use 390×844. This is targeted new-path evidence, not a rerun of the historical 125-path audit.

- SQLite migration audit (2026-10-01): fresh isolated API checks cover completion, abandonment,
  exclusions, stale commands, active-session protection, deletion/restore and export/backup. Fresh
  browser checks on localhost:8766 cover review/selector exits, Random pace setup/launch, stopped-capture
  warning, manual completion/banner/footer exit, Back, CSV download and backup feedback. Review at
  390x844 has no horizontal overflow. This is new storage-cutover evidence, not a rerun of all 125 paths.

- Browser audit: `designs/navigation-audit.json` records 125 passing checks with destination screens
  and locations. It includes four drill setup/launch flows, all seven main screen states' shared
  controls, active-drill setup/deletion guards, manual/automatic completion, abandon/exit cancel and
  confirm, review-only interrupted results, exclusion, deletion, Undo, restore, missing/invalid
  locations, stale live links, Back/Forward/refresh and failed/successful retry after a simulated outage.
- Phone verification at 390x844: review header and footer exits work; Sessions remains selected;
  there is no horizontal page overflow. Screenshot: `designs/web-review-navigation-mobile.png`.
- All state-changing checks used localhost:8766 and temporary session files. Live localhost:8765
  verification uses only navigation and reads; capture and the user's session files remain unchanged.
- JavaScript syntax checks pass. The existing Python suite passed 73/74 tests while live capture was
  running. The worker-invalid-settings test expected a validation message but instead received the
  active capture-lock message. Capture was left running; all web/API tests in that run passed.
- Intentional limits: a browser cannot render the app's retry screen if the entire HTTP server is
  unreachable on a fresh load. Start the server and reload in that case. Unsaved setup drafts are not
  retained when leaving the screen. Review and practice use shared charts, with separate navigation
  identity and recording status.

### Driving range QA (2026-10-01)

Range QA used a separate database/service with synthetic inputs at desktop 1440, tablet 850 and
phone 390 px widths. Checked empty/live/ended/review states, refresh, back navigation, copied setup,
active-session guards, exits/cancellation, abandonment, header capture continuing after completion,
keyboard inspection, cleanup/Undo and recoverable demo deletion. The earlier broad navigation audit
is historical; this range audit verifies the changed paths, not every unrelated feature.

### Fictional hole library (retired 2026-10-03)

Historical implementation (retired from the library 2026-10-03): Play displayed full-art cards for Meadow One, Willow Cove, Pine Bend and Meadow Reach.
Each Set up round preselects its immutable course ID in the existing `#setup/golf-sim` form;
Cancel returns to Play and the course dropdown can choose another hole. The shared round/session
routes and exits remain unchanged. Active sessions disable all four launch cards and provide
Return to active session. Each launch is a single-hole round, not a multi-hole tournament.
Fresh isolated browser review verified all three new card selections, Willow completion/banner,
partial-round End → Play, Meadow active guard → Return → refresh, and responsive card/runner layouts.
