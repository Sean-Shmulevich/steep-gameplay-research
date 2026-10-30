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

Connected link builder: `build_pose_link_rows` implements the metadata-clear/single
family using explicit body/profile resources and retained row/result storage.
It resolves profiles, computes coefficients, allocates by supplied counters and
writes one primary plus two secondary rows per payload row. Untouched bytes and
signed-zero lanes survive. It updates result indices and conditional raw cache
seeding, without running a solver. Zero to four payload rows, sufficient capacity,
valid identities and finite nonsingular arithmetic are required. Full native
validation covers default profile lookup; other families and live ownership are
excluded. Earlier fragment-only row-assembly limits are superseded for this family.

Link-builder inspection: `pose-link-builder-v1` requires explicit reached-family
selection, provenance, complete prior bytes, capacities and symbolic resources.
It copies inputs, runs `build_pose_link_rows` and returns readable new rows plus
all retained raw bytes. JSON guards and inspection bounds are authored. Result
storage represents cache seeding only; no solve, missing data, dispatcher
admission or live identity is synthesized.

Solver control: `run_pose_solver` accepts retained context bytes and explicit
prepare/iterate services. It captures phase/count and storage descriptor, always
prepares, resets the result-slot cursor once before iteration, and retains cursor
changes thereafter. Only phase0x10000000 temporarily substitutes unit scalars and
restores their original raw bits on normal return. Numerical solve, exceptions,
thread safety and allocation remain external.

Primary numerical solve: `prepare_pose_primary_row` fills reciprocal row40 and
applies cached result lanes to the selected first-body state.
`iterate_pose_primary_row` projects the row response, clamps accumulated results
to nonnegative lanes and applies their increments to state. Optional row-relative
accumulation requires retained extra bytes. Finite nonsingular arithmetic and
supplied64-byte body data/32-byte state records are required. No tangent coupling,
body-data producer, alias policy or complete solver convergence is claimed.

Tangent numerical solve: `prepare_pose_tangent_row` computes reciprocal response
without row60 and applies cached result lanes. `iterate_pose_tangent_row` uses
row60 times the linked primary result as per-lane bounds, ignores row10, and applies
old-minus-new result to the first body. Min/max ordering and signed-zero operand
selection remain explicit. Finite arithmetic and retained data are required;
no joint tangent limit, whole-system convergence or universal grip interpretation
is implied.

Connected link solve: `solve_pose_link_rows` connects wrapper control and primary/
tangent numerical routines with explicit context traversal counts. It supports
only categories0 and6 and rejects any other populated category. Special phase
skips tangents; zero iterations still prepare. Counts and body-data producers,
other numerical families, live identity and full-engine convergence remain
external despite uninterrupted native validation of this supported slice.

Solver body buffers: `build_pose_body_buffers` transforms the selected body tensor,
exports scalar124 and initializes motion state with gated external-vector and
optional four-lane damping response. It returns records in input-array order.
Metadata bit3 selects the shared zero tensor/scalar and bypasses state processing.
Damping-library behavior is an explicit service, never an inferred approximation.
Inputs remain constant; index association, TLS lifecycle and physical units remain
caller obligations or unresolved producers.

Body-state feedback: `write_pose_body_feedback` copies raw XYZ lanes from sequential
32-byte state records into retained body fields1a0/1ac. It ignores fourth lanes and
body index fields, preserves all other bytes and processes repeated identities in
order. Complete nonoverlapping storage and caller-established array association
are required; no live lifetime or invalid-range behavior is supplied.

Solver layout: `plan_pose_solver_layout` computes25 category starts, region offsets
and size with recovered stride constants, uint32 arithmetic and uint16 body-count
truncation. `initialize_pose_solver_storage` copies planned counts, clears separate
append counters/results and preserves other retained bytes. Its domain requires
sufficient nonwrapping storage. Allocation/release/failure behavior, category-count
prepasses and body-index assignment remain external.

Link prepass counts: `count_pose_link_rows` accumulates25 uint32 category counters
from enabled retained links/payloads. Second-body metadata bit15 selects paired
categories. Full settings mode zero groups multi-row payloads into category4/5;
nonzero mode reserves two category6/7 rows per point. Counter wrap is preserved.
Pose contributions, valid mode domain, grouped builders and live lifetime remain
external. The prepass mode test must not be conflated with low-bit builder dispatch.

Pose category prepass: `count_pose_categories` accumulates category deltas for raw
resolved virtual types1..6, reusing the type2 six-row classifier. Type4 needs no
second body; other recognized types pair categories by metadata bit15. Type3's
word flag and type5's byte flags remain distinct. Unknown types contribute nothing.
Virtual dispatch/type construction, physical class names and live storage lifetime
remain supplied or unresolved.

Solver settings: `initialize_pose_solver_settings` copies raw settings words,
stores the group token, packs mode/iteration/control flags and clears phase bits.
It writes scalar10 and its float32 reciprocal scalar_c, establishing their native
producer relationship. Finite nonzero reciprocal arithmetic is required; physical
units, upstream settings validation, overlapping buffers and live token lifetime
remain external. Existing row/layout storage is preserved.

Group body buffers: `build_pose_group_body_buffers` is an authored adapter that
checks retained token/group/index membership and constructs indexed solver buffers
in active group order. It does not repair indices or synchronize live memory.
Counts above65535 are rejected to avoid the recovered layout's 16-bit truncation.
The membership producer and numerical consumer are recovered separately; consistent
retained membership connects them, while allocation-time mutation remains external.

Secondary body application: `apply_pose_secondary_body_state` temporarily installs
state XYZ pairs, invokes supplied virtual-slot+0x10 with exactly1.0, and restores
all24 prior motion bytes on normal return. Other method effects persist. Count is
captured while later slots/state reload. The method's native effects, exceptions,
aliases and live ownership remain outside this contract.

Body integration: `integrate_pose_body` reconstructs the transform method selected
by constructor0x18a8e70. It rotates/re-orthonormalizes above angular threshold2^-23,
translates around the local offset, and preserves motion. General half-angle
sine/cosine responses remain an explicit service. Finite nondegenerate arithmetic,
this constructor-selected class and retained storage define the current domain;
other virtual implementations and live class coverage are not assumed.

Body integration inspector: `pose_body_integration_bench.inspect` copies retained
body bytes, requires provenance and an explicit direct/secondary sequence, and
checks supplied trig response arguments. Missing, mismatched and unused responses
reject. The fixture is authored synthetic; its scalar-library responses are not
claimed as native observations. Native wrapper→method composition is separately
validated without interception by replaying observed scalar-library outputs.

Secondary rows: `refresh_pose_secondary_link_rows` resets two append counters,
refreshes enabled retained primary rows by metadata category, broadcasts a clamped
position-error response, zeros row+0x50 and clears the existing indexed result.
Geometry, headers and planned traversal counts persist. First-pass row storage,
finite arithmetic and valid indices are required. Both refresh categories are
recovered; category1 numerical solving is still unsupported.

Paired primary solver: category1 now uses both body indices and angular directions,
with opposite linear directions. Preparation includes both body responses;
iteration clamps the shared result nonnegative and updates both states. Coincident
indices retain native second-write-wins behavior. The connected solver runs
category1 before0 and then6 when permitted by phase. Paired first-pass builders,
category7 tangent rows and other numerical categories remain unsupported.

Paired tangents: category7 uses angular direction+0x50, linked primary index+0x60
and coefficient+0x70. Preparation omits the coefficient from its denominator;
iteration applies the lane-wise primary-result bound and old-minus-new updates.
The connected solver order is1,0,7,6, with both tangent categories skipped in the
special phase. This supersedes the earlier category7 unsupported boundary.
Paired first-pass builders and all other numerical categories remain external.

Group-step orchestration: `run_pose_group_step` captures group identity, reloads
later array spans, sets phase bits, orders feedback, conditionally clears state
and runs secondary work, rechecks the application gate, and supplies current
poststep fields. Every downstream operation is an explicit required service.
Native-shaped tokens are opaque; retained storage, normal returns and nonwrapping
address arithmetic are required. This is recovered orchestration with supplied
operations, not a claim of complete group simulation or live synchronization.

Body quiet-state update: `update_pose_body_quiet_state` resolves per-field-1.0
threshold overrides, requires both motion magnitudes strictly below their limits,
accumulates scalar into timer28, and sets metadata state1 only beyond the duration
limit. Inhibition or motion equality/excess resets timer and the low metadata
nibble. Finite arithmetic only; group action and live sleep/wake are not supplied.

Group poststep: `check_pose_group_quiet` updates every captured body's timer and
transitions a reloaded span only if all metadata low nibbles equal1. Empty groups
pass; failure preserves the existing flag. `transition_pose_body_inactive` marks
state2, clears both motion vectors and traverses a valid circular link ring using
an explicit payload-clear service. `poststep_pose_group` skips integration/refresh
for nonzero group flag, otherwise integrates then reloads the refresh span.
Resource release/refresh, other body classes and reactivation remain external.

Body reset/reactivation: `reset_pose_body_quiet_state` implements constructor-selected
slot0x28, clearing the state nibble and timer while preserving motion. It can supply
the existing ordinary-group finalizer's virtual40 callback. Full finalization
queues state2 links before resetting bodies, clears the group flag and transfers
context collections. Growth, other classes and automatic/live trigger safety
remain external; resetting one body alone is not full group reactivation.

Body resource bounds: `pose_body_bounds.refresh_pose_body_bounds` accepts retained
body storage and identity maps for entry arrays, transforms and metadata. A
required resource callback supplies six finite bounds floats from twelve composed
transform floats. Count is captured; arrays and destination metadata are reloaded.
Zero entries produce a point at body translation; all-null nonempty spans are
rejected as an authored guard. Resource geometry, scratch fourth lanes, concurrent
mutation and broadphase updates remain outside this contract. See LINK_SOLVER.md,
"Body resource bounds refresh".

Kind-7 bounds: `pose_grid_resource_bounds.grid_resource_bounds(resource, frame)`
provides the constructor-selected callback for body refresh. Retained raw resource
storage supplies extents and a separate height-center pair; the frame contains
four XYZ rows. Float32 operations preserve the observed center rule without
assuming midpoint centering or normalized basis. Input producers, grid topology,
contact generation and other resource kinds remain unresolved. See LINK_SOLVER.md,
"Kind-7 grid resource bounds".

Grid cells: `pose_grid_cell.grid_cell_geometry` consumes retained resource fields,
a supplied float sample sequence and valid cell coordinates, returning four local
XYZ vertices and two triangle index triples. `grid_triangle_sample_indices`
decodes a uint32 triangle ID with separate cell divisor and sample stride, retaining
uint32 index wrapping. The byte58 diagonal branch is explicit. Storage guards are
authored; sample loading and collision queries remain separate. See LINK_SOLVER.md,
"Grid cell vertices and triangle identities".

Triangle vertices: `pose_grid_cell.grid_triangle_vertices` maps a triangle ID to
three XYZ0 vectors using the recovered grid rules. Its guarded reuse of cell
geometry matches the separate native vertex method on complete finite cells.
Positive-zero fourth lanes depend on the supplied initialized XYZ mask in native
validation. This endpoint supplies geometry; it does not implement the consuming
contact calculation. See LINK_SOLVER.md, "Grid triangle vertex consumer boundary".

Grid neighborhoods: `pose_grid_cell.grid_vertex_neighbors` returns ordered XYZ
neighbors using sample dimensions0x68/0x6a and the diagonal flag. It clips neighbors
at edges and keeps the native traversal order. Valid dimensions, sample identity
and complete supplied grid are authored requirements. This implements a contact
filter dependency, not the record-rejection policy itself. See LINK_SOLVER.md,
"Grid vertex neighborhood and contact-filter lead".

Grid edge neighbors: `pose_grid_cell.write_grid_edge_neighbors` writes two XYZ
positions into retained output. Numeric endpoint difference and diagonal flag
select neighbor offsets; missing neighbors use the lower endpoint. Unsupported
differences preserve prior positions, and reversed endpoint order still swaps
them. Tail bytes persist. This is a geometry helper, not an adjacency validator
or completed rejection predicate. See LINK_SOLVER.md, "Grid edge neighborhood".

Grid edge rejection: `pose_grid_edge_filter.reject_grid_edge` combines the
recovered edge-neighbor helper with float32 cross/dot tests and a supplied
four-lane threshold. All lanes control near-zero normalization; XYZ lanes control
strict rejection. It requires finite, nondegenerate inputs and recognized index
differences. It does not supply unsupported prior scratch values or claim full
record-filter equivalence. See LINK_SOLVER.md, "Grid edge rejection predicate".

Grid record filter: `pose_grid_contact_filter.filter_grid_records` consumes a
resource, supplied samples/frame/triangle, retained48-byte records and active
count. It returns the remaining count after vertex/edge rejection and swap removal.
Direction XYZ at0 and position XYZ at16 are transformed in the recovered operation
order; other bytes remain opaque. Finite nondegenerate geometry and initialized
XYZ mask semantics are required. It filters existing records, without generating
contacts or asserting live ownership. See LINK_SOLVER.md, "Complete grid record filter".

Grid candidate enumeration: `pose_grid_candidates.write_grid_triangle_candidates`
clips a query box to stored bounds, checks Z overlap, converts XY with float32
reciprocal multiplication and truncation, then emits paired triangle IDs in row
order until positive capacity is reached. Output tails persist. Positive spacings,
nonempty cell dimensions and finite int32-convertible values are authored domain
requirements. No per-triangle sample/contact test is implied. See LINK_SOLVER.md,
"Grid triangle candidate enumeration".

Contact axis selection: `pose_contact_axis_selection.select_contact_axis` consumes
opaque frame/shape pairs and explicit face/edge query services. It preserves
reversed face arguments, positive-distance short circuits, seeded edge output,
float32 bias and strict branch precedence. Result kind/index/distance fields are
recovered; query geometry and contact emission remain dependencies. See
LINK_SOLVER.md, "Contact producer axis selection".

Contact face query: `pose_contact_face_query.query_contact_faces` transforms each
plane, selects the opposite support vertex, and returns the first positive
separation or greatest nonpositive separation with first-tie precedence. Shapes
supply plane/vertex lists and frames supply XYZ rows. It does not normalize planes
or substitute inverse-transpose transforms. Empty support for nonempty planes is
an authored rejection. See LINK_SOLVER.md, "Contact face-distance query".

Contact edge query: `pose_contact_edge_query.query_contact_edges` resets and mutates
a distance/index result using explicit edge/plane/vertex descriptors. It preserves
the transposed-frame calculation, adjacent-normal eligibility gates, short-axis
rejection, orientation and strictly negative best-separation policy. Finite inputs
and nonzero second-edge lengths are required. See LINK_SOLVER.md, "Contact
edge-distance query". Descriptor validity and contact emission remain separate.

Connected contact selection: `select_geometry_contact_axis` uses both recovered
face/edge queries directly and returns the recovered kind/index/distance result.
The explicit-service selector remains available. This is a geometry-query API,
not contact emission or a live mod entry point. See LINK_SOLVER.md, "Connected
geometry axis selection" for schemas and validation boundaries.

Edge contact emission: `pose_contact_edge_emit.emit_edge_contact` writes one48-byte
record from selected edges and supplied frames/shapes, or returns0 for zero
capacity. It preserves segment-clamping order, normal orientation, negative
squared separation and fixed record fields. Finite nonparallel/nondegenerate
geometry is required. This implements the edge emitter, not face emission or the
complete collision pipeline. See LINK_SOLVER.md, "Edge contact record emission".

Face polygon construction: `pose_contact_face_polygon.append_face_polygon` appends
transformed XYZ/tag records to retained 128-slot storage. It preserves float32
operation order, ordinal wrapping and uint32 tag truncation. Capacity enforcement
is an authored guard. Frames, vertices and face indices are supplied explicitly;
clipping and contact emission remain separate. See LINK_SOLVER.md, "Face polygon
vertices and tags".

Reference side planes: `pose_contact_side_planes.append_side_planes` appends one
normal/scalar plane per indexed edge, beginning with the last-to-first edge.
It normalizes the local cross product and preserves the native frame transform
without post-transform normalization. Empty lists, excess capacity and degenerate
cross products are authored rejections. A later failure may retain earlier writes.
See LINK_SOLVER.md, "Reference side-plane construction". Polygon clipping remains
separate.

Single-plane clipping: `pose_contact_polygon_clip.clip_polygon_plane` writes
XYZ/tag records and returns their count. It preserves float32 plane evaluation,
strict tolerance snapping, crossing order and rejected-endpoint tags. Inputs must
be finite, buffers distinct, source count 1..128, and output capacity at least
twice the source count. Capacity checks are authored. See LINK_SOLVER.md,
"Single-plane polygon clipping". Multi-plane orchestration remains separate.

Multi-plane clipping: `pose_contact_polygon_clip.clip_polygon_planes` clips caller
storage in place through at least two planes, using temporary buffers until the
final stage. It returns zero below three points. The API requires 4096 bytes of
storage and rejects intermediate counts above128. These capacity guards are
authored. See LINK_SOLVER.md, "Multi-plane polygon clipping". Final point selection
and face-record emission remain separate dependencies.

Contact point filtering: `pose_contact_point_filter.filter_plane_points` compacts
points at nonpositive plane separation and writes matching float32 scalars.
`remove_near_points` removes later points strictly inside a supplied radius by
swapping the last record and its scalar into the removed slot. Both retain unused
bytes. Inputs are finite; plane-filter count is bounded to128. See LINK_SOLVER.md,
"Contact plane and proximity filtering". Optional four-point reduction is open.

Complete point selection: `pose_contact_point_filter.select_contact_points`
connects plane filtering, proximity removal and optional four-index reduction.
It reuses the recovered geometric selector and gathers matching point/tag and
separation records before overwriting slots0..3. Later ties and duplicate indices
are preserved. See LINK_SOLVER.md, "Complete contact point selection" for the
fixed-angle/trigonometry domain. Final face emission remains separate.

Face emission: `pose_contact_face_emit.emit_face_contacts` connects incident-face
selection, polygon/side-plane construction, clipping, point selection and48-byte
record emission. Shapes supply vertices, planes and per-face vertex indices.
Capacity limits writes after geometry; orientation swaps point roles and negates
the normal. Separation is linear, unlike edge emission's squared field. All helper
finite/nondegenerate and capacity domains apply. See LINK_SOLVER.md, "Connected
face-contact emission". Upstream producer descriptors and live integration remain.

Producer descriptors: `pose_contact_shapes.box_contact_shape` and
`triangle_contact_shape` construct explicit vertices, planes, face indices and
edge adjacency. Triangle normalization and plane-dot operation order match the
native producer prefix. Degenerate triangles are authored rejections. See
LINK_SOLVER.md, "Box and triangle descriptors". CRT initialization and complete
producer dispatch remain separate.

Box-triangle producer: `pose_box_triangle_contact.emit_box_triangle_contacts`
connects recovered descriptors, axis selection and face/edge emission. Triangle
vertices are world-space; box geometry uses extents and a supplied frame. Flags
control edge queries and face-point reduction. Capacity limits output records.
See LINK_SOLVER.md, "Connected box-triangle producer" for dispatch and validation
scope. Terrain candidate/profile/filter orchestration remains outside this API.

Runnable producer inspection: `python3 -m engine.pose_box_triangle_bench INPUT`
accepts explicit provenance and bounded synthetic/observed box-triangle geometry,
and returns decoded records, exact bytes and separation-kind labels. See
LINK_SOLVER.md, "Runnable box-triangle inspection". This is an offline inspection
API; no private binary, live pointer, terrain simulation or native session required.

Terrain record conversion: `pose_grid_contact_records.convert_grid_contact_records`
mutates a specified batch of48-byte records, swapping point roles, sign-flipping
normal bits and setting triangle IDs while retaining scalar/other fields. Range
and identifier guards are authored. See LINK_SOLVER.md, "Terrain record roles".
This is a reached caller block, not full terrain collision orchestration.

Terrain profile admission: `pose_grid_profile_gate.grid_triangle_profile_gate`
resolves a per-cell terrain profile or absent-map default and tests either
64-bit directional mask overlap against the other resource's default profile.
It returns identity and admission separately. Tokens/maps/profiles are supplied;
field-width validation is authored. See LINK_SOLVER.md, "Terrain profile admission".

Preliminary height contact: `pose_grid_height_contact.query_grid_height_contact`
accepts an explicit height/triangle query service and reconstructs center-height
admission plus optional48-byte output. Radius affects separation, not admission.
Null output still permits true. See LINK_SOLVER.md, "Preliminary height contact".
The query service is unresolved and must not be represented as recovered terrain
interpolation. Finite inputs and existing frame conventions apply.

Grid height query: `pose_grid_height_query.query_grid_height` computes biased floor
cell selection and topology-dependent piecewise height, returning height and ID.
Outside-grid queries preserve the caller's ID and return negative FLT_MAX. The
orientation-zero half numbering differs from geometry enumeration and is retained.
See LINK_SOLVER.md, "Grid height query". Samples are supplied; finite positive grid
domains apply and exceptional conversion behavior is excluded.

Connected preliminary contact: `pose_grid_height_contact.query_sampled_grid_contact`
uses the recovered grid query directly, starting triangle identity at0xffffffff.
It retains sentinel-height comparison and topology-specific IDs. See
LINK_SOLVER.md, "Connected preliminary grid contact". Native comparisons include
both routines without service interception; sample payloads remain caller supplied.

Terrain frame conversion: `pose_grid_contact_frames.grid_contact_frames` returns
inverse terrain and relative other frames as four XYZ rows each. It preserves
cofactor inverse and float32 transform ordering. Singular rejection is authored;
fourth SIMD lanes are not represented. See LINK_SOLVER.md, "Terrain inverse and
relative frames". The subsequent virtual bounds call remains separate.

Box resource bounds: `pose_box_resource_bounds.box_resource_bounds` returns six
float32 lowXYZ/highXYZ values from extents and a supplied frame, preserving the
absolute-basis sum order. See LINK_SOLVER.md, "Box resource bounds query". Composed
validation uses the terrain caller's actual kind3 virtual method; other resource
classes and object allocation/lifetime remain separate.

Terrain candidate collection: `pose_grid_candidates.collect_grid_triangle_candidates`
returns IDs and inspection metadata after a min(total,128) first query and exact128
retry at full-grid capacity. Python owns storage; native allocator behavior is not
emulated. See LINK_SOLVER.md, "Terrain candidate collection and ownership". Positive
bounded grid validation is authored; complete caller orchestration remains separate.

Connected terrain-box caller: `pose_grid_box_contact.emit_grid_box_contacts`
combines frame/bounds, optional preliminary height contact, candidates, profiles,
producer, record conversion and filtering. The preliminary flag also enables
face reduction. A successful preliminary query returns1 even at capacity0 without
writing, so return value is not always record count. See LINK_SOLVER.md, "Connected
terrain-box contact caller" for composed evidence and remaining domains.

Terrain inspection CLI: `python3 -m engine.pose_grid_box_bench INPUT` packs explicit
synthetic/observed grid samples and profiles, invokes the reconstructed caller and
returns records plus retained storage. Return-value and record-count distinctions
are preserved; separation is not assumed linear. See LINK_SOLVER.md, "Runnable
terrain-contact inspection". Adapter limits/validation are authored.

Contact role reversal: `pose_contact_reverse.reverse_contact_records` swaps point
fields and flips normal bits over a retained record range while preserving all
identifier/scalar words. See LINK_SOLVER.md, "Reversed contact pair adapter".
`pose_grid_box_contact.emit_box_grid_contacts` connects the full reversed-order
adapter. It requires max(1, capacity) backing records: preliminary success at zero
capacity reverses a retained record without generating one. This authored guard
preserves the observed native mutation. Complete adapter comparisons cover small
grids; dispatch ownership and downstream payload grouping remain unresolved.

Resource-pair lookup: `pose_contact_dispatch.select_contact_handler` takes64
caller-owned handler identities and two raw uint16 kinds. It masks bit15, then
selects `handlers[8 * first + second]`. Null remains null; there is no fallback.
Out-of-table kinds are rejected by authored guards. See LINK_SOLVER.md, "Resource-pair
dispatch lookup". Handler invocation, replacement and lifetime remain external.

Contact handoff: `pose_contact_dispatch.dispatch_contact_pair` selects resources
by explicit pair indices, calls the selected handler with500-record capacity,
then calls supplied grouping for nonzero count or pair clearing for zero. Grouping
key width must be16 or32 and is not inferred. See LINK_SOLVER.md, "Contact generation
to persistent-group handoff". Cache allocation, recycling and lifetime are required
external services; the returned count and input guards are authored diagnostics.

Empty-pair recycling: `pose_contact_cache.clear_contact_pair` mutates retained
16-byte cache entries, caller-supplied payload buffers and a recycled identity
collection. It removes last matching pairs regardless of detail, resets only
payload+0x110 and appends each nonzero identity. A removed null terminates the loop.
See LINK_SOLVER.md, "Empty-pair cache recycling". Python owns storage growth;
allocator failure, capacity overflow and concurrency are outside its domain.

Recycled contact acquisition: `pose_contact_cache.acquire_recycled_contact_payload`
finds the first full-key match or pops a recycler identity, refilling ten at a time.
It writes only the selected miss payload's owner before the supplied append service.
Batch supply owns initialization; cache append owns capacity. See LINK_SOLVER.md,
"Nonempty-group payload acquisition through a recycler". The no-recycler global
allocation/locking branch remains unavailable, rather than guessed.

Stale-group retirement: `pose_contact_cache.retire_stale_contact_groups` takes
already-sorted records and preserves the native forward record cursor across cache
entries. It advances the cache index after swap-last removal, resets the scanned
payload count and appends its identity for reuse. See LINK_SOLVER.md, "Stale
contact-group retirement scan". Upstream order/uniqueness invariants remain unknown;
do not replace this with set subtraction or automatically revisit moved entries.

Contact sorting: `pose_contact_sort.sort_contact_records` mutates48-byte record
order with the recovered unstable sort and explicit16/32-bit comparator. Full keys
use wrapped signed subtraction, not unsigned ordering. See LINK_SOLVER.md,
"Contact record sort ordering". Whole record bytes persist; invalid record lengths
or key widths are authored errors. No cache or solver work occurs in this helper.

Connected contact consumer: `pose_contact_cache.process_contact_cache` accepts
nonempty48-byte records, cache/recycler collections, payload storage, pair frames,
indices and raw entry flags. It sorts, retires, acquires and updates groups in
recovered order while preserving inactive tails. See LINK_SOLVER.md, "Connected
nonempty contact-cache consumer". Supply batch initialization and cache append
services explicitly. Native comparison covers preallocated storage, not allocator
failure, global-pool locking or scheduled live integration.

Dispatch-to-cache integration: `pose_contact_dispatch.process_dispatched_contact_pair`
connects a supplied geometry handler to recovered nonempty processing or pair clear.
It preserves the complete500-record backing buffer, including inactive producer
bytes. See LINK_SOLVER.md, "Terrain generation through contact-cache processing".
Native terrain comparisons cover translated small synthetic grids with preallocated
storage. Solver execution and live body ownership are not part of this API.

Terrain-cache CLI: `python3 -m engine.pose_terrain_cache_bench INPUT` consumes
schema pose-terrain-cache-v1 with complete initial retained storage and explicit
geometry steps/pair metadata. It returns per-step inspection plus resumable final
state. See LINK_SOLVER.md, "Terrain-cache inspection CLI". Snapshot copying and
JSON bounds are authored; storage exhaustion errors rather than inventing native
batch allocation. This command neither advances time nor executes a solver.

Payload pool slot acquisition: `pose_contact_pool.acquire_payload_slot` prioritizes
free-list entries, otherwise takes288-byte slots from registered pages. Allocation
and page-table reserve are explicit services. It updates pool counters/cursors but
leaves payload bytes intact. See LINK_SOLVER.md, "Contact payload pool". Successful
allocation and valid metadata are required; initialization and locking remain caller
responsibilities, not silently implemented substitutes.

Payload batches: `pose_contact_pool.supply_payload_batch` repeatedly acquires slots,
clears only owner and active-row count, and sets flag bit0. Cached rows and all other
bytes persist. See LINK_SOLVER.md, "Payload batch initialization boundary". Caller
must serialize access; protected entry/exit services are outside the reconstructed
core. Page allocation, table reserve and payload backing storage remain explicit.

Paired link point motion: `pose_link_paired_motion.paired_link_point_motion` uses
both body frames/offset128 values and motion1a0/1ac pairs to compute offset-relative
arms and second-minus-first point motion with float32 order. See LINK_SOLVER.md,
"Paired-builder relative point motion". Only finite XYZ is represented; paired
128-byte row assembly, SIMD padding and solver iteration remain separate work.

Paired tangents: `pose_link_paired_motion.paired_link_tangent_basis` projects supplied
relative point motion against the supplied, unnormalized normal, applies the strict
float32 fallback threshold and returns both tangent directions plus first_lane3.
See LINK_SOLVER.md, "Paired-builder tangent directions". Finite nondegenerate inputs
are required; full paired response and row assembly are still separate boundaries.

Paired single-family rows: `pose_link_paired_builder.build_paired_pose_link_rows`
uses retained128-byte arrays, both body motion/offset fields, explicit resources/
profiles/modes and the existing result/payload storage contract. See LINK_SOLVER.md,
"Connected paired single builder" for distinct primary/secondary angular layouts.
It implements metadata-set/single only. Multi families, native allocation and solver
iteration remain outside this contract; do not substitute112-byte rows.

Multi-contact patch: `pose_link_patch_geometry.contact_patch_geometry` consumes
explicit first-body basis/world offset-center and1..4 local offset-relative arms.
It transforms and averages world points, returns the centroid-relative arm and
`max(sum_distance, .001)/count` with inspected float32 order. See LINK_SOLVER.md,
"Multi-row contact patch geometry". Shared208-byte row assembly is still separate;
normal dispatcher gates must not be inferred from this helper's arithmetic domain.

Shared patch directions: `contact_patch_basis` takes explicit normal, centroid arm,
linear/angular motion and positive spread. `pack_contact_patch_directions` modifies
only+0x10..0x7f of a retained208-byte row. See LINK_SOLVER.md, "Shared patch
orientation and packing" for component thresholds, fallback order and transpose.
Coefficient/result fields and full multi-family assembly remain unresolved.

Clear multi-family assembly: `build_multi_pose_link_rows` consumes the existing
body/profile/payload contract plus retained112-byte primary rows,208-byte shared
rows,16-byte results, counters and explicit aligned arena base offsets. It reserves
one shared result then one per contact, writes signed relative links to shared+b0,
and accumulates cached values independently of seeding. See LINK_SOLVER.md,
"Connected multi builder". Supplied storage only; no allocator or solver iteration.

Paired multi-family assembly: `build_paired_multi_pose_link_rows` follows the clear
multi API with128-byte primary and256-byte shared rows. Both bodies' offset centers
and velocities contribute to primary and centroid motion. The shared accumulator
is+0xe0, coefficient+0xf0; signed relative links target+0xe0. See LINK_SOLVER.md,
"Connected paired multi builder". Unreached retained bytes are preserved. No full
solver iteration, allocation or exceptional arithmetic behavior is supplied.

Unified row build: `pose_link_build.build_dispatched_pose_links` supplies all four
concrete builder services to the recovered dispatcher. Six explicit retained pools
have rows/count/base; all share the context's result numbering. See LINK_SOLVER.md,
"Unified build". Inputs retain original mode/metadata gates. Partial mutations are
not rolled back on input/storage errors. No allocation or solver step is implied.

Primary accumulator storage: both primary iteration functions accept optional
`arena` and `row_offset`, resolving signed64-bit row+0x50 in16-byte units from that
row origin. Without an explicit arena the row buffer is the origin. Targets must
fit retained storage. See LINK_SOLVER.md, "Primary accumulator arena addressing".
Accumulation adds the full projected value; clearing between sweeps is not supplied.

One-body shared iteration: `pose_shared_solver.iterate_pose_shared_row` consumes a
prepared208-byte row,64-byte body data,32-byte body state and16-byte result. It
consumes/clears the accumulator, projects a coupled XYZ result and applies its
change. Inverse response matrix remains supplied. See LINK_SOLVER.md, "Shared patch
iteration". No preparation, paired variant or complete traversal is implied.

One-body shared preparation: `prepare_pose_shared_row` now supplies the inverse
response matrix for the208-byte shared row and applies the cached result to body
state. It preserves the inspected removal of third-component coupling before
inversion and separate third reciprocal. See LINK_SOLVER.md, "Shared patch
preparation". Finite nonsingular input only; singular rejection is an authored guard.

Paired shared iteration: `iterate_pose_paired_shared_row` consumes a prepared256-byte
row with two body indices and applies sequential first/second updates. Coincident
indices accumulate both updates. See LINK_SOLVER.md, "Paired shared patch iteration".
The inverse matrix remains supplied; no paired preparation or traversal claim.

Paired shared preparation: `prepare_pose_paired_shared_row` builds the256-byte row's
inverse response using both bodies' linear/angular contributions, clears+0xe0 and
applies cached results sequentially. See LINK_SOLVER.md, "Paired shared patch
preparation". No supplied inverse matrix is needed in the finite nonsingular domain;
full mixed-category traversal remains separate.

Six-category traversal: `solve_pose_link_rows` accepts shared_rows and
paired_shared_rows plus optional context-origin arena storage. It runs primary,
shared and tangent families in native order and skips shared/tangent in special
phase. Primary arena offsets come from retained context layout. See LINK_SOLVER.md,
"Connected six-category solver traversal". Other populated categories still fail.

Arena composition: `build_and_solve_pose_links` consumes initialized context/layout
storage, explicit body/profile/link mappings and retained payloads. Row/result views
share the arena, append counters are published, then six-category traversal runs.
See LINK_SOLVER.md, "Arena composition". No allocation, count inference, body-data
production, body-index assignment or final body integration is supplied.

Contact pass: `run_pose_contact_pass` extends arena build/solve with link-cache and
raw-body motion feedback in recovered order. Explicit body_tokens must correspond
to body_state order; raw and parsed bodies must agree. See LINK_SOLVER.md, "Contact
pass with feedback". No group phases, pose constraints, secondary correction,
position/orientation integration or poststep are implicitly supplied.

Body-origin contact pass: `run_pose_contact_pass_from_bodies` produces body data/state
in arena storage before contact building/solving/feedback. Ordered bodies must
match index1c and supply tensor/mass/metadata fields; frame basis is used. Scalar,
vector and reached damping response remain explicit. See LINK_SOLVER.md, "Contact
pass from body fields". No complete group-step or body integration claim.

Secondary contact correction: `solve_pose_contact_secondary_correction` gates on
secondary-count bits, transitions phase, clears arena state, refreshes primary rows
and solves in special phase. It returns whether the phase ran. Body state must alias
the arena. See LINK_SOLVER.md, "Contact secondary correction composition". Applying
correction to transforms and group poststep remain explicit subsequent stages.

Contact transform correction: `correct_pose_contact_transforms` runs secondary
correction and applies the constructor-selected body integrator through temporary
motion fields, restoring original motion on normal return. Caller supplies reached
half-angle trig responses and must refresh parsed transforms before reuse. See
LINK_SOLVER.md, "Contact correction through transform update". No general body-class
virtual dispatch, exception rollback or group poststep is supplied.

Bounded scalar trig: `small_angle_sin_cos` implements dispatch-zero finite float32
inputs up to binary64 pi/4 in magnitude with inspected binary64 polynomial order.
It may be supplied to half_angle_trig APIs without native observations. See
LINK_SOLVER.md, "Scalar trig". Larger ranges and alternate dispatch are rejected;
status flags and nonfinite native behavior are not modeled.

Reduced scalar trig: `scalar_sin_cos` extends exact dispatch-zero arithmetic to
finite float32 magnitudes below500000 via split-pi/2 reduction and cancellation
correction. It can supply integration without recorded responses. See LINK_SOLVER.md,
"Scalar trig range reduction and independent composition". Wider/nonfinite inputs
and alternate dispatch remain unsupported; no libm fallback is silently selected.

Runnable contact inspection: `python3 -m engine.pose_contact_bench` accepts schema
pose-contact-pass-v1 and explicit provenance/raw inputs. It allocates authored
zero-filled storage through the recovered count/layout plan and returns exact row,
result, payload/body bytes plus stage summaries. See LINK_SOLVER.md, "Contact
inspector". Supplied contacts, disabled damping and explicit body-class/trig bounds;
not a full game tick or native savepoint.

Integrated group poststep: `poststep_integrated_pose_group` composes quiet checking,
constructor-selected inactive transition, ordinary integration and bounds refresh.
See LINK_SOLVER.md, "Integrated group poststep". Callers provide matching retained
metadata identities and explicit trig/resource/release services. Box bounds and
scalar trig can use recovered implementations. No concurrent lifetime guarantee,
other-class dispatch or full group-solve claim is supplied.

Pose constraint feedback: `feedback_pose_constraints` applies endpoint gates,
queries explicit virtual kind and copies kind2 results in packed or scalar mode.
See LINK_SOLVER.md, "Pose constraint feedback". Missing indices preserve values;
raw result bits survive unchanged. Row producers, type discovery, floating-point
exception flags and numerical constraint solving remain separate dependencies.

Command constraint builder: `build_pose_command_constraint` appends the recovered
kind4/category24 row, reserves a result index and expands retained command records
without interpreting their physical meaning. See LINK_SOLVER.md, "Command constraint
rows". Six commands is an authored capacity bound; untouched bytes persist.
Category24 numerical solving remains unsupported.

Command constraint solving: `prepare_pose_command_row` and
`iterate_pose_command_row` recover effective mass, cached impulse application and
bounded updates for category24. See LINK_SOLVER.md, "Command constraint solving".
Finite nonsingular arithmetic, six-command storage bound and explicit body data
are required. Full traversal integration and gameplay command ownership remain open.

Mixed command/contact traversal: `solve_pose_link_rows` accepts `command_rows` and
supports category24 before the six contact categories in normal preparation and
iteration. Special phase skips command rows. Context168 controls traversal, not
append count104. See LINK_SOLVER.md, "Mixed command and contact traversal".
The remaining18 categories and complete group composition are not supplied.

Paired angular solver: `prepare_pose_paired_angular_row` and
`iterate_pose_paired_angular_row` recover category13 matrix preparation, cached
application and capped angular increments. See LINK_SOLVER.md, "Paired angular
increment solver". Caps constrain increments, not accumulated results. Finite
nonsingular storage is required; builder and mixed traversal remain separate.

Single angular solver: `prepare_pose_angular_row` preserves trace normalization,
cofactor inversion and rescaling; `iterate_pose_angular_row` applies capped angular
increments to one body. See LINK_SOLVER.md, "Single angular increment solver".
Zero trace and singular/nonfinite inputs are rejected. Mixed traversal now accepts
categories12/13 in normal phase after commands and before contact primary rows.
Sixteen other categories remain unsupported.

Constraint primary traversal: categories8/9 reuse the validated clear/paired
primary numerical kernels, before contact primary rows in normal phase only.
`constraint_primary_rows` and `paired_constraint_primary_rows` provide explicit
storage. Signed accumulator links resolve from their own category bases.
See LINK_SOLVER.md, "Reused primary kernels in constraint categories".

Paired point solver: category11 preparation/iteration couples linear state and
angular coefficient matrices, applies cached impulses and bounds each increment.
See LINK_SOLVER.md, "Paired point solver". The module name describes the math;
it does not establish a native class or player consumer. Row production and
traversal integration remain open; finite nonsingular retained inputs are required.

Single point solver: category10 uses trace-normalized inversion and bounded
increments coupling one body's linear/angular state. See LINK_SOLVER.md, "Single
point solver". Mixed traversal accepts categories10/11 in normal phase after
constraint primary rows, before contact primary rows. Twelve numerical categories
remain unsupported. Row producers and gameplay ownership are not inferred.

Bounded scalar solvers: categories16/17 preserve per-lane reciprocal responses,
symmetric increment bounds, single-body cached add/subtract rounding and paired
snapshot update semantics. See LINK_SOLVER.md, "Bounded scalar constraint solvers".
Explicit paired selection and complete finite retained storage are required.
Mixed traversal and original gameplay producers are not supplied by these kernels.

Bounded scalar traversal: `bounded_rows` and `paired_bounded_rows` connect
categories16/17 after coupled rows and before contact primary rows in normal
phase. Special phase skips both families. See LINK_SOLVER.md, "Fifteen-category
numerical traversal". Ten numerical categories remain explicitly unsupported.

Angular axis solvers: categories18/19 implement unbounded angular increments with
per-lane response and retained cached add/subtract rounding. Paired endpoint writes
are sequential. See LINK_SOLVER.md, "Unbounded angular axis solvers". Both are now
connected to normal mixed traversal and skipped in special phase. Eight numerical
categories and remaining producers/lifecycle integration remain unsupported.

Added-response angular variants: `softened=True` selects category20/21 layouts,
with a per-lane denominator addition and unchanged iteration rules. "Softened" is
an authored mathematical label, not a recovered physical unit. Both variants are
connected to normal traversal and skipped in special phase. See LINK_SOLVER.md,
"Angular axes with added response terms". Six numerical categories remain open.

Plain bounded rows: `added_response=False` selects categories14/15 and preserves
all four inverse lanes. These variants use tangent preparation and bounded-scalar
iteration, with no extra denominator term. See LINK_SOLVER.md, "Bounded scalar
rows without added response". Both are connected to normal traversal, skipped in
special phase. Four numerical categories and remaining producers/lifecycle are open.

Late primary pools: categories2/3 reuse recovered primary kernels with distinct
bases/counts and normal-only execution. See LINK_SOLVER.md, "Late primary
categories and remaining numerical kernels". `late_primary_rows` and
`paired_late_primary_rows` require explicit retained rows. Only numerical
categories22/23 remain unsupported; broader producer/lifecycle gaps persist.

Two-stage single-body constraint: category22 uses a 256-byte retained row, one
64-byte body-data record, one 32-byte state and an external 16-byte result.
Preparation builds a coupled inverse plus two angular reciprocal responses and
applies both cached impulses. Iteration applies the coupled increment before
reading angular state for its second correction. See LINK_SOLVER.md, "Two-stage
single-body constraint". Finite nonsingular responses are required. Coefficient
producers, physical units and gameplay ownership remain unresolved.
`two_stage_rows` supplies category22 with its normal-only gate and placement
between14 and3. Category23 is the sole unsupported numerical category. This does
not close row production, physical ownership or full group lifecycle.

Two-stage paired constraint: category23 retains 352-byte rows, two body indices,
one external coupled cache and an internal angular cache. Endpoint updates are
sequential, including coincident indices. The second stage reads both updated
angular states and computes two diagonal responses from summed endpoint
contributions. See LINK_SOLVER.md, "Two-stage paired constraint". Finite
nonsingular inputs are required; coefficient producers, units and gameplay
ownership remain unknown. The `paired_two_stage_rows` pool runs before category22
in normal phase and is skipped in special phase. All 25 numerical categories are
now connected, with synthetic native comparisons. This closes the supported-row
numerical traversal boundary, not row production or full engine integration.

Point constraint production: kind1 consumes two retained body frames, local
anchors at70/80 and the second body's metadata bit15 at50. It appends category10
or11 and reserves an external result index, without initializing that result or
publishing traversal counts. See LINK_SOLVER.md, "Point constraint producer".
The normal pose-building phase applies a0.4*context_c position-error response;
other phase masks use zero. Body-center offsets affect angular coefficients,
not world anchor positions. Finite retained inputs and bounded output storage
are required. Full dispatch gates and gameplay ownership remain separate.

Angular limit row helper: `build_pose_angular_limit_row` appends category8/9 from
explicit axis, coordinate, sign, offset and two response vectors. It retains the
strict XYZ response-threshold test, all-four-lane nonnegative test, phase gate and
iteration-dependent response arithmetic. Caller supplies body indices afterward.
See LINK_SOLVER.md, "Angular limit row producer". Finite inputs and nonzero reached
divisors are required; physical units and upstream angle production remain open.

Angular drive row helper: `build_pose_angular_drive_row` produces category14/15
with zero linear direction and opposite paired angular axes. Mode2 negates the
supplied sample directly; other modes scale and clamp sample-reference before
negation. Response W is impulse_bound.X times context10. See LINK_SOLVER.md,
"Angular drive row producer". Caller provides endpoint indices and cached-result
lifecycle. These field names describe arithmetic, not established physical units.

Kind3 angle inputs: `select_pose_angle_interval` preserves the strict all-XYZ
outside-range gate, one-revolution candidate selection and four-lane output.
It does not normalize repeatedly or clamp to bounds. `pose_constraint_drive_sample`
retains the original subtract-and-compare scalar selection from d0/d4/dc. See
LINK_SOLVER.md, "Kind3 angle interval selection". The existing signed-angle helper
remains reusable with an explicit atan2 service; platform bit equivalence is not
claimed. The arena drive API now delegates to the earlier detached drive builder.

Kind3 composition: `build_pose_hinge_constraint` consumes retained frames and
inline configuration, then emits category22/23, two category8/9 rows and an
optional category14/15 drive. Hinge is an authored name. See LINK_SOLVER.md,
"Kind3 constraint composition". The atan2 service remains explicit; a reached
body notification requires a supplied callback. Native validation supplies
observed atan2 output and intercepts notification effects, while checking all
builder writes and callback arguments. No lifecycle/count-publication claim.

Constraint builder caller: `build_pose_constraints` implements endpoint
metadata52 eligibility and virtual-kind dispatch. Kinds1/3/4 use reconstructed
builders; reached kinds2/5/6 require supplied services and unknown kinds skip.
See LINK_SOLVER.md, "Constraint builder eligibility and dispatch". The selected
constraint token is retained across the kind query. Planned-count publication
already exists in `initialize_pose_solver_storage`; integrating prepass, builder
eligibility and lifecycle remains unfinished, not the local publication formula.

Kind6 builder: `build_pose_motion_constraint` emits category2/3 from retained
frames, anchors, normal and body motion. It constructs midpoint-relative angular
coefficients and a positional response; the reached motion term has a zero
multiplier. See LINK_SOLVER.md, "Motion-aware primary constraint producer".
Single-endpoint construction ignores second-body center/motion fields. Kind6 is
connected to the eligibility dispatcher; only kinds2/5 remain external builders.
Finite retained inputs and bounded storage define the supported domain.

Pose quaternion inputs: `multiply_pose_quaternions` and
`pose_matrix_to_quaternion` preserve scalar float32 ordering and dominant-component
branch ties. See LINK_SOLVER.md, "Quaternion inputs to angular drive". Neither
normalizes or repairs its input. The latter consumes three XYZ columns and
ignores optional fourth lanes. Both are verified local dependencies of the kind5
angular drive; complete builder composition and active ownership remain open.

Quaternion angular-drive response: `build_pose_vector_drive_row` appends an80-byte
category12/13 row using normalized relative quaternions, componentwise arcsine,
negative double gain, all-XYZ magnitude gating and an output frame. See
LINK_SOLVER.md, "Quaternion angular-drive response". Endpoint indices and prepared
coefficients are preserved for other stages. `pose_scalar_asin` independently
implements finite[-1,1] output arithmetic; CRT status effects remain excluded.
Complete kind5 composition and caller ownership remain unresolved.

Ellipse dependencies: `pose_ellipse_project` and `pose_ellipse_normal` reconstruct
kind5 limit-geometry helpers with positive finite radii. See LINK_SOLVER.md,
"Elliptical limit projection". Projection targets the boundary even for interior
points, preserves near-axis tie/sign choices, and uses last-evaluated denominators
at the19-update cap. Complete angular geometry and constraint composition remain
open; no player joint ownership is implied.

Angular-limit geometry: `pose_angular_limit_geometry` composes equal-extent and
small-radius shortcuts, ellipse/clamp projection, normal construction, arcsine
correction and quaternion axis rotation. See LINK_SOLVER.md, "Composed angular-limit
geometry". Four-lane extent equality, XYZ radius gating and scalar-X geometry
remain distinct. Early returns preserve axis.W; the rotated result clears it.
Native initializer synchronization and full kind5 row composition are excluded.

Kind5 target preparation: `prepare_pose_target_frame` copies XYZ target columns
while preserving destination padding, optionally transposes the measurement
frame, and applies elliptical and secondary angular bounds. See LINK_SOLVER.md,
"Bounded drive target frame". Atan2 remains an explicit service. Later angle
measurements retain original working vectors after output correction. This is
one preparation stage, not a complete kind5 builder or active rig contract.

Kind5 composition: `build_pose_cone_constraint` emits point, swing-limit, optional
four secondary limits and optional quaternion-drive rows. See LINK_SOLVER.md,
"Kind5 constraint composition". Cone is an authored descriptive name. Target
preparation uses explicit atan2 and reached notification requires a callback.
Target inversion has a retained near-unit determinant shortcut; body-frame
inversion is separate. Kinds1/3/4/5/6 now run directly through the dispatcher;
only kind2 remains external. Full group lifecycle and active rig ownership remain
open; callback-driven mutation is outside the validated contract.

Kind2 translation helpers: `build_pose_translation_row` appends hard14/15 or
soft16/17 rows from supplied axis, points and lever arms. See LINK_SOLVER.md,
"Translation spring row producers". Hard gain is negative0.4 without phase gating;
soft gain is negative and its coefficient uses the existing spring arithmetic.
Caller classification and endpoint completion remain external. This does not
complete kind2's builder or establish physical units.

Kind2 translation limits: `build_pose_translation_limit_pair` emits two completed
category8/9 rows with opposite axes and independently computed signed distance.
See LINK_SOLVER.md, "Paired translation limits". The phase gain requires all XYZ
errors strictly positive; W receives the gain without participating in the gate.
Bounds are not sorted. The returned offset tuple is authored. Full kind2 caller
classification and composition remain open.

Kind2 translation assembly: `prepare_pose_axis_constraint` snapshots world inputs;
`build_pose_axis_translations` applies hard-triple collapse, axis-owner comparison,
lever-arm adjustment and per-axis state dispatch. See LINK_SOLVER.md, "Kind2
translation assembly". Only scalar spring rows publish their feedback indices;
limit-only and skipped axes preserve them. This remains a stage API, not a full
kind2 builder. Angular rows/drives and full lifecycle are unresolved.


Kind2 complete composition: `build_pose_axis_constraint` now assembles angular
frames, hard/soft angular rows, limit pairs and direct drives after translation.
See LINK_SOLVER.md, "Kind2 angular frames and complete composition". All six known
kinds now dispatch directly. Atan2 and notification effects remain explicit
services. States0/1/2 agree with count planning; angular state3 emits limits that
the prepass does not reserve. Full lifecycle and active ownership remain open.
This supersedes the earlier kind2-external/stage-only descriptions.

Group preparation: `prepare_pose_group` combines link/pose counting, retained
storage initialization and settings application in native wrapper order. See
LINK_SOLVER.md, "Group preparation through solve entry". Inputs are stable explicit
views and sufficient caller-owned capacity. No count repair or eligibility filter
is added. Returned layout metadata is authored; solving remains an explicit next
stage. Full-word count mode and low-bit builder mode remain distinct.

Complete solver arena: `solve_pose_arena` derives writable row/body/result views
from retained layout fields and runs all25 numerical categories. See LINK_SOLVER.md,
"Complete arena numerical dispatch". Planned counts govern traversal regardless
of append counters. Rows and body buffers must already be populated; count repair,
row construction, feedback and full group lifecycle are not implicit.

Joined group runtime: `run_pose_group_runtime` connects raw body input parsing,
body-buffer production, six-kind pose building, arena solving and body/constraint
feedback through the recovered group-step orchestrator. See LINK_SOLVER.md,
"Joined group numerical runtime". Link operations and poststep are explicit
mandatory services; damping and secondary update require services when reached.
The joined native validation covers kind2 with empty contact arrays and normal
phase. It does not establish a complete player tick or mixed-contact lifecycle.

Mixed contact services: `make_pose_link_services` connects contact build/cache
feedback/secondary refresh to the shared group arena without a separate solve.
See LINK_SOLVER.md, "Mixed contact and constraint group runtime". Pose categories
are preserved and result allocation is shared. Parsed body views must match raw
bodies and be refreshed before another tick. Normal mixed kind2/contact execution
is native-compared; secondary/poststep integration remains a separate boundary.

Integrated poststep adapter: `make_integrated_pose_poststep` selects the known
constructor body implementation and binds raw membership, quiet overrides and
metadata to quiet aggregation/inactive transition/integration/resource bounds.
See LINK_SOLVER.md, "Joined secondary correction and poststep". Trig, resource
bounds and link clearing are explicit. The joined native test now includes both
solve phases and box poststep, with empty body link rings; it does not establish
complete membership consistency, live lifetime or every body/resource class.

Inactive contact retirement: `clear_pose_link_contacts` binds raw link entry
storage to the existing no-transfer clear behavior. See LINK_SOLVER.md, "Inactive
body rings and contact retirement". It clears active count after successful release
requests and preserves inactive entries. Pool return remains an explicit service.
Refresh parsed link counts before another tick; raw stale entries are not active
contacts. Joined ring validation covers one link shared by both endpoints.

Repeated retained group API: `read_retained_pose_group` rebuilds typed views from
current active spans; `run_retained_pose_group_pass` composes preparation and the
joined runtime. See LINK_SOLVER.md, "Repeated retained group passes". Eager parsing
requires stable well-formed records. Every invocation refreshes frame/motion and
contact/resource counts. Direct repeated calls do not supply scheduler admission,
contact generation, sleep/wake policy, allocator growth or live atomicity.

Group batch worker: `run_pose_group_worker` reconstructs atomic-claim admission,
solver versus free-motion dispatch and per-worker scratch reuse/release. See
LINK_SOLVER.md, "Group batch worker admission". Claim and numerical operations are
explicit services. `claim_pose_batch_serial` is not thread-safe. Inactive group
flags are not tested at this boundary; earlier collection selection and batch
construction remain separate from the validated worker loop.

Numerical worker composition: `advance_pose_free_motion` implements the direct
motion branch with explicit damping response. `run_retained_pose_worker` binds
both worker routes to retained numerical APIs and allocator services. See
LINK_SOLVER.md, "Free-motion worker branch" and "Joined numerical batch worker".
Scratch growth/reuse follows required layout size; ownership, allocator internals,
thread-safe claims, upstream admission and alternative classes remain external.

Group batch construction: `run_pose_group_batches` reads the active group span,
partitions zero-work groups to its tail, requests sorting of the nonzero prefix,
and forms contiguous batches with a signed work threshold of25. Each group costs
at least one after uint32 contact-plus-pose addition. Worker count is bounded by
batch count, dispatcher capacity and32. See LINK_SOLVER.md, "Group batch formation".
Sorting, storage growth, dispatch and completed-group transfer are explicit
services. Dispatch must finish consuming batch records before returning; this API
requires that ordering but does not reconstruct the native dispatcher's join.

Completed-group transfer: `transfer_completed_pose_groups` walks the active list
backwards when context44c is nonzero. Groups with a nonzero inactive flag are
swap-removed, appended to the inactive list, and their body tokens appended to the
tracked list. See LINK_SOLVER.md, "Completed-group transfer". Indices must be
consistent before entry. The inactive flag and stale array tails are preserved.
Growth is an explicit service; concurrent list mutation is outside this contract.

Pose dispatcher: `dispatch_pose_workers` reconstructs callback publication,
caller-help and completion polling with explicit atomic, queue, notify and wait
services. See LINK_SOLVER.md, "Dispatcher claim and completion counters". Valid
admission requires at least one worker and a free slot among32. Queued work has
separate unclaimed and unfinished counts. Return waits for unfinished count to
be nonpositive. This is a service-bound control-flow model, not a new thread pool.

Retained batch pass: `run_retained_pose_batch_pass` composes group ordering,
batching, synchronous dispatcher policy, numerical workers and completed-group
transfer. See LINK_SOLVER.md, "Joined retained batch execution". Job records must
alias the context fields updated by batching, with owner pointers initialized.
Queue/atomic/growth/class services remain explicit. Interior pointer-array views
reference live retained slots instead of copied group lists. This serial reference
composition does not establish a concurrent host or native job construction.

Pose context constructor tail: `initialize_pose_context_tail` clears the observed
collection descriptors, enables completed-group transfer, marks both already
constructed special groups inactive through an explicit service, and initializes32
job owners/indices and argument-table pointers. See LINK_SOLVER.md, "Context job
construction". It excludes allocation and protected constructor calls. Scalar and
settings job fields remain untouched until batch submission. `bind_pose_jobs`
returns authored views that alias these retained records and the raw pointer table.

Pose update stage: `run_pose_update_stage` preserves the phase3 preparation,
contact update, changed-link attachment, pending-link publication, batch solve and
conditional post-solve notification order. See LINK_SOLVER.md, "Outer pose update
stage". Subsystem effects remain explicit services. Owner pointers are reloaded
between calls; pending span bounds are captured once, but slots are read per visit.
Phase resets on normal return only. Exceptions do not imply native cleanup.

Command constraint preparation: `prepare_pose_command_constraint` gates on
endpoint metadata bit0, restores callback endpoint order, passes mutable six-command
and count views with reciprocal scalar/mode1/userdata, then resets unsigned counts
above6 to0. See LINK_SOLVER.md, "Command preparation producer boundary". Skipped
updates preserve old commands/count. Callback arithmetic and creation-time mode0
remain explicit; a post-call count reset cannot prevent callback buffer overflow.

Command construction: `construct_pose_command_constraint` binds supplied base
construction to command defaults, callback/userdata storage, endpoint swap and
single-body mode, then invokes mode0 with scalar0 and cleared count. See
LINK_SOLVER.md, "Command creation and callback modes". It deliberately preserves
counts above6 after the initial callback. Base registration/wake and gameplay
callback production remain external; this is not a complete factory.

Registered command preparation: `prepare_retained_pose_commands` binds the owner20
provider's spans70/78 and80/88 to the recovered preparation driver and kind4 update
wrapper. See LINK_SOLVER.md, "Command registry to preparation". Provider pointers
and slots are read at the observed uses; active counts are captured per loop.
Callbacks remain supplied. No deduplication or ownership/lifetime assertion is added.

Pose command registration: `register_pose_constraint` appends to the general
constraint collection, calls the observed notification service with argument2,
then appends kind4 to the first command list. `register_pose_constraint_container`
appends the supplied object and filters its captured child count into the second
command list. See LINK_SOLVER.md, "Command registry population". Growth and kind
lookup are explicit services. The container return is its pre-growth insertion
index; neither path deduplicates records or supplies lifetime ownership.

Endpoint rings: `attach_pose_endpoint_rings` and `detach_pose_endpoint_rings`
reconstruct two-endpoint circular link insertion/removal. See LINK_SOLVER.md,
"Endpoint ring registration and removal". Selector2 uses body90, selector1 body80,
selector0 body88. Neighbor fields depend on which endpoint matches the body.
Both endpoint bodies and consistent retained rings are required; no lifetime,
duplicate insertion, repeated removal or concurrent mutation policy is added.

Individual unregistration: `unregister_pose_constraint` removes the first command
entry for kind4, detaches selector2 endpoint rings, then swap-removes the previously
located general entry. See LINK_SOLVER.md, "Individual registration removal".
General pointer/count are reloaded after detachment. Missing membership raises an
authored error; native invalid-index writes are not reproduced. No destruction,
freeing, duplicate-ring safety or container-removal equivalence is implied.

### Container registration removal

`unregister_pose_constraint_container` follows LINK_SOLVER.md, "Container removal
and deferred children". It captures body count and container index before callbacks,
processes bodies through explicit services, captures child count afterward, removes
kind4 children from the second command registry, and queues children whose endpoint
metadata bit0 is clear. It swap-removes the container and repairs the moved object's
owner/index/backlink. Valid serial membership and writable retained storage are
required. Tree removal, cross-owner body processing and output allocation remain
supplied services. Missing membership and capacity overflow raise authored errors;
this is not an atomic or concurrent removal API.

### Cross-owner body constraint removal

`process_pose_body_constraints` follows LINK_SOLVER.md, "Cross-owner body ring
processing". It scans body90, leaves edges with null/unowned second endpoints or
matching metadata owners, and unregisters other edges through the real registry
and ring functions. It queues removed edges only with an output descriptor and
both metadata52 bit0 flags clear; otherwise it calls supplied destroy(token,1).
After every removal it restarts at the current body head. Valid serial rings and
membership are required. Growth and destruction are services; this does not prove
native destructor effects, lifetime safety or concurrent traversal.
