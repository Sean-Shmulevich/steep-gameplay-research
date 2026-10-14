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

No native scheduler observation was made in this implementation pass. Six synthetic transport tests cover counter interpretation, empty claims with active executions, changes, guard failures, table/short-read rejection and bounded plan validation. They validate the collector contract, not concurrent game behavior.

The private dependency evidence verifier was also rerun against the inspected image: 778 instruction-byte checks, 19 specific checks and 20 table bindings passed. This rechecks the underlying static evidence separately from the synthetic transport tests.
