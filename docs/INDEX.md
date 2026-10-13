# System index

Start with [status](STATUS.md), [engine reconstruction](ENGINE_RECONSTRUCTION.md), and [agent instructions](../AGENTS.md).

| System | Scope |
| --- | --- |
| Snow | Contact, carving, materials, input shaping, body construction and springs |
| Input | Action ownership and unresolved freshness/order |
| Tricks | Proposals, assistance, resets and target publication |
| Animation | Skeleton, tracks, graph, blending, IK and runtime binding |
| Body | Landing, recovery, physical pose and constraints |
| Air | Wingsuit/paraglider controls, force models and environmental lift |
| Camera | Selection, transitions, filters and projection |
| World | Time, weather and authored metadata |
| Scoring | Formulas, detectors and attribution |
| Walking | Leads only; controller and snow effects remain open |

## Scheduler reconstruction

- [Release gates and current priorities](../engine/SCHEDULER_ROADMAP.md)
- [Timing arithmetic and smoothing](reconstruction/SCHEDULER_SMOOTHING_AUDIT.md)
- [Queue reservation, completion and request rearm](reconstruction/SCHEDULER_REARM.md)
- [Queue eligibility and selection](reconstruction/SCHEDULER_QUEUE_ELIGIBILITY.md)
- [Trace evidence analysis](reconstruction/TRACE_ANALYSIS.md)
- [Gameplay phase integration](reconstruction/GAMEPLAY_JOB_INTEGRATION.md)
- [Outer interface candidate](reconstruction/ENGINE_OUTER_INTERFACE.md)
- [Engine-owner destruction boundary](reconstruction/ENGINE_OWNER_DESTRUCTION.md)
- [Connected executable scheduler](reconstruction/MIXED_SCHEDULER_IMPLEMENTATION.md)
- [Mode writers and stage copies](reconstruction/ENGINE_MODE_WRITERS.md)
- [Concrete provider job chains](reconstruction/ENGINE_PROVIDER_CHAINS.md)
- [Engine event consumer and stop request](reconstruction/ENGINE_EVENT_CONSUMER.md)
- [Root-to-Step mode gates and provider boundaries](reconstruction/ENGINE_ROOT_STEP_ROUTE.md)
- [Engine event submission branch](reconstruction/ENGINE_EVENT_SUBMISSION.md)
- [EndFrame completion and rearm](reconstruction/ENGINE_LOOP_HANDSHAKE.md)
- [Explicit wait-helper accounting](reconstruction/WAIT_HELPER_DISPATCH.md)
- [Executable alternate propagation](reconstruction/ALTERNATE_DEPENDENCY_MODEL.md)
- [Engine-step action-chain caller](reconstruction/ACTION_REARM_CALLER.md)
- [Executable request, hold and credit rules](reconstruction/REQUEST_STATE_MODEL.md)
- [Unselected-branch dependency propagation](reconstruction/ALTERNATE_DEPENDENCY_RELEASE.md)
- [Registered receivers and gathered batches](reconstruction/SCHEDULER_MEMBERSHIP_FOLLOWUP.md)
- [Backend worker registration](reconstruction/BACKEND_WORKER_REGISTRATION.md)

## Air

- [CLIENT_GUIDE.txt](systems/air/CLIENT_GUIDE.txt)
- [collision-coupling/CLIENT_GUIDE.txt](systems/air/collision-coupling/CLIENT_GUIDE.txt)
- [collision-coupling/OPEN_BOUNDARIES.txt](systems/air/collision-coupling/OPEN_BOUNDARIES.txt)
- [controls/CLIENT_GUIDE.txt](systems/air/controls/CLIENT_GUIDE.txt)
- [integration/CLIENT_GUIDE.txt](systems/air/integration/CLIENT_GUIDE.txt)
- [lift/FINDINGS.txt](systems/air/lift/FINDINGS.txt)
- [selection/CLIENT_GUIDE.txt](systems/air/selection/CLIENT_GUIDE.txt)

## Animations

- [OVERVIEW.txt](systems/animations/OVERVIEW.txt)
- [angular-routing/CLIENT_GUIDE.txt](systems/animations/angular-routing/CLIENT_GUIDE.txt)
- [blending/CLIENT_GUIDE.txt](systems/animations/blending/CLIENT_GUIDE.txt)
- [clips/CLIENT_GUIDE.txt](systems/animations/clips/CLIENT_GUIDE.txt)
- [conversion/CLIENT_GUIDE.txt](systems/animations/conversion/CLIENT_GUIDE.txt)
- [corpus/CLIENT_GUIDE.txt](systems/animations/corpus/CLIENT_GUIDE.txt)
- [decisions/CLIENT_GUIDE.txt](systems/animations/decisions/CLIENT_GUIDE.txt)
- [equipment/CLIENT_GUIDE.txt](systems/animations/equipment/CLIENT_GUIDE.txt)
- [field-binding/CLIENT_GUIDE.txt](systems/animations/field-binding/CLIENT_GUIDE.txt)
- [graph-decoding/CLIENT_GUIDE.txt](systems/animations/graph-decoding/CLIENT_GUIDE.txt)
- [ik/CLIENT_GUIDE.txt](systems/animations/ik/CLIENT_GUIDE.txt)
- [ik-solve/CLIENT_GUIDE.txt](systems/animations/ik-solve/CLIENT_GUIDE.txt)
- [landing-inputs/findings.md](systems/animations/landing-inputs/findings.md)
- [landing-inputs/next-investigation.md](systems/animations/landing-inputs/next-investigation.md)
- [landing-inputs/pseudocode.md](systems/animations/landing-inputs/pseudocode.md)
- [landing-inputs/trace-recipe.md](systems/animations/landing-inputs/trace-recipe.md)
- [landing-pose/CLIENT_GUIDE.txt](systems/animations/landing-pose/CLIENT_GUIDE.txt)
- [paths/CLIENT_GUIDE.txt](systems/animations/paths/CLIENT_GUIDE.txt)
- [physics-pose/CLIENT_GUIDE.txt](systems/animations/physics-pose/CLIENT_GUIDE.txt)
- [playback/CLIENT_GUIDE.txt](systems/animations/playback/CLIENT_GUIDE.txt)
- [pose-assembly/CLIENT_GUIDE.txt](systems/animations/pose-assembly/CLIENT_GUIDE.txt)
- [ragdoll/CLIENT_GUIDE.txt](systems/animations/ragdoll/CLIENT_GUIDE.txt)
- [rider-graph/CLIENT_GUIDE.txt](systems/animations/rider-graph/CLIENT_GUIDE.txt)
- [runtime-binding/findings.md](systems/animations/runtime-binding/findings.md)
- [runtime-binding/next-investigation.md](systems/animations/runtime-binding/next-investigation.md)
- [runtime-binding/pseudocode.md](systems/animations/runtime-binding/pseudocode.md)
- [runtime-binding/trace-recipe.md](systems/animations/runtime-binding/trace-recipe.md)
- [scheduling/CLIENT_GUIDE.txt](systems/animations/scheduling/CLIENT_GUIDE.txt)
- [selection/CLIENT_GUIDE.txt](systems/animations/selection/CLIENT_GUIDE.txt)
- [skeleton/CLIENT_GUIDE.txt](systems/animations/skeleton/CLIENT_GUIDE.txt)
- [skinning/CLIENT_GUIDE.txt](systems/animations/skinning/CLIENT_GUIDE.txt)

## Body

- [CLIENT_GUIDE.txt](systems/body/CLIENT_GUIDE.txt)
- [landing-producers/CLIENT_GUIDE.txt](systems/body/landing-producers/CLIENT_GUIDE.txt)
- [landing-quality/CLIENT_GUIDE.txt](systems/body/landing-quality/CLIENT_GUIDE.txt)
- [pose-follower/evidence.md](systems/body/pose-follower/evidence.md)
- [pose-follower/findings.md](systems/body/pose-follower/findings.md)
- [pose-follower/next-investigation.md](systems/body/pose-follower/next-investigation.md)
- [pose-follower/pseudocode.md](systems/body/pose-follower/pseudocode.md)
- [recovery/CLIENT_GUIDE.txt](systems/body/recovery/CLIENT_GUIDE.txt)
- [recovery-transitions/CLIENT_GUIDE.txt](systems/body/recovery-transitions/CLIENT_GUIDE.txt)
- [request-consumer/CLIENT_GUIDE.txt](systems/body/request-consumer/CLIENT_GUIDE.txt)

## Camera

- [CLIENT_GUIDE.txt](systems/camera/CLIENT_GUIDE.txt)
- [final-output/CLIENT_GUIDE.txt](systems/camera/final-output/CLIENT_GUIDE.txt)
- [projection-setup/CLIENT_GUIDE.txt](systems/camera/projection-setup/CLIENT_GUIDE.txt)
- [routing/CLIENT_GUIDE.txt](systems/camera/routing/CLIENT_GUIDE.txt)
- [settings/CLIENT_GUIDE.txt](systems/camera/settings/CLIENT_GUIDE.txt)
- [transitions/CLIENT_GUIDE.txt](systems/camera/transitions/CLIENT_GUIDE.txt)

## Input

- [action-ownership/evidence.md](systems/input/action-ownership/evidence.md)
- [action-ownership/findings.md](systems/input/action-ownership/findings.md)
- [action-ownership/next-investigation.md](systems/input/action-ownership/next-investigation.md)
- [action-ownership/pseudocode.md](systems/input/action-ownership/pseudocode.md)

## Scoring

- [CLIENT_GUIDE.txt](systems/scoring/CLIENT_GUIDE.txt)
- [detector-inputs/CLIENT_GUIDE.txt](systems/scoring/detector-inputs/CLIENT_GUIDE.txt)

## Snow

- [CLIENT_GUIDE.txt](systems/snow/CLIENT_GUIDE.txt)
- [body-construction/CLIENT_GUIDE.txt](systems/snow/body-construction/CLIENT_GUIDE.txt)
- [contact-model.md](systems/snow/contact-model.md)
- [contact-ownership/evidence.md](systems/snow/contact-ownership/evidence.md)
- [contact-ownership/findings.md](systems/snow/contact-ownership/findings.md)
- [contact-ownership/next-investigation.md](systems/snow/contact-ownership/next-investigation.md)
- [contact-ownership/pseudocode.md](systems/snow/contact-ownership/pseudocode.md)
- [environment/WORLD_AND_WEATHER.txt](systems/snow/environment/WORLD_AND_WEATHER.txt)
- [impulse-coupling/CLIENT_GUIDE.txt](systems/snow/impulse-coupling/CLIENT_GUIDE.txt)
- [integration/CLIENT_GUIDE.txt](systems/snow/integration/CLIENT_GUIDE.txt)
- [leg-constraints/CLIENT_GUIDE.txt](systems/snow/leg-constraints/CLIENT_GUIDE.txt)
- [mass-selection/CLIENT_GUIDE.txt](systems/snow/mass-selection/CLIENT_GUIDE.txt)
- [materials/CLIENT_GUIDE.txt](systems/snow/materials/CLIENT_GUIDE.txt)
- [rider-frame-response/CLIENT_GUIDE.txt](systems/snow/rider-frame-response/CLIENT_GUIDE.txt)
- [rider-inputs/CLIENT_GUIDE.txt](systems/snow/rider-inputs/CLIENT_GUIDE.txt)
- [rider-targets/CLIENT_GUIDE.txt](systems/snow/rider-targets/CLIENT_GUIDE.txt)
- [terrain-binding/CLIENT_GUIDE.txt](systems/snow/terrain-binding/CLIENT_GUIDE.txt)

## Tricks

- [OVERVIEW.txt](systems/tricks/OVERVIEW.txt)
- [assistance-transition/CLIENT_GUIDE.txt](systems/tricks/assistance-transition/CLIENT_GUIDE.txt)
- [dynamics/CLIENT_GUIDE.txt](systems/tricks/dynamics/CLIENT_GUIDE.txt)
- [events/CLIENT_GUIDE.txt](systems/tricks/events/CLIENT_GUIDE.txt)
- [grab-input/CLIENT_GUIDE.txt](systems/tricks/grab-input/CLIENT_GUIDE.txt)
- [motion-lifecycle/CLIENT_GUIDE.txt](systems/tricks/motion-lifecycle/CLIENT_GUIDE.txt)
- [response-delay/CLIENT_GUIDE.txt](systems/tricks/response-delay/CLIENT_GUIDE.txt)
- [rotation/CLIENT_GUIDE.txt](systems/tricks/rotation/CLIENT_GUIDE.txt)
- [selection/CLIENT_GUIDE.txt](systems/tricks/selection/CLIENT_GUIDE.txt)
- [sequence/CLIENT_GUIDE.txt](systems/tricks/sequence/CLIENT_GUIDE.txt)
- [target-publication/evidence.md](systems/tricks/target-publication/evidence.md)
- [target-publication/findings.md](systems/tricks/target-publication/findings.md)
- [target-publication/next-investigation.md](systems/tricks/target-publication/next-investigation.md)
- [target-publication/pseudocode.md](systems/tricks/target-publication/pseudocode.md)

## Validation

- [observations/CLIENT_GUIDE.txt](systems/validation/observations/CLIENT_GUIDE.txt)

## Walking

- [research-plan.md](systems/walking/research-plan.md)

## World

- [environment-catalog/CLIENT_GUIDE.txt](systems/world/environment-catalog/CLIENT_GUIDE.txt)
- [environment-runtime/evidence.md](systems/world/environment-runtime/evidence.md)
- [environment-runtime/findings.md](systems/world/environment-runtime/findings.md)
- [environment-runtime/next-investigation.md](systems/world/environment-runtime/next-investigation.md)
- [environment-runtime/pseudocode.md](systems/world/environment-runtime/pseudocode.md)
- [equipment/CLIENT_GUIDE.txt](systems/world/equipment/CLIENT_GUIDE.txt)
- [locations/CLIENT_GUIDE.txt](systems/world/locations/CLIENT_GUIDE.txt)

## Validation

- [Moving-rider contact observation](validation/contact-motion.md)

## Implementation supplements

- [Work packages and acceptance gates](reconstruction/IMPLEMENTATION_TASKS.md)
- [Animation pipeline and unresolved joins](reconstruction/ANIMATION_PIPELINE.md)
- [Asset decoding and Studio findings](reconstruction/ASSET_PIPELINE.md)
- [Testbench and runtime adapters](reconstruction/TESTBENCH.md)
- [Machine-readable contracts](../contracts/systems.json)
- [Executable references and tests](../reference/README.md)
- [Selected resource relationships](../data/resource-links.json)

- [Executable ordinary queue policy](reconstruction/QUEUE_POLICY_MODEL.md)
- [Worker-count and queue-routing producers](reconstruction/SCHEDULER_QUEUE_PRODUCERS.md)

- [Named AI job queue assignments](reconstruction/AI_QUEUE_ASSIGNMENTS.md)

- [Motion and pre-physics queue assignments](reconstruction/MOTION_QUEUE_ASSIGNMENTS.md)

- [Motion job destruction and lifetime requirements](reconstruction/MOTION_JOB_DESTRUCTION.md)

- [Bounded worker-interleaving explorer](reconstruction/INTERLEAVING_EXPLORER.md)

- [Range worker yield counters](reconstruction/RANGE_WORKER_YIELD.md)

- [Worker TLS context and execution mode](reconstruction/WORKER_THREAD_CONTEXT.md)
