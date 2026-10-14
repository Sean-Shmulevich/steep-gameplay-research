# Native stop mode: a live world-suspension boundary

The engine frame graph routes world `Step` through three branch jobs that read a copied engine mode byte ([frame graph](ENGINE_FRAME_GRAPH_COVERAGE.md)). When the mode is set, `Engine::EngineLoop::UpdateWhileEngineIsPaused` replaces `Step`, and the rest of the frame continues. This pass entered and cleared that mode in the running game and observed the routing change directly.

This is the first experiment in this repository that **writes** to the original process. It is one bounded observation, not a released modding API.

## Method

A guarded helper verified the process identity (pid, creation time, image name and base), then compared the four-byte global mode group against an expected value before writing. It could write nothing else. The group holds, in order, the neighbor flag, mode, companion and request-argument bytes described in [mode writers](ENGINE_MODE_WRITERS.md#global-mode-has-explicit-set-and-clear-transitions).

```text
baseline   00 00 00 01   (mode 0; request argument left at 1 by an earlier native transition)
enter      00 01 01 01   (the byte values the native setter writes)
clear      00 00 00 01   (back to baseline)
```

A read-only sampler, the same one used for earlier passive captures, recorded the mode group, the engine's per-frame copy and the headers of the `Step`, `UpdateWhileEngineIsPaused` and `EndFrame` jobs every 0.3 seconds. Screenshots were taken in each phase. Mode was held for about six seconds, or 165 engine frames.

## Result

[The live record](live_native_stop_mode_validation.json) shows each job carrying two counters: the current request number, and the last request in which that job executed.

| Phase | `Step` | `UpdateWhileEngineIsPaused` | `EndFrame` |
| --- | --- | --- | --- |
| Baseline | executes every frame | never executed | every frame |
| Held | last-run frozen | executes every frame | every frame |
| Resumed | executes every frame | last-run frozen | every frame |

During the hold, the engine copied the new mode into its per-frame owner copy at its next `BeginEngineFrame`/`PreActionStep` refresh. `Step` stopped executing on the next request. `UpdateWhileEngineIsPaused` executed on every request, and the frame loop, rendering and HUD continued at the same rate. The camera moved in towards the rider while held and returned after clear, so camera work continues on the paused path. After the clear, `Step` resumed on the next request and the process continued normally until the session's deliberate stop.

This confirms at runtime:

- the three branch jobs select `UpdateWhileEngineIsPaused` exactly when the copied mode is nonzero;
- world stepping can be suspended and resumed without stopping the frame loop or any worker thread;
- the routing reacts within one request of the mode changing.

## Boundaries

- The native setter also calls a mode-transition notification, and the native clear performs world and service transition work. This test reproduced neither. Their effects (camera mode, audio, input, online state) are not accounted for, and the camera change may come from the notification being absent rather than from the paused path itself.
- The write was a plain cross-process store at an arbitrary point in the frame. The engine's own writers also use plain stores, but their caller synchronization is not proved. A safe trigger should write between frames, for example from an `EndFrame`-ordered hook.
- One six-second hold in one session. Long holds, repeated toggles, saving, loading, sport changes and online play were not tested.
- Off-graph work (loading thread, idle task workers, async services) is not suspended by this mode.

## Toward pause and single-step

A native pause can now be expressed as "set mode, keep frames running, clear mode". A single step is "clear mode for exactly one request, then set it again". Because the routing samples the copied mode at fixed frame stages, a toggle made between `EndFrame` and the next `BeginEngineFrame` should affect exactly one request. That is the next experiment. Reproducing or deliberately invoking the native notification and clear side effects is required before calling this a release-quality mod hook.
