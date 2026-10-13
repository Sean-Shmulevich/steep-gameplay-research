# Independent engine implementation

This is a runnable Python research engine assembled from recovered local kernels and explicitly designed policies. It is not original engine source, a complete game port or a claim of full behavioral equivalence. No original assets are required or bundled. Python 3.10+ and its standard library are sufficient.

## Run

From the repository root:

```sh
python3 -m engine.cli --ticks 1200 --sport snowboard
python3 -m engine.cli --sport paraglider --ticks 1200 --output /tmp/flight.json
python3 -m engine.cli --replay /tmp/flight.json
python3 -m engine.cli --serve --port 8770
python3 -m unittest discover -s tests -v
```

Open http://127.0.0.1:8770 for the diagnostic terrain/skeleton view. The server binds loopback only. All clients share one engine. Run/pause, individual steps, checkpoints, sport selection and replay export are available. A/D steer, W tucks or walks forward, S brakes, Space charges then releases a jump, Q/E control flips. Click outside the sport selector to return keyboard control. This is an inspector; visual fidelity is intentionally limited.

## Python API

```python
from engine.runtime import Engine
from engine.replay import record, replay

engine = Engine({'sport': 'snowboard'})
engine.set_input({'jump': True})
engine.step(90)
checkpoint = engine.checkpoint()
engine.set_input({'steer': .3, 'flip': .4})
engine.step(240)
assert replay(record(engine)).state_hash() == engine.state_hash()
engine.restore(checkpoint)
```

`step(n)` advances n fixed development ticks, default 1/120 second. `advance(frame_dt)` uses the configured scheduler, either fixed accumulation or the unsmoothed recovered subdivision policy. They are distinct APIs; step does not simulate an outer-frame scheduler invocation. Both are recorded for replay. The subdivision derivative interval is recorded separately; the point controller currently consumes elapsed time only.

`snapshot()` returns a detached published-state copy. Checkpoints include body/controller histories, input state, scheduler, scoring, environment, animation, camera and scenario identity. Restoring a checkpoint starts a new replay base. Runtime failures roll back the tick and log a bounded incident record; `recover()` resumes the last good state after the caller repairs the fault. Frame advance is transactional across its selected substeps. This is a designed fault-containment policy, not recovered original crash recovery.

## Modules and evidence

| Module | Working scope | Important limitation |
| --- | --- | --- |
| runtime/replay | Stepping, checkpoints, journals, hashes, recovery | Same-runtime determinism only; not original-game replay |
| scheduler | Fixed mode; recovered unsmoothed subdivision | Full smoothing history/table policy absent |
| input | Validated per-command input snapshots | Generations are our design; original writer freshness open |
| world | Analytic slope/bumps, material patches, swept cylindrical obstacles | Synthetic collision world |
| physics | Snow/ski point contact, steering, brake, jump, independent air rotation, walking | Designed integration/controller; not the original full hull/constraint solver |
| rigid | Optional six-cell hull, pressure/contact impulses, rotating inertia and world angular momentum | Synthetic hull, volume-based weights, controls and substrate; not full original constraints |
| contact | Clipped tetrahedron, pressure/contact impulses, point impulse application | Standalone probe, also used by optional rigid_cells mode |
| domains | Wingsuit/paraglider local response laws, environment clock/weather overlays | Synthetic presets and selectors; unknown zones/track evaluator |
| animation | Rig/clip validation, crossfade/additive, hierarchy, palette; optional recovered 60 Hz sampling and inclusive wrap | Default sampling/selection designed; active addon merge unresolved |
| graph | Lazy producer readiness and deferred evaluation kernel | Standalone caller-supplied gates/callbacks; not assumed active rider graph |
| procedural | Recovered limb target, weighted orientation and landing alignment | Explicit caller mapping/order; not full-body IK |
| camera | Recovered spring math with an explicit follow policy | Default distances/FOV and arbitration are designed |
| scoring | Recovered local quantization/commit with flight detector | Detector and event ownership are designed |
| inspection | Rig bindings, sign-invariant pose comparison, aligned trace differences | Inputs must share frames/units and compatible joints |
| assets | Versioned evidence-labeled resource registry | No original archive importer/repacker yet |
| server/view | HTTP operations and diagnostic canvas | Local research interface, not production renderer |

The reference modules retain provenance in REFERENCE_MANIFEST.json. Default rigs, clips, geometry and tuning are synthetic. Studio-authored and video-estimated resources have distinct categories and must never silently become recovered evidence.

## Scenarios and mods

A scenario is a schema-version-1 JSON object with sport, world, body, physics_mode and optional physics, rigid, air, environment, scheduler, scoring, camera and resources configuration. Unknown top-level fields fail. See [the shared contract](CONTRACT.md) and module docstrings for exact field schemas. Configurations are immutable by convention during a run; use a new scenario or a checkpoint-aware API rather than editing live dictionaries behind the journal.

A resource bundle has `category`, `rig` and `clips`; their schema is documented in animation.py. Supply original resources only locally with appropriate access. Missing clip channels remain visible in diagnostics. No heuristic base/addon rig merge is disguised as recovered behavior.

The JSON API accepts POST /api with op: input, step, run, pause, reset, checkpoint, restore, recover, inspect, cell or limb. `run` includes actions and count; `cell` supplies vertices, surface, dt and settings; `limb` supplies a request matching procedural.limb_target. GET /state, /resources and /replay return JSON. Invalid operations return a structured error. Standalone probes do not mutate the engine.

## Validation and next passes

See [implementation progress](PROGRESS.md). Tests cover formulas, meaningful boundaries, phase/state transitions, mutation isolation, all sport runtimes, replay after restoration, failed-tick rollback, stable slope contact and HTTP controls. Passing tests establishes these contracts, not recovered coverage of the full game.

For the optional hull mode, use `Engine({"physics_mode":"rigid_cells"})`. It is supported for snowboard and ski, with dt at most 1/60 second. The default point controller remains available for comparison. `python3 -m engine.scenarios --ticks 3600` runs all five sports through scripted controls and verifies exact replay hashes.
