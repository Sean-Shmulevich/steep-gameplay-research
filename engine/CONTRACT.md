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
