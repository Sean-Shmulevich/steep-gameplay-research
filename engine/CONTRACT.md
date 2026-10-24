# Shared implementation contract

This independent Python engine is built alongside the research. Z is up, +X forward, +Y left. Distances/time in our scenarios are metres/seconds. These units and integration architecture are explicit implementation choices. Quaternion arrays are XYZW. No game assets.

Body dictionary: position [x,y,z], velocity [x,y,z], orientation [x,y,z,w], angular_velocity [x,y,z], grounded bool, mass positive scalar. Subsystems may add JSON-compatible state under dedicated keys. No clock, RNG or global mutable state in numerical kernels.

Controls dictionary: steer, flip, lean in [-1,1]; brake, tuck, jump, grab boolean. Sport is snowboard, ski, walking, wingsuit or paraglider. dt is explicit seconds. Parent runtime owns tick, time, input generation, events, reset and checkpoint.

World.sample(x,y) returns {height, normal:[nx,ny,nz], material:{name,density,thickness,normal_frequency,tangent_frequency,grip}, velocity:[0,0,0]}. Synthetic plane/ramp/obstacle world. World.to_dict() gives immutable scenario description. Physics must not derive material from graphics.

physics.step(body, controls, world, dt, config) mutates only body, returns JSON diagnostics. Snow ski/board and walking contact handled there. config sport selects mode. Prototype policies must be labeled in diagnostics or module evidence. Real recovered numerical helpers from reference may be called. No data copies from authored assets.

domains.step_air(body,controls,dt,config) mutates only body, returns diagnostics for wingsuit/paraglider. domains.step_environment(state,dt,config) mutates environment dict. Air/world ground collision resolved by parent. Environment must not silently alter snow grip.

animation.evaluate(rig, clips, state, dt, inputs) returns {state, local_pose, model_pose, diagnostics}. All JSON-compatible. Rig and clips are caller-provided, validated; synthetic default rig permitted. Physics input includes body orientation/grounded/speed but animation NEVER mutates body. State includes clip/time or crossfade fields as module documents. Expose palette optional helper and validate resources. animation.default_resources() returns synthetic rig/clips. Integrator can use module docs/signatures.

Parent owns runtime.py, world.py, math3d.py, input.py, assets.py, replay.py, cli.py, browser demo and root README/progress. Workers own only assigned files and tests. All run from repository root with python3 -m unittest discover -s tests. Standard library only. No game launch/injection, no git publication by workers.

Paused mod action: Engine.adjust_speed(delta_speed) uses the authored policy
specified in engine/README.md, "Paused brake/boost mod". SchedulerController owns
token validation, serial execution and isolated publication; HTTP exposes the
same operation. No original-game setter equivalence is claimed. Success preserves
angular velocity and clocks and appends a replayable speed command; failed
validation publishes no mutation.

Paused impulse action: Engine.apply_central_impulse consumes a finite float32 XYZ
impulse once using reference.central_impulse. The single independent body is
assumed dynamic and unsuppressed; inverse mass comes from its positive scenario
mass. No dispatch/wake or paired rider behavior is implied. Spin, rigid angular
momentum and clocks are untouched. Controller publication is isolated, tokened
and replayable. Native host integration remains separate and unimplemented.

Command-manager startup: `allocate_construct_publish` requests receiver storage
through supplied allocator services with arguments (384, 8). Nonzero storage goes
to the supplied constructor; zero storage skips it and selects an explicit
uint64 fallback corresponding to incoming RSI. The selected result goes to the
publisher after normal return. Caller-supplied services own storage, lock/container
behavior and cleanup; no live access, native failure policy, rollback, lifetime
pin or concurrent publication safety is implied.

Allocation policy: `select_allocation_context` consumes uint32 size/alignment and
opaque uint64 context identities, preserving resolver precedence and unsigned
low-16-bit comparison. `allocate_bytes` dispatches by alignment <=16, returns
zero for size zero, and permits at most one retry based on the recovery result's
low byte. It reloads the allocator on retry. All native heap methods, context
resolution and recovery bodies remain supplied; Python argument validation and
exception propagation are authored interfaces, not native failure guarantees.

Size-context resolution uses supplied 15-entry and exact-size context tables.
`allocation_context_resolver.resolve_allocation_context` preserves uint32 bitwise
rounding, automatic alignment sentinel and the unsigned virtual-query threshold.
The source token is unused by the recovered routine. Zero means no context from
this resolver and lets the caller apply its fallback. Argument validation is our
Python interface, not recovered native failure behavior. Query implementations,
heap identities, ownership and deallocation remain external.

`command_record_cleanup.cleanup_record` models normal-return record retirement
with detached dictionary references. It nulls the associated reference before its
release, clears the invoker afterwards, then decrements holders at +0x10 and +8.
Associated destruction uses old full count ==1; holder release uses new low24 ==0.
Holder aliases are preserved and decremented twice. Supplied release services
may update holder state; the next decrement observes those updates. No concurrency or native lifetime pin is
provided; repeated cleanup is not an idempotent operation.

`holder_release_queue.release_holder_to_queue` models serial valid-ring behavior
with caller-supplied lock, growth, cleanup and post-unlock services. Bit 24 is set
before growth. Growth return values are ignored; current header capacity controls
insertion. Failed normal-return growth can leave a flagged, unqueued holder and
still trigger post-unlock service. Diagnostic insertion receipts are authored,
not native return values or disposal receipts. No concurrent or exception-safety
contract is supplied.

`holder_ring_resize.resize_holder_ring` preserves valid nonnegative int32 ring
control and uses explicit allocate/copy/free services. Copy is in logical head
order and must reject invalid destinations. A null allocation with retained
items is passed to copy before header reset; no silent loss or invented recovery
is permitted. Empty/discard allocation failure returns zero capacity. Services
and exception behavior remain supplied; native failure outcomes are unproved.

`holder_consumer_step.consume_holder_step` pops one valid ring item before callbacks.
It caches payload and initial low-count eligibility, reads registry mode after
payload virtual48, and clears queued bit on current status. Eligible-path cleanup
is called even if callbacks changed the count; cleanup eligibility is external.
Callbacks may mutate fields or queue work. This is serial ordering, not a native
synchronization, output-capacity or completed-disposal guarantee.

`holder_cleanup.cleanup_holder` requires explicit holder/payload fields and supplied
token-release, token-removal and pool-location services. It models eligibility,
payload detachment, flag changes and pool-link publication on normal return.
Detached/recycled diagnostic values describe local operations, not native return
values or payload destruction. Pool membership and synchronization are external.

`holder_pool_lookup.locate_holder_pool` scans at most 65,535 supplied descriptors
and returns the first whose uint32 capacity exceeds the low32 signed /24 index.
It reproduces loose arithmetic, including unaligned and wrapped matches. It is
not an API pointer validator or lifetime pin. No-match returns None; native
cleanup has no observed null guard before using this result.

`holder_retirement_service.run_retirement_service` models normal-return lock/service
ordering and mode-gated payload destruction. Output collection and allocation
services are supplied. Mode is checked once after unlocking; destructor mode
changes do not abort the captured traversal. Output ownership bit30 separately
controls array freeing. Output storage/descriptor must stay valid and stable during
destruction. No native destructor effects, exception safety or scheduler drain
are supplied by this model.

`resource_preparation_queue.prepare_resource_queue` consumes one exchanged uint32
published budget from a valid triple ring. Matching keys mark bit31 and dispatch
the current payload; queued payloads are unused. Callback publications remain for
another invocation. Budget/occupancy mismatch raises an authored boundary error
with partial progress, not a recovered native recovery or unlock guarantee.

`holder_consumer_scope.run_holder_consumer` supplies the serial outer guard and
worker handoff protocol. The caller supplies locks, signal and progressing item
processing. Reentrancy is checked after two lock acquisitions. Pending transfer,
signed wake-state update and signal precede clearing processing and unlocking.
No concurrent CAS retry, native recursive-lock behavior, exception safety or
receiving-worker completion is established.

`loading_destruction_enqueue.enqueue_loading_destruction` models the mode-zero
payload producer with supplied locks/growth. It increments raw uint32 staged count
even without insertion. The consumer-scope model's worker.pending denotes this
staged +0x28c field; worker.published denotes +0x288. Do not conflate those fields
with completion or assume staging proves queue occupancy. No native failure
recovery or resource-lifetime contract is supplied.

Loading destruction batch: `process_loading_destructions` sets busy, captures and
clears uint32 pending, and processes its signed-positive count. A valid retained
ring uses null slots represented by None. Empty iterations retain the previous
payload, including repeated destruction calls if the captured budget is too
large. Supplied services perform synchronization, metadata lookup, destruction
and storage release. This is a serial reconstruction, not a safe drain API;
callback failure has no invented rollback or guaranteed busy reset.

Allocation metadata: `lookup_allocation_metadata` partitions a uint64 address into
high32 region selection and bits16..31 byte-tag selection. Tags other than 255
select low7 entry bits; absent regions/tag255 use the unmasked default byte.
Supplied readers own table retention, native storage aliases and concurrency.
The returned opaque value is not allocation validity or payload-lifetime proof.

Metadata registration: `register_metadata` trusts an existing non-255 record index;
otherwise it searches exactly 127 entries under supplied locking, publishes the
record and notifies supplied observers after unlocking. Observer count is dynamic.
`select_default_metadata` copies the post-callback index even on failed insertion.
The caller retains registry/record/observer storage and callback modules; returned
success is not a membership, lifetime or concurrent-registration guarantee.

Metadata removal: `unregister_metadata` requires a retained record with index0..126,
captures that index before locking, clears its entry without a membership check,
conditionally clears default, then notifies outside the lock before setting the
record index255. It leaves region tags untouched. `notify_metadata_observers`
ORs low32 callback returns across a dynamically counted retained collection.
Neither operation pins callback modules or establishes safe reclamation.

Region retirement: `retire_metadata_regions` requires retained address-region
tables and an externally supplied initialization/bounds service. It checks low7
ownership at span starts, scans inclusively through a high-bit terminator and
dispatches uint32 byte length with reason2 while locked. Callback effects remain
external. It clears raw record.field10 before unlocking, not region tags itself.
This is a traversal model, not a native release or unload API.

Region release fallback: `release_metadata_region` takes retained writable tags,
uint64 address, uint32 size, byte flags and optional metadata record. It clears
tags before a supplied context virtual operation and subtracts dispatched size
from current uint64 field10 afterward. Bit0 bypasses tag/accounting edits. Zero
size triggers inclusive terminator scanning when a record exists; nonzero size
uses at least one tag and otherwise floor(size/65536). Nested registry locking is
required when composed with the scanner. No actual OS release is implemented.

Selected allocation-context release: `release_context_region` calls a supplied
target with address, original uint32 size and0x4000 only when flags equals1; all
other flag bytes use address, zero and0x8000. This is one statically connected
context family. It does not implement or identify a live OS API. The upstream
fallback's bookkeeping size remains independent of the target's size argument.

Command copying: `copy_record` constructs a destination from retained source
references, increments both holder statuses and the optional associated count,
and preserves unmodeled destination padding. Its serial contract excludes source
mutation during native acquisition. It does not release overwritten destination
references or establish module/manager lifetime. Attachment final release may
occur on disposal with no callback execution.

Attachment acquisition: `acquire_attachment` exposes source read/read/count-read,
saved-pointer comparison and uint32 CAS retry as supplied services. A mismatch
still reads candidate.count; successful CAS does not recheck source identity.
Caller must keep every observed candidate readable. This is not a standalone
concurrent lifetime pin or safe source-replacement operation.

Markup query: `markup_query.query_markup` consumes caller-supplied key, float-bit
interval and flag records plus an external paired-value collector. It preserves
mode-2 flag gating, selector rules and collection-before-selection ordering.
The returned index is an authored diagnostic; native code returns a boolean.
Graph acquisition, record production, allocation, update timing and live identity
remain external. See CENTRAL_IMPULSE.md, Animation-interface markup query.
`query_markup_records` supplies the decoded null-context collector behavior from
caller-owned pair arrays. It validates both uint32 words and selects on the second;
no record producer or live graph access is implied. The non-null-context collector
branch is excluded.

Markup provider observation accepts a caller-verified image and fresh dispatcher
with external guards. It follows the documented build-specific query links and
rejects unexpected provider tables/targets, over-64 record collections, incomplete
reads or changed endpoints. It returns scalar metadata only. No lifetime pin,
atomic snapshot, callback execution proof or nested selector values are provided.

`markup_motion_callback.notification_84` preserves callback service order and
low-byte availability gating with explicit entity/type/lookup, motion dispatch,
in-out vector and accumulation services. It ignores incoming notification value
as the inspected callback does. Native service internals and live object ownership
remain external; returned diagnostics and Python exceptions are authored behavior.

`markup_snow_vector.snow_vector` implements the decoded nested-selector-5 vector
branch for finite XYZ inputs and zero fourth lanes. It preserves float32 order,
componentwise 1e-5 fallback and one RSQRT refinement, using a caller-supplied seed.
It assumes no unit normal. Live state selection, active-handle resolution and
hardware estimate equivalence remain external; nonfinite input is rejected.
`markup_snow_vector.branch3_gain_bits` maps an unnamed uint32 state to one supplied
payload field and preserves its float bits. Other states return positive-zero
bits. It does not resolve the native global/handle or infer state/sport names.
`markup_snow_vector.branch3_vector` accepts finite XYZ inputs, resolved boolean
gates and an explicit RSQRT seed service. It preserves the 0.01 magnitude gate,
reverse-only fallback and unguarded cross normalization. Internal nonfinite
results propagate; no invented parallel-vector recovery is supplied. Native
predicate, transform resolution, units and state selection remain external.

`markup_vector_dispatch` selects from raw uint32 current mode/outer/inner states.
Nonzero mode preserves the four-lane output and returns 1; mode zero dispatches
one of three external helpers or zeroes output, returning 0. Only needed state
arguments are validated. Native locking, deferred work, live receiver resolution
and callback exceptions remain outside this local orchestration contract.

`engine.markup_pending.queue_world_scaled_pending` models the finite-input
four-lane accumulation after native entity/runtime/world presence gates. It
rounds interval*30, vector multiplication and addition separately to float32.
The interval is ordinary world time in seconds, not a proved substep duration.
No pointer acquisition, lock or body-velocity update is supplied.

Markup motion sequence inspection: `markup-motion-sequence-v1` supplies ordered
produce/consume events, four-lane pending state and main/optional-rider body states.
Consumer reachability is an explicit caller boolean after any unmodeled prepass;
it is not inferred from actor snapshots. Only decoded local arithmetic changes
velocities. Other forces, locks, object lifetime, native dispatch and position
integration remain external. Nonfinite production stops inspection at the last
finite state rather than inventing recovery. See CENTRAL_IMPULSE.md's ordered
markup-to-body inspection contract.

Motion-sequence point events: `directional_points`/`summed_points` require explicit
boolean `loop_reached` and resolved loop inputs. Selected records submit in storage
order to the main body only. Event-local `main_geometry` supplies basis, stored
local inverse inertia, center and translation; no transform integration occurs.
Each effect preserves wrapper suppression/dispatch decisions. Pending state and
rider state remain unchanged. Native scheduling and record mutation are external.

Pose observer dispatch: `dispatch_pose_observers` preserves dynamic count iteration,
post-callback registry reload and deferred reverse compaction over retained raw
16-byte records. Callbacks and registry storage are supplied. Disabled records can
remain; inactive tails are preserved. Thread active is a byte, not a recursion
counter. This serial normal-return model supplies no lifetime pin, synchronization,
module unloading protocol or exception recovery.

Pose observer membership: registration appends token/enable1 with explicit
seven-byte padding and supplied capacity growth. Duplicates and zero tokens are
not filtered. Removal finds the first matching token regardless of enabled state,
then disables/defer-cleans during dispatch or shifts immediately outside dispatch.
A missing member raises an authored pre-mutation error; native code has no such
guard. Neither operation supplies concurrency safety or safe module unloading.

Body group updates: `update_pose_body_group` operates on retained mutable body and
context dictionaries with explicit eligibility, detach, virtual, acquire, append
and finalize services. It preserves captured membership comparison and metadata/
group reload points. Services own physical effects, storage, locking and failures;
no rollback, native lifetime protection or sleep/wake semantics are supplied.

Ordinary-group processing: `process_pose_group` captures body count after supplied
finalization, handles empty/single-body retirement, and connects multi-body
preparation, destination completion, migration and temporary release. Slots are
body tokens resolved through retained dictionaries. Retirement uses the saved
reuse decision, not a later count. Single-body append failure is ignored as in
the inspected caller. Services own allocation, destruction and failure effects;
no rollback, concurrency guarantee or safe native retirement API is supplied.

Group storage cleanup: `cleanup_pose_group` consumes retained body/link/pose
storage descriptors with explicit pointer and inline tokens, count and capacity.
It preserves capacity gates, pose/link/body release order and final table change.
Allocator virtual effects are supplied; pointed-to elements are never traversed.
This is not object deletion or a safe native unload operation. Protected pool
return in the deleting wrapper remains outside the implementation.

Group pool acquisition: `acquire_pose_group_storage` uses explicit retained pool
fields and supplied free-link reader, chunk allocator and chunk-list growth.
It preserves free-list precedence,168-byte slot arithmetic and uint16/uint32
wrap. Returned tokens identify storage only. Construction, synchronization,
generation identity and native allocator failure handling remain external.

Group reconstruction after reuse: `construct_pose_group` replaces only defined
constructor fields in168 supplied bytes and preserves inactive inline entries and
unknown padding. Its returned copy is an authored interface. The separate
`return_pose_group_storage` models first-word link write, usage decrement and head
publication on an already resolved retained pool. It supplies no cleanup, locking,
duplicate-return check, generation identity or live memory access.

Ordinary-group inspection: `pose-group-process-v1` starts one supplied source in
its flag-selected context list with empty tracked/pending lists. It connects the
recovered processing operations using authored bounded storage and recorded-only
body-virtual/link-clear/destructor services. Removed group snapshots stay in the
result for diagnostics, not as live handles. The JSON adapter has independent
integration tests, not a full continuous native equivalence claim.

Link payload clearing: `clear_pose_link_payloads` captures the source array and
extent, then either returns nonnull payloads through a supplied service or resets
raw count110 and appends them to a supplied destination. It clears source count
only after normal completion and preserves entry bytes. Payload meaning, protected
return synchronization and lifetime remain external. Missing nested collections
in group-inspection inputs are not implicitly treated as empty.

Link record layout: `decode_payload_row` maps one admitted60-byte serialized field
into64 supplied prior bytes, preserving the last four bytes. It neither admits
fields nor controls active count. Packed link keys truncate to16/16/32 bits;
`remove_link_key` removes the last matching entry by swap-last without releasing
payloads. Physical key/row meanings and full stream framing remain unresolved.

Paired-frame payload update: `update_pose_link_payload` accepts288 retained bytes,
0..4 supplied48-byte records, two finite XYZ bases/translations and pair indices.
It preserves float32 basis-dot order, copied fourth words, old-ID cache matching,
count gates and inactive bytes. The four-record bound comes from the inspected
caller's reduction path; its selector remains external. Cached-word physical
meaning, live transforms, contact generation and solver effects remain unresolved.

Geometric row selection: `select_pose_link_rows` preserves float32 centroid,
tangent selection/normalization, supplied-matrix transform, two projection passes
and later-index ties. Duplicate indices are permitted. Axis-angle matrix behavior
is a service; normal normalization is not added. `reduce_pose_link_records` applies
the caller's >4 gate and snapshots four full records before overwriting active
slots. Nonfinite/zero-tangent rejection is an authored domain restriction.

Fixed-angle selector rotation: default selection now uses the recovered
quaternion-to-matrix operation order and fixed half-sine/cosine float bits from
original scalar evaluation at the selector literal. No normal/quaternion
normalization is inserted. This closes the supplied-matrix dependency only for
that angle and the validated scalar dispatch path; other angles are rejected and
an explicit matrix service remains available.

Record-group payload processing: `process_pose_link_record_group` requires one
already reached nonempty key group, retained payload bytes, finite frames and an
explicit resolved entry flag. It connects flag replacement, optional four-record
reduction and payload update in copied storage. The upstream raw-byte pair gate
is separate. Sorting, payload lookup/acquisition, cached-word solver meaning,
protected operations and native lifetime remain outside this API.

Link-payload inspection: `pose-link-update-v1` requires complete prior bytes and
one reached key group with explicit16/32-bit grouping mode. It packs structural
record fields and exposes recovered reduction/update results, raw cache words and
retained padding. Input bounds, finite checks and JSON diagnostics are authored;
no missing bytes, native acquisition, physical cache semantics or solver behavior
are invented. Synthetic bundled fixtures contain no game payloads.

Link solver feedback: `write_pose_link_feedback` requires retained link/payload
arrays and complete16-byte result rows. Link flag84 bit0 and payload flag114 bit0
gate processing; context flag38 bit29 chooses raw lane0 copy versus zero. Result
indices are supplied through payload rows. This identifies cache provenance, not
physical units, native lifetime or the missing row-builder index publication.

Link result binding: `bind_pose_link_results` reserves three uint32 result indices
and publishes the first as payload feedback index for the inspected builder
family. `seed_pose_link_result` publishes the linked primary reference and
broadcasts cached bits only for zero/unordered gate comparison. Row allocation,
gate production, full equations, exception modes and other families remain
external. Supplied solver results in tests are not simulated original solves.

Link profile coefficients: `combine_link_scalar` preserves raw-mode combination,
float32 operation order and signed-zero tie choices. `link_response_coefficients`
connects fields30/40/60/64 to response and cache-seeding gate using explicit context
scalar/factor/flags. Field64 is not evaluated at/above the recovered threshold.
Profile fields/modes are supplied; physical units, singular arithmetic and full
row equations remain outside the contract.


Paired profile lookup: `resolve_pose_link_profiles` selects retained entry resources
using payload pair indices, then resolves opaque profile tokens through the
kind6/kind7 byte maps or default pointer. Both endpoints share the payload selector.
Null maps select defaults; null table results remain null. Resource storage,
lifetime, kind semantics and other builder families remain external. Returned
profiles may feed `link_response_coefficients`; this does not establish material
names or a live atomic read contract.

Link builder dispatch: `dispatch_pose_link_builders` traverses a retained pointer
range and calls four explicitly supplied services. It captures mode, body pointers,
payload count and second-body metadata branch per enabled link, while reloading
payload slots and payload gates/counts during traversal. Single-path labels include
zero-row payloads and nonzero modes with multiple rows. This defines the reachability
of the recovered metadata-clear/single builder fragments; the other builder bodies,
concurrent lifetime and callback destruction safety remain outside the contract.

Link tangent basis: `link_tangent_basis` transforms the first local point relative
to offset128, combines vectors1ac/1a0 through cross-plus-add, projects against the
payload normal and selects a normalized tangent with a low-magnitude geometric
fallback. The second direction is normal cross first. Float32 ordering is explicit;
normal normalization, second-body motion, physical units, degenerate arithmetic
and the rest of the solver rows are not supplied or inferred.

Primary link response: `link_primary_response` consumes explicit paired-point
separation, normal, first-body opposite-motion projection, recovered coefficient
values and raw context fields1c/20. It gates the motion candidate by rounded
subtraction, then selects the larger magnitude with position winning ties. All
operations retain float32 order. Finite arithmetic, caller-supplied producers and
unresolved physical units remain explicit boundaries.

Link paired geometry: `link_point_geometry` transforms explicit local payload
points with caller-supplied frames. It preserves first offset128 subtraction and
world-center readdition, returning both arms, world points and second-minus-first
separation. Float32 cancellation is part of the behavior. Units, frame validity,
round-trip identity and uninterrupted whole-builder equivalence are not implied.
