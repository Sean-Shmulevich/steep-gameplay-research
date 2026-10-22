# Snow actor batch preparation and identity

`engine.snow_batch` models selector-zero record gathering and the requested claim
size. The caller supplies stable registration snapshots. Python tokens, frozen
records and tuple ownership are authored representations; no native allocation,
locking, scheduling or object lifetime is provided.

## Recovered preparation

The first actor batch in each world substep creates a local job and a record
array. Under the first registration lock, gathering copies the first registration
list to tag-zero records, then the alternate list to tag-two records. Each native
record occupies 16 bytes, with tag at the beginning and actor pointer at byte 8.
The copies preserve source order and duplicates. Gathering does not apply player
wrapper gates, sleep tests or sport filtering.

```text
records = []
under registration_lock:
    for actor in first_registration_list:
        records.append({tag: 0, actor: actor})
    for actor in alternate_registration_list:
        records.append({tag: 2, actor: actor})
requested_claim_size = max(unsigned_record_count // 20, 1)
if records are not empty:
    configure_local_job(records, requested_claim_size)
    bind_elapsed_and_consumed_pair()
    submit_local_job()
    wait_for_claim_exhaustion_and_dispatch_completion()
```

The division partitions records, not time. Alternate records participate in the
count even though the selected tag-two visitor is a no-op. The job's chunk setter
and range claim behavior are separate operations described in the
[claim audit](SCHEDULER_BATCH_EPOCH.md). This module returns the requested size;
it does not silently equate that with a full worker execution policy.

The [instruction receipt](../../native/snow_host/snow_gather_validation.json)
compares six selector-zero gather cases against the portable model, including
empty lists, alternate-only data, duplicates and mixed lists. Lock and capacity
helpers are intercepted with sufficient storage supplied. It also compares the
isolated original division/clamp instructions against every unsigned 16-bit count,
65,536 cases. This does not test allocator growth, malformed headers or concurrent
registration. The portable gather rejects combined counts beyond the packed
14-bit capacity as an authored validation boundary.

## Conditional uniqueness and completion

The retained registration research identifies an insertion helper that searches
for the exact pointer and returns without inserting when it is already present.
The matching removal helper swaps the final entry into the removed slot. Both
are called under the list lock on the inspected registration path. These findings
come from retained private membership research, whose hash is recorded in the
receipt. Its build-specific anchors are insertion `140999d70`, pointer search
`1406cd390`, removal `140766ab0`, and swap-last helper `14115b8d0`. This pass
reviewed that finding; it did not rerun those registration helpers. See also
[the input audit](SCHEDULER_INPUT_AUDIT.md).

Thus an initially valid unique list maintained exclusively by the inspected
insertion/removal helpers remains unique. Gathering copies that invariant; it
does not enforce it. Duplicate fixture inputs correctly yield duplicate records.
Do not strengthen this conditional invariant into proof that every writer uses
those helpers or that every live batch has unique membership.

The nonempty first-batch path forces the explicit wait. Its first phase waits for
claim exhaustion; its second waits for job lifecycle zero and nonpositive signed
outstanding dispatch accounting. These are distinct from the claim count alone.
The [outer-loop check](research/scheduler.md#outer-world-loop-instruction-check)
places backend integration after the batch returns. This supports serial
substeps while allowing different workers to run their actor callbacks.

## Identity needed in the next capture

The job and callable are constructed in the batch caller's stack frame. Their
addresses may be reused in later invocations. A pointer alone is therefore not a
batch generation, and the outer request counter alone cannot distinguish its
substeps. The existing actor capture has neither a batch invocation token nor a
direct native substep index.

A future recorder needs an authored invocation token at batch entry, associated
with the local job and copied callable before submission. Carry that association
to record dispatch; retire it only after the explicit wait returns. Record the
outer world invocation separately. This is a proposed observation protocol, not
an identified native generation field or an installed hook. Account for recursive
helper dispatch and reused stack addresses. A thread ID cannot replace this
association because actor work migrates among workers.

The next unresolved join is the execution-context job pointer available at the
actor visitor and its relation to that batch-local job. Once established, the
existing player callback can be attributed to a batch without inventing a
substep index from elapsed time or record ordering.


## Actor-entry register attribution

A follow-up resolves a more direct local route than the proposed TLS lookup.
The [worker context contract](WORKER_THREAD_CONTEXT.md) establishes that scheduler
TLS holds the worker receiver, not a demonstrated current-job field. The selected
range visitor instead retains the job in a nonvolatile register while calling
its record dispatcher. The dispatcher tail-jumps to the actor wrapper.

At the original actor entry, before its prologue, this inspected route carries:

| Machine value | Established local role |
| --- | --- |
| RDI | Batch job pointer |
| RSI | Address of the worker's claimed-range base pointer slot |
| EBX | Reverse index within that claimed range |
| RCX | Actor pointer |
| Return address | Instruction after the visitor's callable dispatch |

Consequently the selected record address is:

```text
range_base = read_pointer(entry.RSI)  # copy now, not after return
record = range_base + 16 * unsigned(entry.EBX)
job = entry.RDI
actor = entry.RCX
```

The index is local to the claimed range. It is neither a global record index nor
a substep index. For a separately validated job record-array base, subtracting
that base and dividing by 16 yields the record index. The range-pointer slot is
reused after each claim, so deferred reads can identify a later range incorrectly.
The same applies to reading the record array after the batch returns.

The [instruction receipt](../../native/snow_host/actor_job_register_validation.json)
checks 72 visitor/dispatcher fixtures with mixed tags and shifted range bases,
including 72 actor entries. A second set joins the actual range worker, installed
job table, visitor and tag dispatcher in 81 cases, covering counts zero through
eight, claim sizes one/two/four and tail thresholds zero/two/five. All 324 actor
entries identify the expected job and record. The actor body is intercepted with
normal-return ABI behavior. The joined check is single-threaded and does not run
the outer scheduler or prove native lifetime protection.

This gives the next recorder a concrete entry observation. It must capture the
registers before a compiled C prologue can reuse them, then validate the expected
caller route, job type, readable range slot, record tag and actor identity.
Simply reading RDI inside the existing C callback is not equivalent. An ABI-tested
entry adapter is needed; none was installed by this pass. Failure to match this
route must produce unavailable attribution rather than accepting an arbitrary
register value as a job.

Job identity at actor entry is now locally established for this route. Mapping
that job to a fresh batch invocation and outer world invocation remains open.
The job address can still be reused. Thread migration, helper recursion and
simultaneously active worlds require explicit invocation identities in the
recorder. No original TLS current-job API or global exclusion guarantee follows.


## Authored entry adapter fixture

[The entry adapter](../../native/snow_host/snow_entry_thunk.S) now captures RDI,
RSI, RBX, the caller return address and entry RSP before entering compiled C.
It passes a temporary `SnowEntryRegisters` pointer as the fourth Win64 argument
to `SnowProbe_EntryDispatch`, retaining actor in RCX and the two scalar arguments
in XMM1/XMM2. The 72-byte stack allocation contains 32 bytes of callee shadow
space followed by the 40-byte snapshot. Windows unwind metadata describes the
allocation. No original executable instructions are included in this adapter.

The [test](../../tests/test_snow_entry_thunk.py) builds the adapter and an authored
C fixture with MinGW, then executes the resulting PE in Unicorn. It checks actor
and metadata forwarding, scalar bit preservation including signed zero and NaN,
callee stack alignment, return-address/RSP balance, all eight nonvolatile integer
registers and XMM6 through XMM15. The test overwrites every callee shadow slot at
C entry to detect overlap with the snapshot. It checks that the adapter has an
exception-directory entry; it does not exercise Windows exception unwinding.

```sh
python3 -m unittest tests.test_snow_entry_thunk -v
```

This test requires `x86_64-w64-mingw32-gcc` on PATH and `pefile` plus `unicorn`
importable by Python. It explicitly skips when those dependencies are absent;
a skipped test is not adapter validation. The development pass ran it with all
dependencies present and passed all three scalar/register configurations.

The fixture is deliberately not linked into the live probe yet. Its C dispatch
implementation only records values. A real dispatch must validate the return
route and guarded job/range/record reads, copy ephemeral data immediately, and
forward the original call exactly once. The snapshot pointer must not escape
the dispatch lifetime. Exceptions and nonlocal exits are outside the tested
normal-return contract. This proves adapter calling-convention behavior under
emulation, not Wine integration, native job lifetime or batch-generation identity.


## Guarded entry attribution decoder

[snow_entry_attribute](../../native/snow_host/snow_entry_attribution.h) accepts
captured entry registers, the actor argument, an externally verified build
profile and an exact-read callback. It checks the return address before any
memory read, then checks job table, job record-array base and initial count,
callable pointer/table, range-pointer slot, actor table and selected record.
The selected record must have tag zero and the same actor pointer. Range offset
and index must fit the initial record count and 16-byte record alignment.

The initial count comes from job+0x1a4, initialized alongside remaining count
job+0x1a0 by the inspected batch constructor call site. The decoder deliberately
does not bound records by remaining count: claimed callbacks can execute after
remaining reaches zero. The supplied profile holds build-specific expected
tables and caller return address; this module does not guess them or acquire a
player. Combined count beyond 0x3fff is rejected as an authored domain bound.

The decoder repeats its observations and rejects differences. It clears all
output on failure, bounds address arithmetic against uint64 overflow, makes at
most 18 exact reads, and performs no game writes. This bracket check cannot detect
ABA or pin a job, actor or record array. Successful output means the observations
matched this route, not that object lifetime or concurrent writer exclusion was
proved. Job and record addresses are private trace data and do not identify a
fresh batch invocation by themselves.

The native fixture exercises a shifted claimed range and index, each of the 18
read failures, changes to all nine observed fields between passes, wrong return
route, misalignment, out-of-range and overflowing indices, zero/excess count and
address overflow. All failed cases produce zero output. Run it with:

```sh
python3 -m unittest tests.test_snow_update_trace.SnowUpdateTraceTests.test_entry_attribution -v
```

This decoder remains separate from the live recorder. Integration must copy the
result before forwarding, record failed attribution explicitly, and preserve
exactly-once forwarding regardless of attribution success. The original call
must never depend on a successful optional observation.


## Recorder attribution channel

The recorder core now provides `snow_trace_call_attributed` with an optional
invocation-local observation callback. It reserves a record first, records its
entry timestamp, invokes attribution, captures before-state, forwards the original
call once, then captures after-state. Attribution failure clears its payload and
continues. The original `snow_trace_call` remains a no-attribution adapter.

Records distinguish `attribution_attempted` and `attribution_valid`. A full or
closed recorder forwards without running optional attribution. The observation
callback must be bounded, non-mutating and return normally. Faults, exceptions or
nonlocal exits are not contained by the core. Existing close/drain, cached-caller
and lifetime limits still apply.

The native fixture checks success, partial-output failure, full-buffer and
closed-capture forwarding. Every invocation forwards exactly once in those
cases; failed output is zero and unattempted records remain explicitly unattempted.
Existing nesting and concurrent capture tests continue to pass. The experimental
probe record ABI is now version 3, requiring matching rebuilt headers and binaries.
The JSON exporter includes the two validity fields and, only for valid attribution,
private job identity plus record index/count. These raw identities must stay out
of public aggregate receipts.

The Windows host, probe and optional capture plugin were rebuilt successfully.
The live dispatcher still uses the original no-attribution entry route. Wiring
the assembly thunk, verified profile and guarded decoder into that dispatcher
remains the next integration step; the new fields must not be reported as live
job observations until that step and an actual capture pass.


## Opt-in probe wiring

The probe now offers `SnowProbe_ConfigureAttributed`, which copies an immutable
entry profile during its one-time configuration. Installation selects the entry
thunk for this mode, and restoration compares against that same target. Selected
actor calls use the guarded attribution callback; unrelated actors forward
without attribution. The regular configuration API retains its existing route.

The optional capture plugin enables this with `[capture] attribute_jobs=1`.
Default is zero. Its existing held-player acquisition verifies the adapter build;
additional checks join the job visitor and callable dispatcher tables before
configuration. All sources are included in both public build commands and the
bounded session launcher. Configuration alone neither installs nor launches.

Twenty-five focused tests passed, including the compiled entry adapter and
native guarded-reader/recorder fixtures. The complete host, probe and optional
capture plugin built with MinGW. A separate authored Wine fixture passed the
existing normal capture and competing-slot cases with the rebuilt probe.
The attributed-mode fixture also passed with a deliberately wrong return route:
its record marks attribution attempted but invalid, the update forwards, and
slot conflict/restoration plus late forwarding still work. These fixtures use
synthetic objects, not a running game.

Actual game attribution, successful integrated native attribution, and batch
invocation generation remain separate validation gates. Do not treat a successful
build or optional-mode installation as evidence that a game job was identified.


## Integrated successful-attribution fixture

An authored assembly caller now supplies job, claimed-range slot and local index
through the recovered register convention. Its own return label supplies the
expected route. Synthetic job, callable and record storage are built in the
Windows fixture. Calling through the installed actor-table slot reaches the
entry thunk, guarded decoder, recorder and original synthetic update.

The Wine fixture confirms valid attribution to record index 3 in a five-record
array, with the range beginning at index 2 and local index 1. It also exercises
slot conflict refusal/restoration, unrelated-actor forwarding, closed capture,
late calls and module pinning. All stored pointers describe authored fixture
objects. This closes successful integrated attribution under Wine for the
fixture, not game job identity or generation.

The reproducible runner builds fresh sources and runs normal, conflict,
invalid-attribution and valid-attribution modes:

```sh
python3 scripts/test_update_probe_fixture.py --wine /path/to/wine \
  --prefix /path/to/existing-fixture-prefix --out /tmp/new-probe-fixture-output
```

Supply an existing dedicated fixture prefix. Outputs must be outside the repo in
a new directory. Logs remain there; the terminal prints a bounded result summary.
The runner launches only its authored fixture executable and loads its authored
probe DLL. It does not launch or install into the game. These checks do not test
native game concurrency, exceptions, stack reuse across batch generations or
full Windows exception unwinding.


## First live actor-to-job attribution

The [aggregate live receipt](../../native/snow_host/entry_live_observation.json)
records 221 selected player calls during a two-second attributed capture. All
221 passed guarded attribution; none were rejected, malformed or dropped.
Installation, restoration and drain passed. The session completed its subsequent
health observation, stopped the bottle, restored temporary launch settings and
verified the original DLL without replacing it. Raw pointer-bearing JSONL and
screenshots remain private.

There were ten distinct job addresses. Every captured batch reported initial
record count one. The calls formed 216 observed request groups: 211 single-call
groups and five two-call groups. All groups matched float32 consumed/count timing.
All five two-call groups reused the same job address within the request. Therefore
job address plus outer request does not distinguish their two invocations. This
is concrete evidence for keeping a separate batch invocation/substep identity.
It is not proof that a native generation field exists.

No captured player intervals overlapped; 182 of 220 neighboring calls changed
worker thread. Every pre-consumption counter pair decremented once. All 221
countdown pairs matched elapsed subtraction, including ten where elapsed and
consumed differed. These markers corroborate the existing route without proving
an exact pending-consumer entry or the timing of input publication.

To request the same bounded observation in the configured research workspace:

```sh
python3 scripts/run_late_load.py --experiment host --load-at startup \
  --plan update-capture --attribute-jobs
```

This launches the game, uses a five-minute watchdog, navigates recognized startup
screens, captures for two seconds and restores. Leave controls alone during the
automated sequence. The controller now refuses to call an attribution-requested
capture successful when it has no valid attributed records. Aggregate analysis
separates unavailable, unattempted, rejected, valid and malformed attribution;
unique job addresses are explicitly not counted as batch generations.

The next unresolved edge is batch invocation identity and its connection to input
ingestion. The entry shim and actor/job/record link have now been exercised in
the original process. That does not establish full scheduler reconstruction,
universal no-overlap behavior, safe arbitrary-thread mutation or deterministic
replay.


## Direct outer-loop ordinal in the batch frame

The live job pointer provides a build-specific route back to the batch caller's
saved registers. Let S be stack pointer at entry to the first actor-batch routine.
Its prologue saves RBX at S+8 and RDI at S+24, pushes three registers, sets
RBP=S-24-0x1ae0, and constructs the local job at RBP-0x60. Thus job=S-0x1b58.
For the inspected outer world-loop call site, RBX is the timing owner and EDI is
the zero-based loop ordinal. The batch saves these before using its own registers.

```text
batch_entry_rsp = job + 0x1b58
caller_return  = read_u64(job + 0x1b58)
timing_owner   = read_u64(job + 0x1b60)  # saved outer RBX
loop_ordinal   = read_u64(job + 0x1b70)  # saved outer RDI
```

The expected caller return is the instruction immediately following the first
actor-batch call in the outer loop, `141389ad8` in this analyzed image. This check
must precede interpreting the saved registers. It is distinct from the visitor
return address already checked at actor entry.

The [instruction receipt](../../native/snow_host/batch_frame_validation.json)
executes the original outer loop plus original batch prologue and epilogue in
12 scenarios. At the constructor call, its RCX supplies the actual job address.
The test reads the derived stack locations and verifies the caller return,
timing-owner pointer, owner-to-world link and ordinal sequence. It covers zero,
one, two and five iterations, synthetic count changes, and outer counter wrap.
A supplied gather count makes the constructor reachable. Construction, submission,
wait, actor execution and backend calls are bypassed; this is a frame-layout join,
not a concurrent or live-frame read. No frame offsets were inferred by scanning
for plausible pointer values.

A bounded future observation can join these reads with:

```text
require caller_return == verified_outer_loop_return
require timing_owner points to the already attributed world
selected_count = read_u32(timing_owner + 0x1390)
require loop_ordinal fits uint32 and loop_ordinal < selected_count
elapsed_bits  = read_u32(timing_owner + 0x1394)
consumed_bits = read_u32(timing_owner + 0x136c)
outer_counter = read_u64(world + 0x20)
```

Compare both scalar bit patterns with the callback arguments and bracket all
identity/control reads. The outer counter here is the loop's own completion
counter; do not silently identify it with the existing trace's request field,
which came from a separately resolved started counter. Their live relationship
needs measurement. Likewise, the ordinal would be a direct observation of the
outer loop index for this call route, not a globally unique invocation ID.

The first batch's explicit wait keeps its caller frame active while ordinary
workers execute. That provides a conditional lifetime argument for this route,
but the memory-reader must still reject bad addresses, changed links, unexpected
callers and mismatched world identity. A different batch caller invalidates this
saved-register interpretation. Game exceptions, alternate entry routes and
reentrant worlds remain outside the checked cases.

This is the next attribution extension to implement and test before another live
capture. The existing live receipt contains no such saved-register reads and
must continue to report direct native substep indexing unavailable.


## Bounded batch-frame reader

[snow_batch_frame](../../native/snow_host/snow_batch_frame.h) implements the saved
frame observation as a separate optional reader. The caller must first establish
the actor/job route with the existing attribution decoder. It then supplies that
job, the expected outer-loop return address, independently bound world and the
actual callback's two scalar bit patterns.

The reader checks the expected return before interpreting saved registers. It
requires the saved timing owner to reference the expected world, ordinal strictly
less than the unsigned selected count, and exact scalar-bit agreement. Two passes
compare caller, owner, ordinal, world, count, scalars and outer completion counter.
It performs at most 16 exact reads and clears its entire output on failure. Zero
ordinal and zero completion counter are valid observations, not missing sentinels.
Saved ordinal upper bits cannot be silently truncated into an apparently valid
32-bit index.

The [native fixture](../../tests/fixtures/snow_batch_frame_fixture.c) checks every
read failure, all eight fields changing between passes, unexpected caller/world,
zero count, ordinal bounds, nonzero upper ordinal bits and address overflow.
It checks both first/second substep positions and zero/maximal outer counters.
The fixture uses synthetic memory. No process writes, game launch or stack probing
occurred in these checks. Bracketing still does not pin lifetime or detect ABA.

This reader has not yet been connected to capture records. Its outer completion
counter must remain separate from the existing request field, and missing frame
attribution must not invalidate an otherwise valid actor/job observation. The
next step is additive recording of this optional result with explicit validity,
followed by a fixture and bounded live capture.


## Optional frame capture integration

The experimental record/profile ABI is now version 4. `SnowEntryProfile` has an
optional `batch_return`, with zero disabling frame reads. After successful job
attribution, the dispatcher calls the batch-frame reader with the already-bound
world and bit-copied scalar arguments. Its result is recorded independently as
`frame_valid` plus frame metadata. A failed frame read preserves valid job
attribution and exactly-once forwarding. Legacy no-attribution calls leave both
optional results unavailable.

The selected game capture plugin supplies the verified outer-loop return for
this build. Valid JSON records now include `substep_ordinal`, `selected_count`
and `outer_completion_counter`. These fields do not replace `before.request`,
`after.request` or the existing snapshot's optional substep field. The completion
counter's live relationship to the request counter remains unmeasured.

The [integrated fixture receipt](../../native/snow_host/batch_frame_fixture_validation.json)
passed five Wine modes. Successful attribution records ordinal 1 of 2 and outer
counter 42 through the installed thunk, guarded readers and recorder. A timing
mismatch keeps job attribution valid, rejects the frame and zeroes its payload.
Normal, conflict and wrong-route cases still pass. The recorder's native tests
also verify clearing a partially written frame on invalid results. All fixture
objects and values are synthetic; no game launched in this integration pass.

The host, probe and optional capture plugin build with the new sources. All users
of the experimental ABI must rebuild together. Next is a bounded original-game
capture plus analysis that compares direct ordinals against the existing request
groups, without silently treating either counter as the other's generation.


## Enclosing world versus physics manager correction

The first original-game frame attempt produced 248 valid job attributions and
zero valid frames. The [rejected-frame receipt](../../native/snow_host/batch_frame_rejected_live.json)
preserves that failure separately from successful slot restoration, capture drain,
zero drops and session cleanup. The general capture controller passed because it
required job attribution; this is explicitly not a successful direct-ordinal run.

A static ownership recheck identified an incorrect argument in the integration:
`binding.world` names the actor's enclosing world object. The timing owner's first
pointer names that world's physics manager. Those objects are joined through
`binding.world + 0xff0`, and the manager's +0x18 points back to the timing owner.
The earlier frame-layout discussion's generic word "world" denoted this manager;
it must not be equated with the binding's world field. The synthetic fixture had
collapsed those objects and did not catch the mismatch. No frame reads were
accepted in the affected live run.

The corrected probe verifies:

```text
physics_manager = read_pointer(binding.world + 0xff0)
expected_timing_owner = read_pointer(physics_manager + 0x18)
frame = guarded_frame_reader(job, expected_return, physics_manager, clocks)
require frame.timing_owner == expected_timing_owner
require both ownership links still match on reread
```

The frame output now calls its manager field `physics_manager`. Its completion
counter resides at physics_manager+0x20, not enclosing_world+0x20. The two added
ownership links add at most four exact reads around the 16-read frame reader.
Failure preserves valid job attribution and clears the optional frame result.

The [corrected fixture](../../native/snow_host/batch_frame_world_join_validation.json)
uses distinct enclosing-world, manager and timing-owner objects and passes all
five Wine modes. This is fixture validation only; a corrected live run is still
required. The analyzer now distinguishes direct frame validity from timing-derived
group matches and reports partial/repeated ordinal sequences without inventing
missing steps. It compares the request and completion counters numerically modulo
2^32 while explicitly withholding semantic equivalence or global generation claims.
