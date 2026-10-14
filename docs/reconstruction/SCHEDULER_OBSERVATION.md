# Observing the animation scheduler before attempting native stepping

The [observation adapter](../../engine/scheduler_observation.py) turns a caller-supplied exact-read transport into two guarded sweeps of seven named jobs. It does not attach to a process, write memory, stop threads or launch the game. This is collection infrastructure, not a successful live experiment.

## Layout and evidence

The job offsets and constructor-matched table identities come from the [animation dependency audit](ANIMATION_STAGE_DEPENDENCIES.md). The [rearm audit](SCHEDULER_REARM.md) explains execution accounting, lifecycle and request fields. Each header read includes the table pointer and six adjacent 32-bit fields:

| Job-relative offset | Interpretation |
| --- | --- |
| `0x4c` | Executions, including reserved work not yet inside its callback |
| `0x50` | Outstanding dispatches, including final bookkeeping |
| `0x54` | Lifecycle state: 0 unscheduled, 1 scheduled, 2 done |
| `0x58` | Started request count |
| `0x5c` | Requested count |
| `0x60` | Dependency holds |

Counters are reported as raw unsigned 32-bit values. Differences are retained as before/after pairs; subtraction is deliberately avoided because wrapping and missed transitions make frame-count inference invalid. Unknown lifecycle values remain visible.

Only `AnimationUpdateTime` gets a separate remaining-to-claim read at `0x1a0`, as established in the [claim lifecycle audit](ANIMATION_CLAIM_LIFECYCLE.md). The adapter does not extend that field interpretation to every range job merely because its table matches.

The layout targets the inspected image SHA-256 recorded in the module. Callers must validate their image separately. Matching virtual tables alone does not identify the player's world or establish ownership.

## Resolving the action graph from a world

`capture_world_pair(readv, world, image_base, guards)` resolves the graph through `world + 0x1038`. It adds two identity guards to every sweep: the world must still point to that graph, and the graph's first pointer must still point back to the world. The first pointer is data, not a virtual table. The seven embedded jobs have their own table pointers.

The static chain is explicit:

```text
world construction:
    graph = construct_action_graph(allocate(0xd728))
    world.action_graph = graph

world setup:
    setup_action_graph(world.action_graph, world)

setup_action_graph(graph, world):
    graph.world = world
    configure_action_and_animation_jobs(graph)
    ...
```

Construction calls `1408aff20` at `1408aef28` and stores its result at world+`0x1038` at `1408aef37`. World setup loads that field at `1408e5402`, passes the world as the second argument, and calls `140903b80` at `1408e540c`. Its entry stores the world into graph+0 at `140903b92` before invoking job setup. Four instruction spans were checked against the hash-matched image; the existing constructor verifier also passed 32 instruction slices and five table bindings.

This action graph is distinct from the physics scheduling state reached through world+`0xff0`, then component+`0x18`. Earlier player captures used that physics state to inspect motion jobs. Passing it as the animation graph owner would address different memory. The new wrapper checks the graph backlink and all seven job tables instead of assuming the owners are interchangeable.

A private capture command now connects fresh player acquisition, the selected managed-world handle, component/world backlinks and process-identity-checked bounded reads to this wrapper. It takes a current process identity and a new private output directory, sends no input and performs no game writes or debugger attachment. It has not yet been exercised against a live game in this pass. Matching these links still does not prove that the selected player's Kino component is present in the animation receiver array.

## Transport contract

```python
from engine.scheduler_observation import capture_pair

# readv([(address, size), ...]) must return equally ordered exact bytes.
# Discover and validate these values in the current process first.
report = capture_pair(readv, scheduler_owner, image_base, identity_guards)
```

`identity_guards` contains `(address, expected_bytes)` pairs for externally established process/object ownership links. Each of two sweeps performs guard reads, job reads, then guard reads again. A mismatch, incomplete read or wrong job table aborts. The transport must independently check process identity and enforce timeouts. The adapter bounds read sizes and count but cannot interrupt a blocked transport.

The report brackets each sweep with monotonic timestamps and records decoded counter changes. It does not publish raw memory. Caller-owned reports may still contain sensitive observations and should remain private until reviewed.

Equal guards can miss an object disappearing and being replaced at the same address. Equal counters can hide a complete update between reads. Even a single successful memory read is not a transaction across concurrently written fields. Consequently the report always leaves atomicity, player membership and safe stepping unestablished.

## Next live experiment

1. Validate process creation identity, image identity and the selected player's root/world chain using the existing private bounded reader. Join that world to this scheduler owner; do not substitute a nearby object or a previous session's address.
2. Collect these sweeps passively during a short session. Retain failed guard checks and transport failures in the private capture receipt.
3. Determine which jobs change and whether animation execution is observable while its claim count is zero. Missing that interval is inconclusive because polling can miss short jobs.
4. Use the observed identities to design entry/exit instrumentation at the ordinary frame boundary. Sampling alone cannot prove ordering, exclude new submissions or establish a safe pause.
5. Only after submission exclusion and completion of relevant work are demonstrated, attempt one-update release and verify return to the same controlled boundary. Rendering, loading and platform-service requirements remain separate checks.

No native scheduler observation was made in these implementation passes. Nine synthetic transport tests cover counter interpretation, empty claims with active executions, changes, guard failures, table/short-read rejection, bounded plan validation, world graph resolution, changed backlinks and missing graphs. They validate the collector contract, not concurrent game behavior.

The private dependency evidence verifier was also rerun against the inspected image: 778 instruction-byte checks, 19 specific checks and 20 table bindings passed. This rechecks the underlying static evidence separately from the synthetic transport tests.
