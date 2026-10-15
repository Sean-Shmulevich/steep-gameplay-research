# The selected player's actor is in the `BeforeSimulation` motion batch

This closes the static/live **membership** part of release gate 3 ([scheduler roadmap](../../engine/SCHEDULER_ROADMAP.md)) for one gameplay state. The selected player's snowboard actor is a receiver of `Physic::BeforeSimulation`, whose callback dispatches receiver table slot `0x270`. For this actor that slot is the already-traced player update that reaches action ingestion. The candidate batch named in the [input audit](SCHEDULER_INPUT_AUDIT.md#focused-follow-up-one-motion-batch-is-upstream-of-world-simulation), `Physic::PreBeforeSimulation`, was empty and had never been allocated.

Request association, callback execution and input freshness remain open. Addresses below are image RVAs (preferred base `0x140000000`) for the analyzed image SHA-256 `32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`. Runtime pointers stay private.

## Static joins

All four facts below are checked as exact instruction bytes by the private capture before any live read.

| Fact | Evidence |
| --- | --- |
| Generic motion thunk | `0x8b9750`: `mov rax,[rcx]; jmp [rax+0x270]`. Each receiver's own table slot `0x270` is called. |
| `Physic::PreBeforeSimulation` | Job at action graph `+0x4ad8`; setup `0x907d4e` stores the thunk at `+0x4c98` (job `+0x1c0`). Gather `0x8be137` copies world registry entry 24 (`world+0x730`) into `graph+0x4c70` (job `+0x198`), append off. |
| `Physic::BeforeSimulation` | Job at `+0x4ca0`; the same setup stores the thunk (callee-saved `rbx`) at `+0x4e60` at `0x907e37`. Gather `0x8be150` copies entry 25 (`world+0x770`) into `graph+0x4e38`. |
| `Ai::UpdateAIPreUpdate` | Setup `0x905834` stores the thunk at `graph+0x1ca0` (job `+0x1ae0`). Builder `0x9119c0`, an inlined lock-and-copy, fills `graph+0x1c78` from entry 5 (`world+0x270`, count `+0x278`, lock `+0x280`) and another job from entry 4. |

Registry entries begin at `world+0x130` with stride `0x40` (pointer, signed count, tagged capacity), as in the [membership follow-up](SCHEDULER_MEMBERSHIP_FOLLOWUP.md). All three jobs carry the shared range-job table `0x1ec7f38` live. A constructor at `0x8b0d5c` that installs `0x1e92e70` at offset `0x4ad8` builds a different object; the live value settled this.

The input audit's setup already registers `PreBeforeSimulation -> BeforeSimulation -> PhysicsWorldStep`. Run5/run37 private evidence binds the player's slot `0x270` to `0x564ee0`, which passes the actor's motion object (`actor+0x1010`) to `0x5654c0` and on to action ingestion `0x541da0`.

## Live result

A bounded Highball/D3DMetal session reached gameplay through startup navigation, acquired the player freshly, then made two guarded passes. There were no gameplay inputs, memory writes or debugger. The [sanitized receipt](live_motion_membership_validation.json) records the outputs and hashes of the private result and acquisition.

| Batch (registry entry) | Source count | Storage capacity | Remaining | Player receivers |
| --- | --- | --- | --- | --- |
| `Physic::PreBeforeSimulation` (24) | 0 | 0 | 0 | none |
| `Ai::UpdateAIPreUpdate` (5) | 1 | 1 | 0 | index 0: owned component, table `0x1e789b8`, slot `0x270` -> `0x67ceb0` |
| `Physic::BeforeSimulation` (25) | 5 | 5 | 0 | index 2: **the acquired actor pointer**, table `0x1e7a350`, slot `0x270` -> `0x564ee0`, storage index 2; index 1: owned component, table `0x1ee5a40` |

Both passes matched. The actor match is pointer equality with the acquisition's actor, whose table and `actor+0x10 == entity` link the acquisition already guards. The animation Kino membership reproduced at source and storage index 3 of 4.

A registry scan of entries 0–31 found the entity pointer itself in none of them. Components owned by the entity (qword at receiver `+0x10`) appear in entries 4, 5, 8, 12, 13, 15, 16, 17, 19, 23, 25 and 30. The registries hold components, not entities. The owner offset is proven for `KinoComponent` and confirmed for the actor; for other receiver layouts it is an assumption, so the scan names it as such.

Earlier sessions in the same series show the guards working: one stopped at a wrong job-table expectation before reporting anything, and one found PreBeforeSimulation unallocated.

## Per-request submission (passive burst)

Burst sampling of both jobs' headers (287 accepted samples over ten roughly 24 ms bursts, read-only) showed `BeforeSimulation` and `Ai::UpdateAIPreUpdate` requested and started together. That happened about every 12 ms, with identical counters in 283 samples. The request-to-start window was visible with one dependency hold (21 samples). One sample caught the AI batch started with one unclaimed receiver while `BeforeSimulation` was still held. Execution counters and the `BeforeSimulation` claim count were always zero: claiming finished faster than the sampling could catch.

## Execution: entry probe

With explicit approval, a private Snow-host plugin replaced **one heap pointer** by compare-and-swap. That pointer is `BeforeSimulation`'s installed callback field, which held the motion thunk. The plugin pointed it at a recording thunk that saves the argument registers, records the entry, restores the registers and tail-jumps into the original thunk unchanged. No game code or tables were modified. The field held the expected thunk and the job held the range table before install, and the plugin compare-and-swapped the field back after a 10 s window. Exit is not recorded, because the callee's full signature is not known. A synthetic Wine test (four threads, forwarded arguments checked) passed before the live run.

| Measure (10 s live window) | Result |
| --- | --- |
| Install / restore | installed, restored, 0 records dropped; game continued, session closed normally |
| Selected actor entries | 1,009, exactly one per `BeforeSimulation` request (1,009 distinct request counts) |
| Job state at actor entry | started equal to requested in 1,009 of 1,009 |
| Relation to world `Step` | request count minus Step last-run count constant across all entries: one request per Step |
| Relation to `EndFrame` | Step last-run exactly one ahead of EndFrame at every entry: within the Step frame |
| Threads, cadence | 10 distinct worker threads; median 9.87 ms between actor entries (p10 9.02, p90 10.81) |
| Other receivers | 4,036 entries: the batch's other four receivers, once per request |

Two further 10 s windows replicated this. One was standing: 948 of 948 actor entries, exactly once per request. In the other, forward was held through chained 1.5 s holds for part of the window: 1,002 of 1,002. Game acceptance of that input is unverified. The batch's other receivers rose from exactly 4 to about 4.84 per request during the hold, so membership changed, yet the actor still entered exactly once per request. Over all three windows: 2,959 of 2,959.

This joins membership to execution: in this gameplay state, the selected actor's slot-`0x270` route into action ingestion is entered once in every world request, on worker threads, inside that request's Step frame. Its order against `PhysicsWorldStep` rests on the registered dependency, not on a measured exit. The probe is a research tool with build-specific addresses and is not published.

## What this establishes and what it does not

Established for this state:

- the selected player's actor, by exact pointer, is in entry 25 and in `BeforeSimulation`'s gathered storage at the same index;
- that batch's installed callback dispatches slot `0x270`, which is the traced player update that reaches action ingestion;
- the earlier candidate `PreBeforeSimulation` carried no receivers this session.

Not established:

- (now shown by the entry probe) per-request invocation of the actor's callback;
- the measured order of that invocation against `PhysicsWorldStep`'s body (entry only, no exit or world-step counter);
- that the actor's gates (activity, controller, actor `+0x1fd` skip) passed inside the call;
- riding or other gameplay states: the player had just spawned and no input was sent;
- input freshness: who writes the action payload and when it is published.

`callback_execution_established`, `input_freshness_established` and `safe_to_step_established` remain false in every output.

## Reader and validation

[`engine/motion_membership_observation.py`](../../engine/motion_membership_observation.py) provides:

- `capture_motion_membership(readv, entity, world, image_base, guards, job=..., entry=..., actor=None)` for the three named batches. It checks the job table and the installed thunk, then reports per receiver whether it is the entity or the supplied actor, whether it is owned by the entity, its table and slot-`0x270` RVAs, and its storage and unclaimed indices.
- `scan_registry(readv, entity, world, guards, entries=32, image_base=None)`, which reports where the entity and its owned components appear. Implausible headers are marked invalid rather than followed.

Both bound counts (256 source receivers, 1024 storage slots), recheck every followed header and identity field, and never dereference destination storage values. Thirteen synthetic tests cover the three batches, actor and owned matches, unclaimed prefixes, empty sources with stale storage, tables outside the image, identity-check failures, malformed headers, replaced sources and short transports.

## Next

1. Measure order against `PhysicsWorldStep` (record the world-step job's start in the same window, or add a safe exit record).
2. Repeat the membership and entry measurements during riding.
3. Continue the separate freshness work on the action payload writer.
