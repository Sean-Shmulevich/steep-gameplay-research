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

## Single-step

A later session held stop mode and released single world steps from inside one helper process:

```text
single_step(engine):
    assert mode group is held
    before = Step.last_run
    clear mode group
    spin until Step.last_run != before     # this request has already passed every routing branch
    restore held mode group                 # the next request sees the held mode at every branch
    confirm Step.last_run is unchanged after >= 120 ms
```

Setting the mode again as soon as `Step` starts is safe for routing. By then the current request has already read the global mode at `CheckEngineStop` and the copied mode at both owner branches, and the next request has not yet started.

[The live record](live_native_single_step_validation.json) covers 35 steps: 5 spaced about 0.4 s apart, then 30 in quick succession. **Every one released exactly one `Step` execution.** Re-arming took 2.7–11.9 ms after the clear. `Step` then stayed frozen for the following 11–45 requests, while `UpdateWhileEngineIsPaused` executed on each of them. Clearing the mode afterwards resumed `Step` on every request.

This is a working native pause and single-step at **engine-request granularity**, with rendering alive throughout. It does not control simulation substeps inside a request, input delivered during the hold, or the native transition side effects noted above.

### Visual artefact on each step

A person watching the game window during the single-step session reported a brief glitched overlay of the image on every released step. The screenshot capture (about one second per frame) was too slow to record it. Two explanations fit what is known, and neither is confirmed:

- **Camera switch.** While held, the paused path shows a different, closer camera. A released request runs `Step`, which may update the gameplay camera for that one frame before the paused camera resumes.
- **Temporal reconstruction.** Anti-aliasing history, motion vectors or motion blur may blend the previous image after a sudden jump in world and camera state.

Telling these apart needs frame-accurate capture around a release, and reproducing the native mode-transition notification, which may also control the camera mode.

## Entering and leaving through the engine's own routines

[A later session](live_native_routines_stop_mode_validation.json) entered stop mode by running the engine's compact setter (request argument 1) and left it by running the native clear routine, each once on a new thread in the game process. Both completed. The mode group changed exactly as with the byte-level writes, and the same jobs froze and resumed. The process continued normally.

A window recording at about 33 fps showed that entering stop mode **cuts in a single frame** from the gameplay camera to a closer pause camera, which also hides the waypoint marker. Leaving cuts back in a single frame. Frames during the hold were nearly static. The native path produced the same pause view as the byte-level enter, so the camera change belongs to the engine's pause path rather than to the skipped notification.

This also offers the most likely explanation for the per-step artefact below. While held, `UpdateCamera` is frozen and the pause camera is shown. A released step runs the camera job once, which plausibly renders one gameplay-camera frame before the pause camera returns. This has not yet been recorded during stepping.

## What stop mode suspends

[A survey of every embedded engine job](live_stop_mode_job_survey_validation.json) sampled each job's last-run and current-request counters in baseline, held and resumed phases. While held, `CheckEngineStop` takes its bypass, so the whole simulation half of the frame stops, not just `Step`.

- **Still running every request:** `BeginFrame`, the graphics chain (`BeginGraphicFrame`, `GraphicFrame`, `EndGraphicFrame`), `BeginEngineFrame`, `UpdateWhileEngineIsPaused`, `EndEngineFrame`, the finish fanout and `EndFrame`.
- **Frozen:** universe component updates, domino, pre-action/pre-step, `Step` and the world chain, `UpdateCamera`, `UpdatePadManager`, cinematics, every sound job, network pre/post update, action and accomplishment managers, loading advisor and the menus-and-sounds group.

Because `UpdateCamera` is frozen, the camera change seen while held must come from `UpdateWhileEngineIsPaused` or the graphics side, not from the gameplay camera job. Input polling and sound updates are suspended for the duration of a hold.

## What a released step simulates

This section is static analysis plus instruction emulation of the original timing routines; it has not yet been measured live.

- `BeginFrame` runs the frame-clock driver every request, held or not. The driver measures the timer delta since its previous call and caps it at one second. The clock updater overwrites the interval rather than accumulating it.
- `BeginEngineFrame` runs the physics timing producer every request. It caps the world interval at 1/15 s and computes a substep count (`n = floor(f * dt)`, rounded up at a half, at most 7) and substep length. Only the physics world step inside `Step` consumes them.
- So a released step simulates **about one frame, typically 1–2 substeps**, not the whole hold. Emulation of a 5 s hold at 60 Hz followed by one release produced two 8.3 ms substeps.
- **Exception:** the world's accumulated millisecond timestamp keeps advancing through the hold. Logic that measures "time since" an event sees the whole hold as one jump on release.
- **Input:** the pad manager is wired only inside the Step chain. On release it swaps snapshots and polls once. A button held across the release probably reads as a new press, and a press and release entirely inside a hold is lost (inferred).
- No world-clock hold was found on the paused or clear paths within a bounded search. Protected callees, including the setter notification, keep this at medium-high confidence.

A live check should sample the physics scheduler's substep count and length, its step counter, the world clock's interval and total, and the frame driver, across about 20 held requests, one release and 20 more held requests.

## Remaining release work

- Reproduce or invoke the native setter notification and clear-side transitions, and determine whether the camera change comes from their absence.
- Measure what a released request simulates: elapsed time after a long hold (see the [clock cap](CLOCK_TREE.md)), substep count and input freshness.
- Repeat under movement, airtime, sport changes, saves and long holds.
- Move the toggle in-process (an `EndFrame`-ordered hook) so stepping does not rely on cross-process polling.
