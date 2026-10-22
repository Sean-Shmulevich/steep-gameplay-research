# Build and run the native mod host

The host, startup launcher, plugins, build-specific game adapter and observation
probe are now published as independently authored C source. A checkout can build
the native components without the private research workspace. You still need your
own compatible game installation and Windows or a working Wine environment.

## Build

Install a Windows x64 MinGW compiler and Python 3.9 or later. From the repository
root, choose an output directory outside the repository:

```sh
python3 scripts/build_snow_host.py --adapter steep --out /tmp/snow-host-steep
```

Use `--adapter fixture` for a synthetic host build with no game dependency. The
builder compiles the host DLL, startup launcher, checked loader, two sample
plugins and the separate snow-update observation DLL. It never starts the game.
The checked-in sources were compiled with MinGW using warnings as errors for both
adapters. No compiled game files are distributed.

## Start against your own installation

In a Windows command prompt, use absolute Windows paths:

```text
C:\mods\snow-host\startup_launcher.exe C:\Games\Steep\steep.exe C:\mods\snow-host\snow_host.dll 47017
```

Keep the `plugins` directory beside `snow_host.dll`. On Wine, invoke the launcher
through your configured Wine executable, and supply paths as seen by that Wine
prefix. This does not create a suitable graphics/prefix configuration for you.
The launcher starts the game normally, then loads and starts the host as soon as
the Windows loader is available. It is not an executable-entrypoint hook.

The host listens on loopback. The client implementation and CLI are in
`scripts/snow_host_client.py`; run it with `--help` for its current commands.
Start with `status` and reader commands before trying a mutation. The host
README documents command capabilities, leases and limitations. The standalone
launcher remains the game's parent until exit and has no research-session
five-minute watchdog. The workspace-only `run_late_load.py` automation adds that
watchdog and navigation, but still needs private Highball/control helpers.

## Compatibility and evidence

`steep_adapter.c` is tied to the analyzed image and contains fixed addresses,
short instruction signatures and object-link checks. The analyzed memory-image
hash is recorded in its header; the adapter does not calculate that full hash at
runtime. Passing short guards is not general compatibility proof. Do not rebase
addresses or disable checks to make another build bind.

Pause, step, resume, player reads and speed assignment have a documented live
acceptance receipt in this repository. This turn's publication build does not
repeat that gameplay test. Velocity assignment resets angular velocity; the new
spin-preserving impulse path is not installed in the native game yet.

`snow_update_probe.dll` is a separate experimental observation component. Do not
put that DLL in `plugins`: it does not implement `SnowMod_Initialize`. The separate
optional `--capture-plugin` build supplies `plugins/update_capture.dll`, which
does implement the host callbacks and remains disabled until configured. Its synthetic
Windows fixture passes under Wine, and it now has explicit guarded slot install/restore entry points. A later [live lifecycle check](update_capture_live_slot_validation.json) installed and restored the slot in gameplay but recorded zero calls; invocation remains unproved. Its README explains configuration, capture close/drain and lifetime
requirements. Source availability does not turn it into a finished live hook.

Game assets, executable payloads, raw memory dumps, recordings, saves and local
credentials remain excluded. Build-specific offsets and our authored integration
source are included so another engineer can actually continue the loader work.

## Bounded original-game capture plan

In the configured private research workspace, run:

```sh
python3 scripts/run_late_load.py --experiment host --load-at startup --plan update-capture
```

This command builds the opt-in capture plugin, launches with a five-minute
watchdog, and requires recognized gameplay before requesting pause. The plugin
acquires the player while held; resume starts a two-second observation interval.
The controller requires confirmed slot installation, restoration, drain, zero
dropped records and at least one valid before/after pair. It requests resume on
exit even if capture fails. Raw traces stay in the private session directory.
This runner depends on the existing private navigation and runtime helpers; it
is not the standalone build command above.

The [first live attempt](update_capture_live_attempt.json) loaded the host and
plugin but failed startup navigation after capture/recognition timeouts. It did
not reach the capture plan or install the observation slot. Cleanup verified the
original DLL, restored settings and stopped the bottle. The next live gate is
still a real paired snow-update capture; no impulse is applied by this plan.

### Screen-recognition diagnostic

An [offline comparison](capture_ocr_diagnostic.json) reproduced the recognition
timeout using an existing splash image with no running game. Vision accurate
mode timed out both with and without CPU-only processing. Fast mode completed
in 0.13–0.27 seconds; Tesseract also read the image. The private capture helper
now selects Vision fast mode. Recognition of the title, map and gameplay HUD
still needs a live check.

To test an existing local capture independently of Wine or window selection:

```sh
python3 scripts/image_text.py /path/to/capture.png --timeout 8
```

This uses an installed `tesseract` executable, returns structured text and timing,
and fails on OCR timeout or process failure. It performs no capture or input.
Game screenshots remain private. OCR text alone does not establish player-object
identity or a safe physics boundary.

The [second live attempt](update_capture_live_slot_validation.json) reached
gameplay with one manually assisted offline-dialog dismissal. The configured
plugin reported installation, restoration and drain success, but zero records.
The host ended in ordinary mode and cleanup passed. A redundant resume in the
controller obscured this result; the controller now avoids a second resume
after a confirmed first one and preserves an earlier exception if cleanup fails.
Eight focused controller tests pass; the fix has not yet been repeated live.

Fast Vision OCR returned promptly but misread the offline notice. The private
capture command now retains native window selection/capture and uses the public
Tesseract helper for recognition; that combination recognized the gameplay HUD
in this run. Full unattended startup remains to be retested.

Next discriminate no slot dispatch from no selected-actor match, then verify
motion before repeating capture. Empty records establish neither a physical
update boundary nor a safe location for impulse writes.

The capture summary now includes `dispatch_counts_valid`, `selected_calls` and
`other_calls`. These are lifetime hook-entry counts, including forwarding after
capture closes; each counter is atomic, but the pair is not an atomic snapshot.
[Windows fixture validation](update_capture_dispatch_validation.json) covers
filtering, late calls and the plugin export. A synthetic plugin run exported
363 selected calls and 363 records with zero other calls or drops.

For the next live result, interpret zero selected and nonzero other calls as
evidence that the hook ran for other actors. Both zero means no dispatch was
observed through this installed hook during the interval. Neither result alone
identifies an alternative scheduler route. Selected calls with zero records
require checking capture closure and lifetime timing before blaming snapshots.

### First paired original-game capture

The [moving-rider run](update_capture_live_success.json) passed unattended
startup navigation, a 700 ms normal forward-input preparation, player identity
checks, pause/configure/resume, capture, and 20 seconds of advancing ordinary
simulation. Cleanup restored settings and verified the original DLL. The rider
changed from flags 1 to 3 and its position changed across the subsequent reads.

The plugin installed/restored/drained successfully and recorded 235 selected
actor calls with 235 valid before/after pairs, zero other calls and zero drops.
All pairs showed changes in main-body linear and angular velocity. Ten threads
executed calls. This establishes invocation of this actor route in this run,
not deterministic execution or exhaustive state coverage.

Grouping by the observed request counter produced 204 single-call groups,
14 two-call groups and one three-call group. Within every group the second
timing argument divided by the first matched that group's call count within
1e-5. The request counter stayed unchanged across each pair. This supports
the substep interpretation, but does not supply a directly read substep index.

Pending impulse was zero before every call. Native impulse consumption and
safe impulse submission remain open. The next useful controlled experiment
is observation at the pending-consumer boundary, with an explicit thread/order
contract before adding a write API. The earlier empty result remains evidence
of an inactive-state capture; inactivity is a supported explanation, not proved
as its sole cause.

### Reproduce the timing comparison

```sh
python3 scripts/analyze_update_capture.py /path/to/update_capture.ini.trace.jsonl
```

The analyzer rejects incomplete exports and duplicate record indices. It groups
consecutive guarded observations by actor/body ownership and request counter,
then checks `elapsed == f32(consumed / f32(observed_count))` exactly after
rounding the JSON numbers back to float32. Missing request validity, changed
ownership and changed request values within a pair break the group. Partial
groups are reported as nonmatching, not silently repaired. The output omits
raw pointers, body payloads and process paths.

The [first live timing comparison](update_capture_timing_comparison.json) found
219 of 219 groups matching the reconstructed subdivision arithmetic, with no
rejected records. This narrows the timing boundary beyond an approximate ratio
check; it does not validate upstream smoothing or all scheduler policies.

Probe ABI v2 adds `preconsume_counter` and `preconsume_timers` to snapshots and
JSONL rows. Rebuild all probe consumers with the matching header; this is an
experimental exact-build ABI, not a compatible extension for old record buffers.
The [marker contract](../../docs/reconstruction/CENTRAL_IMPULSE.md#non-mutating-pre-consumption-markers)
and [synthetic validation](preconsume_snapshot_validation.json) distinguish
static placement from the pending live check. No physics setter is added.

ABI v2 has now [captured the marker live](preconsume_live_observation.json):
228 valid pairs, each with exactly one signed-counter decrement interpreted
modulo 2^32. All 211 timing groups matched float32 subdivision, including one
five-call group. Pending impulse remained zero at both observation boundaries.
Stability and cleanup passed. The earlier [map-recognition failure](preconsume_navigation_failure.json)
is retained separately and contains no physics result.

The analyzer reports counter availability, invalid pairs, unchanged pairs and
unsigned delta counts. It deliberately does not label a decrement as proof of
consumer execution. Old traces without the fields remain analyzable and are
reported as unavailable, not as zero counters.

The legacy `preconsume_timers` array is now interpreted more precisely:
element 0 is a neighboring impulse-magnitude scalar; element 1 is a countdown.
The [clock comparison](preconsume_countdown_validation.json) found exact
per-substep countdown subtraction in all 228 pairs, including 31 calls where
the consumed interval differs. `analyze_update_capture.py` reports both
clock-match counts and isolates those discriminating calls.

## Bounded action identity observation

In the established private research workspace, run:

```sh
python3 scripts/run_late_load.py --experiment host --load-at startup --plan action-observe
```

This requires the private action collector and analyzed image in addition to
the normal launch prerequisites. It navigates recognized startup screens,
checks host readiness, reads action 0x76 without gameplay input, checks ordinary
simulation for 20 seconds, then closes its session and restores settings. The
collector uses process identity and selected instruction signatures; it makes
no atomicity claim. Raw reads stay in the private session directory. The first
live run passed and identified a composite action; see the
[action identity receipt](action_identity_live_observation.json).

Use `--plan composite-observe` with the same command to enumerate up to sixteen
children of the selected composite action. It checks the parent lookup again
after enumeration and verifies callback signatures. It does not invoke child
callbacks or determine the producer that last executed. The first live run
observed a vector-source child followed by a two-axis fallback; see the
[child observation receipt](composite_children_live_observation.json).

Use `--plan source-observe` to add source gates, query IDs and processor
configuration to the child observation. The first run produced a partial
receipt and rejected changing unused handle bits. The corrected comparison has
passed recorded-read replay but still needs a new live run. See the
[source receipt](action_sources_live_observation.json).

Use `--plan chain-observe` to include one level of the directional processor
chain and recheck its source afterward. The first run passed with two stages,
using 212 of the helper's 224 permitted requests. A larger traversal may exhaust
that bound and must report refusal, not silently omit checks. See the
[live chain receipt](action_chain_live_observation.json).
