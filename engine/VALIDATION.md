# Reconstruction validation scope

The automated suite covers synthetic fixtures, recovered local numerical kernels and the independent runtime's contracts. It does not establish original-game equivalence. Run `python3 -m unittest discover -s tests -q` from the repository root; HTTP tests require permission to bind loopback.

Current checkpoint: 440 tests passed. Repository packaging, source hashes and local links passed verification; the inspector JavaScript passed syntax checking. The new private-scene browser rendering has not yet been visually validated.

## Private archive checks

The read-only adapter parsed 27 locally available archives containing 165,021 index entries. A selection of 54 resources was decoded in memory with checksum and output-length checks, exercising both Zstandard and LZO paths. No decoded payload is included here. This establishes compatibility with those indexes and samples, not comprehensive decoding of every resource or every archive version.

The parser supports the observed version-27 index and observed compression-layout/type combinations. It rejects malformed bounds, duplicate resource identifiers, inconsistent lengths and unsupported framing. Native codecs are optional adapters to installed libraries. Synthetic tests cover corruption and boundary failures without reproducing game data.

## Private animation checks

The typed adapter was compared against the existing local pose-assembly reference for 100 poses: ten clips, two base rigs and five sample times. Both rigs were deliberately evaluated; this does not prove which rig or clip the game selects in a particular state. Translation scale was explicitly 1 in authored units.

- Maximum translation difference: `7.027413480595403e-08` authored units.
- Maximum sign-invariant quaternion component distance: `0.0006016519442461972`.

The largest quaternion difference occurs at a near-identical-rotation branch. The newer recovered float32 dot product reaches the copy-source threshold while the older host-double reference interpolates. These references are therefore not bit-identical; the discrepancy is retained rather than hidden by a broad tolerance. Live pose agreement remains unverified.

An imported private base rig and navigation clip also completed a 120-tick engine run without a recorded incident. This proves the adapter-to-runtime path for that resource, not correct gameplay selection, world scale, root motion, addon assembly or visual fidelity. The imported scene remains outside the public source repository.

## Determinism and boundaries

Checkpoint/replay tests include graph clocks and configuration changes. Resource replacement and tuning establish a fresh replay base. Exact hash equality is a same-runtime property; it is not a claim of cross-platform numerical determinism or deterministic replay inside the original game.

Original clip payloads, decoded skeleton arrays, private scenes and raw observation receipts are deliberately absent from this repository. Public tests use invented transforms and clips. Active rig merging, authored graph identity, root-motion ownership and actor-to-pose timing remain open reconstruction tasks.

## Scheduler pass

Recovered smoothing and constructor initialization have boundary tests for history wrap/reset, raw-versus-capped intervals, policy overrides, float32 thresholds and checkpoint continuation. The dependency executor tests delayed claims, retained callback identity, failure-blocked dependencies, safe replacement and quiescent restoration. Those executor lifecycle rules are designed behavior.

The scripted scheduler experiment completed 171 frames and 280 substeps with exact replay agreement and all 1,636 trace records retained. A separate five-sport run completed 3,600 ticks per sport with matching replay hashes and zero recorded incidents. Its default bounded traces may overflow; those stress results validate state replay, not complete trace retention.

Static verification and newly closed conditional ordering are documented in the linked scheduler audits. No original game was launched or controlled in this pass. The original action writer, current membership/request join and submission-exclusion protocol remain open.

A further history-continuation stress check ran 2,000 synthetic frames for each of policies 0, 1 and 2. It checked step accounting, elapsed/derivative separation, ring bounds and exact continuation from the midpoint checkpoint. All 6,000 frames passed, including epsilon, single-step, floor, round-up and retained-remainder branches. This is invariant checking, not comparison to native execution.

The owned pause controller passed 11 tests covering token validity, serialized competing submissions, failure rollback, fixed-tick versus planned-frame stepping, checkpoint continuation and replay. A separate 200-frame check advanced 300 substeps while remaining paused between requests, rejected an old token after restore and recorded no trace drops. The membership helper has six tests preserving the recovered empty-source retention behavior. Native submission exclusion and player membership remain unverified.

The next static pass added six action-publication kernel tests and four range-claim tests. They cover cancellation, nonunit diagonal samples, four-lane magnitude, strict activation/small-vector thresholds, explicit reciprocal seeds, reverse tail visitation and claim-versus-completion distinction. Source-backed audit documents close selected construction, map, batch-consumption and normal queued-callback edges. No native stepping, global barrier or device-to-substep freshness was established.

Five default-processor tests verify four-lane pass-through, signed zero, marker handling, copied state and rejected nonfinite inputs. Four composed-pipeline tests distinguish fallback, bypass and supplied configured output, retaining nonunit diagonal samples. These tests establish the inspected local paths only; they do not select the player's runtime binding or prove device update timing.

Static follow-ups connect the backend consumer's descriptor/wrapper registration and the ordinary scheduler's reservation-to-finalization path. They identify the action graph's conditional entry and terminal nodes but do not prove next-request exclusion. The engine test count is not evidence for those native execution relationships; consult their separate source-backed audit scope.

Fourteen request-state tests now cover activation/release, two-predecessor joins, credit deferral and wakeup, alias rejection, rollback and JSON continuation. The full suite passed 278 tests. Static audits resolve alternate-route propagation and the action graph's outer Step integration; no live engine-loop exclusion test was performed.

Ten alternate-propagation tests preserve branch-specific callbacks, after-traversal clearing, current-hold rechecks and order-sensitive reconvergence. The full 288-test suite passed. EndFrame, root-route and event findings are separately bounded static evidence; these tests do not constitute a native frame trace or pause/resume test.

Fourteen mixed-scheduler tests combine normal and alternate release with four job kinds, delayed claims, callback reservation, credits and repeated root submission. Malformed numeric token fields are rejected before mutation. Full suite: 302 passing tests. The three-cycle probe executes motion in cycles one and three, skips it in cycle two, and records two next-root submissions while EndFrame still has executions=1 and outstanding=1. Two complete reports matched exactly, with 189 trace records and zero drops. This demonstrates the independent serial model, not native concurrency or gameplay parity.

The gameplay integration adds twelve tests covering actual phase dispatch, exact direct/mixed state parity across all five sports, rigid contact with graph animation, checkpoint/replay, controller ownership after restore, trace overflow and late-substep rollback. The full suite passed 314 tests. The runnable gameplay probe completed 12 outer frames and 28 substeps, with 28 reservations for each of the five phases, 28 ready terminals, 2,288 retained trace events, no drops and no incidents. Direct state/events, checkpoint continuation and replay matched. The graph is an owned design, not recovered native phase wiring.

Nine trace-analysis tests and one HTTP test bring the suite to 323 passing tests. They cover direct/mixed evidence, outer-frame rollback, missing endings, overflow, malformed identifiers and contradictory phase order. The HTTP endpoint preserves both state and raw trace. A complete analysis can describe an aborted execution; completeness is not success.

Eight queue-policy tests cover signed overflow and division, ordering, affinity, job-specific eligibility, enqueue sentinel resolution and read-only inspection. The synthetic queue probe selects local category zero, shared category zero, then local category one, while incompatible shared work remains scheduled. Full suite: 332 passing tests. These checks validate the independent serial model; they do not establish native concurrent scheduling or safe process control.

Six queue-producer tests bring the suite to 338. They validate pure arithmetic and routing boundaries, including absent versus null worker slots. No threads are allocated and no original scheduler execution is claimed.

Five explicit-worker topology tests bring the suite to 348. The 100-receiver probe holds one range while another worker completes the remainder, and verifies successor release waits for the held dispatch. This models serially chosen interleavings with worker identity; it does not test OS thread races.
