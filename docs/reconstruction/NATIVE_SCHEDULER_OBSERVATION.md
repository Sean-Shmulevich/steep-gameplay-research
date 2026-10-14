# First live observation of the selected world's action graph

The guarded collector successfully followed a freshly acquired player/world relationship to the world's action graph in a running Highball session. Both world/graph links and the seven expected job tables matched. Three independent acquisitions succeeded. This closes the practical address-resolution question for this session; it does not establish a safe pause boundary or player membership in the animation receiver array.

The [aggregate receipt](native_scheduler_observation_validation.json) contains counts, timing summaries, counter observations and hashes of the private results. Raw process addresses, memory reads and screenshots remain private.

## Observations

The established D3DMetal configuration reached the gameplay HUD. Startup navigation sent title, offline-notice and map-screen controls. The capture sent no riding controls, performed no game memory writes and attached no debugger.

- 44 ordinary sweeps decoded seven jobs each.
- Ten bounded burst requests produced 283 complete, guard-matched groups over 398.5068 ms.
- 102 individual read records from incomplete groups were excluded from interpretation. These were partial records, not 102 additional complete samples.
- Burst requests ended at their time or group limits. The retained partial records contained no read-error values.
- All seven jobs showed changing started/requested counts. Across the burst, each job's first and last requested values were 12751 and 12782. These are request observations, not a measured frame count or frame rate.
- Holds varied between zero and one for six jobs, and between zero and two for `ActionGatherComponents`.
- Every sampled execution count, outstanding-dispatch count and lifecycle state was zero. `AnimationUpdateTime` also had zero remaining claims at every sampled read.

The first ordinary pair additionally observed `UpdatePreActionGather.started` advance from 4971 to 4972 while its hold count changed from one to zero. These sequential reads support changing live state, not a simultaneous causal trace.

## What polling did not resolve

Median burst group duration was 0.6156 ms; maximum duration was 5.9475 ms. Median start-to-start spacing was 0.6237 ms, with a maximum gap of 42.7616 ms between groups. Each group reads several guarded fields sequentially. Reversing field order on alternate groups reduces one systematic ordering bias but does not make the snapshot atomic.

The consistently zero execution counters do not prove the game was idle. Short worker activity could fit between the relevant reads. An immediate-completion or different dispatch path could also produce observations that the current model does not yet explain. The capture does not distinguish these possibilities. In particular, a changing request counter does not prove that animation callbacks ran, and zero remaining claims does not prove their completion.

The subsequent [begin-path audit](SCHEDULER_BEGIN_PATHS.md) narrows this: empty ranges can complete without dispatch, but the three matched callback jobs have an always-false empty predicate and queue on their ordinary begin path. Empty populations therefore cannot explain all seven jobs' zero samples through a common immediate-completion shortcut.

The action gather's observed hold range is consistent with the recovered converging dependency topology. It is not proof that its two holds came from the two named branches in any particular read; other dependencies and changing fields remain possible.

## Next discriminating checks

1. Read the animation registry and gathered-array headers with ownership guards, then join the selected player's Kino component to the source population. This tests whether the animation range was populated for this world rather than inferring membership from graph identity.
2. Inspect the concrete begin/empty/body paths for these live-matched job tables. Identify whether a configured route can advance request counters without entering the accounted worker wrapper.
3. If the accounted worker path is selected, use matched entry/exit instrumentation or a narrower counter capture to seek the short execution interval. Retain loss accounting and per-thread ordering. More zero samples alone cannot establish non-execution.
4. Join the verified live graph to the ordinary frame rearm path before designing submission exclusion. Do not write a pause flag merely because local job counts are zero.

The four-minute watchdog stopped the game at its time limit, restored configuration and left no Wine/game/debugger processes running. This experiment validated the observation path in one session. Repeated pause, one-update release, clock control and deterministic replay remain unimplemented for the original game.
