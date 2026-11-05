# Physics substep order (Phase 1 map)

Status: static map plus existing receipts, 2026-11-05. No game was launched for this
pass and no protected thunk (anything at or above `0x143000000`, or the lock helpers that
jump into that range) was emulated or traced. Machine-readable copy:
[physics_substep_order.json](physics_substep_order.json).

This page orders everything known to run inside one physics substep of the player's
world, and marks each stage **reconstructed** (engine module plus receipt), **supplied**
(a known call that existing modules take as an explicit service) or **unknown**. RVAs are
evidence anchors for the analysed build only. Reconstructed module names are our design
names, not original engine names.

Evidence classes used in every row:

- **S**: static read of the image (this pass or an earlier cited section).
- **N**: native receipt, offline instruction emulation in the private harness.
- **L**: live receipt from a bounded capture in the running game.
- **I**: inference. Stated as such; not a measurement.

New static facts established in this pass (class S, not yet covered by any receipt):

1. The solver half of the substep has a unique direct-call chain:
   `1389a50` → `140efa0` → `18ae2c0` → `18b9710` → `18e2fb0` → (dispatcher `18b7ca0`) →
   `18e3340` → `18e31b0` → `1994da0` → `1993ed0` → `19574f0`. A rel32 scan finds exactly
   one caller for each of `140efa0`, `18ae2c0`, `18b9710`, `18e2fb0`, `1994da0` and `1993ed0`.
2. `18ae2c0` is the island-step thunk. After `18b9710` it calls `18b74e0` with the island's
   two body lists (`+0x480/+0x488`, `+0x470/+0x478`) and then `18e1990`, which zeroes both counts.
3. World settings live at `world+0x08` (getter `12af2d0`, world = `controller+0x20`). Default
   constructor `19414b0` writes gravity `(0, 0, -10)`. World creation `13d1bd0`, right after
   the controller factory, sets gravity to `(0, 0, -9.81)` (constant at RVA `0x1f28140`),
   byte `+0x21 = 1`, mode `+0x24 = 1` and secondary iterations `+0x2a = 4`. Normal iterations
   stay at the default 8.
4. The second per-substep actor batch `13c08f0` calls actor slot `+0x2c8`. For
   `PlayerSnowboardComponent` (vtable `0x1e7a350`) that is `0x53d7f0`. The first batch's
   slot `+0x2c0` is the documented snow wrapper `0x53ec30`.
5. `140b3d0` (after the island step) walks a listener map at `manager+0x18`. For each
   listener it gathers records from its body's link ring (`14070f0` → `18a88a0` → `18babf0` →
   `195c380`) and calls listener slot `+0x10` once per 16-byte record.
6. Inside the loop, the pair update, island step and listener dispatch sit inside a bracket on
   global `0x1433125e0`, made from protected helpers `1c3a2b0`, `1c388a0`, `1c3d1e0` and `1c3d1c0`.
   Their semantics were not examined.

## 1. Ordered call sequence

### 1.1 Frame level (once per engine request)

| # | Stage | RVA(s) | Evidence | Module | Receipt | Status |
|---|---|---|---|---|---|---|
| F1 | `Physic::PreBeforeSimulation`, then `Physic::BeforeSimulation` receivers. The player's slot `0x270` = `0x564ee0`: motion update, input ingestion, state dispatch, conditional `queue_pending_impulse` | `0x564ee0`; route in [CENTRAL_IMPULSE](CENTRAL_IMPULSE.md#producer-route-reaches-beforesimulation) | L (the receiver returned before PhysicsWorldStep in 701 of 701 requests), S, N | `engine/snow_batch.py` (gather only); impulse route model | [live membership](live_motion_membership_validation.json), [impulse route](../../native/snow_host/impulse_route_validation.json) | partly reconstructed (route and producer gates; not the whole motion update) |
| F2 | Physics timing producer (in `BeginEngineFrame`): substep count `timing+0x1390`, elapsed substep `+0x1394`, consumed outer interval `+0x136c` | see [scheduler clocks](research/scheduler.md#preserve-three-different-clocks) | S, N, L (selected counts 1, 2, 3 and 8 observed, then 1–5 in the settings session (8 not seen there); float32 subdivision matched 176 of 177 groups) | testbench subdivision model | [direct substeps](../../native/snow_host/direct_substep_live_observation.json) | reconstructed (arithmetic); live bound not fixed |
| F3 | `PhysicsWorldStep` job (callback `0x8ab390`, delegate `0x1389a50` stored by `136a550`) | `136a550`, `1389a50` | S for the store. L: the outer-loop return `0x141389ad8` was verified in every frame read | — | [direct substeps](../../native/snow_host/direct_substep_live_observation.json) | job-to-delegate binding statically unverified; the loop is live-confirmed |
| F4 | After the world step: `AfterPhysicSimulationUpdate` (`0x1371bd8`) and `...CharacterWrapup` (`0x13c0b40`). Cache swap and velocity publication to the actor | see [scheduler flow](research/scheduler.md#established-producerconsumer-flow) | S, L (membership) | — | — | outside the substep; partly mapped |

`PhysicsTerrainUpdate` (`0x13c8bc0`) and `PhysicsPropsUpdate` (`0x13c9950`) are stored by
the same constructor. Their order relative to `PhysicsWorldStep` is not established here.

### 1.2 World step body `1389a50` and the substep loop

```text
1389a50(timing):                      # timing = job record; manager = [timing]
    if profiling == 2: open scope "Physic::UpdateBroadphase"
    1365890([manager+8]+0x7b0, byte)  # pre-loop world service, unknown
    i = 0
    while i < u32 [timing+0x1390]:    # reread every iteration
        13c30c0(manager, elapsed=[+0x1394], consumed=[+0x136c])  # actor batch 1
        1c3a2b0(G); 75e600(0); 1c388a0(G)      # protected bracket, G = 0x1433125e0
        140b1a0([manager]) -> 18ae2b0 -> 18b8fa0(controller)     # pair update
        1c3d1e0(G)
        140efa0([manager], elapsed) -> 18ae2c0(controller, dt)   # island step
        140b3d0([manager])                                       # listener dispatch
        75e600(); 1c3d1c0(G)
        13c08f0(manager, elapsed)                                # actor batch 2
        i += 1
    [manager+0x20] += 1               # outer completion counter, also when count is 0
```

The `dt` passed to the island step is the elapsed substep interval (`timing+0x1394`). The
consumed outer interval goes only to actor batch 1. The substep count has no universal
bound: live captures saw 1, 2, 3 and 8.

### 1.3 Stages inside one substep

| # | Stage | RVA(s) | Evidence | Module | Receipt | Status |
|---|---|---|---|---|---|---|
| A1 | Actor batch 1: gathers tag-0 and tag-2 registrations; chunk = max(n/20, 1); submit and wait. Tag 0 calls actor slot `+0x2c0(elapsed, consumed)`; tag 2 is a no-op | `13c30c0`, callable `13cd590` | S, N, L (270 of 270 player calls attributed to the loop) | `engine/snow_batch.py` | [gather](../../native/snow_host/snow_gather_validation.json), [frame](../../native/snow_host/batch_frame_validation.json), [direct substeps](../../native/snow_host/direct_substep_live_observation.json) | reconstructed (gather, frame); wait and claim are supplied |
| A2 | Player snow wrapper (`PlayerSnowboardComponent` slot `+0x2c0` = `0x53ec30`): gates, then prepare, shared snow update, finish. Snow forces enter here (section 2) | `0x53ec30` | S, N (64-case wrapper) | snow modules (see section 2) | [wrapper](../../native/snow_host/consumer_wrapper_validation.json) | wrapper reconstructed; the full snow update is only partly reconstructed |
| A3 | Lock bracket on `0x1433125e0` | `1c3a2b0`, `1c388a0` | S | — | — | unknown (protected; do not emulate) |
| B1 | Pair update: phase `controller+0x48 = 1`; broadphase update slot `+0x90` (`199c880`) | `18b8fa0`, `19598b0`, `199c880` | S, N, L | `engine/pose_pair_update_step.py`, `engine/pose_broadphase_pair_lists.py` | [step](../../native/snow_host/pose_pair_update_step_validation.json), [live](../../native/snow_host/pose_pair_update_live_validation.json) | reconstructed; `199c880` (tree and overlap update) supplied |
| B2 | Removed-pair selection and connectivity rebuild | `18dedf0`, `18e28d0` | N, L (byte for byte on 64 live steps) | `engine/pose_pair_update_step.py` plus the select and rebuild modules | [live](../../native/snow_host/pose_pair_update_live_validation.json) | reconstructed and live-validated |
| B3 | Pair jobs: retire, neighbor retire, rebalance, dispatch (capacity 1 live), worker, merges | `18ddc40`, `18de440`, `18de510`, `1989e60`, `18b7ca0`, `18ddd30`, `18df4e0`, `18df630` | N; L (structural only) | `engine/pose_pair_link_jobs.py`, `engine/pose_pair_link_worker.py` | [jobs](../../native/snow_host/pose_pair_link_jobs_validation.json), [worker](../../native/snow_host/pose_pair_link_worker_validation.json), [threads](../../native/snow_host/physics_thread_lock_live_observation.json) | reconstructed; tree inserts `18de6a0`/`18de830` and byte-level live comparison open |
| B4 | Narrow-phase contact generation per pair: shape loop, tester table, terrain wrappers, payload update | `18dd400`, testers, `18e08a0`/`18e0980` → `198f910`, `198fdc0` | N, L (tester census) | `engine/pose_pair_contact_generation.py`, `engine/pose_contact_payload_update.py`, narrow-phase modules | [generation](../../native/snow_host/pose_pair_contact_generation_validation.json), [payload](../../native/snow_host/pose_contact_payload_update_validation.json), [census](../../native/snow_host/narrowphase_tester_census_live.json) | reconstructed (see [LINK_SOLVER](LINK_SOLVER.md#pair-contact-generation) limits) |
| B5 | Broadphase slot `+0x88` (stub); frame counter `+0x4c` += 1; `bp+8` and `provider+0x180` = counter; phase = 2 | `18b8fa0`, `18df490` | S, N | `engine/pose_pair_update_step.py` | [step](../../native/snow_host/pose_pair_update_step_validation.json) | reconstructed |
| B6 | Lock transition | `1c3d1e0` | S | — | — | unknown (protected) |
| C1 | Outer stage entry: phase = 3 | `18b9710` | S, N | `engine/pose_update_stage.py` | [stage](../../native/snow_host/pose_update_stage_validation.json) | reconstructed (order only; subsystems supplied) |
| C2 | Command constraint preparation: computes 1/dt, then prepares two collections, each through `19445c0` (callback writes up to 6 records) | `18b9830`, `19445c0`, `19440c0` | N | `engine/pose_update_stage.py`, `engine/pose_command_prepare.py` | [collections](../../native/snow_host/pose_collection_prepare_validation.json), [command](../../native/snow_host/pose_command_prepare_validation.json) | reconstructed apart from the callback |
| C3 | Action tree walk on `world+0xd0`: for each node object, slot `+8(dt)`, then callback `18b8c90(obj+8)`; nodes in state 2 are removed and destroyed | `1959a70`, `18b8c90`, `11fd350` | S (this pass) | — | — | **unknown**: contents and effects not traced; could write body state before the solve |
| C4 | Stage object at `controller+0x40` (0x1040 bytes, built by `1959fc0`). Begin `195b190` scans world constraints of kind 6 and drains a deferred list at `+0x1030/+0x1038`; `ed2ea0` stores dt at `+0x10`; finish `195c040` → `195b250` | `195b190`, `ed2ea0`, `195c040` | S (this pass) | — | — | **unknown** role |
| C5 | Attach changed links (`provider+0x28/+0x30`): wake, endpoint migration, group merge | `18e2200` | S, partial N | `engine/pose_group_migration.py`, `engine/pose_group_finalize.py` (pieces) | [reactivation](../../native/snow_host/pose_group_reactivation_validation.json) | partly reconstructed; whole routine not natively composed |
| C6 | Publish pending links (`island+0x490/+0x498`) to broadphase slot `+0x98` (passes link+8, or null) | `18b9710` loop | S, N | `engine/pose_update_stage.py` | [stage](../../native/snow_host/pose_update_stage_validation.json) | reconstructed (order); broadphase method supplied |
| C7 | Settings = `world+8`; batch wrapper: partition zero-work groups, sort by work, batches of weight ≥ 25, dispatch on global `0x143336610`, transfer completed groups | `12af2d0`, `18e2fb0`, `18e2d00`, `18e19a0`, `18b7ca0`, `18e3350`, `18e1740` | N | `engine/pose_group_batches.py`, `engine/pose_dispatch.py`, `engine/pose_group_transfer.py`, `engine/pose_batch_runtime.py` | [batches](../../native/snow_host/pose_group_batches_validation.json), [dispatch](../../native/snow_host/pose_dispatch_validation.json), [transfer](../../native/snow_host/pose_group_transfer_validation.json), [joined batch](../../native/snow_host/pose_joined_batch_validation.json) | reconstructed (offline, synthetic fixtures) |
| C8 | Worker per batch and group: solve if `settings.byte20 == 0` and links+poses ≠ 0; otherwise free motion then poststep | `18e3340`, `18e31b0` | N | `engine/pose_group_worker.py`, `engine/pose_worker_runtime.py` | [worker](../../native/snow_host/pose_group_worker_validation.json), [numerical worker](../../native/snow_host/pose_numerical_worker_validation.json) | reconstructed |
| D1 | Group prepare: counts (`1994bb0` when mode = 0, `1994cc0` otherwise; then `1994ad0`), layout `19908d0`, settings `1990ba0` (ctx+0x10 = dt, +0x0c = 1/dt, ctx+0x00..0x08 = gravity) | `1994da0` | N | `engine/pose_group_prepare.py`, `engine/pose_link_counts.py`, `engine/pose_category_counts.py`, `engine/pose_solver_layout.py`, `engine/pose_solver_settings.py` | [prepare](../../native/snow_host/pose_group_prepare_validation.json) | reconstructed |
| D2 | Body buffers: per body in group order, data = tensor and inverse-mass-like scalar `+0x124`; state = velocity `+0x1a0/+0x1ac` **plus gravity·dt**, times the damping multiplier | `1994560`, `1990af0`, library `1c453d0` | N | `engine/pose_body_buffers.py`, `engine/pose_group_body_buffers.py` | [buffers](../../native/snow_host/pose_body_buffers_validation.json), [group buffers](../../native/snow_host/pose_group_body_buffers_validation.json) | reconstructed; damping library supplied |
| D3 | Contact row builders (four families) | `1994970` → `1991da0`/`19933d0`/`1991110`/`1992800` | N | `engine/pose_link_dispatch.py`, `engine/pose_link_arena.py` | [dispatch](../../native/snow_host/pose_link_dispatch_validation.json), [arena](../../native/snow_host/pose_link_arena_composition_validation.json) | reconstructed |
| D4 | Phase bit 27; pose and constraint builders (kinds 1–6) | `19948d0` → `19905f0` | N | constraint builder modules | [mixed runtime](../../native/snow_host/pose_mixed_group_runtime_validation.json) | reconstructed for the tested kinds and states |
| D5 | Solve: prepare `19e4710` + N iterations `19e4d10`; N = `(flags>>2)&0x3fff` from settings `+0x28` (default 8) | `1994e80`, `19e5aa0` | N | `engine/pose_solver_control.py`, `engine/pose_solver_arena.py` | [control](../../native/snow_host/pose_solver_control_validation.json), [arena](../../native/snow_host/pose_solver_arena_validation.json) | reconstructed (all 25 categories) |
| D6 | Feedback: link cache, body motion (`+0x1a0/+0x1ac`), kind-2 pose results | `1994470`, `1994240`, `1994080` | N | `engine/pose_body_feedback.py`, `engine/pose_constraint_feedback.py`, `engine/pose_link_runtime.py` | [body](../../native/snow_host/pose_body_feedback_validation.json), [pose](../../native/snow_host/pose_constraint_feedback_validation.json), [contact pass](../../native/snow_host/pose_contact_pass_validation.json) | reconstructed |
| D7 | Secondary pass when settings `+0x2a` ≠ 0 (4 at world creation): phase bit 28, zero state, refresh primary rows `1993e50`, solve again (special phase: primary rows only, `(flags>>16)&0x7ff` iterations) | `1993ed0`, `1993e50`, `1994e80` | N | `engine/pose_link_secondary_rows.py`, `engine/pose_group_step.py` | [secondary](../../native/snow_host/pose_mixed_group_secondary_validation.json), [composition](../../native/snow_host/pose_contact_secondary_composition_validation.json) | reconstructed |
| D8 | Apply the secondary state to transforms: temporary motion, then body slot `+0x10` = `18befb0` with scalar 1.0, then restore motion | `19906b0`, `18befb0` | N | `engine/pose_body_secondary_update.py`, `engine/pose_body_integration.py` | [secondary integration](../../native/snow_host/pose_secondary_integration_validation.json) | reconstructed for body table `0x29c99a8` |
| D9 | Poststep(dt, quiet flag, thresholds): quiet aggregation `1958460` (`18c0190`, inactive slot `+0x20` = `18bebd0`); if active, integrate every body `18befb0(dt)` (x += v·dt, axis-angle rotation), then bounds refresh `18bcee0` | `19574f0` | N | `engine/pose_group_poststep.py`, `engine/pose_poststep_runtime.py`, `engine/pose_body_quiet_state.py`, `engine/pose_body_bounds.py` | [integrated](../../native/snow_host/pose_group_integrated_validation.json), [joined poststep](../../native/snow_host/pose_mixed_group_poststep_validation.json), [retirement](../../native/snow_host/pose_mixed_group_retirement_validation.json) | reconstructed (box resources, one body class) |
| D10 | Zero-work groups: free motion `v = (v + g·dt)·damping`, skipping a single fixed body; then poststep | `1957590`, `19574f0` | N | `engine/pose_free_motion.py` | [free motion](../../native/snow_host/pose_free_motion_validation.json) | reconstructed |
| C9 | If `island.active_count ≠ 0`: broadphase slot `+0xa8(null)`; phase = 0 | `18b9710` | S, N | `engine/pose_update_stage.py` | [stage](../../native/snow_host/pose_update_stage_validation.json) | reconstructed (order) |
| C10 | Sleep/wake body lists to callback `[0x1433365e0]+0x38` (args: controller, `island+0x480`/`+0x488`, `+0x470`/`+0x478`); then `18e1990` clears both counts | `18b74e0`, `18e1990` | S (this pass); `+0x480` is filled by transfer (N) | `engine/pose_group_transfer.py` (producer only) | [transfer](../../native/snow_host/pose_group_transfer_validation.json) | **unknown** consumer; the `+0x470` producer is inferred to be the wake path |
| E1 | Listener dispatch: for each listener in the map at `manager+0x18`, gather the body's link records (filter byte `+0x28`), then listener slot `+0x10(manager, record)` per record | `140b3d0`, `14070f0`, `18babf0`, `195c380` | S (this pass) | — | — | **unknown** (I: contact-event delivery after the solve) |
| E2 | Lock release | `1c3d1c0` | S | — | — | unknown (protected) |
| F5 | Actor batch 2: tag 1 calls actor slot `+0x2c8()`, tag 3 calls `13ecb10(actor)`. Player slot `+0x2c8` = `0x53d7f0`: gates, then `13ac220` and `5390d0(+0x1010)` (slot `+0x460`) | `13c08f0`, callable `13cd5e0`, `0x53d7f0`, `13ac220` | S (this pass) | — | — | **unknown**. `13ac220`: if vector `+0x1d0` is nonzero, it reads the main (`runtime+0x6e8`) and rider (`+0xb90`) linear velocities, subtracts `+0x1e0`, clamps per axis to runtime `.data` bounds and writes back through `18aa520` with force (I: post-integration velocity limit) |

## 2. Where gravity and the snow and board forces enter

### 2.1 Gravity and damping

- **Source.** Settings object at `world+0x08` (vtable `0x29ca978`, data `+0x08..+0x47`); gravity is
  settings `+0x08/+0x0c/+0x10`, i.e. `world+0x10..+0x18` (class S, layout corrected by the live read).
  The default constructor `19414b0` writes `(0, 0, -10)`. World creation `13d1bd0` immediately calls
  setter `18ae420` with `(0, 0, -9.81)`. A runtime setter `13b7bb0` (referenced from data at
  `0x3096c18`) can change it later. Live: (0, 0, -9.81), unchanged in the session (see "Live
  settings" below).
- **Transfer.** `1990ba0` copies settings `+0x08/+0x0c/+0x10` to solver context `+0x00/+0x04/+0x08`
  (N, [settings](../../native/snow_host/pose_solver_settings_validation.json)). `1993ed0` passes
  `ctx+0x10` (dt) and `ctx+0x00` (vector) to `1994560` (S, this pass).
- **Application.** Gravity becomes a velocity increment `g·dt` added to the solver's initial body
  state, once per substep, before any row is solved (N,
  [buffers](../../native/snow_host/pose_body_buffers_validation.json)). Zero-work groups add the
  same increment in free motion `1957590` (N). Per-body suppression: body `flagsaa` bit 3 zeroes
  the vector, and metadata `+0x52` bit 3 (fixed body) bypasses both the increment and damping.
  The stored body velocity is overwritten only by feedback `1994240` after the solve.
- **Damping.** When `body+0x1b8` is set, library `1c453d0` receives `1 - damping` and dt. Its
  result multiplies linear XYZ (lanes 0–2) and angular velocity (lane 3). That this is a
  `pow`-style per-second damping is inference.
- **Units.** m/s² and seconds are inferred from the 9.81 value and from the float32 subdivision
  of the frame interval. They are not proven.

### Live settings

This is a live observation (class L), not a reconstruction check. Receipt:
[physics settings live](../../native/snow_host/physics_settings_live_observation.json).

**Capture.** A private, bounded snow-host plugin. Its only write was the existing broad-phase slot
`+0x60` vtable-pointer swap (S0 inside `18b8fa0`), compare-exchanged in and back and verified after
restore. Inside the detour, before forwarding, it read only: the `18b8fa0` caller frame (returns into
`18ae2b0` at `18ae2b9` and into the substep loop at `1389b02` required), giving the loop's timing
pointer (saved rbx) and substep index (saved edi), checked by `[[[timing]]+8] == controller` and
index < count; `timing+0x1390/+0x1394/+0x136c` and the outer counter `[timing]+0x20`; and the
settings object at `world+0x08` (world = `controller+0x20`). Three Step-hold reads (spawn, +63 s,
+130 s) were taken with the host paused; neither the host step nor the plugin's substep count
changed during them. Session: 130 s of riding, Wine on macOS.

**Layout.** `world+0x08` is a 0x48-byte object: vtable `0x29ca978` at `+0x00`, data `+0x08..+0x47`
(copy `1941420`/`1941520`, default constructor `19414b0`). Settings offsets on this page are relative
to that object.

**Values.** One value set in all 14,752 substep reads, the arm-time read and the 3 held reads:

| Settings offset | Raw | Value | Use |
| --- | --- | --- | --- |
| `+0x08/+0x0c/+0x10` | `0 / 0 / c11cf5c3` | gravity (0, 0, −9.81) | ctx `+0x00..+0x08` |
| `+0x14` (byte) | `01` | 1 | solver flags bit 30 |
| `+0x18` | `40000000` | 2.0 | ctx `+0x20` |
| `+0x1c` | `bc23d70a` | −0.01 | ctx `+0x1c` |
| `+0x20` (byte) | `00` | 0 | C8 solve gate open |
| `+0x21` (byte) | `01` | 1 | solver flags bit 29 (default already 1) |
| `+0x24` | `00000001` | mode 1 | flags low 2 bits; full word selects `1994cc0` |
| `+0x28` (u16) | `0008` | 8 normal iterations | flags bits 2.. |
| `+0x2a` (u16) | `0004` | 4 secondary iterations | flags bits 16..; D7 runs |
| `+0x2c`, `+0x30` | `3dcccccd`, `3e4ccccd` | 0.1, 0.2 | ctx `+0x14`, `+0x18` |
| `+0x34/+0x38/+0x3c` | `3f000000` ×3 | 0.5 | ctx `+0x24..+0x2c` |
| `+0x40`, `+0x44` | `3a83126f` ×2 | 0.001 | not copied by `1990ba0` |

These are exactly the static prediction: `19414b0` defaults, then `13d1bd0` sets gravity (from
`0x1f28140`), mode 1 and secondary 4. The runtime setter `13b7bb0` changed nothing in this session.
Live mode is 1, so the single-row contact builder path (D4 note) applies in the observed states.

**Substep timing.** 9,798 consecutive PhysicsWorldStep frames, 14,752 substeps, every frame with
ordinals 0..count−1 complete. Frames by count: 1: 5,016; 2: 4,620; 3: 153; 4: 8; 5: 1 (no 8 this
time; an earlier receipt saw one). Within a frame dt was constant, and dt = float32(consumed
`+0x136c` / count) in 9,798 of 9,798 frames. dt is continuous: 9,244 distinct bit patterns, range
0.0062501–0.016657, median 0.0094. The consumed range for count 1 (0.0078–0.0167) overlaps that for
count 2 (0.0125–0.0249), so the count is not a function of the current interval alone; the
selection rule remains open.

**Limits.** One session, one build, Wine frame pacing (count and dt distributions reflect this host's
frame rate). Sequential reads, not atomic. The frame-layout interpretation of the timing pointer is
build-specific. Meanings of `+0x14`, `+0x18`, `+0x1c` and `+0x2c..+0x44` beyond their solver-context
destinations are unassigned.

### 2.2 Snow-fluid and board forces

Everything below happens **in actor batch 1** (stage A2). That is per substep, with the elapsed
substep dt, **before** that substep's pair update and contact generation, and before the island
solve. The forces are written straight into the body velocity fields (`+0x1a0` linear,
`+0x1ac` angular). They are external increments that the solver then reads as initial state in
D2. They are not solver rows.

| Contribution | Mechanism | Evidence | Reference |
|---|---|---|---|
| Pending impulse (queued once per frame from BeforeSimulation, F1) | central impulse to the main body, then the rider; consumed and cleared on the first eligible substep | N; producer route S; L membership | [pending consumer](CENTRAL_IMPULSE.md#pending-impulse-consumer-and-lock-scope) |
| Ground-stick / helper impulse | central impulses to rider then main, `timed_scale = signed_scale·dt` | N | [helper tail](CENTRAL_IMPULSE.md#optional-helper-direct-impulse-tail) |
| Immersion density reactions and contact forces (hull/foil), adhesion | point impulses `18aa180` → `18be8a0` (`J = dt·F`; linear and angular), two loops; runtime scale `+0x1520` = elapsed substep dt (L) | N, L | [point loops](CENTRAL_IMPULSE.md#post-pending-point-impulse-loops), [runtime scale](CENTRAL_IMPULSE.md#expanded-point-sampler-accepted-runtime-scale-is-elapsed-substep-time) |
| Velocity correction / speed floor / directional decay | direct linear setter `18aa520` (replaces, not adds) | N (local snippets) | [velocity setter](CENTRAL_IMPULSE.md#post-submission-velocity-setter-and-speed-floor) |
| Jump impulse | central impulses with mass split | N | [integration guide](../systems/snow/integration/CLIENT_GUIDE.txt) |
| Rider/leg pose springs | **constraint rows**: config prepared at `13fad40`, record submitted through `13f7180` → `18aee00` into linked object `+0x70`; built as pose kind 2 in D4 and solved in D5 | N (preparation and record layout); I (that a record submitted in A2 is consumed by the same substep's D4) | [pose record](CENTRAL_IMPULSE.md#pose-record-submission-boundary) |
| Post-integration velocity clamp | `13ac220` in actor batch 2 (F5), after D9 integration | S only | this page |

The snow model's own terrain and immersion queries are separate from the physics narrow phase.
The narrow phase still makes rigid contacts for the same bodies: capsule and sphere against grid
and terrain were seen live in the [census](../../native/snow_host/narrowphase_tester_census_live.json).
Inference: a board body receives snow impulses in A2 and rigid contact rows in D3–D5 within the
same substep.

## 3. The group routine, body indices and layout

- **Caller of `1994970` and `1994e80`.** Only `1993ed0` calls them. `1993ed0` is called only by
  `1994da0`, which is called only by worker `18e31b0` (reached through thunk `18e3340`). The
  worker is dispatched by `18e2fb0`, which only `18b9710` calls (S, rel32 scan, this pass).
- **Body indices.** Append `19573c0` stores the group's current count at `body+0x1c` and inserts
  into the group body array (`group+0x10/+0x18`). Body buffers, builders (low 16 bits of `+0x1c`)
  and feedback all use that order. See [group membership](LINK_SOLVER.md#group-membership-and-solver-body-indices).
  Membership changes in the pair update's rebuild (B2) and in attach (C5).
- **Counts and layout.** `1994da0` zeroes 25 counters. It counts links with `count_pose_link_rows`
  (`1994bb0`/`1994cc0`, chosen by the **full** mode word, which is 1 at world creation) and poses
  with `1994ad0`, plans layout with `19908d0` (`plan_pose_solver_layout`), then initializes
  settings with `1990ba0`. Builders see only the low two bits of mode. With mode 1, every contact
  payload takes a single-row builder, including multi-point payloads (I: whether live mode is
  still 1 is unknown).
- **Allocation.** The solve buffer is the worker's reusable request buffer (`request+0x10/+0x18`),
  grown through allocator global `0x1433365b8` (N, [numerical worker](../../native/snow_host/pose_numerical_worker_validation.json)).
- **Single native entry for one group step.** Yes: `1994da0(group, request{dt, settings, buffer, capacity})`
  covers counting, layout, settings, body buffers with gravity, building, solving, feedback,
  secondary correction, transform application, quiet check and integration. It has already
  run offline uninterrupted on synthetic fixtures. Its external needs are the allocator,
  byte-fill, the protected payload pool return (`1958720` path) and atan2 (native outputs were
  replayed into the reconstruction).

## 4. Coverage gaps by stage

Reconstructed and natively composed: B1–B5 (B2 also live), C1, C2, C6–C9, D1–D10. Partial:
A1/A2 (wrapper and many snow kernels, but not the whole shared snow update), C5. Unknown:
F1's full motion update, the pre-loop `1365890`, the protected bracket (A3/B6/E2), C3, C4,
C10's consumer, E1 and F5.

The joined native receipts already cover C7 → C8 → D1–D10 as one execution
([joined batch](../../native/snow_host/pose_joined_batch_validation.json)). They use synthetic
groups, one body class (`0x29c99a8`), box resources, damping disabled and an empty link ring
(the [retirement](../../native/snow_host/pose_mixed_group_retirement_validation.json) receipt
adds one shared link). No receipt yet feeds them a live-captured group.

## 5. Recommended Phase 2 native entry point

**Primary entry: `18ae2c0(controller, dt)`**, the whole solver half of one substep. Fall back to
`18e2fb0(island, dt, settings)` if C3/C4/C5 cannot be satisfied. Use `1994da0` per group for
fault isolation. Prefix `18ae2b0` → `18b8fa0` (pair update, already Unicorn-validated) to cover
B1–C10 in one run. Do **not** start the run at `140efa0`/`1389a50`: that would cross the
protected lock helpers and the game-side actor batches.

Fixture requirements, all captured from one live substep of the player's world:

1. Controller (0x78 bytes), world object (`controller+0x20`; settings at `+0x08`, 0x48 bytes;
   action tree at `+0xd0`), island context (0x4a0 bytes: active and inactive arrays
   `+0x418..+0x434`, batch storage, jobs `+0x008..+0x307`, argument table `+0x308`, claim
   `+0x448`, transfer byte `+0x44c`, lists `+0x470..+0x498`), and the provider changed-link span
   (`+0x28/+0x30`).
2. Every active group: body, link and pose arrays (`+0x10/+0x18`, `+0x40/+0x48`, `+0x90/+0x98`),
   index and flag `+0xa0`.
3. Every body: the full record up to at least `+0x1c8`, with vtable `0x29c99a8` verified, metadata
   (`+0x30` → `+0x50..+0x53`), resource entries `+0xb8/+0xc0` (72-byte stride) and their shape
   vtables, damping record `+0x1b8`, quiet overrides `+0x1c0`, link ring head `+0x80`.
4. Every link: header (`+0x84` flags, endpoints, ring next `+0x20/+0x30`), entries `+0x58/+0x60`
   and each payload (rows, `+0x110` count, `+0x114` flags); plus the profile/material tables that
   the profile combination reads.
5. Every pose/constraint: vtable (kind query slot `+0x10`), inline config `+0x70`, endpoints; and
   the kind-4 command callbacks if the C2 collections are not empty.
6. Exact float32 bits of dt (`timing+0x1394`) and the frame ordinal (batch-frame reader).
7. Services: allocator (`0x1433365b8` slots), byte-fill, protected pool return, dispatcher
   record with capacity 1 (the inline branch, as observed live), broadphase slots `+0x98/+0xa8`
   recorded, callback `[0x1433365e0]+0x38` recorded, and C3/C4 run natively only if their lists
   are empty in the capture. Otherwise supply them.
8. Comparison target: the same records captured after the island step (section 6, P5/P6).

## 6. Recommended Phase 3 live capture points

All use techniques already shown safe live: vtable-pointer swaps to private copies with return-site
gates, compare-exchange install and restore, and drain. None needs code patches or protected-stub
execution.

| # | Point | Hook | When it fires | Captures | Status |
|---|---|---|---|---|---|
| P0 | Step-hold | host stop mode | between Steps | world settings (gravity, iterations, mode), group/body inventory, body classes | existing ([check](LINK_SOLVER.md#step-hold-safe-point-live-check)) |
| P1 | Snow wrapper entry/exit | actor slot `+0x2c0` (existing update capture, frame ordinal) | A2 | body velocity before and after snow impulses (= solver input velocity for the player's bodies) | existing ([direct substeps](SNOW_BATCH_DISPATCH.md#live-direct-substep-validation)) |
| P2 | S0 / S1 | broadphase slots `+0x60` / `+0x40` | B1 / B2 | pair lists, post-broadphase state | existing |
| P3 | S2 | broadphase slot `+0x88`, return `18b907b` | after B4 | player group links, payload rows and bodies: the **Phase 2 input fixture** | existing hook; fixture read is new |
| P4 | Pending publish | broadphase slot `+0x98`, return site after `0x18b97c9` | C6 (only when links are pending) | group membership after attach C5 | new, same vtable copy |
| P5 | Post-batch notify | broadphase slot `+0xa8`, return site after `0x18b9802` | after C7–D10, only if active groups remain | bodies after solve and integration, group flags: the **Phase 2 comparison target** | new, same vtable copy |
| P6 | Post-step actor | actor slot `+0x2c8` (`0x53d7f0`) entry, through the same actor-vtable swap as P1 | F5, after E1/E2 and before `13ac220` | the player's body transform and velocity after the whole physics half | new, same technique as P1 |

Read budgets at the in-step points stay within the safe-point contract's
[candidate B](PHYSICS_SAFE_POINT_CONTRACT.md#32-candidate-b-in-step-pair-update-points-s0s1s2-stepping-thread-host-code-only)
policy. A full fixture read at S2 is larger than earlier captures, so measure its cost first
and record one substep at a time.

## 6a. Phase 2 update: island stages C2–C6

These rows supersede the C2–C6 (and amend C9) rows of the stage table above.

| # | Stage | RVA(s) | Evidence | Module | Receipt | Status |
|---|---|---|---|---|---|---|
| C2 | Command constraint preparation (unchanged) | `18b9830`, `19445c0`, `19440c0` | N | `engine/pose_update_stage.py`, `engine/pose_command_prepare.py`, `engine/pose_command_registry.py` | [collections](../../native/snow_host/pose_collection_prepare_validation.json), [command](../../native/snow_host/pose_command_prepare_validation.json), [registry](../../native/snow_host/pose_command_registry_validation.json) | reconstructed; the gameplay callback stays supplied |
| C3 | Action tree walk on provider+0xd0: entry slot +8 (dt), then wake callback `18b8c90`, state-2 entries retired and destroyed | `11fd350`, `1959a70`, `18b8c90`, `1959c50`, `18be770` | S, N | `engine/pose_island_action_tree.py` | [action tree](../../native/snow_host/pose_island_action_tree_validation.json) | reconstructed (walk and callback); entry update supplied (class and insertion site not found); no velocity/transform writes |
| C4 | Swept-contact stage at controller+0x40: begin collects and destroys kind-6 constraints; `ed2ea0` dt; finish scans moving bodies, sweeps and creates kind-6 constraints from a velocity/transform snapshot | `195b190`, `195af30`, `ed2ea0`, `195c040`, `195b250`, `195a0f0`, `1985920` | S, N (begin, dt) | `engine/pose_island_ccd_stage.py` | [swept stage](../../native/snow_host/pose_island_ccd_stage_validation.json) | begin and dt reconstructed; finish static only |
| C5 | Attach changed links: clear pending, skip flag bit1, finalize both groups, bit15-gated special move or merge (larger absorbs), append link | `18e2200`, `18e21a0`, `1957d80`, `1957430` | S, N | `engine/pose_island_attach.py` | [attach](../../native/snow_host/pose_island_attach_validation.json) | reconstructed as one composition; body removal `1957fc0` supplied |
| C6 | Publish pending links to broadphase slot +0x98 = `199b590` (24-byte record into the +0xf8 new-pair vector; a null entry would fault) | `18b9710`, `199b590`, `1940990` | S, N | `engine/pose_update_stage.py`, `engine/pose_island_attach.py` | [stage](../../native/snow_host/pose_update_stage_validation.json), [publish](../../native/snow_host/pose_island_publish_validation.json) | reconstructed including the receiver |
| C9 | (amend) slot +0xa8 = `193fa10`: byte +0x49 \|= 1 | `193fa10` | N | `engine/pose_island_attach.py` | [publish](../../native/snow_host/pose_island_publish_validation.json) | reconstructed |

Answer to open question 1: no velocity or transform write was found in C2–C6 (closure scan
for stores to body +0x1a0..+0x1b7 and calls to the known setters; 1957590 and 13ac220 are
flagged by the same scan as positive controls). Two dynamic gaps remain: the C3 entry
update virtual and the C2 gameplay callback.

## 7. Open questions (ranked)

1. **C3 action tree** (`1959a70` on `world+0xd0`): which objects, and whether they write body
   velocity or transform before the solve. Read the node count at P0.
2. ~~Live settings values~~ Answered: see "Live settings" (gravity (0,0,-9.81), mode 1,
   iterations 8 / 4, exactly the static prediction).
3. **C4 stage at `controller+0x40`** and its kind-6 scan.
4. **C5 attach `18e2200`** as one native composition (wake, migrate, merge).
5. **E1 listener dispatch** record format (`195c380`) and who registers listeners.
6. **F5 slot `+0x2c8`** work: clamp bounds (runtime `.data` near `0x3315958`) and `5390d0` slot `+0x460`.
7. **C10 consumer** at `[0x1433365e0]+0x38` and the producer of the `+0x470` list.
8. Same-substep consumption of rider pose records submitted in A2.
9. Pre-loop `1365890`; the protected bracket on `0x1433125e0`; ordering of PhysicsTerrainUpdate
   and PhysicsPropsUpdate relative to PhysicsWorldStep.
10. Body and resource classes other than `0x29c99a8` and box; damping library `1c453d0` inside the
    joined runs; island dispatch with more than one worker (capacity 1 is inferred from the
    shared global `0x143336610` and the live pair-job capacity).

Nothing on this page claims a complete physics tick or equivalence with the original engine.
