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

### Ramp configuration observation

`--plan ramp-observe` prepares a directional-only variant of the private action
collector. It discovers the current action, composite, directional source and
processor chain, then reads the known ramp stage's duration, axis mode, axis
count and up to 64 keys. It skips vector-source details. Independent chain
identity reads are batched before and after the ramp settings to preserve the
existing 224-request/40-second helper limit. Parent and source checks remain.

This mode requires the private collector and supported original-game setup;
it is not a standalone public memory reader. It has passed an offline transport
fixture with 64 synthetic keys in 219 requests. It has **not** run live.
Larger or changing graphs can still exceed the budget and must refuse rather
than extend it. An observed active handle does not prove thread-local
availability or actual ramp execution. Results contain private-session
addresses and curve data; keep the raw result outside the public repository.
Use only when current session ownership permits live testing.

### Experimental delegate recorder

The build also emits `snow_delegate_probe.dll`. It is not loaded automatically.
It records a selected graphics-main or engine-main invoker's two-argument calls and supplies an opt-in,
one-attempt heap-slot installer with conflict-aware restoration. See
[delegate adapter contract](../../docs/reconstruction/SCHEDULER_DELEGATES.md#experimental-windows-adapter)
for caller lifetime requirements and synthetic Windows validation. The fixture
passing does not establish a safe live-game installation window.

To build the separate one-shot main-delegate capture plugin, add
`--delegate-capture-plugin` with `--adapter steep`. It remains disabled without
its INI opt-in and refuses a trigger that exists at initialization. See the
[capture controller contract](../../docs/reconstruction/SCHEDULER_DELEGATES.md#one-shot-capture-controller)
before using it; it does not establish an owner-lifetime lock.

In `plugins/delegate_capture.ini`, the optional `[capture]` key `site=engine`
selects BeginEngineFrame. Omit `site` or use `site=graphics` for the existing
BeginGraphicFrame behavior. Other values refuse initialization. Example:

```ini
[capture]
enabled=1
site=engine
milliseconds=500
```

Initialization still waits for a newly created `delegate_capture.ini.trigger`;
it does not create the trigger itself. The summary in
`delegate_capture.ini.trace.jsonl` identifies `site` so captures cannot silently
be confused. This is an experimental observer, not an engine command publisher.

### Experimental finalizer recorder

The build emits `snow_finalizer_probe.dll`, a separate ABI 1 component, not an
automatically installed plugin. It filters one configured graphics job while
forwarding other objects sharing its table. See the
[finalizer adapter contract](../../docs/reconstruction/SCHEDULER_DELEGATES.md#filtered-native-finalizer-adapter)
for lifetime, ABI, installation, observation and cleanup requirements. A bounded
live controller with build fingerprint checks is still needed. Finalizer entry
and return occur before worker completion accounting finishes; neither is an
unlocked mod callback or an unload barrier.

To build the synthetic Windows fixture from the repository root:

```sh
x86_64-w64-mingw32-gcc -std=c11 -O2 -Wall -Wextra -Werror -I native/snow_host tests/fixtures/snow_finalizer_probe_fixture.c -o /tmp/snow_finalizer_probe_fixture.exe
```

Run the fixture in Windows/Wine as `snow_finalizer_probe_fixture.exe <DLL-path>
<scenario>`. Scenarios are `normal`, `readonly`, `conflict`, `identity_before`,
`identity_during`, `closed`, and `heap_table`. Each process uses synthetic
allocated job storage and its own executable-backed table, not game memory.

Build the opt-in one-shot finalizer controller with `--adapter steep
--finalizer-capture-plugin`. Its `finalizer_capture.ini` needs `[capture] enabled=1`
and optionally `milliseconds=500` (allowed 100..2000). It refuses an existing
`.trigger` at initialization and waits up to 180 seconds for a fresh trigger.
Use a new output/config path per experiment. Output is private JSONL at
`<config>.trace.jsonl`; check the complete row count and all install/restore/drain
outcomes. The controller verifies three code fingerprints and the selected job
binding before installation. It never sends input or pauses the scheduler.

### Coordinated main/finalizer capture

Build with `--adapter steep --scheduler-phase-capture-plugin`. This produces
`plugins/scheduler_phase_capture.dll`; use it instead of the two independent
capture plugins for a paired experiment. Configuration is the same `[capture]`
section. It refuses stale trigger or output files. A single `<config>.trigger`
starts installation of both probes, followed by a shared interval only after both
installations succeed. It writes `<config>.main.trace.jsonl` and
`<config>.finalizer.trace.jsonl`, each with identical `joint_start_tick` and
`joint_end_tick` markers. It restores both configured adapters, including partial
installation cases, before closing/draining and writing output. No simultaneous
atomic installation or hard wall-clock deadline is claimed.

For engine/job-only experiments, `scripts/startup_entry.py --readiness scheduler`
requires consecutive gameplay HUD and advancing, nonfaulted host samples but
performs no player acquisition. It returns the distinct `scheduler_ready` outcome
and does not claim player readiness or a spawn position. The default remains
`--readiness player`; `--expect-spawn` requires that mode. The experiment controller
must still qualify engine owner/job bindings before installing any probe.

## Inspect command admission and callback records without the game

```sh
python3 scripts/run_command_pipeline_probe.py
```

Run from the repository root with a native 64-bit C11 compiler available. This
builds and runs the admission, attachment and observer C components against synthetic queue,
lock and lifetime services. See the [combined probe contract](../../docs/reconstruction/REQUEST_COMMAND_LIFECYCLE.md#combined-native-code-inspection-probe)
for refusals, disposal, repeated delivery and recorder-close boundaries. This
console probe neither launches the game nor installs a native callback. Output
separates ownership finalization from observed delivery; the known synthetic
invocation count also exposes recorder overflow and forwarding after close.


### Read-only command-manager startup observation

Build with `--adapter steep --command-manager-startup-plugin` to include
`plugins/command_manager_startup.dll`. It is disabled by default. Enable it with
`plugins/command_manager_startup.ini`:

```ini
[observation]
enabled=1
```

During `SnowMod_Initialize`, the plugin checks the inspected singleton getter's
code fingerprint and performs one bounded sequence of `ReadProcessMemory` calls.
It reads the singleton, selected queue fields when the pointer is plausible, and
the singleton again. No original engine routine is invoked and no hook, background
worker or gameplay write is installed. The output is
`command_manager_startup.ini.observation.json` beside the INI, overwritten for
this initialization. It contains private addresses, process creation identity and
QPC timestamps; keep the raw file private.

`owner_read=1` with `manager="0"` means the global was readable and null at that
sample. `fields_read=0` then means no manager fields were read, not a zero-capacity
manager. `same_pointer=1` only compares two reads; it does not prove ownership or
an atomic snapshot. A matching getter fingerprint is a local compatibility check,
not verification of the complete executable. Publication may predate or follow
plugin initialization; this one-shot observer does not capture the writer.


### Experimental startup page-write controller

`--adapter steep --command-manager-write-plugin` builds an opt-in controller for
`snow_first_write`. It requires `plugins/command_manager_write.ini`:

```ini
[publication]
enabled=1
timeout_ms=60000
```

It checks the singleton-getter fingerprint, requires a sampled null singleton,
and accepts a READWRITE or WRITECOPY image page belonging to the main executable. The
observer pins code/image modules and stays registered until process exit. The
worker waits at most the configured 100..90000 ms, then attempts cancellation for
up to two additional seconds. An external process watchdog is still required.
No game command is submitted. This changes data-page protection only if armed;
it is not the read-only startup observer.

Output `command_manager_write.ini.write.json` contains private addresses,
registers and a bounded instruction-byte snapshot. Keep it outside public
research. Instruction bytes are read after the handler restores protection, so
they are not an atomic code/context snapshot. No captured context proves the
faulting instruction subsequently completed or targeted the singleton rather
than another global on the page.

The first live attempt declined to arm. Its post-refusal page query reported
`PAGE_WRITECOPY`, unsupported by the initial READWRITE-only observer revision. Do not
interpret this as a successful publication capture or override it with a generic
READWRITE restore. See the
[refusal receipt](command_manager_write_live_refusal.json). The subsequent copy-on-write extension preserves the original protection and
adds an image-backed fixture; see the copy-on-write section in the command
lifecycle guide. The separate initial-protection field remains zero
on this refused branch; it is not an observed protection value.


The startup write controller now includes three pre-retry context-relative memory
windows in its private JSON output: RBP-16 for 64 bytes, RBX-16 for 32 bytes and
RSP for 128 bytes. Each has an explicit validity flag. Bytes are collected in the
fault handler before protection restoration; instruction-byte output remains a
separate later read. Do not treat stack words as a call stack, or invalid windows
as zero-valued game data. The generic observer permits at most three 128-byte
windows and refuses reconfiguration after arming.

### First-execution diagnostic fixture

`snow_first_execute.c` is an authored one-shot RX-page observer. Its contract and
limitations are in `snow_first_execute.h` and the constructor-observer section of
[command lifecycle research](../../docs/reconstruction/REQUEST_COMMAND_LIFECYCLE.md).
It is not enabled in the host or wired to a game page by default.

Build the standalone Windows fixture outside this repository:

```sh
x86_64-w64-mingw32-gcc -std=c11 -O2 -Wall -Wextra -Werror \
  -I native/snow_host native/snow_host/snow_first_execute.c \
  tests/fixtures/snow_first_execute_fixture.c -o /tmp/first-execute.exe
x86_64-w64-mingw32-gcc -std=c11 -O2 -Wall -Wextra -Werror \
  -fno-toplevel-reorder -shared tests/fixtures/snow_first_execute_image.c \
  -o /tmp/first-execute-image.dll
```

Run `first-execute.exe CASE` in Windows or your configured Wine environment.
Cases are `cold`, `warm`, `neighbor`, `cancel`, `rw`, `rwx`, `self`, `concurrent`.
An optional second argument is the Windows path to `first-execute-image.dll`;
this exercises image-backed code instead of a private executable page. Each case
needs a fresh process because the observer deliberately permits only one arm.
No game files are required. The fixture retains its watched allocation until exit.

### Constructor-page startup experiment

`--adapter steep --command-manager-execute-plugin` builds the opt-in controller.
It requires `plugins/command_manager_execute.ini`:

```ini
[execution]
enabled=1
timeout_ms=60000
```

The controller checks the local getter and constructor fingerprints, a null
manager singleton, and an RX main-image page before arming. The wait is bounded
between 100 and 90000 ms. Output is `.ini.execute.json`, including restoration,
page protection, eligibility/pin results and observer arm-stage errors, whether
the exact constructor entry won, registers and a bounded
stack snapshot. Keep this raw output private. The worker's later singleton read
is a separate observation, not an atomic join with the entry context. Another
function on the same page can consume the one-shot capture. Host startup placement
does not guarantee that no earlier constructor invocation occurred.

The handler/module and main image stay pinned for process lifetime. Use an
external process watchdog and verify restoration/cleanup. This experimental
controller is not a general plugin unload or command-manager lifetime API.

### Execution observer control inside the host

`--execution-control-plugin` builds an optional control plugin for either adapter.
Enable it with `plugins/execution_control.ini`:

```ini
[control]
enabled=1
```

It allocates a dedicated private page, writes an authored function returning 42,
makes it RX, arms the one-shot observer and calls the function. The handler must
restore RX before the function returns. Output `.ini.control.json` records the
steps, exact-entry match, result, code-byte comparison, queried protections and
protection-API module identity. It contains no game-state capture, but raw API
addresses should stay private. The page and pinned observer remain until exit.
No game page is modified and no game routine is called. Use the usual external
watchdog; this is an instrumentation control, not a modding feature.

The standalone fixture `tests/fixtures/snow_execution_control_fixture.c` loads
the plugin DLL and accepts DLL path, INI path, and expected initialization result.
Disabled configuration must decline with no output. Enabled configuration must
produce a captured exact entry, return 42, preserve bytes and restore RX.

The same control can inspect a separate **authored fixture DLL**:

```ini
[control]
enabled=1
source=image
image_path=C:\research\fixtures\execution_control_image.dll
```

The build flag also produces `fixtures/execution_control_image.dll`. Keep that
fixture outside the host's plugin-discovery directory. Only point `image_path`
at this authored fixture: loading a DLL executes its loader initialization even
if later validation refuses its exported function. The controller checks the
`snow_execute_target` export, page alignment, RX image mapping, allocation owner
and exact authored function bytes, then pins the fixture before observing it.
It does not rewrite image code. A missing/invalid fixture records refusal with
`page_available=0`, `armed=0`, `executed=0`. `allocated` refers only to the private
control; use `page_available` for either source. Unsupported source names decline
initialization. Each source needs a fresh process because the observer is one-shot.

### Read-only protection API snapshots

`--protection-api-snapshot-plugin` builds an optional inspection plugin. Enable
`[snapshot] enabled=1` in `plugins/protection_api_snapshot.ini`. It writes
`.ini.api.json` with six exported entry points: VirtualProtect/VirtualProtectEx
from kernel32 and kernelbase, and NtProtectVirtualMemory/ZwProtectVirtualMemory
from ntdll. It reads at most four 128-byte nodes per export and bounded indirect
pointer slots. It never calls the inspected entry points or changes protection.

The recognizer follows only entry E9, EB, FF25, 48FF25 and mov-rax/jmp-rax forms,
optionally following the exact eight-byte lea-rsp-self prefix observed in Wine.
Cycles, unreadable ranges and the node limit stop traversal. This is not a general
control-flow decoder: ordinary prologues, calls and conditional branches stop it.
Reads are sequential, not atomic against other threads. Missing exports remain
explicit. Raw code bytes and absolute addresses must stay outside this repository.
`tests/fixtures/snow_api_route_fixture.c` exercises the recognized forms and bounds
using authored bytes that are never executed.

### Protection dispatcher context snapshot

`--adapter steep --protection-context-snapshot-plugin` builds an opt-in, read-only
startup sampler. Enable `[context] enabled=1` in
`plugins/protection_context_snapshot.ini`. It checks the local wrapper fingerprint,
then reads the protection context pointer and three 256-byte windows: that context,
a selected dispatcher stream window, and a selected image window read by the
synthetic dispatcher probe. It rereads the context pointer afterward.

The `.ini.context.json` output is private: it contains addresses and raw payload
bytes. Equal pointer reads do not pin the allocation, exclude address reuse or
make the three reads atomic. A valid fingerprint does not establish that the
context layout or all dispatcher state is known. No target routine is called and
no memory/protection is changed. Incompatible images emit no payload windows.

Optional `[context] follow_candidate=1` adds one bounded window through the qword
at context offset `0x78`. This is a research lead, not a stable context layout or
callable API. The 256-byte context storage window does not establish object size
and may include neighboring heap storage. No candidate function is invoked.

### Continuation identity and authored-page control

`--adapter steep --protection-continuation-control-plugin` builds a bounded
experimental control. Enable `plugins/protection_continuation_control.ini`:

```ini
[continuation]
enabled=1
exercise=0
```

With `exercise=0`, it only checks the current ntdll export, context candidate,
code fingerprints and observed forwarding arrangement, then rereads the sampled
pointers and bytes. The fingerprints qualify the locally inspected Wine build;
this is not a portable Windows syscall implementation. `snow_continuation_identity`
is the pure matcher and never reads memory or calls a function.

`exercise=1` additionally permits a test on a page allocated by this control,
only if the identity checks pass. It makes that page RX through VirtualProtect,
then calls the qualified candidate to change it to read-only and back to RX.
An unaligned request checks returned address/size normalization. The control
checks returned old protection, actual page protection and unchanged marker bytes,
then releases its allocation. A public VirtualProtect fallback is available if
restoration did not yield RX. No game page is selected or changed, no hook is
installed/removed, and no target-address configuration exists.

Output `.ini.join.json` records gates and operation results. Keep raw pointers
private. Rereads are not a lifetime pin for the candidate's private allocation;
this remains a bounded startup experiment with the external watchdog, not a
persistent callable mod API. Disabled or incompatible configurations never call
the candidate or allocate a control page.

### Supplied execution-observer protection backend

`snow_first_execute_backend(callback, context)` optionally configures a backend
before arming. The default remains VirtualProtect. The callback follows its
success/old-protection/error convention and must be usable from a vectored
exception handler. Its module is pinned; the caller retains its context and
indirect dependencies. A watched page cannot belong to the callback's module or
contain the supplied context pointer. No callback/context extent is inferred.

The observer checks actual protection after successful backend calls. It allows
the arming race where execution has already faulted and restored RX before the
arming backend returns. A failed restoration does not publish a successful
capture or cancellation. There is no automatic fallback inside the observer.
The failure fixtures use a separate authored recovery handler to verify failure
reporting without crashing the test process; that is not a production recovery API.

For the continuation control, `[continuation] observer=1` together with
`exercise=1` selects an authored return-42 function and the observer round trip
instead of the direct permission-change test. It uses the freshly qualified
candidate as backend, records capture/restoration and preserves code bytes. The
watched allocation stays until process exit rather than being freed. There is
still no option to select a game page. The backend's private continuation lifetime
is not generally pinned or recovered; this is a bounded experiment, not a durable
mod API. Raw output distinguishes the observer mode from direct-call fields.

For the constructor-page experiment, `[execution] backend=continuation` explicitly
selects the locally qualified continuation through `snow_local_protection`.
The default remains `backend=virtualprotect`. Unknown values decline loading.
Continuation mode freshly checks the wrapper, current export, context candidate,
forwarding arrangement and repeated bytes before configuring the observer. A
failed identity check refuses arming; it never silently falls back to another
backend. Output includes selection, qualification and backend call/status fields.

This remains a bounded constructor-page experiment, not a general protection API.
The callback's module and context stay resident, but the private continuation's
allocation lifetime is not established generally. Use the external watchdog and
verify actual restoration. No continuation pointer is reused across sessions.

Constructor initialization also appends `.execute.json.stages.jsonl` milestones
after eligibility, backend configuration and return from arming. Each record is
closed immediately, outside the exception handler. These milestones can survive
an early game exit that prevents the worker's final report. They do not establish
capture or restoration; only the final report can report those observations.

Set `[execution] trace=1` to create `.execute.json.trace.bin` before arming.
Version 2 has a 24-byte little-endian header containing six signed 32-bit fields:
version, handler-entry count, matching-fault count, phase, restoration error and
event capacity. Capacity is 8. Phase 0 means no winning fault was recorded; 1
means a winning fault; 2 means stack sampling returned; 3 means restoration is
about to be attempted; 4 means capture was published; 5 means restoration failed.
Phase 0 does not prove the game executed no faults: another handler could consume
them first. The decoder also accepts the older 20-byte version-1 counter record.

Eight 64-byte event slots follow the header, making the file 536 bytes. Each slot
contains eight 64-bit fields: published, exception code, flags, parameter count,
classification reason, parameter 0, parameter 1 and instruction address. The
parameters mean access kind and fault address only for an access violation; other
exception codes define their own meanings. Slots are reserved with an interlocked
counter and published once after writing. Further events increment the counter
but do not overwrite the first eight slots. Unpublished slots must be ignored.

The handler does not open/write/flush files or allocate memory for this trace.
Counters and slot publication are atomic, but the full record is not a consistent
multi-field snapshot. The view stays mapped until process exit. Trace setup
failure declines the experiment when explicitly requested. Tracing does not
change game registers, matching predicates or exception handling decisions.

Decode with `python3 scripts/decode_execute_trace.py TRACE_FILE`. Inspect after
process exit for a stable final file. Version 2 contains process-local addresses
and raw exception parameters: keep the file and decoded output private. Public
receipts should summarize classifications without publishing raw address data.

The execution matcher also accepts an instruction starting in the preceding
14 bytes when the reported execute-fault address lies inside the watched page.
This handles a maximum-15-byte x86-64 instruction spanning the page boundary.
It does not accept a fault address outside the watched page, relax the execute
access requirement, or claim the captured instruction is the requested target.
The cross-page fixture compares the old rejection with the corrected capture
and verifies restoration without fixture recovery after the correction.

`[execution] wait_input_table=1` is an opt-in selection experiment. Before arming,
it verifies the analyzed input-table publication instruction, then samples the
input-table and command-manager globals until the table is nonzero, the manager
is already published, a read fails, or the configured timeout expires. It then
rechecks ordinary constructor eligibility, including a still-null manager.
The default remains immediate arming. Invalid values decline initialization.

This blocks this plugin's initialization for at most the configured wait budget;
the capture has its own budget afterward. Use an external watchdog covering both.
The 1-ms polling interval is not a scheduler boundary or an atomic event callback.
Construction may race between checks and arming. Final output and milestones
report wait gates, samples, late/read-failure refusal and the sampled table pointer.
A successful wait is not proof of exact-constructor capture or object lifetime.

### One resident engine-delegate observation request

The opt-in `delegate_capture` plugin accepts `request_id=91` under `[capture]`
with `site=engine`. Zero, the default, leaves request observation disabled.
The controller must still establish the bounded owner-lifetime experiment and
create the trigger only after readiness. The plugin arms the request before
installing the wrapper. This is an authored one-slot observation inside the
intercepted engine callback, not native command-queue submission.

The next intercepted invocation atomically claims the request. It reads the
command-manager global through `ReadProcessMemory`, forwards the original
invoker unchanged, samples that global again, and publishes a returned receipt.
Concurrent or cached later calls do not reexecute the request. There is no engine
lock acquisition or gameplay mutation. A nonreturning original leaves the receipt
unavailable. A failed pointer read has a separate validity bit, not a valid zero.
The `.trace.jsonl.request.json` sidecar contains private process pointers, request
ID, callback bounds and thread; keep it out of the public repository.

`SnowDelegateProbe_ArmObservation` requires configured engine-main, an open
recorder and no install attempt. It refuses zero IDs, graphics site, rearming,
and calls after installation. `ReadObservation` succeeds only after forwarding
returns. This does not pin the manager, establish an atomic snapshot, prove a
native queue delivery phase or authorize arbitrary commands. The plugin, recorder
and original image remain resident; existing installation lifetime prerequisites
still apply.

### Repeated resident observation requests

Set `request_count=16` alongside a nonzero `request_id` and `site=engine` to run
up to 16 sequential observation requests inside the existing 100–2000 ms capture
window. The default remains one request. The controller collects each receipt
before submitting the next ID. Output `.trace.jsonl.requests.json` reports the
requested/submitted/collected counts, admission results, receipt outcomes and
private callback observations. An incomplete count is not silently promoted to
success. This remains an opt-in bounded experiment, not a general gameplay API.

The new adapter methods expose one reusable slot:

- `SubmitObservation(id)` requires an installed engine-main binding, strictly
  increasing nonzero ID, and an empty slot. It reports accepted, busy, closed,
  invalid or stale binding. Failed submissions do not consume IDs. Invalid
  configuration/ID checks precede closed/busy/binding checks.
- `CollectObservation(out)` consumes a returned or cancelled receipt; pending
  and running requests return not-ready. A null output does not consume anything.
  Non-consuming `ReadObservation` still reports returned receipts only.
- `CloseObservations()` permanently closes admission. Its CAS cancels an unclaimed
  request; if a callback already claimed it, that callback finishes normally.
  `Restore` also closes admission, even if restoring the slot later conflicts.
  `Close` waits for both trace drain and any running request before reporting drain.

Control calls serialize with the existing SRW lock. The callback claims the slot
atomically and never takes that control lock. It publishes a returned receipt only
after the original invoker and final read have returned, and does not access that
receipt afterward. Pending, running and uncollected receipts all apply
backpressure. Collection can permit another callback to claim a new request before
an older wrapper finishes its final machine return; there is no whole-job idle
claim. Neither request closure nor collection releases module/owner storage.

### Observation invalidation after admission

A claimed request now verifies owner/descriptor identity and actual callback
storage/receiver both before and after forwarding. It allows the restored original
invoker for an in-flight or cached call. A mismatch suppresses the manager-global
read at that boundary and permanently closes future observation admission.
Collection reports `STALE_BEFORE` (3) or `STALE_AFTER` (4), with before taking
precedence when both fail. These describe a failed observation qualification;
the original callback still executes. Single-request output now includes numeric
`outcome` as well as the legacy `returned` boolean. Repeated capture stops submitting
when a receipt is not RETURNED. Receipt layout and trace ABI are unchanged.

Restoring the pointer or descriptor afterward does not reopen admission. This is
an authored invalidation policy, not a recovered native generation mechanism.
The checks cannot detect change-and-restore between observations, prove that an
address still represents the same allocation, or protect original forwarding
through freed storage. Keep the existing bounded owner-lifetime prerequisites.

### Physics samples associated with engine-phase requests

The opt-in capture plugin accepts `physics=1` with engine site and nonzero request
ID. A controller must freshly acquire a snow actor in the same verified process,
write its hexadecimal `actor` value into the private session INI, then create the
capture trigger. Never reuse that heap address in another session. Configuration
fails closed if the profile or actor/world/counter links do not validate. There is
no actor discovery in the plugin and no independent selected-player identity proof.

`SnowDelegateProbe_ConfigurePhysics(actor, profile)` configures this channel once,
before arming/installing. The build profile identifies actor/runtime tables,
actor update target and world-job invoker. The fixed actor/world/counter binding
is checked afresh at every sample; runtime/body links are reread. Samples reuse
`snow_update_resolve_binding` and `snow_update_snapshot`, with a second resolver
pass afterward. World/profile changes invalidate a sample; body replacements
within the same binding can be observed. No setters or native game routines run
in this reader.

`CollectPhysics(receipt, physics)` collects the request and its associated before/
after snapshots under the same control lock. Both outputs are required. The
legacy collector may ignore this optional channel. A RETURNED request may still
have an invalid physics sample; valid bits must be checked separately. Physics
request counters are not engine request IDs. Unavailable substep attribution must
not be presented as substep zero.

`.trace.jsonl.physics.json` contains the optional private samples keyed by request
ID. Float fields are serialized as uint32 bit patterns, preserving nonfinite/raw
values without invalid JSON. It includes velocity, angular velocity, inverse mass,
pending impulse, gates, preconsume counter and physics-job counter. This is not a
pose/position reader and not an atomic snapshot. Link checks neither retain the
actor nor detect address reuse. Build/link `snow_update_snapshot.c` with delegate
probe users; the public build script now includes it.
