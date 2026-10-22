# Startup entry into gameplay

Goal: launch through the existing startup launcher and reach gameplay with minimal
interaction, without skipping engine or world initialization. This covers menu
interaction only. It skips no asset or world loading and selects no map or spawn.

## Command

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

The startup map is closed rather than confirmed. Closing it leaves the rider
where the profile spawns. Choosing a drop zone there could later give a
repeatable spawn, but this is untested.

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
stability and cleanup). Pressing Enter does not shorten the intros; Escape and
other keys are untested. Deferring player reads cut the host's refused commands
from 44 to 4.

## Open

- Reliability: two full passes and one earlier gate failure so far.
- Intro videos (about 45 s): Enter does not skip them. Escape is untested; the
  native-intro mode stays only as a recorded experiment.
- A repeatable spawn through drop-zone selection. Untested.
- Native flow transitions (title, offline notice, map) without input. Not
  attempted.
