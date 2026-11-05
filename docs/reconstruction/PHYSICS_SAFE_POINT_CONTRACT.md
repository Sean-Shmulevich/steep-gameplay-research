# Physics safe-point contract for snow host plugins (draft)

Status: **draft design contract.** Nothing here is implemented. It states when a native plugin
running in the snow host may read or change physics pair and body state (broadphase pair lists,
the narrow-phase provider and its link trees, links, groups and pools), what it may call, and
what it must check first. The proposed API is sketched in
[snow_physics_safe_point.h](../../native/snow_host/snow_physics_safe_point.h) and is marked
PROPOSED there.

Offsets and RVAs below are evidence anchors for the analysed build. They are not API fields, and
nothing here claims equivalence with the original engine. Every clause carries one label:

- **ESTABLISHED**: backed by a cited receipt or reconstruction document. "(live)" means observed in
  the running game; "(static)" means image analysis or instruction emulation only.
- **PENDING**: being tested now by a named lane. The clause has a marked slot and must not be
  relied on until the slot is filled.
- **AUTHORED POLICY**: our design choice. It is not game evidence and may be changed without new
  evidence.

## 1. Scope

In scope:

- The player's world physics controller (the 0x78-byte object built by `18b8150`), its broadphase
  at controller+0x28, island context at +0x30 and narrow-phase provider at +0x38. See
  [Pair update step](LINK_SOLVER.md#pair-update-step).
- Pair rows in the two broadphase lists, links in the provider trees, groups and their link
  arrays, and the 11 CRITICAL_SECTION-backed pools in the [physics lock map](PHYSICS_LOCK_MAP.md).
- Snow host plugins as defined by [snow_plugin.h](../../native/snow_host/snow_plugin.h) (API v1).

Out of scope:

- Other worlds and controllers. Only the player's world controller has been captured live
  (ESTABLISHED (live), limit stated in [Live pair update capture](LINK_SOLVER.md#live-pair-update-capture)).
- Contact solving, integration and island solving after the pair update (`140efa0`, `140b3d0`,
  `13c08f0` in the substep loop). No contract is offered for their state.
- Windows. All live evidence is from Wine on macOS (ESTABLISHED (live) limit of
  [Live thread and lock observation](LINK_SOLVER.md#live-thread-and-lock-observation)).
- The protected stubs at addresses at or above 0x143000000. They are treated as opaque supplied
  services and are never called, traced or emulated by this contract (AUTHORED POLICY).

## 2. Threads and placement

| # | Clause | Label |
|---|---|---|
| T1 | Every plugin call runs on the host's plugin thread, one call at a time, never on a game thread. | ESTABLISHED (host design, [snow_plugin.h](../../native/snow_host/snow_plugin.h), [README plugins](../../native/snow_host/README.md#plugins-api-v1)) |
| T2 | Host adapter calls (pause, step, setters) run on the host executor thread, an ordinary thread in the game process. It is not an engine-ordered tick callback. | ESTABLISHED ([README design](../../native/snow_host/README.md#design), execution-context caveat) |
| T3 | The per-substep pair update `18b8fa0` does not run on a fixed thread. In census-01 it ran on 10 different threads, with 4,542 switches in 12,000 steps. It never ran on the host plugin thread. | ESTABLISHED (live, `physics_thread_lock_live_observation.json`) |
| T4 | All pair-worker factory calls of one step came from the thread running that step (11,999 of 11,999 steps). | ESTABLISHED (live, same receipt) |
| T5 | Pair-job dispatcher capacity is 1, so `18b7ca0` takes its single-worker branch and runs the pair work inline on the stepping thread. Live: capacity 1 and cursor delta 1 in all 12,000 steps. Static: the override global is set to 1 unconditionally, so no dedicated dispatcher workers are created. | ESTABLISHED (live and static; [atomics and threads](PHYSICS_ATOMICS_AND_THREADS.md#pair-job-worker-capacity)) |
| T6 | The 24 threads sharing start RVA `0x1c94b94` are CRT-created threads, not a dedicated physics pool. Which scheduler pool owns the 10 stepping threads is unknown. | ESTABLISHED (static) for the trampoline; owner pool unknown ([atomics and threads](PHYSICS_ATOMICS_AND_THREADS.md#thread-entry-points)) |
| T7 | `18b8fa0` is reached only through `1389a50` (substep loop) -> `140b1a0` -> `18ae2b0`. It runs once per physics substep. | ESTABLISHED (static, [Pair update step](LINK_SOLVER.md#pair-update-step) leads) |
| T8 | Plugin code never runs on an engine thread. Work at an in-step point is done only by host-owned code that applies declarative requests the plugin queued earlier. | AUTHORED POLICY (a fault on an engine thread cannot be contained the way plugin-thread faults are) |
| T9 | Thread identity is never a fixed value. At an in-step point the host records the current thread at S0 and requires the same thread at S1 and S2 of that `18b8fa0` call. No TLS or thread affinity is assumed. | AUTHORED POLICY, built on T3/T4 |

## 3. Safe-point candidates

### 3.1 Candidate A: Step-hold (plugin thread)

The host holds native stop mode. `Step` is frozen while the frame loop, rendering and
`UpdateWhileEngineIsPaused` continue. Plugins run in `on_pause` and `on_step`.

| # | Clause | Label |
|---|---|---|
| A1 | Held stop mode freezes `Step` and the whole simulation half of the frame (world chain, camera, pad, sound). | ESTABLISHED (live, [native stop mode](NATIVE_STOP_MODE.md#what-stop-mode-suspends)) |
| A2 | Single-step releases exactly one `Step` execution and re-arms (35/35 in the stop-mode session, 410/410 in the host stress run). | ESTABLISHED (live, [single-step](NATIVE_STOP_MODE.md#single-step), [README plugins](../../native/snow_host/README.md#plugins-api-v1)) |
| A3 | While held, the player body reads identical across samples. Ten released steps give ten steps of motion. | ESTABLISHED (live, [README player state](../../native/snow_host/README.md#player-state-host-03)) |
| A4 | `1389a50` is the PhysicsWorldStep job's delegate. The delegate slots lie inside that job record, but the job calling through them is not verified. | ESTABLISHED (static) for the store; binding unverified ([atomics and threads](PHYSICS_ATOMICS_AND_THREADS.md#evidence-for-the-hold)) |
| A5 | **SLOT P1 (lane t2live):** while held, `18b8fa0` is not entered, the pair lists, provider trees, link objects, group arrays and pool counts are byte-stable across the hold, and all guard CRITICAL_SECTIONs read free. Until this slot is filled, Step-hold reads of pair state are best-effort and may tear. | PENDING (t2live) |
| A6 | Off-graph work (loading thread, idle task workers, async services) is **not** suspended by the hold. | ESTABLISHED (live boundary, [native stop mode](NATIVE_STOP_MODE.md#boundaries)) |
| A7 | **SLOT P3 (lane t2mutators):** which outside-step mutators (body create/setup/destroy, loading, game-side callers of `1401190`, `18aa340`, `18aa4f0`) can run during a hold, on which thread, and what observable condition excludes them. | PENDING (t2mutators) |

Entry protocol (AUTHORED POLICY unless noted):

1. Host pause has been verified: group held and `Step` frozen while `EndFrame` advances
   (ESTABLISHED host behavior, [README design](../../native/snow_host/README.md#design)).
2. Host resolves the controller from the bound player chain and checks its vtable (`0x29ca0e0`),
   the broadphase vtable (`0x29ca8a0`) and the provider factory vtable (`0x29ca780`) against the
   image, as the live capture plugins did before installing (ESTABLISHED (live) check set).
3. Host records an entry snapshot: controller+0x48 (phase word, expected 2 after a completed
   update), controller+0x4c (frame counter), list counts and the guard-free test (section 6).
4. Host calls `on_physics_safe_point` with kind `STEP_HOLD`. Reads during the call go through
   host copy functions only.
5. Exit: the host re-reads the entry snapshot. Any difference marks the safe point **torn**, and
   every request queued during that call is discarded with `SNOW_E_TORN`.

### 3.2 Candidate B: in-step pair-update points S0/S1/S2 (stepping thread, host code only)

These are the three points the live captures already used inside `18b8fa0`. A broadphase
vtable-pointer swap to a private copy of the 34-slot table detours slots +0x60, +0x40 and +0x88,
gated on `self == B` and the matching return site (`18b8ff2`, `18b902c`, `18b907b`). No code
bytes, page protections or shared `.rdata` are changed.

| Point | Where | What has happened | Label |
|---|---|---|---|
| S0 | +0x60 getter, before select | broadphase update (`vfunc 0x90`) done; select, rebuild and pair jobs not yet run | ESTABLISHED (live, 3,021 + 12,000 steps, never missed) |
| S1 | +0x40 getter | select `18dedf0` and rebuild `18e28d0` done; pair jobs not yet run | ESTABLISHED (live) |
| S2 | +0x88 stub | pair jobs `18ddc40` done (retire, neighbor retire, rebalance, worker, merges); counter bump and `18df490` not yet run | ESTABLISHED (live) |

| # | Clause | Label |
|---|---|---|
| B1 | All 11 CRITICAL_SECTION guards read free (OwningThread 0, LockCount -1) at S0, S1, S2 and in the worker path, in 2,288 samples. Sampling is not proof of exclusion. | ESTABLISHED (live, `physics_thread_lock_live_observation.json`) |
| B2 | Stage A (S0 to S1) of the engine's own select and rebuild matches the reconstruction byte for byte in 64 captured steps (1,164,424 bytes, 0 unattributed). Stage B is structurally checked only. | ESTABLISHED (live, `pose_pair_update_live_validation.json`) |
| B3 | Install and restore by compare-exchange of the vtable pointer, with drain of in-flight detours, restored cleanly in every session. | ESTABLISHED (live, both pair-update receipts) |
| B4 | "Between substeps" in the strict sense (after `13c08f0` of substep k and before `13c30c0` of substep k+1) has no known hook. Nothing stored points into the loop. S0 is the nearest point after the substep's broadphase update. S2 is the nearest point before the solver half. | ESTABLISHED (static, call chain in [Live pair update capture](LINK_SOLVER.md#live-pair-update-capture)) |
| B5 | A released step can run 1 to 7 substeps, so S0 fires one or more times per `Step`. A queued request is applied at most once, at the first S0 of the first released step after it was queued. | ESTABLISHED (static/emulated substep count, [native stop mode](NATIVE_STOP_MODE.md#what-a-released-step-simulates)); once-only rule AUTHORED POLICY |
| B6 | Each in-step host action has a hard budget (proposed 50 us) and does O(rows) copies of data prepared at Step-hold. No allocation, logging, file I/O or wait on the stepping thread. | AUTHORED POLICY |
| B7 | **SLOT P4:** whether other engine jobs mutate the same provider, group or pool state concurrently with S0..S2 on other threads (for example `BeforeSimulation` receivers, or a second world). Only the stepping thread was observed in the worker path; other writers were not instrumented. | PENDING (no lane assigned yet; partly t2mutators) |

Entry protocol at S0 (host code, AUTHORED POLICY):

1. The detour runs only if `self == B` and the return address is `18b8ff2`. Otherwise it forwards
   unchanged.
2. Check controller+0x48 == 1 (set at routine entry; ESTABLISHED (static) in
   [Pair update step](LINK_SOLVER.md#pair-update-step)), the controller still points at B, and
   B's vtable pointer is still the private table.
3. Record the current thread id and controller+0x4c. Compare +0x4c with the value the request was
   prepared against (it advances once per substep).
4. Apply the queued request (see 5.2), then forward to the original slot.

At S1 the host checks the same thread and records the request outcome from the selection vector.
At S2 it checks the same thread, verifies postconditions (section 6) and releases any private
buffer. Exit happens when S2 forwards. If S1 or S2 is missed, the request is marked
`SNOW_E_TORN` and the host performs no further in-step action until a full S0..S2 cycle is seen
again.

## 4. Allowed reads

Plugins never dereference engine pointers. They receive copies made by the host into
caller-supplied buffers (AUTHORED POLICY).

| Read | Source | When | Label |
|---|---|---|---|
| Overlapping-pair rows {body A, body B, u64 key} | B.vt+0x40/+0x48, header at B+0xf8 | Step-hold | Layout ESTABLISHED (static and live); stability while held PENDING (P1) |
| Removed-pair rows | B.vt+0x60/+0x68, inline list B+0x118 | Step-hold | Same as above |
| Link presence and flags by pair key (bit0 enabled, bit1 filter-rejected) | provider link tree | Step-hold | Tree shape and red-black validity ESTABLISHED (live, every snapshot); flag meanings ESTABLISHED (static, [Pair link filter](LINK_SOLVER.md#pair-link-filter)) |
| Body group membership, in-world flag | body+0x30 metadata, group | Step-hold | In-world flag ESTABLISHED (live, `SNOW_PLAYER_IN_WORLD`); group read PENDING (P1) |
| Pool free counts (+0x28) | pool pointer at guard-8 | Step-hold, diagnostic only | Layout ESTABLISHED (static, [lock map](PHYSICS_LOCK_MAP.md#summary)) |
| Guard state (OwningThread, LockCount) | the 11 guard pointees | any time, read-only | ESTABLISHED (live layout); a read is not exclusion |
| Outcome of a queued request | host-recorded at S1/S2 | next Step-hold | AUTHORED POLICY |

Reads made while the game runs, not at a safe point, are refused with `SNOW_E_NOT_HELD`, as for
`get_player` (ESTABLISHED host behavior). Bodies are exposed only as opaque handles whose identity
the host re-checks on every use (AUTHORED POLICY, the same model as the player binding).

## 5. Allowed mutations

### 5.1 Already shipped (Step-hold)

| Mutation | Engine routine | Label |
|---|---|---|
| Player linear velocity | `141397ba0` -> `141404910` (takes the runtime lock at runtime+0x1588) | ESTABLISHED (live, host 0.4) |
| Player pose and velocities | `1413bcbb0` -> `14140f990` (runtime lock) | ESTABLISHED (live, host 0.5) |
| Setter gates: `18aa520` (linear, body+0x1a0) and `18aa360` (angular, body+0x1ac) store 12 bytes. They skip the store for kind-2 bodies (metadata+0x53 low nibble) when the force byte is zero, and call `18b8380` only when force != 0 and the controller is non-null. Pose `18a8c20` calls body virtual +0xa0, then always notifies a non-null controller through `18b8380`, with no force flag. | `18aa520`, `18aa360`, `18a8c20` | **SLOT P2 filled (t2hostpath):** ESTABLISHED (static, 512 native cases, `engine/pose_body_state_setters.py`, [Body velocity and pose setters](LINK_SOLVER.md#body-velocity-and-pose-setters-host-set_velocity--set_pose-entry-path)) |
| Pool-guard reach. Guards are reached only when, in order: the setter gate passes, `18b8380`'s gates pass (flags52 bit0 clear, group non-null), and `18e14f0`'s group selection actually changes. Then guard `0x143336bb8` (contact payload pool) is reached via `18e23c0` -> `1957fc0` -> `1958030` -> `1958b90` -> `1958720`, for links with non-null contact payloads. Guard `0x143336aa0` (pose-group pool) is reached via `18e19c0` (third arm) or `18e23c0` -> `18e2de0`. With no selection change, no pool guard is taken; only the protected controller sync at controller+0x50 runs. | `18b8380` -> `18e14f0` | ESTABLISHED (static, same receipt). That no selection change is the usual steady state is expected, not measured |
| Host path. `set_pose` reaches `18a8c20` under the runtime lock (runtime+0x1588), so it always notifies the controller. `set_velocity` reaches `18aa520` and `18aa360` under the runtime lock with force byte 1 (`mov r8b,1` at `14140495d` and `141404968`), so it also always notifies the controller. | `141404910`, `14140f990` | ESTABLISHED (static); whether a host setter ever changes group selection live remains PENDING (P2b) |
| Thread and lock order: the host setters enter controller+0x50 (and possibly a pool guard) from the executor thread while holding the runtime lock. No engine thread is stepping (A1), but off-graph threads are not excluded (A6). | executor thread | Order ESTABLISHED (static); contention with off-graph threads PENDING (P3) |

### 5.2 Proposed for T3 (requested at Step-hold, applied at S0)

All new physics mutations are **declarative requests** queued at Step-hold and applied by the
host at the next S0. The engine's own routines then perform the actual change (AUTHORED POLICY).

| Request | Mechanism | Engine routines that do the work | Label |
|---|---|---|---|
| `RETIRE_PAIR_LINK(key)`: retire one existing pair link for one substep | At S0 the +0x60/+0x68 detours return a **host-private copy** of the removed-row array with one extra row {A, B, key}. B's own storage is not written. | select `18dedf0` (priority and quiet gate) -> rebuild `18e28d0` (`remove_pose_group_link`, context counter) -> retire `18de440` inside `18ddc40` | Mechanism AUTHORED POLICY; each routine ESTABLISHED (live stage A, static receipts for the others) |
| `SUPPRESS_PAIR(key, steps)`: keep a pair's link disabled | Install a host-owned predicate in a filter slot read by `18deb70` (provider+0x188, or body+0xA0 for one body) | filter `18deb70`. A rejected existing link loses bit0 and is not pushed; a rejected new link is pushed with bit1 | Filter behavior ESTABLISHED (static, 512 cases); slot ownership and live values unknown, so **not in T3** |
| Change a body's collision mask or filter word | No field identified | none | Not offered. The field is unidentified (open item O5) |

Notes on `RETIRE_PAIR_LINK`, all ESTABLISHED (live) from the pair-update capture:

- Only removed rows that pass the select gate are retired (43 rows passed, 35 links were selected,
  8 eligible rows had no tree node). The request outcome must therefore be
  `selected` / `not_selected` / `no_link`, never assumed.
- A removed pair that still overlaps reappears in the same step's pair list. Its retired link goes
  to the slot owner's free list and is usually reused for that pair (27 of 35). The visible effect
  is a link **reset** (fresh link state, contacts regenerated), not a lasting removal.
- The private array must stay valid until select has consumed it. S1 comes after select and
  rebuild, so the host releases it at S1 or later.

## 6. Required checks

| # | Check | When | Label |
|---|---|---|---|
| C1 | Image identity: base, fingerprints of `18b8fa0` (274 bytes) and the four getters (64 bytes), all 34 broadphase slots, factory slots and `18de680` fingerprint, call-site encodings | before installing any detour | ESTABLISHED (live check set from the capture plugins) |
| C2 | Object identity: controller reached from the player chain, controller vtable `0x29ca0e0`, controller+0x28 == B, B vtable == image table (install) or private table (in step) | install, every S0, restore | ESTABLISHED (live) |
| C3 | Guard free: for each of the 11 guards, OwningThread == 0 and LockCount == -1 **before and after** the request is applied. If any guard is held, defer to the next substep (at most 8 tries), then drop with `SNOW_E_GUARD_HELD`. | S0 before apply, S2 after | Read layout ESTABLISHED (live); defer/drop rule AUTHORED POLICY. A free read is not exclusion: the engine does not take these CRITICAL_SECTIONs on our behalf |
| C4 | The 7 other guard globals (`0x143336728`, `5d0`, `bc8`, `7e0`, `858`, `748`, `ba8`) have no live shape. Requests whose engine routines touch their pools are refused. `RETIRE_PAIR_LINK` reaches only link, held-record, contact-payload and pose-group pools. | request validation | Guard list ESTABLISHED (static map plus live sample of 12 globals); refusal AUTHORED POLICY |
| C5 | Pair identity: key is present in the current overlap list or the link tree at queue time, and both bodies are still the same handles (re-checked at S0 against the S0 row arrays) | queue, S0 | AUTHORED POLICY |
| C6 | Phase and sequence: controller+0x48 == 1 at S0; +0x4c equals the expected value; same thread at S0, S1 and S2 | S0..S2 | Fields ESTABLISHED (static); rule AUTHORED POLICY |
| C7 | Dispatcher capacity `[[0x143336610]+0x10]` == 1. Otherwise refuse, because multi-worker dispatch was never observed. | S0 | Capacity value ESTABLISHED (live and static); refusal AUTHORED POLICY |
| C8 | No loading in flight and no body create/destroy in progress. **SLOT P3:** the observable predicate is to be supplied by t2mutators. Until it exists, T3 runs only in a steady riding state with no world, sport or respawn transition in the last 2 s and `SNOW_PLAYER_IN_WORLD` set. | queue and S0 | PENDING (t2mutators); interim rule AUTHORED POLICY |
| C9 | Postconditions at S2: both provider trees red-black valid (debug builds), the retired link either reused for its pair or on the owner free list, every merged link in both endpoint +0x80 rings | S2 | Invariants ESTABLISHED (live checks in the capture); use as gate AUTHORED POLICY |
| C10 | Lease: the host pause lease is valid when the request is queued, and the request expires if the hold ends before a release | queue | ESTABLISHED (host lease); expiry AUTHORED POLICY |

## 7. Forbidden actions

All AUTHORED POLICY. The reason is given where evidence motivates it.

- Writing directly to pair rows, B's lists or headers, provider trees, link objects, group slot
  arrays, body records or pool free lists. Engine routines reload fields at each use and rely on
  invariants that we only partly reproduce (stage B is structural only).
- Calling pool take or return routines (`18b5d10`, `18b5c00`, `18dcff0`, `18dd100`, refills) or any
  routine in the [lock map](PHYSICS_LOCK_MAP.md) directly.
- Calling, tracing or emulating protected stubs at 0x143000000 or above, including the guard
  acquire and release stubs.
- Entering a guard CRITICAL_SECTION ourselves as an exclusion. The lock type is only observed. The
  protected stubs may do more than enter and leave, recursion is unknown, and the static chain
  already re-enters controller+0x50
  ([controller group-transition wrapper](LINK_SOLVER.md#controller-group-transition-wrapper)).
- Running plugin code on an engine thread (T8), or blocking, allocating or logging on the
  stepping thread.
- Changing code bytes, page protections or shared `.rdata`. Hooks are heap vtable-pointer swaps
  only.
- Reusing heap addresses, keys or handles across sessions or across a player-lost event.
- Mutating while not held, while torn, while a guard reads held, or while `SNOW_PLAYER_IN_WORLD`
  is clear.
- Queuing more than one physics request per released step in T3.
- Calling `set_player_velocity` or `set_player_pose` in a hold that has a queued physics request
  (T3 interim rule until P2b is settled). `set_pose` always notifies the controller, and either
  setter can take pool guards if group selection changes (P2, ESTABLISHED (static)).

## 8. Failure modes and recovery

| Failure | Detection | Response | Label |
|---|---|---|---|
| Identity mismatch (image, vtable, controller, B) | C1/C2 | Refuse install or request; no write | AUTHORED POLICY |
| Detour reached from a foreign object or call site | self/return-site gate | Forward unchanged, count it | ESTABLISHED (live: 0 foreign calls) |
| S1 or S2 missed, or thread changed mid-call | C6 | Mark torn, release buffer at next S0, suspend in-step actions | AUTHORED POLICY |
| Guard reads held | C3 | Defer, then drop | AUTHORED POLICY |
| Request not selected by the engine gate | S1 selection vector | Report `not_selected`; nothing changed | ESTABLISHED (live behavior) |
| Postcondition fails at S2 | C9 | Uninstall the detour (CAS restore, drain), resume the game, mark the host physics feature faulted for the session | AUTHORED POLICY |
| Restore CAS fails (owner changed) | CAS result | Do not write. Keep the private table pinned and leaked (the module stays pinned) and mark the host faulted | ESTABLISHED (live restore protocol); leak rule AUTHORED POLICY |
| Player lost, world change, lease expiry, client disconnect | host events | Drop all queued requests, uninstall, then resume | AUTHORED POLICY on top of ESTABLISHED events |
| Memory pressure (watchdog stop seen in census-03) | host | Fixed small buffers (at most 64 rows and one request) | ESTABLISHED (live incident); limits AUTHORED POLICY |
| Engine crash on the stepping thread | none in process | Not containable. This is why T8 keeps plugin code off engine threads | AUTHORED POLICY |

## 9. Open items mapped to lanes

| ID | Item | Slot | Lane |
|---|---|---|---|
| O1 | Step-hold freeze of pair and provider state, guard state while held, `18b8fa0` not entered | A5 / P1 | t2live |
| O2 | Host setter path. Filled by t2hostpath: setter gates, `18b8380` gates and the selection-change condition for pool-guard reach. Force byte settled: the host velocity path passes 1, so both host setters always notify `18b8380`. Still open (P2b): whether a host setter ever changes group selection live | 5.1 / P2, P2b | t2hostpath (P2 done; P2b open) |
| O3 | Outside-step mutators: thread, trigger and an observable "loading or body lifecycle in flight" predicate | A7, C8 / P3 | t2mutators |
| O4 | Concurrent writers to provider, group or pool state during S0..S2 from other threads | B7 / P4 | unassigned (partly t2mutators) |
| O5 | Collision-mask or filter word on a body; identity of predicates at provider+0x188, kind+0x70, body+0xA0 | 5.2 | unassigned, static lead in [Pair link filter](LINK_SOLVER.md#pair-link-filter) |
| O6 | Producer and clearer of B+0x118, so that it is known whether anything reads the substituted array after select | 5.2 | unassigned, static lead in [Broadphase pair lists](LINK_SOLVER.md#broadphase-pair-lists) |
| O7 | Byte-level stage B (tree inserts `18de6a0`, `18de830`) to turn C9 into an exact prediction | C9 | unassigned |
| O8 | Lock type of the 7 unsampled guards | C4 | unassigned |
| O9 | Windows behavior and other CPU counts | scope | unassigned |

## 10. T3 release-gate checklist (first guarded mutation: one `RETIRE_PAIR_LINK`)

T3 may run live only when every box is checked. The main session ticks the boxes; this draft
leaves them open.

Evidence gates:

- [ ] P1 (t2live) filled: during a hold, `18b8fa0` was not entered, pair lists and both trees were
      byte-stable, and all guards read free.
- [x] P2 (t2hostpath) filled statically: the setters reach pool guards only on a group-selection
      change ([Body velocity and pose setters](LINK_SOLVER.md#body-velocity-and-pose-setters-host-set_velocity--set_pose-entry-path)).
- [ ] P2b settled, or T3 forbids host setters in the same hold as a queued request. The interim
      rule is to forbid them, so a setter cannot change group selection or take guard
      `0x143336aa0`/`0x143336bb8` before the S0 apply.
- [ ] P3 (t2mutators) filled with an observable in-flight predicate, or the interim steady-ride rule
      in C8 is accepted in writing for T3 only.
- [ ] O6 answered statically: nothing reads the removed-row array after select in `18b8fa0` or the
      broadphase update.

Implementation gates:

- [ ] Detour code is host-owned, in a pinned module, with no allocation or I/O on the stepping
      thread. The private row buffer is preallocated at Step-hold.
- [ ] C1–C10 implemented. Each refusal path is unit-tested with the synthetic adapter (identity
      mismatch, guard held, torn, not selected, lease expiry, player lost).
- [ ] Offline: a Unicorn run of native `18b8fa0` over the memory image with the substituted
      removed array (supplied select, rebuild and jobs as in `check_pose_pair_update_step.py`)
      shows the substituted rows reaching `18dedf0` and no other byte change in the fixture.
- [ ] Offline composition: `select_pose_provider_links` plus `rebuild_pose_body_connectivity` on the
      substituted rows predicts the S1 bytes. A deliberate bug injected into the prediction fails
      the check.

Live gates (one bounded session, director startup, small buffers, experiment lock held):

- [ ] Read-only rehearsal: same install, S0/S1/S2 identity and guard checks, no substitution, for
      at least 1,000 steps, with clean restore and 0 foreign calls.
- [ ] One request: S1 selection vector contains the target link, stage A bytes match the
      prediction with 0 unattributed bytes, S2 shows the link reused for its pair or on the free
      list, C9 holds.
- [ ] 20 more steps afterwards: trees valid at every snapshot, pair keys still linked, no guard ever
      read held, and the player keeps riding.
- [ ] Negative control: a request for a key with no link reports `no_link` and changes no bytes.
- [ ] Clean restore: vtable pointer restored and drained, bottle stopped, saves and settings restored,
      original DLL verified.
- [ ] Receipt written with honest limits (sequential reads, one world, Wine, one-worker dispatch).

## Evidence index

- [PHYSICS_LOCK_MAP.md](PHYSICS_LOCK_MAP.md): guards, pools, pairing, no nested acquisition.
- [PHYSICS_ATOMICS_AND_THREADS.md](PHYSICS_ATOMICS_AND_THREADS.md): dispatcher capacity, thread
  entry, step-hold static view, non-step mutators, host mutation reach.
- [LINK_SOLVER.md](LINK_SOLVER.md): sections "Broadphase pair lists", "Pair update step", "Live pair
  update capture", "Job ring queue", "Live thread and lock observation", "Pair link filter",
  "Controller group-transition wrapper".
- [NATIVE_STOP_MODE.md](NATIVE_STOP_MODE.md): hold, single-step, what is suspended, substep counts.
- [snow_host README](../../native/snow_host/README.md): held model, `SNOW_E_NOT_HELD`, runtime lock,
  plugin containment.
- [SCHEDULER_ROADMAP.md](../../engine/SCHEDULER_ROADMAP.md#next-implementation-and-release-gates):
  gates 5 and 6 (native pause, modding release), which this contract does not close.
- Receipts: `native/snow_host/physics_thread_lock_live_observation.json`,
  `pose_pair_update_live_validation.json`, `pose_pair_update_step_validation.json`,
  `pose_pair_link_filter_validation.json`, `pose_body_controller_transition_validation.json`,
  `pose_job_ring_queue_validation.json`.
