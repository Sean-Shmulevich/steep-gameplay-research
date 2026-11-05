

### Live invocation capture

The two snapshot checks evaluated captured state offline. This check records
real in-game calls of `18b8860` instead. The receipt is
`native/snow_host/pose_connectivity_live_invocation_validation.json`.

**Capture point.** `18b8860` has exactly two static call sites, `18b8757` and
`18b8776`. Both are inside controller listener `18b8670`, in event 0. Nothing
calls `18b8670` directly, and no image pointer to it is stored. It is reached
only through a row of the global body-listener registry (descriptor pointer at
image `0x33367c0`), which broadcaster `18a7f60` calls as
`row.callback(body, event)`.

A private plugin swapped that one row's callback to a detour, using an aligned
8-byte compare-exchange on heap data. No code bytes or page protections were
changed. The detour always forwards to `18b8670`. Before installing, the plugin
checked:

- the image base;
- fingerprints of `18b8670`, `18b8860` and `18a7f60`;
- that both call sites decode as `call rel32` to `18b8860`;
- that exactly one enabled registry row holds `18b8670`.

On restore, the plugin scanned the current registry for rows holding the detour,
compared and swapped them back, waited for in-flight calls to drain, and kept
the module pinned.

The detour classifies each event-0 call by the listener's own gate:

- **Path A:** priority bit 15 clear and metadata+0x1c != controller+0x4c. The
  listener stamps the metadata and calls `18b8860`.
- **Path B:** priority bit 15 set and quiet nibble 2. The listener calls
  `18b8380`, then `18b8860`.
- **Neither:** any other event-0 call.

For path A calls, the plugin copies the walked refresh regions just before
the listener runs and again just after it returns, using self
`ReadProcessMemory`. The regions are: body, metadata, owner, controller,
context, provider with its node array, slot owners and their +0x28 vectors,
+0x80 ring links, endpoint bodies with their metadata and rings, tree values,
contact spans, and groups with their slot arrays and members. Session 1
captured the first 32 path A calls. Sessions 2 and 3 captured only calls whose
+0x80 head was nonempty, at most 4 per body.

Offline, the expected post-state is the pre-state plus the listener stamp,
with `analyze.run_python` (same stubs) applied. That is compared with the
post-state the game produced at every captured address. Differences are
attributed to the services that really ran in game (`18e2de0`, allocator,
pool return, listener enter/leave). Any other difference is unattributed and
fails the pair. Native `18b8860` also runs in Unicorn on the stamped pre-state
as a coverage cross-check.

**Results.** Three sessions used director startup and forward holds (scan 17,
1500 ms). The plugin armed when a player body first had a controller and a
+0x80 head. Install windows were 150, 150 and 300 s. In every session the row
was restored (no conflicts, the detour absent afterwards, one `18b8670` row) and
in-flight calls drained. Cleanup was fully verified.

While installed, the listener received 149,689 calls, 90,549 of them event 0.
Of those:

- **Path A:** 10,552 calls.
- **Path B:** 0 calls.
- **Neither:** 55,535 calls.
- **No controller:** 24,462 event-0 calls had a null or unreadable controller
  chain.

Every path A call whose ring state was recorded had an empty +0x80 ring: the 32
captured, plus 6,775 and 3,694 counted in sessions 2 and 3. The other 51
session-1 calls were not split. Session 3 counted 3,694 path A calls on 1,276
distinct bodies, all with class table `0x29c98c8` and none of them player
bodies.

Session 3 also counted event-0 calls on bodies with a nonempty ring: 19,078,
all with priority bit 15 set and quiet nibble 0, so the listener calls neither
`18b8380` nor `18b8860`. Of these, 18,516 were on the player's main and rider
bodies, which carry priority `0x8002`.

The 32 captured invocations, all on world bodies, each matched the Python
chain:

- **Path taken:** empty-ring early return, with no rows, selection or service
  calls.
- **Bytes:** 405,296 bytes compared. Of these, 64 changed in game: exactly the
  four stamp bytes per call, all predicted.
- **Differences:** 0 unattributed differing bytes. Nothing else in the captured
  regions changed, including the controller enter/leave bytes and any effects
  of `controller28` virtual+a8.
- **Cross-check:** Unicorn agreed with Python in 32 of 32 runs, with 0
  coverage gaps.

Pre and post reads ran on the same thread around each call. Sampled walks took
0.05–0.9 ms.

**Interpretation.** The empty-ring early return is now confirmed on real
invocations. The selection, rebuild and retire paths were not reached by any
observed in-game call. The bodies that carry selector-1 links (player and
ragdoll/world bodies) receive event 0 only with priority set and quiet 0. Session 2's
window included two crash detaches and one respawn. Those paths
therefore remain validated only on synthetic data and live snapshots.

Limits:

- **Atomicity:** pre and post reads are sequential self-reads, not atomic.
- **Bracket:** the capture brackets the whole listener call, not `18b8860`
  alone.
- **Untested branch:** path B never occurred, so it was never tested.
- **Removal hazard:** native removal `18bb610` does not guard a failed search.
  Short install windows bound this hazard but do not exclude it.

**Leads.** Nonempty-ring refreshes probably come from somewhere other than this
listener branch. Candidates are a quiet-2 wake (path B), or link creation
paths that call the selection, rebuild and retire services directly. Next
steps:

- Find other callers of `18dedf0`, `18e28d0` and `18de440`.
- Capture around priority-set bodies whose quiet nibble becomes 2.

### Broadphase pair lists

The object at controller+0x28 is the "Dynamic tree multi-threaded broad phase"
instance (string at image 0x29c9ce0), built by `193f450` (vtable `0x29ca8a0`,
allocation size 0xb10, base constructor `199a760`).

**Why this vtable is the installed one.** The controller constructor `18b8150`
stores its second argument at controller+0x28 (`18b8172`). It has two callers,
the factories `18ae130` and `18b64f4`. Both allocate 0xb10 bytes and construct
the object with `193f450` before passing it in. `193f450` has exactly these two
callers, so there is no sibling or derived broadphase class. Slots 0x40, 0x48,
0x60 and 0x68 of `0x29ca8a0` hold the four getters below (checked in the
harness).

**Accessors (all leaf, no side effects).**

    slot 0x40  1940410  count = u32 [ [obj+0xf8] + 8 ]
    slot 0x48  1940400  data  = ptr  [ [obj+0xf8] + 0 ]
    slot 0x60  19403f0  count = u32 [obj+0x120]
    slot 0x68  19403e0  data  = ptr [obj+0x118]

Siblings not used by the controller: slot 0x50 (`140e5df50`) returns u32
[obj+0x110] and slot 0x58 (`1419403d0`) returns ptr [obj+0x108], a third list
with the same inline layout (capacity u32 at +0x114).

**Storage.** `[obj+0xf8]` points at one of two vector headers `{data, count u32,
cap u32}` stored at obj+0xd8 and obj+0xe8 (base constructor `199a760`, stores
at `199a930` and `199a93e`). The per-step routine `199c880` swaps `[obj+0xf8]`
and `[obj+0x100]` (and copies the result to +0xd0), so the "current" header
alternates between steps. The append helper `199b590` pushes onto the current
header's vector, growing through `1940990`. The list at +0x118 is not a header:
data at +0x118, count at +0x120, capacity at +0x124 (initial capacity 0x20
rows, allocation 0x300 bytes).

**Pair row, 24 bytes (0x18).** Evidence from consumers and the append helper:

    +0x00  first body pointer   (consumers read body+0x30 -> shared state)
    +0x08  second body pointer
    +0x10  64-bit pair key      (0x18dedf0 reads it; 0x18ddd30 passes rows on)

`18ddd30` indexes rows as index*3*8 and reads +0/+8; `18dedf0` steps by 0x18 and
reads +0 and +0x10; `199b590` writes 16 bytes then 8 bytes per row.

**Controller use (`18b8fa0`, for orientation only).** Slots 0x60/0x68 (list at
+0x118) feed `18dedf0(provider, rows, count, buffer)` and then `18e28d0`. Slots
0x40/0x48 (current header) feed pair-link jobs `18ddc40(provider, rows, count,
buffer)`. The role names "removed" and "added" are inferred from that order
and from `18dedf0` locating existing links by key; they are not proven by a
producer trace.

Validation. `engine/pose_broadphase_pair_lists.py` has the four accessors plus
an authored row decoder. `check_pose_broadphase_pair_lists.py` ran 512
randomized cases in Unicorn over the memory image (2048 native getter runs).
Each compares rax to the Python accessor and requires object, header, row and
removed-array bytes to be unchanged, with return address and stack pointer
checked. Half the cases use an inline header (obj+0xd8/+0xe8), half a heap
header. 325 cases have added rows and 334 removed rows; 8 use a count with the
high bit set. The vtable slots were statically compared to the getter
addresses. Injecting the wrong count offset (+0x124 for +0x120) failed the
harness on case 0; restored and regenerated. Pose tests green (910).
Receipt: `native/snow_host/pose_broadphase_pair_lists_validation.json`.

Limits: only leaf getters run natively. The producers that fill the lists
(`199b590` callers, the broadphase update virtuals 0xc8/0xd0/0xa0) are not
reconstructed, and the row field meaning is from consumer reads.

Static leads: reconstruct slot 0x98 (`199b590`, append) and slot 0xa0
(`14199ed90`), the step `199c880`, and the dynamic-tree update behind virtuals
0xc8/0xd0; find which one writes the +0x118 list.

### Pair update step

`18b8fa0(controller)` (unwind `0x18b8fa0..0x18b90b2`) is the per-substep driver of the
select / rebuild / retire chain. The live capture showed that the body-event refresh
`18b8860` never runs with a nonempty ring, so this routine is the real driver. Module:
`engine/pose_pair_update_step.py`.

The controller is the 0x78-byte object built by `18b8150`. Its fields:

- `+0x28`: the broadphase.
- `+0x30`: the island context (the "Multi threaded island manager", 0x4a0 bytes, built by `18e0ca0`).
- `+0x38`: the provider (the "Narrow Phase", 0x190 bytes, built by `18dc300`).
- `+0x48`: the phase word. The constructor sets it to 0.
- `+0x4c`: the frame counter. The constructor sets it to 1.

The factory `18ae130` builds all four objects.

```
controller+0x48 = 1
19598b0(controller+0x28)            ; = bp->vfunc[0x90] () (update); returns 1, ignored
output = {ptr = inline[0x200], count 0, cap 0x200}   ; 0x1000-byte stack buffer
bp = controller+0x28
n = (u32) bp->vfunc[0x60] ()         ; removed-pair count, called before the array
a = bp->vfunc[0x68] ()               ; removed-pair array
18dedf0(controller+0x38, a, n, &output)    ; select (resets output count itself)
18e28d0(controller+0x30, &output)          ; rebuild
bp = controller+0x28
n = (u32) bp->vfunc[0x40] ()         ; new-pair count
a = bp->vfunc[0x48] ()               ; new-pair array
18ddc40(controller+0x38, a, n, &output)    ; pair jobs; their retire 18de440 consumes output
if output.cap != 0 and output.ptr != inline: allocator[0x1433365b8]->vfunc[0x18] (ptr)
(controller+0x28)->vfunc[0x88] ()    ; `ret 0` stub 0x75e600 in the observed class
controller+0x4c += 1
u32 (controller+0x28)+8 = controller+0x4c
18df490(controller+0x38, controller+0x4c)  ; provider u32 +0x180 = frame
controller+0x48 = 2
return 1
```

`19598b0` is `bp->vfunc[0x90] (); return 1`. `18df490` is `mov [rcx+0x180], edx; ret`. Both are reconstructed inline.

Preserved quirks:

- **One shared output vector.** The same output vector feeds select, rebuild and the
  pair jobs. The links selected from removed pairs are retired inside `18ddc40` (its
  `18de440` call), using the worker-count divisor rather than the refresh's divisor of 1.
  The vector is never cleared between stages.
- **Field reloads.** Every controller field is reloaded at each use. The broadphase
  pointer is read 5 times: the update, the removed lists, the new lists, `+0x88` and the
  `+8` store. The provider is read 3 times, and `+0x4c` is reloaded after the increment.
- **Count truncation.** Only `eax` is used from the count getters (u32).
- **Release check.** The output buffer is released only when its capacity is nonzero
  and its pointer is not the inline buffer. An external pointer with zero capacity is
  kept.
- **Return value.** The routine always returns `al = 1`. The thunk `18ae2b0` discards it.

Pair row format: both broadphase arrays hold 24-byte rows {bodyA, bodyB, u64 key}, the
same rows that the refresh `18b8860` builds. Two pieces of evidence confirm this: the
`add r14, 0x18` stride in `18dedf0`, and `index*24` in the pair worker `18ddd30`. The
broadphase lane's `engine/pose_broadphase_pair_lists.py` decodes them. The getters of the
observed class (vtable RVA `0x29ca8a0`) are:

- `+0x40`: `[[obj+0xf8]+8]`
- `+0x48`: `[[obj+0xf8]]`
- `+0x60`: `[obj+0x120]`
- `+0x68`: `[obj+0x118]`

These getters are also exposed as `pose_dynamic_tree_broadphase_vcall`. Its update
`199c880` swaps `+0xf8`/`+0x100` and stays supplied.

**Validation.** `check_pose_pair_update_step.py` ran 512 Unicorn cases of native `18b8fa0`
over the memory image (receipt `native/snow_host/pose_pair_update_step_validation.json`).
`19598b0` and `18df490` ran natively.

- **Vtable modes.** 256 cases used the real vtable `0x1429ca8a0`, so the four getters
  and the `+0x88` stub ran natively and only `199c880` was supplied. The other 256 used
  a fixture vtable that routes all six slots to supplied stubs, with garbage in the
  upper 32 bits of the counts.
- **Mutation.** 256 cases mutated controller `+0x28/+0x30/+0x38/+0x4c` and the broadphase
  lists from inside the services.
- **Comparisons.** The harness compared:
  - 3,398 service calls, with their arguments;
  - 16,452 24-byte rows;
  - the output descriptor state (count, capacity, inline or external, items) at each stage;
  - all fixture bytes.
- **Output storage.** 101 outputs grew past 0x200 entries. 70 were released and 31 were
  kept, being external with zero capacity.
- **Injected bug.** Releasing without the capacity check was caught, and the receipt was
  regenerated after the restore.

Composition test (`tests/test_pose_pair_update_step.py`): the full-chain scenario,
driven through the broadphase lane's getters, select, rebuild, the pair jobs and the retire
stage, reaches the same end state as the refresh chain: 3 tree keys removed, queue (10,
60, 30), groups GA and GB processed. It also shows the added row published at provider
`+0x170` for dispatch. Limits:

- Select, rebuild, the jobs, the broadphase update and the allocator are supplied (each
  has its own receipt).
- The select hook emulates output growth; `18df270` does not run.
- The harness is single-threaded, and this routine has no live validation.

Static leads:

- **Caller.** `18ae2b0` (`call 18b8fa0; ret`) is entered only by a tail jump from
  `0x140b1a0` (`mov rcx,[rcx+8]; jmp 18ae2b0`). That stub's only caller is `0x1389afd`,
  inside `1389a50`.
- **`1389a50`.** This is the broadphase job body. When profiling global `0x143075a88`
  equals 2, it opens a profiler scope named `"Physic::UpdateBroadphase"` (string RVA
  `0x2913250`). It then loops over substeps (count at `this+0x1390`, dt at `+0x1394`):
  `13c30c0`, then `140b1a0` (this step), then `140efa0(dt)`, `140b3d0` and `13c08f0(dt)`.
  So the pair update runs once per physics substep, with the controller at `[[this]]+8`.
- **Scheduling.** Nothing calls `1389a50` directly. Setup `136a550` stores it as a delegate
  at record `+0x2c0` (lea at `0x136aacf`), just before it names the job
  `"PhysicsWorldStep"` in batch `"Physic::PhysicsUpdate"` (`0x136ab7e`/`0x136ab8e`). That
  is probably the PhysicsWorldStep job's broadphase delegate, but the delegate-to-job
  binding has not been verified.
- **Controller factory.** `18ae130` (called from `13d1c8e`) allocates 0xb10 bytes for
  the broadphase (`193f450`, string "Dynamic tree multi-threaded broad phase"), 0x190 for
  the narrow phase, 0x4a0 for the island manager, and 0x78 for the controller (`18b8150`).
  The controller's vtable is at `0x1429ca0e0`.
- **Other callers.** The live gap is closed by capturing this routine rather than
  `18b8860`. A rel32 scan finds that `18dedf0` and `18e28d0` are called only from the
  refresh (chunk `18b88e1`) and from this step. `18de440` is called only from the
  refresh and from `18ddc40`, and `18ddc40` only from this step. So in gameplay, every
  select, rebuild and retire runs inside `18b8fa0`.
