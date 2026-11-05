# Physics atomics and threads

## Scope and evidence

These are static findings from the analyzed image unless stated otherwise. Where a point comes from live observation, the text says so. Where the underlying notes call a point unverified or inferred, this document keeps that label. RVAs are reproduced as written in the sources. Absolute image addresses, heap addresses, file paths and raw bytes are left out on purpose.

Static call analysis followed direct calls only. Indirect and vtable calls were not treated as edges, so "not reachable" below means "not reachable by direct calls," not "never runs." For the lock inventory see [Physics lock map](PHYSICS_LOCK_MAP.md). For the stop-mode boundaries see [native stop mode](NATIVE_STOP_MODE.md).

## Atomic instruction census

The census lists 131 lock-prefixed instructions in the physics address range. Counts per category:

| Category | Count | Pattern in the census reasons |
|---|---|---|
| COUNTER_READ | 41 | Locked add of zero, used as an atomic read of a counter or cursor |
| WORK_CLAIM | 26 | Locked add of +1 claiming an index into a work list, compared against a count |
| OTHER | 25 | Does not fit the other labels (see below) |
| REFCOUNT_INC | 12 | Locked +1 on an object's reference count, result discarded |
| ID_ALLOC | 9 | Locked +1 on a process-wide counter, old value stored into a new object |
| CAS_CLAIM | 9 | Compare-exchange retry loop claiming a slot in a ring or table |
| CAS_PUBLISH | 8 | Compare-exchange retry loop advancing a commit cursor |
| REFCOUNT_DEC | 1 | Locked -1 on an object count, gating a release call |

These add up to the 131 total. The sites cluster in a few functions: the ring reserve and commit routines around 0x18b7710, 0x18b797e, 0x18b7d03 and 0x18b7f80; the level-counter routine at 0x18c0db0; a family of work-claim clones built from the template at 0x193e520; and the published-count and claim-cursor routine at 0x1940e80.

### OTHER sites

The census did not assign these 25 sites to a named pattern. The reasons attached to each site group them as follows:

- Decrements with no zero check, followed by an unconditional virtual call: 0x18aeb07, 0x18b7ebe, 0x18b7ed4, 0x18b809c, 0x18b80a4, 0x18b8104, 0x18b811a, 0x18c0ea3, 0x18c1c95.
- Level-counter steering with a bidirectional decrement path, not a cursor: 0x18c0e55.
- Single-shot compare-exchange claim marks with no retry loop and an unchecked result: 0x193e5c6, 0x193e696, 0x193e766, 0x193e836, 0x193e906, 0x193e9d6, 0x193eaa6, 0x193eb76, 0x193ec46, 0x1963a10.
- Batch accounting and range reservation with variable addends: 0x19402b8, 0x19402c0, 0x1941130, 0x1941146.
- Locked add on a stack local, in a region whose decode the census describes as obfuscated: 0x18ad1b3 (unverified).

The census also notes that the addend at 0x18e31f1 is assumed to be +1 because it is not set in that function (inferred).

## Pair-job worker capacity

A static probe of the job dispatcher reports the following.

- The dispatcher is a single object referenced through a global at RVA 0x3336610, 0x728 bytes in size. Its only creator is the function at 0x19a3be0. The constructor at 0x18b77e0 sets the worker-count fields to 0xffff until a value is set.
- The init routine at 0x18b7b30 computes the worker count as the minimum of 0x20, the processor count, an override global, and the 0xffff default. It then creates that count minus one threads. Threads are created through a wrapper at 0x18b7590 over the CRT thread-begin call, with the thread procedure at 0x18b7f50.
- The processor-count value is set lazily and is capped at 32.
- The override global has one writer, the function at 0x18a7640, and one caller, 0x98c427, inside a constructor-like function at 0x98c390 (reached from 0x648a60). That caller passes a count of zero and a null list, and sets the override to 1 unconditionally.
- The probe's conclusion is that the effective capacity is 1, giving zero dedicated worker threads regardless of core count. This is the probe's static reading of the call pattern.
- The worker-count getter at 0x18a7600 returns the minimum of the two values minus one. It is reached through 0x139d860.
- The dispatch routine at 0x18b7ca0 takes the minimum of the requested count and the dispatcher capacity. When that minimum is 1, the function runs inline on the calling thread. Otherwise it places n minus one 24-byte records into a ring at offset 0x218 via 0x18b7710, signals worker events, runs the remainder on the caller, and waits on per-slot counters.
- The probe and the step-hold notes both describe the workers as the "Motion worker thread" pool.

Consequence (inferred from the capacity of 1): pair-job work runs on the stepping thread rather than on a pool.

## Thread entry points

- **0x1c94b94** is the CRT thread-start trampoline (`_threadstartex`). It is referenced only by the thread-begin call at 0x1c94e08 and an address load at 0x1c94e58. Every CRT-created thread shares this start address, so a count of threads at this address does not identify a dedicated pool. The step-hold notes report 24 threads at this start address.
- **0x18b7f50** is the dispatcher worker procedure per the dispatcher probe. It spins until the dispatcher pointer is non-null, pops work from the ring at offset 0x218, and waits on a per-thread event.
- **0x18b8fa0** is a routine that the step-hold notes report as seen running on ten pool threads in live sampling. The notes state that with Step frozen this routine is not entered (inferred).
- **Off-graph threads** are not suspended by the step hold according to the stop-mode boundaries: the loading thread, idle task workers, and async services. The idle task workers are described as needing a proof that their tasks cannot touch modified state. No entry-point address is given for these in the sources.

## Step-hold safe point (static view)

Status: a likely but unproven safe point. The sources do not establish it directly.

### Evidence for the hold

- Held mode makes the stop check bypass the simulation half of the frame. Step, the world chain, camera update, pad and sound are frozen, while the begin-frame, graphics, end-frame and paused-update work still runs. See [native stop mode](NATIVE_STOP_MODE.md).
- The store routine at 0x136a550 writes the physics-step delegate at 0x1389a50 into two offsets (0x2c0 and 0x348) of a state object, and writes the job callback at 0x8ab390 at offset 0x360. The documented physics-step job starts at offset 0x1b0 and is 0x1b8 bytes long, so the two delegate slots fall inside that job record (at +0x110 and +0x198 of the job). This is strong static evidence that 0x1389a50 is that job's delegate. That the job calls through these slots is not verified.
- Live observation: the player body read the same across samples while held, and ten released steps produced ten steps of motion. Physics integration therefore did not run during the hold.
- No per-job counter for the physics step exists in the repository, so this is not verified directly.
- Whether the Step job transitively contains the physics step is not an extracted edge. It is inferred from the behavior.

### Limits

- Off-graph threads are not suspended (see Thread entry points).
- A held state is not a quiescent pool. Pool workers exist, and with Step frozen the routine at 0x18b8fa0 is not entered (inferred).

### Reach from the step

Functions that take pool guards and are reached from the step by direct calls: 0x18dc740, 0x18dc8a0, 0x1958610, 0x1958720, 0x1958ba0, 0x18e19c0, 0x18e1a60, 0x18b6e50, 0x18ba6a0, 0x18d2ac0. Through the vtable pair-worker path (per [LINK_SOLVER](LINK_SOLVER.md)), 0x18de060, 0x198f910, 0x18de1e0, 0x18de3e0 and 0x18e0ad0 are also reached.

### Non-step mutators

These groups are not reached from the step by direct calls:

- Body velocity and pose setters at 0x18aa520 (linear), 0x18aa360 (angular) and 0x18a8c20 (pose).
- Body creation, setup and destruction: record setters at 0x18a98d0, 0x18a9e90, 0x18a9b00, 0x18a9c30 and 0x18a9d60, with callers at 0x18a93e0, 0x18aa340, 0x18aa4f0, 0x18aa5b0 through 0x18aa5d0, and 0x18bec50. The sources note that 0x18aa340 and 0x18aa4f0 are called from game-side runtime code.
- Destructors and base teardown: 0x18be6b0, 0x18a7bc0 and 0x18a7a70.
- World and physics initialization: 0x18e0ca0 and 0x18b5e70 (pool subsystem init and teardown).
- Body retire and destroy: 0x1958c20.
- Island and solver side: 0x18d9040, 0x18d9150 and 0x18d91d0.
- Broad users with many callers: 0x18aae40 (14 callers, multi-entry), 0x18c1c30, 0x18b6f00, 0x18b6de0, 0x18a7910, and 0x18ba600.
- Not reached by direct calls from the step: 0x1985ae0, 0x19ea0f0 and 0x1989cd0.

Two functions in this list, 0x18b6e50 and 0x18ba6a0, are also in the step's direct-call reach, so they are not purely non-step.

### Host mutation reach

The host velocity and pose entry points mutate the main body and the rider. Their path reaches the pool guards through a notification wrapper at 0x18b8380 (the controller group-transition wrapper):

- Body setters call 0x18b8380 only when a notify flag is nonzero and the controller pointer is non-null. Whether the host path sets that flag is not checked (unverified).
- From 0x18b8380 the chain reaches 0x18e19c0, which takes the pose-group pool guard, and also reaches 0x1958720 through 0x18e23c0, 0x1958030 and 0x1958b90, which takes the contact-payload pool guard and retires links.
- The documented locking for the host entry points is only a runtime lock. No document or code ties the host path to the eleven pool critical sections (static).
- The host adapter runs on the host executor thread, not an engine tick callback (per the host README's execution-context caveat). The README claims a consistent snapshot only for reads while held.
- Live observation: about 410 steps, 12 pause cycles and the velocity and pose sets passed with no crash recorded. The pool guards were never seen held at sampled points. All eleven critical sections were free in 2288 samples taken at the sampled points.

## Open questions

1. Does the physics-step job actually call through the delegate slots at +0x110 and +0x198 of the job record? (unverified)
2. Does the Step job transitively contain the physics world step? (inferred from behavior, not an extracted edge)
3. Without a per-job counter, is physics integration ever active during the hold? The live observations say no, but no counter confirms it.
4. Thread ownership. These counts are consistent rather than conflicting. With capacity 1 the pair-job dispatcher creates no dedicated "Motion worker thread" workers. The 24 threads at the shared CRT start are all CRT-created threads in the process. The ten threads seen running 0x18b8fa0 are engine threads that run the physics job and execute the pair work inline. Which scheduler pool those ten belong to is not established (unverified).
5. Does the host velocity and pose path set the notify flag that reaches the pool guards? (unverified)
6. Can the pool guards be contended while held? Sampling never saw them held, but sampling is not proof.
7. Are the loading thread and idle task workers related to the pool guards? The sources say this is not established.
8. Indirect and vtable calls are not in the static graph, so the reach lists above are lower bounds on what can run.
9. Is the routine at 0x18b8fa0 entered during the hold? The notes say no (inferred).
