# Building an independent engine source tree

The useful deliverable is a small, inspectable implementation of the recovered gameplay systems. It would be **our source tree**, not the original engine's source. Completing the tree does not mean all original behavior has been recovered.

## Proposed layout

These are design names, not recovered class names. The layout is language-neutral; use the implementation project's language and build system.

```text
src/
  core/          scalar precision, vector/quaternion math, units, simulation clock
  input/         semantic actions, source adapters, cookers, edge/release history
  world/         terrain queries, material selection, weather and time controllers
  physics/       bodies, contact geometry, force/impulse integration, constraints
  movement/
    snow/        board/ski contact, carving, adhesion, coil, jump, rider response
    air/         wingsuit and paraglider control/force models
    walking/     separate on-foot controller; initially an explicit substitute
  tricks/        proposals, assistance, accepted state, reset and target publication
  animation/     resource adapter, playback, graph, pose blend, IK, physical pose
  landing/       classification inputs, known predicates, recovery interfaces
  camera/        mode selection, transitions, response, projection adapter
  scoring/       detectors, history, attribution, multipliers and commit/cancel
  runtime/       explicit orchestration and unresolved ordering adapters
  telemetry/     per-step inputs, gates, selected resources, forces and state changes
tests/
  unit/          arithmetic boundaries and frame conventions
  scenarios/     synthetic slopes, takeoff/landing, spin/release, weather transitions
  fixtures/      synthetic or separately supplied permitted fixtures, labeled by origin
docs/
  contracts/     units, ownership, cadence and unresolved inputs per module
  provenance/    links from rules to these research documents
  substitutions/ invented behavior and replacement criteria
```

Keep renderer and platform wrappers replaceable. Rendering and the original backend solver were deferred in this research; importing those assumptions into gameplay equations would obscure the evidence.

## Define shared contracts before implementation

| Contract | Minimum information | Known boundary |
| --- | --- | --- |
| Simulation step | elapsed time, step index, request/batch identity | Original input/substep/publication order is not fully recovered |
| Action sample | semantic values, device/source identity, observation time, press/release history | Game action storage/freshness is still being traced |
| Body state | pose, linear/angular velocity, mass/inertia, center of mass and frames | Different rider/hull representations must remain distinct |
| Surface query | hit identity, normal/plane, selected material/profile, depth/thickness and validity | Collision-mask summary is not material identity |
| Contact state | immersion, contact/absence timers, actual contact evidence, cached flags | Sequential observations may cross updates; immersion alone is insufficient |
| Trick state | proposal, accepted values, assistance state, target pose and resets | Main-body actuation through component/child receivers remains unresolved |
| Animation state | requested/selected resource, phase, playback controls, weights/masks, local pose | Complete authored-to-runtime binding and active landing selection remain open |
| Environment state | time coordinate, pause gates, selected controllers, transition state | Track time encoding and some physical consumers are unresolved |

Do not collapse requested, accepted, cached and physically applied values into one variable. That would erase several distinctions the investigation worked to establish.

## Implementation sequence

### 1. Headless numerical foundation

Implement frame conventions, vector/quaternion operations and explicit time inputs. Put float32-sensitive operations behind tested helpers. Use synthetic plane geometry so contact changes can be understood without uncertain terrain.

Acceptance: coordinate round trips, quaternion sign/equivalence checks, time-step handling and threshold boundary tests pass. Every unit is documented or marked unresolved.

### 2. Snow vertical slice

Read the snow guide, material, body construction, integration, rider and contact-ownership chapters. Implement the local forces, input shaping and jump-release rules for one documented representation. Expose unknown selection rules as inputs.

Acceptance: tests cover flat/slope descent, contact loss/return, steering changes, coil release and mass selection. Record force contributions and gates independently. Stability or plausible motion is not evidence of original-game equivalence.

### 3. Trick and landing state

Implement proven proposal, assistance and reset rules. Represent the missing target-to-physical-body consumer as an explicit adapter. If an approximate actuator is necessary to make the prototype playable, name and document it as a substitute.

Acceptance: pure-axis rotation, release/latch lifetime and landing/reset tests distinguish the controller target, visual orientation and physical angular velocity. Do not impose the separate pose follower's angular caps globally.

### 4. Animation

Start with a minimal authored or independently supplied rig/clip fixture. Implement proven playback, blending and IK kernels before recreating selection. The repository contains explanations, not the actual decoded clip payloads.

Acceptance: sampling, segment bounds, blend order, pose frames and procedural corrections have tests. Landing selection and missing resource bindings remain visible as unresolved interfaces or documented approximations.

### 5. Environment and other sports

Implement time-of-day progression, weather scalar interpolation and ordered overlays from the environment pseudocode, leaving the unknown track time adapter explicit. Add air sport models with their stated assumptions. Begin walking as a separate investigation or clearly labeled prototype controller.

Acceptance: pause, single-wrap behavior, target holds and overlay ordering have tests. No wind-to-aerodynamics or weather-to-grip link is invented as a recovered fact.

### 6. Camera, scoring and presentation integration

Add documented camera and scoring components through their contracts. Use telemetry to explain the visible result. Compare controlled scenarios with observed behavior only where inputs, terrain, state and measurement uncertainty are recorded.

Acceptance: each discrepancy is classified as an implementation error, missing producer/selection, substituted behavior or insufficient evidence. Visual similarity alone cannot close a physics or timing question.

## Agent task template

```text
Own: one module plus its contracts and tests.
Read: specific system documents, current status and evidence conventions.
Deliver:
  - Input/output/frame/unit/cadence contract.
  - Implemented local rules with document/section citations.
  - Explicit unresolved dependencies and labeled substitutes.
  - Boundary/state-transition tests and a reproducible synthetic scenario.
  - Telemetry fields that distinguish competing explanations.
  - Short implementation status with remaining questions.
Do not claim complete engine parity or modify another agent's interfaces silently.
```

Possible parallel ownership is snow/contact, input/runtime timing, tricks/landing, animation, and environment. Establish shared contracts first, then implement independently. Cross-system integration and validation need a designated owner.

## What would justify calling it complete?

For a scoped module, completeness means its agreed behavior and dependencies are implemented and tested, and unresolved original behavior is explicitly documented. For the whole original engine, this research cannot supply such a claim: rendering, networking, streaming, audio, tooling and many backend systems have not been reconstructed.
