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
