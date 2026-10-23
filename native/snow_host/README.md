# Snow mod host (v0.7, startup launcher, command interface and plugin API v1)

[Standalone build and launch instructions](BUILD_AND_RUN.md). The authored game adapter is now public in `steep_adapter.c`; older private-workspace references below describe the original experiments.

Status: first release of the host interface. A persistent DLL is loaded late into
the running game. It exposes guarded pause, world-step and resume operations
through a local command channel, and loads native plugins that run between world
steps ([plugin API v1](#plugins-api-v1)). One live session passed on 2026-10-14 (see below
and the [sanitized validation record](validation.json)). Host 0.3 added the first game
state for plugins and clients, the [selected player's body](#player-state-host-03). Host 0.4
finds the player in-process and adds velocity assignment, host 0.5 adds placement, and host 0.6
adds player events, a liveness check against the engine's registries and a "being simulated" flag.
Host 0.7 adds automatic loading during process startup and deferred engine readiness.

## Startup loading (host 0.7)

From the configured local game/research workspace:

```sh
python3 steep-gameplay-research/scripts/run_late_load.py --experiment host --load-at startup --steps 5
```

The experiment builds a native `startup_launcher.exe`, which creates the original
game process normally and loads/starts the host as soon as the Windows loader is
available. The original XInput DLL is preserved. The launcher waits for its game
child to exit. This is automatic launch-time loading through our launcher; it is
not a hook before the executable entrypoint or an installation into Steam.

The command service can answer status while the game is still initializing.
`ready: false` means controls and plugins are not enabled. The executor retries
the existing read-only adapter identity checks and waits for a readable engine
owner; only then does it initialize plugins once and report `ready: true` and
`plugins_initialized: true`. Signature mismatches are never bypassed. `DllMain`
still only records the module handle. The existing gameplay-loading path remains
available with `--load-at gameplay` (the default).

**Live result, 2026-10-15.** The launcher created the original process and began
loading after 93 ms. The host had started after 7,754 ms; both window enumerations
reported zero visible child-process windows. The first command response was
unbound/not ready with no active plugins. After the unpacked routine signatures
matched, the host waited for the engine owner, then initialized `step_logger`.
The same host remained resident through startup navigation and gameplay. Five
single-step releases passed, resume required no external fallback, and a 20 s
check showed advancing simulation. Settings were restored, the bottle stopped,
and the original DLL hash matched. See [startup validation](startup_validation.json).

The first attempt used the normal late-loader's 5 s thread wait and timed out
before host initialization. The startup launcher now permits a bounded 30 s wait
per remote call; the ordinary late-loader retains its 5 s wait. No timed-out
thread is terminated, and its path allocation is retained while it may be in use.
The test's watchdog closes the owned process if startup cannot complete.

A separate delayed-readiness fixture verified that early pause was refused,
status remained available, plugin initialization waited for the synthetic engine,
and three controlled steps passed afterward. This and one successful live startup
session do not establish compatibility with every game build or launch route.

```text
Python client ──TCP 127.0.0.1──▶ io thread ──mailbox──▶ executor thread ──▶ game adapter ──▶ game
                                  (parse only)           (serial, lease timer)  (private, build-specific)
```

## Brake and boost reference mod

The command client now provides a one-shot brake/boost experiment using
`player.adjust_speed`. The host calls the existing engine velocity-assignment
routine. It does not overwrite body velocity fields or install a physics-tick
hook. This is a command-client reference mod, not yet a hotkey plugin.

With the newly built host loaded and gameplay active, run from the repository:

```sh
python3 scripts/snow_host_client.py boost --amount 5
python3 scripts/snow_host_client.py brake --amount 5
```

Each invocation holds physics briefly, asks the host to calculate and apply the
change, records the result as JSON, and attempts to resume even on failure.
It refuses an existing host-held pause. Disconnect/lease recovery remains the
fallback if the connection breaks. Never automatically retry a lost mutation
response: the engine call may already have happened.

Contract for `player.adjust_speed`:

- Required parameter `delta_speed`: finite, nonzero, between -10 and 10 world
  units/s. No velocity, position, handle, count or lease parameters are accepted.
- Requires a host-held simulation and a currently bound, simulated player body.
  It reads and computes on the serialized executor; clients send no heap address
  or velocity calculated from a running snapshot.
- For speed `s = length(v)`, target speed is `max(0, s + delta_speed)` and the
  requested velocity is `v * target / s`. Boost is capped at 60 world units/s;
  a player already at or above that cap is refused. Braking above the cap still
  subtracts only the requested amount. Braking never reverses direction.
- Refuses speed below 0.5 because direction is unresolved. Refuses angular speed
  above 0.25 in the adapter's units. These are authored mod policies, not recovered
  game thresholds or a proven grounded/trick detector.
- This scales the full 3D velocity, including vertical speed. The existing engine
  setter updates both coupled bodies by default, resets speed history and clears
  angular velocity. Even below the rotation refusal threshold it can affect a
  trick. There is no claim of a snow-only force, preserved spin or continuous boost.
- Response includes player identity, prior velocity/speed, target speed and a
  held readback. Readback is not proof that the target persists after contacts and
  constraints run. The host's existing player-liveness and setter guards still apply.

The next implementation target is an engine-ordered callback and an impulse/force
path that preserves rotation and respects contact. A conventional plugin can then
consume input and apply acceleration once per physics tick without repeated pauses.

Synthetic verification is available with
`python3 scripts/speed_mod_fixture_probe.py --port PORT` against a separately
started fixture host. It refuses the game adapter and requires the new fixture
handles. Client recovery tests are in `tests/test_speed_pulse.py`. On 2026-10-15, the focused Wine
fixture passed 21 checks, the existing native regression suite passed 56 checks,
and the Python suite passed 696 tests. Both fixture and private game-adapter DLLs
compiled with warnings treated as errors.

A subsequent [live speed test](speed_validation.json) passed both pulses in one
startup-loaded session. Brake changed speed from 3.95798 to 1.95798 world units/s;
boost changed it from 39.37785 to 41.37785. Five controlled world-step jobs followed
each pulse, with stable player identity. The game resumed and advanced for 20 s;
the runner then stopped the bottle and restored temporary settings. Angular
velocity was zero immediately after both assignments. Speed evolved afterward,
so the target is an assignment rather than a sustained speed lock. Terrain and
contact were uncontrolled; this does not establish grounded-only behavior or
comparative acceleration without a mod.

Repeat in the configured research workspace with:

```sh
python3 steep-gameplay-research/scripts/run_late_load.py --experiment host --plan speed --load-at startup
```

The bounded test navigates startup, waits for a moving low-rotation rider, applies
-2 and +2 pulses, records held readbacks after one and five world-step jobs, checks
20 s of advancing simulation, and cleans up. It may briefly hold forward input
between eligibility checks. It never retries an uncertain mutation response.

For a deliberately exaggerated visual demo, use `--plan fast` instead of
`--plan speed`. It waits for a moving low-rotation rider, holds for a 10-second
countdown, assigns 90 world units/s through `player.set_velocity`, and resumes
for 30 seconds of observation followed by the usual stability check and cleanup.
It preserves the full 3D movement direction, so a descending rider accelerates
downward too. This explicit experiment does not raise the normal boost command's
60-unit/s cap. It is a single assignment; terrain, drag and collisions still act.

[Live visual-demo evidence](fast_validation.json): speed changed from 4.10355 to
90.0 world units/s, then sampled 48.88, 41.01 and 37.60 during the first three
seconds. Thirty running samples and the subsequent 20-second stability check
completed. The initial attempt refused because no player was available; the
runner now waits up to 20 seconds for player acquisition before starting.

## Design

| Piece | Behavior |
|---|---|
| `snow_host.c` | Host core. `DllMain` only records its handle. `SnowHost_Start`, run on its own thread after `LoadLibraryW` returns, starts the io and executor threads once. The executor waits for adapter/engine readiness before initializing plugins. |
| io thread | Accepts one loopback client at a time and parses requests. It never touches game memory. |
| executor thread | The only caller of the adapter. Commands run serially. It also owns the recovery lease. |
| `snow_adapter.h` | Boundary between the host and the game: identity check, counter read, mode-group compare-and-swap, and the engine's own enter and clear routines. The host core contains no game addresses. |
| `fixture_adapter.c` | SYNTHETIC simulated request loop for testing. It models only stop-mode routing, not the engine. |
| `steep_adapter.c` | Published build-specific game adapter. It refuses to bind unless the process is `steep.exe` at the analyzed image base and both stop-mode routines match the analyzed bytes. |
| `host_loader.c` | Uses the guards from `../mod_loader/load_probe.c`, then resolves `SnowHost_Start` locally. It verifies the export's entry bytes in the target and runs it with the port as its argument. |
| `startup_launcher.c` | Creates the original game process and reuses the checked host loader during startup. Records loading timestamps and visible-window counts beside the host DLL. |

Each operation uses a [validated native mechanism](../../docs/reconstruction/NATIVE_STOP_MODE.md):

- **pause**: Step must be advancing. The host runs the engine's setter (argument 1), then verifies that the group is held and Step is frozen while EndFrame continues.
- **step_world**: Step must be frozen. The host clears the group by compare-and-swap, waits until Step's last-run counter changes, then re-arms immediately. It checks the result over the next four EndFrames. The recorded live in-process stress run passed 410 single-step checks; the startup-loaded host also passed five releases.
- **resume**: The host runs the engine's clear routine. If the group is not ordinary afterwards, it restores the group recorded at pause time by compare-and-swap. Then it verifies that Step advances.

**One world step is one execution of the world `Step` job (one engine request).** It is not a rendered frame and not a physics substep; a step simulates roughly one frame, typically in 1–2 substeps (static and emulated evidence only).

**Recovery:** a host-held pause has a lease, 30 s by default (1–300 s). Any command renews it, and `host.heartbeat` exists for this purpose. When the lease expires, or when the client disconnects, the executor resumes the game. If recovery fails, the host marks itself faulted and refuses further control commands. A pause therefore lasts only while a client is connected and active.

**Execution context caveat:** the executor is an ordinary thread inside the game process. This matches how the native routines and mode writes were validated live (from a new thread and cross-process, respectively). It is **not** an engine-ordered per-tick callback. An `EndFrame`-ordered hook remains future work.

## Protocol

Newline-delimited JSON on `127.0.0.1:<port>` (default 47017). Wine sockets are host sockets, so a macOS process can connect directly.

```json
{"id":1,"method":"simulation.pause","params":{"lease_ms":30000}}
{"id":2,"method":"simulation.step_world","params":{"count":1}}
{"id":3,"method":"simulation.status"}
{"id":4,"method":"simulation.resume"}
```

A valid request receives `{"id":N,"status":"accepted"}`, then one final line with `"status":"completed"` or `"failed"` and a `result` object. Failures carry `result.error`. A malformed request or unknown method receives a single `"status":"rejected"` line.

| Method | Params | Result |
|---|---|---|
| `host.hello`, `simulation.status`, `host.heartbeat` | — | versions, adapter, `bound`, `host_paused`, lease, `last_recovery`, `plugins_active`, `steps_released`, and `engine` {group, held, step, paused_job, end_frame} |
| `plugins.list` | — | `plugins`: one entry per discovered DLL with `file`, `name`, `version`, `state` (`active`, `disabled`, `faulted`, `rejected`), `reason`, `calls` |
| `simulation.pause` | `lease_ms` | `baseline_group`, `engine`. Repeating it while the host holds the pause renews the lease. |
| `simulation.step_world` | `count` 1–60 | `unit: world_step_job`, one record per step (`step_before`, `step_released`, `step_after`, `release_ms`, `exactly_one`), totals |
| `simulation.resume` | — | `fallback_restore`, `engine` |
| `player.bind` | `handle` (string, optional) | `identity`. Without a handle the adapter finds the player in-process; with one, it validates the external acquisition's handle |
| `player.get` | — | `identity`, `held`, `flags`, `position`, `axes`, `linear_velocity`, `angular_velocity`. Acquires in-process first if nothing is bound |
| `player.set_velocity` | `vx`, `vy`, `vz` (numbers) | `set`, `after` (a `player.get` result). Only while host-paused |
| `player.set_position` | `px`, `py`, `pz`; optional `vx`, `vy`, `vz` | `set`, `after`. Keeps orientation (and velocity unless given). Only while host-paused |

Error codes: `adapter_unavailable`, `host_faulted`, `not_ordinary`, `step_not_advancing`, `hold_not_verified`, `not_paused_by_host`, `not_held`, `step_not_frozen`, `group_changed`, `rearm_failed`, `step_timeout`, `frames_stalled`, `not_exactly_one`, `owner_changed`, `restore_failed`, `step_not_resumed`, `bad_params`, `read_failed`,
`unsupported`, `player_rejected`, `no_player`, `player_changed`.

Counter values describe the engine's state. They are not stable identifiers and should not be used as API fields.

The host also writes `snow_host.json` (state, port, adapter binding) and a tagged `snow_host.log` next to the DLL.

## Plugins (API v1)

The public header is [snow_plugin.h](snow_plugin.h); [examples/step_logger.c](examples/step_logger.c)
is a complete plugin. Plugins are DLLs in a `plugins` folder next to `snow_host.dll`.
Each exports `int SnowMod_Initialize(const SnowHostApiV1 *host, SnowPluginV1 *plugin)`,
fills in its name, version and callbacks, and returns 0.

| Callback | When it runs |
|---|---|
| `on_pause` | After the host has verified the hold |
| `on_step` | After each observed release: the Step request token changed and the hold is re-armed. This does not independently count executed callbacks. The simulation is held during the call. Receives the batch position and a host-wide step count |
| `on_resume` | After `Step` is verified advancing again. Reason: requested, lease expired, or client disconnected |
| `on_unload` | When a plugin that returned nonzero is disabled cleanly, just before it is unloaded |
| `on_player` | Host 0.6+, optional: the player binding was lost or (re)acquired ([events](#player-events-host-06)). The simulation may be running |

The host provides `log` (into `snow_host.log`, tagged with the plugin name),
`config_path` (`plugins\<file>.ini`, which may not exist), `get_state`
(`host_paused`, `steps_released`) and, from host 0.3, `get_player`
([player state](#player-state-host-03)).

All plugin calls run one at a time on a host plugin thread, never on a game
thread, and each has a 250 ms budget (1 s for `SnowMod_Initialize`).
[snow_plugins.c](snow_plugins.c) contains failures per plugin:

- **Rejected at load:** no export, `Initialize` returned nonzero, wrong
  `api_version` or `struct_size`, or an invalid name.
- **Disabled:** a callback returned nonzero. The plugin gets `on_unload` and is
  unloaded.
- **Faulted:** a call exceeded its budget, or crashed (access violation, illegal
  instruction, divide by zero, stack overflow and similar). A vectored handler
  scoped to plugin threads moves the faulting thread onto a private stack, where
  it reports the fault and exits. A plugin that timed out is abandoned on its own
  thread with its own job slot. Faulted plugins are never unloaded.

In every case the host keeps stepping and resuming, and other plugins are
unaffected. Containment is best-effort: a plugin that faults while holding a
lock it shares with the game (for example the process heap) can still hang the
game, and plugin `DllMain` runs under the loader lock without containment.

A Wine fixture test with the synthetic adapter covers nine plugins: the two examples,
a well-behaved counter, a crash on the third step, a 5 s hang, a nonzero return,
a declining `Initialize`, a wrong API version and a DLL with no export. All 42
protocol, recovery, plugin and player checks pass. During the crash, every one of 10
steps was still exactly one. The fixture's simulated player moves only when its
simulated `Step` runs: it stays still while held, moves exactly ten steps' worth over
ten released steps, and a handle that expires drops the binding.

**Live result, 2026-10-15.** The example plugin ran inside the game during the
stress plan (`run_late_load.py --experiment host --plan stress`), which runs 300
consecutive steps, 10 pause/5-step/resume cycles, and 60 steps paused mid-ride
at about 100 km/h. All 410 steps were exactly one. The plugin received exactly 435
calls: initialize, 12 `on_pause`, 410 `on_step` and 12 `on_resume`. At every
resume its own count matched the host's, and it stayed active. Resume needed no
fallback restore, and `Step` advanced through the 20 s check.

## Player state (host 0.3)

`get_player` (plugins) and `player.get` (clients) return the bound player's physical body:

| Field | Meaning |
|---|---|
| `identity` | Opaque; changes whenever the host binds a player |
| `flags` | Host 0.6+: `SNOW_PLAYER_FLAGS_VALID`, `SNOW_PLAYER_IN_WORLD`. Without `IN_WORLD` the body is not being simulated and its values are stale |
| `position` | Body origin in world units (not calibrated to metres; not necessarily the visible board centre) |
| `axes` | The body's three basis vectors in world space |
| `linear_velocity`, `angular_velocity` | As stored by the engine, in world units per second |

**Binding.** From host 0.4 the adapter finds the player in-process. It walks the engine's root
records to each active world, then that world's motion receivers, and requires exactly one actor that
passes every identity check. A read with nothing bound acquires first, so plugins need no client. A
client may still supply an opaque handle from an external acquisition (`player.bind` with `handle`),
which the adapter validates the same way: object types, back-links and the owning world. Either way the
adapter pins the owning entity and world at bind time. Every read re-checks the whole chain
before and after copying the body. If any link changed (respawn, sport or world change), the read
fails with `SNOW_E_PLAYER_CHANGED` / `player_changed` and the binding is dropped. In-process acquisition is
[future work](#next).

**When it may be read.** Plugins may call `get_player` only while the host holds the simulation
(`on_pause`, `on_step`); otherwise it returns `SNOW_E_NOT_HELD`. While held the body is not being stepped,
so a read is a consistent snapshot. `player.get` also works while the game runs and reports
`held: false`; such reads race the simulation and are not a consistent snapshot.

**Velocity assignment (host 0.4).** `set_player_velocity` (plugins) and `player.set_velocity` (clients)
call the engine's own velocity-assignment routine, which the game itself uses. It sets the player's
linear velocity, zeroes angular velocity and resets the player's speed history. It is accepted only while
held, with finite values up to `SNOW_MAX_SET_SPEED` (300 units/s), after the adapter re-checks the routine's
code bytes and the player's identity. The new velocity takes effect from the next released step; after that
the game's own physics and controls carry on from it.

The player is two coupled physics bodies: the main body that `get_player` reports, and a heavier rider body
joined to it by a leg constraint. The routine has a flag that also re-poses the rider and gives it the same
velocity, and the adapter sets it. Without it, only the main body changes. The rider keeps its speed, and
the coupling drags the main body back within a few steps. This is how the first live attempt appeared to
have no effect. Live results while riding at about 37 units/s, paused:

| Assignment | Next released steps |
|---|---|
| main body only, 0 | main body speed 7, 16, 25 units/s over three steps (rider still at about 36) |
| both bodies, 0 | 1.1, 3.6, 4.7, 5.1, 4.5 units/s over five steps: the player nearly stops, then slope and gravity act |
| both bodies, 12 units/s up | rose 0.110–0.132 units per step for ten steps (12 units/s × about 10 ms); both bodies stayed near 12 units/s upward |

All steps were exactly one and resume needed no fallback restore.

**Placement (host 0.5).** `set_player_pose` (plugins) takes a `SnowPlayerStateV1`: read with
`get_player`, edit `position`, `axes` and velocities, and pass it back. `player.set_position` (clients)
keeps the current orientation and, unless `vx`/`vy`/`vz` are given, the current velocity. Both call the
engine's own placement routine, which the game calls from several places in player code. It sets the main
body's pose and velocities under the runtime lock, re-poses the rider body and resets the motion caches. The
host accepts finite values, orthonormal axes, the speed limit above and moves of at most
`SNOW_MAX_TELEPORT_DISTANCE` (100 units) per call, only while held.

Live while riding at about 43 units/s, paused:

| Placement | Result |
|---|---|
| 3 units straight up, velocity kept | read back exactly; over the next five steps the player continued from the new position at the usual 0.42–0.49 units per step |
| 3 units straight up, velocity zero | read back exactly with both bodies at zero velocity, but the first released step moved the player 3.32 units down and back to about 43 units/s, undoing the placement |

| 5 units along world x and 3 up, linear velocity zero | read back exactly and stayed at the new x and y. That direction was uphill, which put the player inside the slope; the physics then pushed them out over several steps (speeds up to 73 units/s, rising about 1 unit per step), and the next placement was refused because angular velocity exceeded the host's limit |

**The host does not check the ground.** A placement can put the player inside terrain, and the physics then
ejects them violently. Keep moves small and above the surface; one way is to move along the current velocity
or straight up.

Why the zero-velocity lift was undone is not yet known. The placement routine has a separate branch for
linear *and* angular velocity at or below 1e-5 that resets the player's ground-contact frame. Because
`player.set_position` keeps the current angular velocity, that branch did not run in these tests. Until
this is understood, place with the velocity you want the player to have, or place and then assign velocity
separately.

**Compatibility.** `get_player` is appended to `SnowHostApiV1`; the API version stays 1. A plugin that
needs it checks `struct_size >= offsetof(SnowHostApiV1, get_player) + sizeof(void *)`, as
[examples/player_logger.c](examples/player_logger.c) does. Plugins built against host 0.2 keep working.

The body fields and the identity chain come from earlier guarded live reads
(the [player measurement work](../../docs/reconstruction/TESTBENCH.md)).

**Live result, 2026-10-15.** In one bounded session, the client bound the player from a fresh guarded
acquisition, rode forward with ordinary key holds, paused mid-ride and released ten single steps:

- Two reads 0.5 s apart while held were identical (position, axes and velocities): the body is still
  while held.
- 10 of 10 steps were exactly one, and the player moved after every one: 0.33–0.41 units per step at a
  speed of about 37.5 units/s. Distance divided by speed was 8.8–11.0 ms per step, consistent with the
  ~10 ms world-request cadence measured separately. A released step advances the player by about one
  request's worth of motion.
- `player_logger` read the player on pause and after each step (cumulative displacement −1.50, −0.32,
  −3.45 after ten steps, speed 37.45), and `get_player` returned `SNOW_E_NOT_HELD` after resume.
- The orientation axes were unit length. After resume the player kept moving (60.7 units in about 1 s
  of reads and waits), the binding stayed valid, and resume needed no fallback restore.

**Live result, host 0.4 (same day, two bounded sessions paused mid-ride).** In-process acquisition found
the same player as the external acquisition: identical position, axes and velocities. The velocity results
are in the table above. Resume needed no fallback restore, and the binding stayed valid afterwards.

A first attempt the same day stopped in startup navigation (the game opened on the map screen) before
the host was loaded. One session establishes the read path while riding; it does not cover respawn,
sport or world changes, where the binding is expected to drop.

## Player events (host 0.6)

**Liveness.** A bound player is valid only while the engine's live registries still hold exactly that actor.
The host checks this before every read and setter, and about every 250 ms on the executor. Pointer and type
checks alone could accept an actor whose memory was freed but is still mapped; the registry walk does not.

**Events.** When the check fails, the host drops the binding and calls `on_player` with
`SNOW_PLAYER_LOST`. As soon as a single player is registered again, it binds that player and calls
`on_player` with `SNOW_PLAYER_ACQUIRED` and a new `identity` (`world_changed` is set if the world differs).
Events are delivered on the plugin thread from the executor, between commands and on the watch tick, never
from inside another plugin call. `on_player` is appended to `SnowPluginV1`. Plugins built against older
headers still load (the host accepts the 0.2 structure size, and the fixture checks it), and simply get no
events.

**Simulated or not.** `SNOW_PLAYER_IN_WORLD` reports whether the main body belongs to a physics world. In a
70 s live ride the flag stayed set while riding, cleared at the moment the body froze after a crash, stayed
clear while the player was moved to a respawn point, and came back when riding resumed. The actor was the
same throughout, so no event fired: a crash and respawn reuses the player. Velocity assignment and placement
refuse while the flag is clear.

Live, 2026-10-15: over about 50 s of riding the watcher reported exactly one `acquired` event and no false
`lost`. A forced crash (assigning 80 units/s into the slope) did not replace the player. The fixture covers
loss, automatic re-acquisition and event delivery (56/56 checks).

## Client

`scripts/snow_host_client.py` is both a library and a CLI:

```text
python3 scripts/snow_host_client.py status
python3 scripts/snow_host_client.py step 5        # pause, 5 world steps, resume
python3 scripts/snow_host_client.py pause         # hold until Enter; heartbeats keep the lease
python3 scripts/snow_host_client.py demo --steps 10
python3 scripts/snow_host_client.py player --bind <handle>
```

## Live run

From the configured research workspace (it requires the private adapter):

```text
python3 steep-gameplay-research/scripts/run_late_load.py --experiment host --steps 10
```

This uses the same bounded launch, startup navigation, gameplay check, watchdog and settings restoration as the late-load probe. It then loads the host, runs the client demo, and checks 20 s of stability through `simulation.status`. If the host cannot restore ordinary mode, a private guarded byte restore (`analysis/mod-host/private/restore_mode.py`) is the fallback; like the game adapter, it holds build-specific addresses and is not published. Running it targets the game process and requires explicit authorization.

### Live result, 2026-10-14

- The host loaded, started and bound its game adapter inside the running game.
- Pause ran the engine's setter. The group changed from `00000001` to `00010101`, and Step froze while EndFrame continued.
- **10 of 10 single steps released exactly one Step.** Step stayed frozen after each release, and each release took 1.8–17.1 ms.
- Resume ran the engine's clear routine without the fallback restore. The group returned to `00000001`, and Step advanced at all five samples over the next 20 s.
- The original DLL was verified, settings were restored and the bottle stopped.

This was the first in-process single step and the first one through the command interface. It establishes one tested session, not long-term stability, behavior under movement or sport changes, or deterministic replay.

An earlier attempt the same day refused to bind. The adapter's page-protection check rejected the owner slot, so the check now also accepts copy-on-write protections. No pause, step or write happened in that attempt, and cleanup completed.

## Build

```text
x86_64-w64-mingw32-gcc -std=c11 -Wall -Wextra -Werror -O2 -shared -o snow_host.dll snow_host.c snow_plugins.c fixture_adapter.c -lws2_32
x86_64-w64-mingw32-gcc -Wall -Wextra -Werror -O2 -shared -I. -o plugins/step_logger.dll examples/step_logger.c
x86_64-w64-mingw32-gcc -Wall -Wextra -Werror -O2 -shared -I. -o plugins/player_logger.dll examples/player_logger.c -lm
x86_64-w64-mingw32-gcc -Wall -Wextra -Werror -O2 -municode -o host_loader.exe host_loader.c
```

For the game build, replace `fixture_adapter.c` with the private adapter and add `-I` for this directory.

## Next

1. Observe a sport switch and a world change live (expected to fire `lost`/`acquired`), then a ground query for safe placement.
2. Events: world loaded, player changed, sport changed.
3. Measure what a released step simulates (time delta, substeps, input), and a world-change stress run.
4. Repeat startup loading across fresh launches and additional supported builds.

## Rotation-preserving actuation research

[Central-impulse contract and next live gates](../../docs/reconstruction/CENTRAL_IMPULSE.md)
records the native arithmetic validated in 960 offline cases. This primitive is
not yet exposed by the live host; lock/thread context and paired-body submission
remain unresolved. It is the next candidate for continuous brake/boost.

## Experimental animation observation command

`animation.get_channel` accepts one unsigned 32-bit integer `key`. The command
returns the opaque player identity, lookup result, bank epoch, and, when found,
a four-component local vector and quaternion. It also returns the retained parent
record and recovered provider conversion. Coordinate semantics remain unresolved.
It rejects missing/out-of-range keys, failed identity/bank guards and non-finite
channel values. This is a read-only command, with no animation write operation.

The synthetic adapter supplies key `10` with vector `[1,2,3,0]` and rotation
`[0,0,0,1]`; all other keys are missing. These are invented test values.
The private game adapter connects the bounded native reader. One
[live session](animation_host_live_observation.json) returned 12/12 successful
queries with matching player identity and twelve distinct epochs, vectors and
rotations. The game continued advancing for the following twenty seconds; the
launcher stopped the bottle and restored its settings. This verifies one
player/channel/session, not all skeleton types or animation states.
A ready adapter without a callback returns `animation_unsupported`; an unready
host returns `adapter_unavailable` first.

Responses explicitly report `atomic_snapshot`, `lifetime_pinned`,
`animation_completion_established` and `suitable_for_animation_writes` as false.
A simulation hold alone does not prove completion of animation work. The optional
adapter callback must revalidate player, skeleton ownership and bank endpoints.
This command does not extend the plugin ABI.

`snow_animation_reader.h` performs exact type/owner checks, unsigned channel
lookup, metadata capacity checks, finite-value checks and retained-span rechecks.
It examines at most 256 components and 4096 resource entries, retaining at most
512 spans of 256 bytes. It returns the local provider record plus its recovered parent-space
conversion. Supplied transports must safely perform exact reads and verify the
process/build. The private adapter uses `ReadProcessMemory` and brackets the
reader with player registry and actor/entity/world checks. These checks do not
pin objects or prevent ABA changes.

Twenty compiled-C synthetic tests cover malformed identities, lookup bounds,
duplicate keys, failed reads, mutation and agreement with the Python reader,
including 128 direct/composed float32 conversion cases.
Run `python3 -m unittest discover -s tests -p 'test_native_animation_reader.py'`.
The fixture C entry has no process access and uses invented memory.

Against an already running synthetic fixture host:

```sh
python3 scripts/animation_fixture_probe.py --port 47117
```

The probe refuses non-fixture adapters and checks values, missing keys, range
errors and observation limits. It does not launch a process or change simulation
state. The reader follows the
[guarded Python observation contract](../../docs/reconstruction/CENTRAL_IMPULSE.md#composed-player-animation-observation-api),
The next gate is controlled-action and lifecycle testing; animation writes remain unsupported.

For the configured private research workspace, the bounded launcher now supports:

```sh
python3 scripts/run_late_load.py --experiment host --plan animation
```

It verifies the original DLL, acquires the experiment lock, starts a watchdog,
navigates recognized startup screens and loads the host after gameplay is
recognized. The capture requests twelve player/channel pairs for resource key
`743623600`, previously observed as channel zero. It preserves refused queries,
checks opaque player identities and then observes simulation advancement for
20 seconds. The capture sends no gameplay input or simulation-control command.
The launcher still sends startup-navigation input and loads the host DLL.
It closes its session and checks launch-setting restoration afterward.
A successful query does not identify a clip or prove animation-job completion.

`--plan animation-motion` adds one 700 ms forward-key pulse using the existing
identity-checked input helper, with eight baseline, twenty-four pulse-window and
eight follow-up samples. The helper reports OS delivery and key release; these
are not proof of engine input ingestion. The pulse-window samples span helper
startup, delivery and release rather than an exact simulation-time interval.

Capture schema v2 brackets every pose query with two player reads, requiring all
three opaque identities to match for a paired observation. It records the host
request duration and wall-clock endpoints. Equal identities do not exclude ABA,
make the reads atomic or align physics and animation updates.
`summarize_animation` reports adjacent-sample deltas only within one identity,
using quaternion-sign-invariant angular distance; it does not assign clip names
or claim causality. Units for position and speed remain stored engine units.

One [live forward-pulse trial](animation_motion_live_observation.json) accepted all
40 identity brackets. Baseline body speed was zero while the local pose varied.
Maximum body speed was about 0.60 stored units/s during the pulse window and 4.60
in the follow-up window. These are observations from one uncontrolled terrain
location, not a fitted acceleration model. Maximum request span was about 10.9 ms;
the requested sample spacing was 100 ms. Key release, twenty-second advancement
and session cleanup checks passed. Sport/clip identity and exact ingestion timing
were not established.

The optional animation response fields now include `record_index`, `bank_flags`,
`conversion_direct`, `parent_vector`, `parent_rotation`, `provider_vector` and
`provider_rotation`. `vector` and `rotation` retain their original local-record
meaning. Flag bit 26 selects direct copy; otherwise the recovered formula rotates
XYZ, adds parent position and composes XYZW quaternions without normalization.
The W lane follows the recovered formula rather than an assumed homogeneous-point
convention. `coordinate_space_semantics` is `native_provider_conversion_only`.
Neither output is asserted to be a named bone or world-space transform.
Parent records are guarded along with the selected local record; non-finite input
or conversion output causes refusal. A subsequent
[live conversion check](provider_conversion_live_validation.json) matched all
twelve composed-branch samples against the Python reference and offline original
instruction execution using captured inputs. All 36 instruction slices matched,
with no replaced calls. The original accessor was not invoked or observed live.
Direct mode still has synthetic validation only.

To validate a private capture or session result without launching anything:

```sh
python3 scripts/validate_animation_conversion.py /path/to/private/result.json
```

The validator emits aggregate counts and mismatches, not pose tracks. This is
formula consistency checking, not evidence of clip identity or coordinate space.

The read-only response also retains `owner_matrix`, `owner_accessor_present` and
`owner_reader_word`. It reads the owner's stored 4×4 matrix directly and validates
an indirect accessor's owner backlink and synchronization metadata when present.
It does not invoke the accessor or read its reusable scratch result. The stored
matrix can be stale, even when guards match; `owner_transform_freshness_established`
is always false. A subsequent [live trial](owner_parent_live_observation.json)
returned forty identity-bracketed observations. Every owner-derived XYZ and
quaternion matched the bank parent at float32 precision. Four parent W lanes
were `1`, while the decoded guarded-refresh writer clears W to `0`.
This is evidence for investigating other writer/initialization paths, not grounds
for forcing every parent W to zero. All forty samples used an indirect accessor;
none invoked it from the observer.

```sh
python3 scripts/compare_animation_parent.py /path/to/private/result.json
```

This comparison prepares a parent pose from the sampled owner matrix and reports
bit-exact agreement or disagreement with the captured bank parent. A disagreement
is retained as an observation, not treated as proof of a bad formula. Equality
does not establish the last writer, atomicity, freshness or world-space meaning.

In that trial, the stored owner matrix and the bracketing body matrix coincided
in baseline and pulse-window observations. Some follow-up samples differed while
the body moved, up to about 0.029 stored translation units. Sequential sampling
and update ordering remain possible explanations; no common coordinate-frame
contract is inferred. The comparison canonicalizes JSON numbers to float32 before
reporting parent deltas, and separates XYZ, quaternion and W matches.

### Cached parent and callback inspection

`animation.get_cached_parent` takes no parameters and requires a bound player.
It returns the opaque player identity, eight-lane `cached_parent`, `primary_parent`
and `current_parent` arrays, callback eligibility/presence flags and context tag.
Missing banks return null. No component, holder or function pointers are exposed.

```python
with SnowHostClient(port=port) as client:
    observation = client.call('animation.get_cached_parent')
```

The private adapter brackets the read with player checks and actor/entity/world
identity guards. The portable reader verifies unique skeleton binding and rereads
all retained spans. Failure refuses the observation; identity loss drops binding.
Eligibility does not prove invocation. Atomicity, lifetime pinning, executable
memory verification, writer attribution and safe native calls remain false.
The command performs no game calls through the observed callback and no writes.

The read-only collector in `scripts/cached_parent_capture_probe.py` accepts an
already connected client and records 1–32 samples. Each sample reads player,
cached-parent observation, then player again. The summary excludes refused,
malformed, or identity-mismatched observations and counts changes only across
consecutive accepted samples with the same identity. No gap is bridged.

```python
from cached_parent_capture_probe import capture_cached_parent
capture = capture_cached_parent(client, samples=12, interval=0.1)
print(capture['summary'])
```

Run with `scripts` on the Python import path. Store raw rows only in private
session storage; they contain runtime pose data. The summary contains counts,
not poses or identities. Eligibility and pose changes never establish callback
execution, writer identity, or safe mutation. The client request timeout bounds
each transport operation; the collector does not launch or control the game.

In the configured private workspace, the bounded session runner can launch,
navigate to gameplay, collect 32 observations, check ordinary advancement for
20 seconds, and clean up:

```sh
python3 scripts/run_late_load.py --experiment host --plan cached-parent --check
python3 scripts/run_late_load.py --experiment host --plan cached-parent
```

The second command launches the game and loads the host. Startup navigation may
send input, but the capture plan itself sends no riding input, steps, or writes.
Its raw result remains in private session storage under `probe/result.json`.

## Client stepping recovery

The `step` and `demo` commands now share one bounded pause/step/resume
transaction. They refuse an already host-held pause, require each released step
to report exactly one execution, stop on the first failed/uncertain step, and
attempt resume even if the pause response was lost. They never retry a mutation.
A successful resume does not turn a failed step into a successful command.
Recovery and final-status failures remain in the JSON result alongside partial
step evidence. Disconnect and the host lease remain the fallback if communication
fails; a client-side recovery attempt alone does not prove the game resumed.

Run from the repository:

```sh
python3 scripts/run_late_load.py --experiment host --load-at startup --check
python3 scripts/snow_host_client.py status
python3 scripts/snow_host_client.py player
python3 scripts/snow_host_client.py step 1
```

The preflight checks local prerequisites without launching the game. The other
commands require a running host. Loopback protocol and injected-failure tests
cover the revised client transaction; no new live-session result is implied.
The `step` JSON result now uses the same `ok`, `steps`, `resume` and `after`
structure as `demo`, replacing its previous single `step` response field.

## Current launch prerequisite failure (2026-10-22)

The latest bounded startup acceptance attempt built the host and launcher but
failed before the game started: macOS refused Intel process execution. A separate
`arch -x86_64 /usr/bin/true` check failed with `Bad CPU type in executable`.
No gameplay or steps were tested. Settings were restored, the bottle stopped,
and the original DLL hash remained correct. See the
[sanitized result](startup_runtime_prerequisite_failure.json).

Preflight now checks Intel execution on Apple Silicon before building or launching
this configured Intel Wine workflow. Package files alone do not prove Rosetta
works. Restore Rosetta, then rerun `--check` before the bounded acceptance test.
Earlier successful live results remain historical evidence, not a result of this
latest attempt. The launcher does not install Rosetta or accept its license.

## End-to-end acceptance plan

After Intel execution is restored and preflight passes, run:

```sh
python3 scripts/run_late_load.py --experiment host --load-at startup --plan acceptance --steps 3
```

This builds and starts the host through the existing bounded launcher, verifies
startup loading and gameplay navigation, then checks these stages in order:

1. A bound, simulated player is readable.
2. The revised client pauses, releases three individually verified world steps,
   and resumes successfully.
3. The existing speed trial applies one eligible -2 and one +2 unit/s pulse,
   checking held readback and player identity after one/five world steps.
4. A bound, simulated player remains readable afterward.

The speed trial may send bounded forward input to leave a stationary spawn; leave
controls alone during this experiment. It retries eligibility checks only, never
an uncertain mutation. The probe then requires 20 seconds of unheld advancing
simulation and verifies final ordinary mode. The launcher independently checks
settings restoration, bottle shutdown and the original DLL hash.

Each acceptance stage stores its result or exception. A failed stage prevents
later stages and cannot be converted into success by a successful cleanup.
The configured watchdog remains five minutes, with at most 160 seconds allotted
to the acceptance probe. This plan is implemented and tested with scripted
clients; it has not passed a live run while the Rosetta prerequisite is broken.
It establishes a bounded mod-host acceptance target, not complete engine parity.

The speed acceptance implementation retains every attempted resume alongside
partial mutation/readback evidence. An uncertain pause response also enters
recovery. Existing holds are refused, mutation responses are never retried,
and failed step counts or changed player identity stop the trial immediately.
Forward-input helper failures stop eligibility retries. Scripted failure tests
cover this control flow; these checks do not substitute for live acceptance.

The combined acceptance probe independently checks each requested speed target
against the held pre-operation velocity and the host's documented 0..60 boost
cap. Readback must contain three finite components. Each step receipt must match
the count sent by the client, not merely agree with its own other counters.
A mismatch stops further mutations and attempts resume while retaining the
failed receipt. Scripted failure tests cover these checks; they do not establish
live gameplay success or perceptible brake/boost behavior.

### Portable acceptance against an already-running host

On a machine where the host is already running and the player is bound, move
onto a clear slope, then leave the controls alone and run from the repository:

```sh
python3 scripts/run_host_acceptance.py --steps 3 --output /tmp/snow-host-acceptance.json
```

Only Python's standard library and the host's loopback port are required.
`--port` selects a nondefault port. The command pauses/steps/resumes and applies
bounded -2/+2 speed pulses through the existing API. It does not launch the game,
find or bind a player, inject forward input, or capture video. Ineligible speed
trials fail with a request to reposition and rerun; uncertain mutations are never
retried. Exit code zero requires every acceptance stage to pass. JSON retains
partial results and recovery failures, with explicit false flags for startup and
visual validation. Player snapshots are sequential reads, not atomic captures.
Keep receipts private: they contain session-specific player identities.

`tests/test_host_acceptance_cli.py` exercises the actual client and acceptance
sequence over a synthetic loopback server, including receipt output and released
holds. This is protocol integration evidence, not native-host or live-game proof.
The bounded launcher above remains the full startup/cleanup acceptance route.

The [build validation receipt](acceptance_build_validation.json) records a full
1,591-test Python pass and warning-clean Windows cross-compilation of the fixture
host, both loaders, and both example plugins. The native animation-reader test
initially failed because the selected linker could not parse the default macOS
27 SDK; selecting the installed 26.5 SDK via process-local `SDKROOT` allowed the
entire suite to execute without skipping that test. This is an uncommitted
worktree validation snapshot. No Windows artifact was executed in this pass.

### Post-update acceptance attempt

On 2026-10-22, after Intel execution was restored on macOS 27.0.1, the rebuilt
0.7.0 host loaded before any visible game window. Deferred binding subsequently
verified the adapter identity, reached engine-ready state and initialized the
step logger plugin. The initial binding rejection during startup was transient.

The acceptance run did **not** reach gameplay verification, pause/step or speed
checks. Navigation's capture/OCR helper exceeded its 15-second deadline. A capture
file existed and showed a blank game window; this does not establish a game crash.
The launcher closed its owned session, restored temporary settings, verified the
original DLL and confirmed the bottle had stopped. The private navigation helper
now allows up to 30 seconds for capture/OCR within its overall deadline and records
timeouts instead of losing the navigation result to an exception. That adjustment
has only a syntax check so far. See the [bounded result](post_update_acceptance.json).

A second bounded attempt recovered from two capture timeouts and reached the
recognized gameplay HUD. The host reported ready, ordinary simulation, one active
plugin and a bound player. The first player read had flags=1, without IN_WORLD,
so acceptance stopped before any pause/step or speed mutation. This does not prove
why the player was inactive. Cleanup again passed. The acceptance helper now
supports up to 20 seconds of read-only readiness polling, enabled in the launched
acceptance plan; it retains each sample and never retries a transport failure or
host refusal. Fourteen acceptance/client/speed tests pass. This readiness change
still needs a live run; no gameplay acceptance success is claimed.

With the 200-second navigation budget, gameplay was reached and readiness polling
completed: 41 successful reads over 20 seconds retained flags=1. The screenshot
showed an idle snowboard rider. Waiting alone did not activate the selected body;
no physics mutation was attempted. The next launched acceptance preparation now
sends one identity-checked 700 ms forward input only for a valid, inactive player
in ordinary running simulation. It retains key-release evidence, checks player
identity afterward and preserves the IN_WORLD gate for every subsequent physics
test. Already-active players receive no preparation input. This is an experiment
to test activation through normal controls, not a proven wake-body mechanism.
Twenty-four focused launcher, acceptance and client tests pass; live validation
of the preparation remains pending.

### Post-update end-to-end acceptance passed

A subsequent bounded offline snowboard session passed startup host loading,
plugin initialization, gameplay/player binding, ten single-world-step requests,
resume, both brake/boost trials, player readback after the trials and 20 seconds
of stable observation. The normal 700 ms forward input preceded a flags=1 to
flags=3 transition with unchanged player identity and about 0.170 units of
position displacement. This is observed activation after input, not an instrumented
proof of input ingestion or a universal body-wake rule.

Brake changed speed from 4.17635933 to 2.17635933; boost changed it from 34.7476899
to 36.7476899. Both matched independent target/readback checks, followed by requests
for one and four world steps. The existing setter **resets angular velocity**;
this pass does not validate a momentum-preserving impulse API. Single-step results
refer to the host's world-step job criterion, not deterministic full-engine replay.
Cleanup stopped the bottle, restored settings and retained the original DLL hash.
See the [successful acceptance receipt](post_update_acceptance_success.json).

Run from the repository in the configured private workspace:

```sh
python3 scripts/run_late_load.py --experiment host --load-at startup --plan acceptance
```

This plan advances recognized startup screens and may send a short normal forward
input to start an inactive rider. Leave controls alone during the run. The existing
five-minute watchdog remains active. Earlier failed attempts remain documented
above; the successful result does not erase their capture and readiness findings.

## Snow-update capture core

`snow_update_trace.c` and `.h` provide authored, bounded recording around a typed
`void(actor, elapsed_dt, derivative_dt)` call. They do not install a hook, resolve
game objects or expose an impulse command. The intended actor route and its
conditional nature are documented in
[central impulse research](../../docs/reconstruction/CENTRAL_IMPULSE.md#actor-virtual-boundary-leading-to-the-consumer).

Initialize a trace once with fixed storage and immutable callbacks, before any
caller can access it. The original-call adapter receives the exact actor and two
float arguments. A separately supplied, non-mutating snapshot callback records
pending impulse, both bodies, identity/gates and request/substep fields. It must
set validity explicitly; a zero-initialized or failed sample is not valid evidence.
The core itself contains no game offsets or memory reads. Snapshot reads remain
sequential unless the adapter establishes a stronger guarantee.

Each captured invocation owns one record containing entry and exit observations.
An atomic capacity reservation keeps concurrent and nested invocations separate.
Capacity exhaustion increments `dropped` and still calls the original. Record
order is reservation order, not a cross-thread causal ordering. Only read records
after `snow_trace_close` followed by a true `snow_trace_drained` result. Closing
atomically prevents new capture admissions; admitted calls finish before drain
succeeds. Calls arriving afterward still forward to the original.

**Drain does not authorize unloading or freeing the trace.** A cached wrapper
pointer can arrive after close. Context, callbacks, original target and wrapper
code must remain valid for those callers. There is no reopen operation, and no
live ownership or reclamation guarantee is supplied. Callbacks must return
normally; an exception or nonlocal exit leaves the active count outstanding and
must be reported as an incomplete capture, not forcibly reset.

The synthetic native fixture covers nested records, timing argument forwarding,
800 calls from four threads, capacity exhaustion, a close racing an admitted call,
late forwarding without log mutation, and zero-capacity capture. The C core also
cross-compiles with MinGW for Windows x64. Those checks establish authored recorder
behavior, not game ABI compatibility, live capture, atomic snapshots or a safe
installation point.

`snow_update_snapshot.c` supplies the build-specific reader for that capture core.
Its binding requires a freshly validated actor/table/world and independently
attributed counter addresses where available. Its transport callback must perform exact, safe reads and enforce the
process/build identity. An integration adapter can call it from `SnowUpdateRead`;
no live adapter or callback installation is included yet.

The reader brackets actor table, actor self-link, entity, world, runtime, main and
optional rider pointers, plus request/substep counters. Every failed read or
changed guarded value returns failure and leaves the entire output zero. A
successful sample sets `SNOW_SNAPSHOT_VALID`; `SNOW_SNAPSHOT_RIDER_PRESENT` marks a
non-null rider. Missing rider data stays zero and must not be interpreted as an
observed stationary rider. Raw pending/velocity/mass values are retained without
normalizing or rejecting nonfinite values, since the reader measures state rather
than authorizing a physics mutation. The four flag bytes are sampled once.

Counter addresses must belong to the same current world/request, established by
the integration adapter. Numeric equality alone does not prove that association.
Bracketing neither detects address reuse/ABA nor pins the objects. It can reject a
legitimate sample when counters advance during observation. Pointer ranges and
failure handling are authored observer policy, not recovered engine behavior.

The synthetic reader fixture injects failure at every read, changes each of the
nine guarded values between passes, and covers an absent rider, wrong self/world,
null main body and overflowing runtime pointer. Native fixture execution and
Windows x64 cross-compilation pass. Live object linkage and capture cadence still
need verification in the game.

### Windows probe assembly

`snow_update_probe.c` connects the capture core to `ReadProcessMemory`, the guarded
snapshot reader, `QueryPerformanceCounter` and Windows thread IDs. It exports a
small experimental ABI declared in `snow_update_probe.h`:

- `SnowProbe_Configure(binding, original)` validates one initial snapshot,
  initializes fixed storage for 4,096 invocations and pins the DLL. Call once,
  before publishing its dispatcher. A failed attempt cannot be retried.
- `SnowProbe_Dispatch(actor, elapsed, derivative)` records the selected actor and
  forwards every other receiver directly to the supplied original function.
- `SnowProbe_Close(used, dropped)` closes capture and reports success only when
  admitted captures have returned. It does not wait or unload the DLL.
- `SnowProbe_ReadRecord(index, out)` copies one record only after close and drain.

Configuration alone performs no hook installation. The explicit slot installer
below replaces one vtable pointer; it does not launch the game, mutate physics
state or patch executable instructions. The caller must verify the game build, original target,
argument signature and counter ownership before configuration, then establish a
safe publication mechanism. Calling Dispatch before successful configuration is
an API violation. The DLL and immutable capture context remain pinned for late
callers. Tick values are raw QPC counts, not seconds. A production session must
also record QueryPerformanceFrequency when exporting them.

The Windows fixture dynamically loads the DLL and uses synthetic byte-array game
objects. It checks selected/unselected forwarding, timing arguments, both bodies'
angular values, closed-read guards, an invalid after-snapshot when the runtime
link changes, late forwarding without log mutation and DLL pinning after
FreeLibrary. The original callback in this fixture applies an authored test
change; it is not original game physics. See the
[Wine fixture receipt](snow_update_probe_validation.json).

Build from the repository root, with artifacts outside the findings tree:

```sh
mkdir -p /tmp/snow-update-probe
x86_64-w64-mingw32-gcc -std=c11 -O2 -Wall -Wextra -Werror -shared native/snow_host/snow_update_probe.c native/snow_host/snow_update_trace.c native/snow_host/snow_update_snapshot.c native/snow_host/snow_entry_attribution.c native/snow_host/snow_batch_frame.c native/snow_host/snow_entry_thunk.S native/snow_host/snow_motion_observation.c -o /tmp/snow-update-probe/snow_update_probe.dll
x86_64-w64-mingw32-gcc -std=c11 -O2 -Wall -Wextra -Werror -I native/snow_host tests/fixtures/snow_update_probe_fixture.c -o /tmp/snow-update-probe/fixture.exe
```

On Windows, run `fixture.exe` with the absolute DLL path as its sole argument.
Under Wine, give the fixture a Windows-mapped path to the DLL. This test needs no
game files. Success verifies the probe assembly; it does not establish safety or
correctness when installed in the original game's actor dispatch.


### Explicit slot installation and restoration

`SnowProbe_InstallSlot()` is a separate opt-in after successful configuration.
It checks the selected actor snapshot again and verifies the aligned slot at
`actor_table + 0x2c0` still contains the configured original. The slot must be in
a nonexecutable committed image region, and both slot and original target must
belong to the same loaded module. The module is pinned to retain its table and
code. These checks do not establish player lifetime or supported game-build
identity; the acquisition adapter must establish those independently.

The installer makes the slot's page writable, replaces the pointer with an atomic
compare/exchange, and restores the previous protection. Other instances using
that shared vtable reach the wrapper too, but forward directly to the original.
It permits only one installation attempt. There is no instruction detour or
trampoline. Page permissions apply to a whole page, so concurrent external
protection changes on that page are unsupported.

`SnowProbe_RestoreSlot()` replaces the pointer only when it still equals this
probe. An unexpected pointer is preserved and reported as a conflict. The
recorded page protection is restored even on that conflict. Restoration is
retryable and idempotent when the original already occupies the slot. Return
values are 1 for success, 0 for refusal/conflict, and -1 for a page-protection
failure. Call restoration after any attempted installation, even a failure;
installation rollback is best-effort. Check restoration's result, then close
capture and wait for drain before copying records. Never unload the pinned probe
or treat drain as permission to free game objects or retained callback contexts.

The updated Windows fixture runs through a read-only synthetic image vtable.
Normal installation, argument forwarding, read-only protection restoration,
conflicting-pointer preservation, retry restoration, and mismatched-original
refusal pass under Wine. Windows API failure injection and live installation in
the game have not run. The remaining integration work is fresh owner/counter
acquisition, bounded session orchestration and trace export with QPC frequency.

### Timing availability and fresh binding resolution

Snapshot validity is a bitmask: bit 0 marks a successful guarded snapshot, bit 1
marks a present rider, bit 2 marks an available request counter, and bit 3 marks
an available substep counter. A zero binding address for either counter means
unavailable. Its numeric output remains zero with the corresponding validity bit
clear; do not interpret that as an observed index zero. A supplied address that
cannot be read still invalidates the whole snapshot. Rebuild consumers with the
current header; the experimental interface has no cross-version ABI promise.

`snow_update_resolve_binding` resolves a freshly acquired actor through its entity,
world, runtime and the world's physics owner to the scheduler state. It checks
actor/self/runtime backlinks, the original actor slot, the world callback and
job-owner relationship against an externally verified build profile, then rereads
the identity links. Its returned request address is the world job's **started
counter**, not a device-event sequence or a full simulation generation. The
substep address is zero. The observed loop index has not been established as a
stable readable field; neither total substep count nor a world-step counter is a
valid substitute for it.

This helper does not discover the player or prove current registry membership.
The session adapter must acquire the actor freshly, establish the profile/build,
resolve immediately before configuration, and stop/rebind on owner replacement.
Later snapshot equality still cannot exclude ABA or a stale counter allocation.
Tests cover failure at each of the resolver's 27 reads and independent absence
of either timing field. The resolver is synthetic-tested, not live-validated.

### Bounded capture plugin

The optional `examples/update_capture.c` plugin connects acquisition, configuration,
installation, restoration and JSONL export. Build it explicitly:

```sh
python3 scripts/build_snow_host.py --adapter steep --capture-plugin --out /tmp/snow-capture-host
```

This adds `plugins/update_capture.dll`. It is disabled unless the adjacent
`update_capture.ini` contains:

```ini
[capture]
enabled=1
seconds=2
```

Only 1–5 seconds are accepted. This is an experimental live-game probe, not a
routine gameplay mod. Its lifecycle has been tested under Wine with synthetic
objects; actual player acquisition and installation in the game remain untested.
Use a bounded game session when validating it.

On a host pause callback, the plugin's separate adapter instance acquires the
player from the live registry, checks held-mode/owner/step stability, resolves the
world job, and configures the probe. Wait for the host log message `capture
configured; resume starts bounded observation` before resuming. Host callbacks
are asynchronous; an immediate pause/resume command pair can outrun acquisition
and produce no capture. A failed acquisition leaves the plugin available for a
later pause; failed probe configuration ends that attempt.

The next resume callback starts one worker. The worker installs the slot, observes
for the configured window, restores the slot, closes capture and allows up to two
seconds for drain. It then writes `update_capture.ini.trace.jsonl` beside the
configuration file. It never calls the pose or velocity setters. Installation,
restoration and drain results are separate fields: a log existing does not mean
that any of those operations succeeded. A failed restoration requires investigation;
do not unload the pinned DLL or overwrite a competing slot to force success.

The first JSONL line reports installation/restoration/drain, capacity drops and
QPC frequency. Subsequent records contain timing, validity, gates, pending impulse,
main/rider linear and angular velocities and inverse masses. Process pointers in
these local traces support identity comparisons only; never reuse them in another
session or publish the raw trace as an asset-free research receipt. Nonfinite
floats export as null. Substep remains explicitly unavailable.

The synthetic plugin fixture uses the real configuration/callback/worker/export
path but replaces acquisition with a supplied fake binding. One Wine run produced
395 records, no drops, successful restoration/drain, the expected authored test
velocity change and unchanged angular values. See
[the session receipt](update_capture_session_validation.json). This is a lifecycle
check, not a native impulse or scheduler-fidelity result.

### Optional history-action recorder channel

Experimental recorder ABI v7 appends history observations to `SnowUpdateRecord`.
Rebuild the probe, capture plugin and every direct `SnowProbe_ReadRecord` caller
from the same header; the old v6 record buffer is too small. Historical v6
receipts remain evidence for those earlier builds.

`snow_trace_call_with_history` accepts an optional bounded history observer and
context alongside the existing attribution and motion observers. It records
history just before the original actor callback and just after it returns.
Exactly return code 1 marks a sample valid; other returns clear that sample,
without affecting the original call or other observation channels. Overflow,
closed capture and counter saturation forward without optional observations.
The normal close/drain lifetime requirements still apply.

The payload preserves action/source/configuration/history/clock identities,
reference and feature vector bits, magnitude bits, settings, recent history
times and action timer state. These are observations, not native object layouts,
producer generation numbers or proof that an inner evaluator executed. The
observer must resolve fresh action provenance for the actor and obey the
bounded, non-mutating, thread-safe callback contract. No exception containment
or pointer-lifetime protection is introduced.

This pass adds recorder plumbing only. Existing probe configuration and the
capture plugin do not enable a concrete history reader. The Python
[passive observer contract](../../docs/reconstruction/INPUT_TO_ACTION_ROUTE.md#passive-history-action-capture-contract)
is the reference for the future native reader. Budgeting that reader, selecting
the active action and exposing an opt-in configuration remain required before
live use. No hook was installed or game launched for this change.

### Native history-action reader

`snow_history_observe` in `snow_history_observation.c` implements the passive
history-action layout reader. The caller supplies an exact `SnowEntryRead`, a
fresh action pointer, expected action table/evaluator and clock-global slots.
It returns two samples in `SnowHistoryCapture`, bounded to 32 reads and 1,024
requested bytes. Float fields remain raw uint32 bits, including NaN payloads.

Return 1 means matching identity/settings receipts; 2 means those receipts differ;
0 means invalid, unavailable or unsupported input and clears both samples.
Dynamic equality is independent of identity equality. Changing clock values are
retained, not treated as an identity failure. Both null clock-selection branches
and the selected-object branch use the decoded accessor layout. Required zero
pointers, empty threshold arrays, invalid channel and address overflow refuse
capture. The byte reader remains responsible for rejecting inaccessible memory.

The fixture checks both channels, clock fallbacks, identity mutation, dynamic
changes, raw float bits, every read-failure position on the selected and fallback
routes, and pointer overflow. Six native fixture tests pass and the new source
compiles with MinGW C11 warnings treated as errors. This validates authored
reader behavior against synthetic memory, not game execution.

This supersedes the prior absence of a concrete native reader. The reader is
not yet connected to probe configuration or a live actor-to-action resolver.
A recorder callback may retain the second sample only after return 1, but must
not discard the two-sample semantics when making temporal claims. Return 1 does
not prove atomicity, ownership, producer execution or input freshness. No live
capture, hook installation or game launch was performed.

### Fresh-resolution history recorder adapter

`snow_history_trace_read` matches the recorder's `SnowUpdateHistoryRead` callback.
Its `SnowHistoryTraceContext` contains the exact reader, a caller-supplied actor-
to-action resolver, expected table/evaluator and clock-global slots. It contains
no retained action pointer. The resolver runs before the two-sample read and
again afterward; both must return the same nonzero action with return code 1.
The observation must also have matching identities/settings. Only then does the
adapter copy the second sample into the recorder. Every refusal clears output.

This adapter deliberately discards the first dynamic sample when filling one
recorder boundary. Use `snow_history_observe` directly when both observations
are needed. Neither matching resolver calls nor matching identities provide
lifetime protection, detect ABA, prove active ownership or count inner execution.
The resolver contract must be implemented from fresh chain evidence; returning a
cached pointer would violate it.

A before/after actor record can therefore cost up to 64 memory reads / 2,048
requested bytes for this channel, plus up to four resolver invocations and their
separate read budget. Existing attribution/motion observations add their own
cost. These are bounds, not a measured safe live capture rate.

The native integration fixture runs the real reader through the real recorder
around an authored original callback. It checks four resolver calls, before/after
clock values, late forwarding without observations, changing resolution,
configuration instability and failed reads. Six native fixture tests pass and
the combined fixture cross-compiles for Windows. No live resolver or probe
configuration has been enabled. The previously observed player chain's vector
and directional source types do not by themselves prove that this history-sector
source is active; do not attach this reader to either of those other types.

### Checking record compatibility before copying

Probe ABI v7 now exports `SnowProbe_ABIVersion`, `SnowProbe_RecordSize` and
`SnowProbe_ReadRecordSized(index, output, output_size)`. A dynamic caller should
resolve these symbols, require version `SNOW_PROBE_ABI_VERSION` and record size
`sizeof(SnowUpdateRecord)`, then pass that size on every read. A missing symbol
or mismatch means the caller must rebuild/use the matching DLL, not guess the
layout. These checks do not require capture to be configured.

The sized API checks readiness, close/drain, index and exact buffer size before
copying. Refusal leaves caller storage untouched. The caller remains responsible
for supplying valid writable storage and preserving object lifetime. The legacy
`SnowProbe_ReadRecord` symbol remains for exact-header callers and cannot detect
a falsely sized allocation; new code should use the sized API. The capture plugin
and dynamic Windows fixture now do so.

The shared copy implementation is exercised by the native recorder fixture for
every smaller size, an oversized buffer declaration, invalid index, null output,
and calls before close/drain. A valid read matches the complete stored record.
Six native fixture tests pass. The host, probe and capture plugin cross-compile,
and the new exports are present in the Windows DLL. The dynamic Windows fixture
also compiles, but was not executed under Wine during this pass. No game launch
or shared Wine-session operation was performed.

## Explicit action-evaluator event recorder

`snow_action_trace.h/c` provides authored capture plumbing for a verified
`void evaluator(void *action)` callback. It records action identity, thread ID
and entry/exit ticks around every captured call. It does not read game objects,
install hooks, select an action, or claim that an evaluation consumed new input.
The separate recorder leaves the existing update-record ABI unchanged.

Initialize before publishing the wrapper. Supply bounded, thread-safe clock and
thread callbacks; use a verified common clock domain with the physics recorder
and report its frequency. Route the wrapper through `snow_action_trace_call`.
The original callback always executes, including overflow and calls after close.
Nested original calls can create separate records. Storage reservation order is
not chronological order across threads. Recorded intervals include tracing
cost and preemption, so they are not pure evaluator CPU-time measurements.

Close capture, then wait for `snow_action_trace_drained` before reading through
the exact-size copy function. A closed/drained recorder must still remain alive
for late callers; this does not authorize unloading or restoring/reusing its
storage. Exceptions or nonlocal exits are not contained. Reinitialization while
any caller could retain the wrapper is prohibited.

The native fixture checks nested intervals, zero-capacity forwarding, late
forwarding, close while the original is blocked, exact-size reads and concurrent
reservation/overflow. Windows compilation is checked separately. No live hook
installation or action/physics ordering is established by these fixtures.
Remaining integration needs verified target/calling convention, guarded slot
installation/restoration, selected-player attribution, clock-domain qualification,
and export of evaluator events alongside the update trace.

### Action probe DLL and guarded slot installer

The build script also produces `snow_action_probe.dll`. Its separate experimental
ABI 2 exports configure, install, restore, close, sized record reads, ABI/record
size queries and QPC frequency. Configuration supplies a verified slot address
and original void evaluator. No game offsets or selected action are built in.
Installation accepts an aligned nonexecutable committed image slot only when
its current pointer matches the original and both belong to the same module.
It pins the probe and target modules and permits one install attempt.

Restoration compares against this probe's dispatch pointer, preserves competing
pointers, and restores the recorded page protection. Always attempt restoration
after installation, including failed installation, then close and drain. A
protection failure returns -1 and requires retry/diagnosis. Neither restoration
nor drain permits unloading because a caller may retain a dispatch pointer.
Capture includes every object routed through that class slot; selected-player
attribution must be established separately and renewed across lifecycle changes.

The synthetic Windows fixture passed under Wine in normal and competing-pointer
modes, including actual read-only image-page protection changes, original-call
forwarding, captured records, restoration and late dispatch after close. This is
not a live game hook result. Game signature qualification, class-slot selection,
player attribution, and combined action/update capture remain open. See
[action probe validation](action_probe_validation.json).

### Optional action publication samples

Action-probe ABI 2 extends each event with an attempted flag, independent
before/after validity flags, and `SnowActionSample` values containing four raw
uint32 vector lanes and an active byte. Rebuild direct readers and query both
ABI and record size before copying. Existing unsampled configuration remains
available and leaves the optional fields zero.

`SnowActionProbe_ConfigureObserved` accepts an explicit bounded, non-mutating,
thread-safe reader and context. The portable recorder counterpart is
`snow_action_trace_call_observed`. A return value of exactly 1 accepts a sample;
all other returns clear that sample, including partially written data. Failed
reads never suppress original evaluation. Overflow and closed capture skip
observation while preserving forwarding. Event timestamps enclose both samples
and evaluation, so they include reader overhead.

These are authored recording interfaces. They do not encode a game layout,
resolve a selected player, or guarantee atomic snapshots. A live parent reader
must validate the parent type and explain its source fields. Before/after values
show observed publication state, not the exact store instruction or ingestion
time. Native fixtures cover all four validity combinations and forwarding, and
the Windows DLL fixture checks actual before/after samples through ABI 2.

## Preloaded input trigger gate

`armed_input_gate.cs` provides a bounded ready/trigger handshake for an external
input helper. It sends no input itself. The helper loads first, verifies its
process/window and held-key conditions, then calls `ArmedInputGate.Wait` with
fresh, distinct ready/trigger paths, a timeout of at most 30 seconds, and a target
validation callback. The gate creates the ready file exclusively and keeps
validating while waiting. A stale trigger, expired wait or failed validation
throws before the helper reaches its delivery code. Recheck held keys after
return and retain the existing bounded hold/finally-release logic.

The controller waits for ready before starting recorders. Once recording is
confirmed, it creates the trigger file. The helper then performs its normal
verified delivery and reports QPC timestamps for actual key-down and key-up.
Those reports must pass the delivery-window coverage check; file creation time
is not game acceptance time. Use a fresh session directory for every attempt.
The handshake removes process startup from the capture window, not OS input
latency or scheduling uncertainty.

`tests/fixtures/armed_input_gate_fixture.cs` can be compiled with this source
using a C# compiler and run without input injection. It tests ready-before-release,
fresh-trigger rejection, timeout and target invalidation. The private input
helper's original focus/cleanup self-test is retained separately.

### Input coverage acceptance

`capture_update` requires a `delivery_reports` list whenever `during_capture`
is supplied. Return the two helper `key_delivery` reports in down/up order,
including `key_up`, `scan_raw`, `api_reported_sent`, `qpc_ticks`, and
`qpc_frequency`. Both must report OS acceptance for the same scan code.
Their QPC frequency must match the capture summary. The adapter must supply
reports from the same live session and Windows QPC clock domain; frequency
equality alone cannot establish clock identity.

Both delivery timestamps must fall inside the recorded physics span, and at
least one recorded update must intersect the hold. Missing reports, malformed
timestamps and uncovered pulses fail acceptance even if input delivery reports
success. Passive captures need no input reports. This checks observation coverage,
not continuous sampling or whether the game ingested the input.

Regression against retained private traces rejects the late lateral pulse and
accepts the armed lateral pulse with 56 intersecting update intervals. No new
live test was performed for this controller change.

### Step-result evidence correction

`SnowCounters.step` is the Step job's last-run **request identifier**, not a
monotonic execution count. Paused frames can produce gaps between successive
values. The historical public receipt includes a stable transition from 9806
to 9814; subtracting these values does not count eight executed world steps.

The host checks that the request token changed, stopped changing after rearm,
and the hold is set. Responses now explicitly include
`verification: "request_token_stable_after_rearm"` and
`execution_count_verified: false`. The legacy `exactly_one` fields and error
name remain for protocol compatibility but denote this stability check, not
an independently measured callback count. Historical “exactly one” claims in
this document and receipts should be read with that limitation. Those claims
require callback recording to establish actual execution count. `on_step` and
`steps_released` count accepted host release operations.

The native acceptance fixture tests request gaps, wrap, no change, continued
change and missing hold. The game adapter and capture plugin build with this
clarification. No new live stepping experiment has validated execution count.

Step records also provide `release_begin_qpc`, `rearm_verified_qpc` and
`qpc_frequency`. The first timestamp precedes the release CAS; the second follows
the post-rearm frame wait. They bracket the host operation, not the exact job
entry or completion instruction. Correlate same-session QPC recorder events
and exclude calls crossing the interval boundaries.

A three-release live observation recorded one actor BeforeSimulation callback
in each host interval, followed by complete actor-physics batches of 3, 3 and 2
substeps. Their request-token gaps were 8, 7 and 5. The probes restored/drained
with no drops. The final resume verification failed with `step_not_resumed`,
so this is a partial session, not a passing stepping/recovery acceptance test.
See [receipt](controlled_release_observation.json). Cleanup restored the bottle,
saves, settings and original DLL. The resume failure needs a separate diagnosis.

A diagnostic retry of the same three-release procedure resumed successfully
without fallback. Each release contained one BeforeSimulation callback and
complete physics batches of 2, 7 and 7 substeps. See
[retry receipt](controlled_release_resume_retry.json), which also records elapsed
and derivative intervals. This establishes a successful recorded session but
does not explain the earlier resume failure. Release count alone therefore
cannot specify fixed simulated duration or deterministic replay.

On `step_not_resumed`, the host now reports `frame_wait_succeeded`, the recorded
`baseline_group`, and counter snapshots `before_clear` and `before_fallback`.
`after_wait` is included only when that wait succeeded, avoiding an uninitialized
or failed-read snapshot. These are sequential diagnostic reads, not an atomic
state capture. Recovery behavior was not changed by adding the diagnostics.

The offline update analyzer now reports timing arithmetic for complete direct
ordinal sequences separately from request-based grouping. It records matching
consumed intervals and equality to the recovered accumulator-cap value. Partial
sequences cannot count as matching complete batches. The two saved controlled
release captures contain six complete release batches whose elapsed durations
match float32(consumed/count); two have consumed duration equal to the cap.
See [timing comparison](controlled_release_timing_comparison.json). Matching the
cap value does not prove the cap branch ran. Incoming time, retained accumulator,
history and selected frequency still need same-batch observation.


### Nonfinite player diagnostics

The build-specific adapter rejects nonfinite transform or velocity values after
copying and bracketing the player links. Its error detail now names the first
failing field/lane and the copied IEEE-754 bits, for example
`nonfinite transform[12] bits=7fc01234` (synthetic example). This does not return
a usable player snapshot or relax validation. A lane diagnostic does not identify
the writer or distinguish bad simulation state from an incorrect body layout.
No process address is included in this error detail.
