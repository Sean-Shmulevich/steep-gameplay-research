# Startup entry into gameplay

Goal: launch through the existing startup launcher and reach gameplay with minimal
interaction, without skipping engine or world initialization. This covers menu
interaction only. It skips no asset or world loading and selects no map or spawn.

## Command

Recommended (fastest, repeatable spawn enforced):

```sh
python3 scripts/run_late_load.py --experiment host --load-at startup --navigator native-intro \
    --intro-key escape --expect-spawn=-2312.95581,-4273.34521,2385.9326 --plan demo
```

Without the intro skip:

```sh
python3 scripts/run_late_load.py --experiment host --load-at startup --navigator native --plan demo
# prerequisites only, no launch:
python3 scripts/run_late_load.py --experiment host --load-at startup --navigator native --plan demo --check
```

`--navigator native` runs [`scripts/startup_entry.py`](../../scripts/startup_entry.py).
The default `--navigator ocr` keeps the existing private navigator unchanged. The
runner's five-minute watchdog, workspace lock, settings restore, bottle stop and
original-DLL hash check apply to both.

## Startup sequence (live, three sessions)

| Screen | Leaves by | Input |
| --- | --- | --- |
| black, logo videos, epilepsy/safety/autosave notices | timer, about 45 s | none |
| title, "press any key" | input | Enter |
| loading 1/3 to 3/3 | loading completes | none |
| offline notice | input | Enter |
| startup map (region overview, drop zones) | input | map key (closes the map) |
| gameplay HUD | | |

The startup map is closed rather than confirmed. Closing it leaves the rider at
the profile's spawn, which is repeatable (see below). Choosing a drop zone there
could give a different, chosen spawn; this is untested.

## Static findings (no launch)

- There are no command-line option strings for skipping intros or choosing a
  map/world, and the settings file has only language, display, quality and music
  keys. No supported launch option or saved preference was found.
- The disclaimer video is queued only when two global switches are clear. The
  same switches gate many unrelated systems, and nothing found sets them from an
  option. They are not a startup option and were not changed.
- The title-flow state machine and its loading-stage handlers were located. No
  exposed continue, map-confirm or start-gameplay command was found. Invoking
  internal flow transitions would need new adapter work and identity guards. This
  was not attempted.

## Approach

`startup_entry.py` sends only the existing transitions above. It does so as soon as
the screen is recognized, retries after 5 s, and makes at most 4 inputs per
screen. It never sends input on unrecognized screens or during gameplay. Gameplay
is accepted only when the recognized HUD and the startup-loaded host agree on two
consecutive samples: commands ready, world step advancing and player acquired
with valid flags. Host samples are read-only (status, player get, in-process
acquisition), each over its own short connection.

## Live result, 2026-10-22 ([receipt](startup_entry_live_attempt.json))

Host startup load passed with no visible window. The command service answered at
26 s, the host was ready at 37 s and the world step advanced from 42 s, all
during the intro videos. The navigator sent its three inputs at 83, 101 and
114 s, and the HUD was recognized at 124 s. The player was acquired at 96 s,
during loading and before the offline notice and map. So closing the map is a
menu transition, not the point where the world loads.

The run failed its own gate. The first gate required the IN_WORLD flag, but an
idle freshly spawned rider reported valid flags without IN_WORLD for 77 s. This
matches the earlier acceptance run, where a forward pulse was needed before the
body was simulated. The gate now requires valid flags and records IN_WORLD
separately. Replaying the recorded samples offline, the corrected gate accepts at
126 s; this is not yet live proof. The host plan did not run. Cleanup passed:
settings restored, bottle stopped, original DLL verified.

## Live pass, 2026-10-22 ([receipt](startup_entry_live_pass.json))

The second run, with the corrected gate, passed end to end. The navigator sent
three inputs (69, 85 and 98 s). The player was acquired at 80 s, during
loading, and the HUD appeared at 107 s. Native agreement accepted gameplay at
110 s; IN_WORLD stayed clear while the rider was idle. The demo plan then
released 10 single world steps, each exactly one step (worst release 17.8 ms),
and resumed to ordinary mode without the fallback restore. The game stayed
stable for 20 seconds. Cleanup passed: settings restored, bottle stopped and
original DLL verified.

The host counted 44 failed commands. These are the navigator's read-only
`player.get`/`player.bind` attempts made before the player existed; they are
expected refusals, not faults.

## Intro-skip experiment, 2026-10-22 ([receipt](startup_intro_skip_attempt.json))

`--navigator native-intro` pressed Enter six times on the visible pre-title
screens. Nothing was skipped: each video and notice still showed in order. It
took 45.9 s from the first visible screen to the title, compared with 46.5 and
44.6 s without the presses, and the engine step count at the title matched (about
4,400 to 4,500). The title then advanced normally and the whole run passed (demo,
stability and cleanup). Pressing Enter does not shorten the intros; Escape does
(below). Deferring player reads cut the host's refused commands
from 44 to 4.

## Repeatable spawn, 2026-10-22 ([receipt](startup_spawn_check.json))

The idle player's position at gameplay entry was bit-identical in nine earlier
sessions: (-2312.956, -4273.345, 2385.933) in Aravis. Several of those sessions
moved the rider and changed its speed after entry, and two save files are
rewritten every session, yet the next startup still spawned there. The navigator
now records `spawn_position`. `--expect-spawn=X,Y,Z` (tolerance 0.01) fails the
run on any other spawn. A run with that check passed: exact match, demo,
stability and cleanup. Use the `=` form, because a coordinate starting with `-`
would otherwise be read as an option; an earlier run failed that way and cleaned
up normally.

This makes the spawn repeatable for this profile, not selectable. Sessions that
travel elsewhere (helicopter, drop zone) before an autosave are untested and
could move it. Other maps or spawns are not supported.

## Escape skips the intros, 2026-10-23 ([receipt](startup_escape_intro_skip.json))

In two runs with `--intro-key escape`, four Escape presses on the visible
pre-title screens skipped the logo videos, the notices and the title, so no title
was ever seen. Loading began by 55 to 60 s, and gameplay was confirmed at 85 and
89 s, compared with 110 to 121 s without skipping. Both runs matched the expected
spawn and passed demo, stability and cleanup. The skip uses the game's own key
handling; no initialization was bypassed. The only inputs left are Enter on the
offline notice and the map key. In the first run one press landed on the loading
screen, which was harmless. Intro presses now stop as soon as loading text
appears, and the second run confirmed that.

## Startup failure is bounded, 2026-10-23 ([receipt](startup_host_failure_injection.json))

To force a host failure, a local listener held the command port before launch.
The host loaded but could not listen (address in use), and the startup probe gave
up after its 75 s limit. The runner then failed the session and cleaned up:
settings restored, bottle stopped and original DLL verified. Two earlier
navigation failures also shut down cleanly.

## Native director, 2026-10-23 ([receipt](startup_native_director.json))

A private in-process plugin (build-specific, not published) now handles the intro
videos, the title, the offline notice and the startup map through the game's own calls, using per-class vtable slot swaps that are restored on
unload:

- Intro videos: 1 s after the intro state starts, it moves the splash player's
  playlist index to the end and sends one "entry ended" event. The player runs its own
  finish path, which releases the intro. The video does not linger.
- Title: 1 s after the title flow event it calls the game's frontend command entry
  with the press-start command. That posts the same chart event the title posts
  itself when a user is already assigned. The title is never seen.
- Startup map: 1.5 s after the in-game flow event it posts the back-to-player flow
  event, the same event the map's Back key posts. The map never appears.
- Offline notice: from the notice's own UI-thread update it queues the UI manager's
  close-top-page command. Replaying the accept action, or a raw Enter traced from a
  real key press, did nothing outside real input dispatch.

The navigator runs with `--hands-off offline_notice,map` and only sends Escape during
the intros. Two live passes entered gameplay at 57.5 s and 61.1 s (previously
78.3 s). Both were natively verified at the usual spawn, and the step counter kept
advancing after entry. A navigator bug was fixed along the way: hands-off runs never
read the player, because reads waited for a menu input. They now also start after a
loading or post-title screen.

With the title handled as well (`--hands-off title,offline_notice,map`, no intro key),
a third pass sent no input at all. The intros played in full, and gameplay was
natively verified at 78.4 s at the same spawn. A 0.5 s forward key after entry moved
the rider (in-world flag set, about 22 m/s), so control works without a real
press-start. With the intro skip added, the next pass also sent no input and reached
natively verified gameplay at 48.6 s, faster than the Escape runs (57–61 s).

## Open

- Reliability: five full passes (two with Escape), one gate failure and one
  argument failure so far.
- Choosing a different map or spawn (drop zone or helicopter on the startup map),
  and whether long-distance travel changes the startup spawn. Untested.
- Reliability of the fully native path: one pass so far (x28, gameplay at 48.6 s
  with no input; the rider responds to input afterwards).
