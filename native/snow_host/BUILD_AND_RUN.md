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
