# Snow mod host (v0.2, command interface and plugin API v1)

Status: first release of the host interface. A persistent DLL is loaded late into
the running game. It exposes guarded pause, world-step and resume operations
through a local command channel, and loads native plugins that run between world
steps ([plugin API v1](#plugins-api-v1)). One live session passed on 2026-10-14 (see below
and the [sanitized validation record](validation.json)). Plugins do not yet have
access to game state; see [Next](#next).

```text
Python client ──TCP 127.0.0.1──▶ io thread ──mailbox──▶ executor thread ──▶ game adapter ──▶ game
                                  (parse only)           (serial, lease timer)  (private, build-specific)
```

## Design

| Piece | Behavior |
|---|---|
| `snow_host.c` | Host core. `DllMain` only records its handle. `SnowHost_Start`, run on its own thread after `LoadLibraryW` returns, starts the io and executor threads once. |
| io thread | Accepts one loopback client at a time and parses requests. It never touches game memory. |
| executor thread | The only caller of the adapter. Commands run serially. It also owns the recovery lease. |
| `snow_adapter.h` | Boundary between the host and the game: identity check, counter read, mode-group compare-and-swap, and the engine's own enter and clear routines. The host core contains no game addresses. |
| `fixture_adapter.c` | SYNTHETIC simulated request loop for testing. It models only stop-mode routing, not the engine. |
| game adapter | Lives in the private research workspace (`analysis/mod-host/private/steep_adapter.c`) because it contains build-specific addresses. It refuses to bind unless the process is `steep.exe` at the analyzed image base and both stop-mode routines match the analyzed bytes. |
| `host_loader.c` | Uses the guards from `../mod_loader/load_probe.c`, then resolves `SnowHost_Start` locally. It verifies the export's entry bytes in the target and runs it with the port as its argument. |

Each operation uses a [validated native mechanism](../../docs/reconstruction/NATIVE_STOP_MODE.md):

- **pause**: Step must be advancing. The host runs the engine's setter (argument 1), then verifies that the group is held and Step is frozen while EndFrame continues.
- **step_world**: Step must be frozen. The host clears the group by compare-and-swap, waits until Step's last-run counter changes, then re-arms immediately. It confirms that only one Step ran over the next four EndFrames. The cross-process version of this method released exactly one Step 35 of 35 times. The in-process version is untested in the game.
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

Error codes: `adapter_unavailable`, `host_faulted`, `not_ordinary`, `step_not_advancing`, `hold_not_verified`, `not_paused_by_host`, `not_held`, `step_not_frozen`, `group_changed`, `rearm_failed`, `step_timeout`, `frames_stalled`, `not_exactly_one`, `owner_changed`, `restore_failed`, `step_not_resumed`, `bad_params`, `read_failed`.

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
| `on_step` | After each released world step: exactly one `Step` ran and the hold is re-armed, so the simulation is held during the call. Receives the batch position and a host-wide step count |
| `on_resume` | After `Step` is verified advancing again. Reason: requested, lease expired, or client disconnected |
| `on_unload` | When a plugin that returned nonzero is disabled cleanly, just before it is unloaded |

The host provides `log` (into `snow_host.log`, tagged with the plugin name),
`config_path` (`plugins\<file>.ini`, which may not exist) and `get_state`
(`host_paused`, `steps_released`).

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

A Wine fixture test with the synthetic adapter covers eight plugins: the example,
a well-behaved counter, a crash on the third step, a 5 s hang, a nonzero return,
a declining `Initialize`, a wrong API version and a DLL with no export. All 32
protocol, recovery and plugin checks pass. During the crash, every one of 10
steps was still exactly one.

**Live result, 2026-10-15.** The example plugin ran inside the game during the
stress plan (`run_late_load.py --experiment host --plan stress`), which runs 300
consecutive steps, 10 pause/5-step/resume cycles, and 60 steps paused mid-ride
at about 100 km/h. All 410 steps were exactly one. The plugin received exactly 435
calls: initialize, 12 `on_pause`, 410 `on_step` and 12 `on_resume`. At every
resume its own count matched the host's, and it stayed active. Resume needed no
fallback restore, and `Step` advanced through the 20 s check.

## Client

`scripts/snow_host_client.py` is both a library and a CLI:

```text
python3 scripts/snow_host_client.py status
python3 scripts/snow_host_client.py step 5        # pause, 5 world steps, resume
python3 scripts/snow_host_client.py pause         # hold until Enter; heartbeats keep the lease
python3 scripts/snow_host_client.py demo --steps 10
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
x86_64-w64-mingw32-gcc -Wall -Wextra -Werror -O2 -municode -o host_loader.exe host_loader.c
```

For the game build, replace `fixture_adapter.c` with the private adapter and add `-I` for this directory.

## Next

1. Game-state access for plugins: validated adapter getters and setters (player transform and velocity first), offered through `SnowHostApiV1` and usable only from `on_step` or while paused.
2. Events: world loaded, player changed, sport changed.
3. Measure what a released step simulates (time delta, substeps, input), and a world-change stress run.
4. Load at launch instead of late load.
