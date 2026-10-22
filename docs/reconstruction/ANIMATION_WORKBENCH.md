# Animation work-transform testbench

This offline inspection API composes recovered pose-bank gathering and context
conversion math. It requires no game executable or assets. It does not run the
animation scheduler, choose clips, publish a pose or call a live game function.

From the repository root:

```sh
python3 -m engine.animation_workbench engine/examples/animation_work_input.json
python3 -m engine.animation_workbench engine/examples/animation_work_input.json --output /tmp/animation-work.json
```

The bundled input is entirely synthetic. It selects records `[1, 0, 1]`, preserving
duplicates, and converts them relative to a translated identity context. Its
output positions are `[1,2,3,1]`, `[2,4,6,3]`, `[1,2,3,1]`. The context's raw fourth
position lane is intentionally 99; the recovered caller masks it, yielding unit
inverse scale. Rotation normalization uses an explicitly labeled substitute in
this example.

## Python API and input contract

```python
from engine.animation_workbench import inspect_work
result = inspect_work(request)
```

Input schema is `animation-work-input-v1`.

| Field | Meaning |
| --- | --- |
| `records` | Array of `[position4, rotation4]` records; XYZW quaternion order |
| `indices` | Ordered uint16 record selections; duplicates retained |
| `direct` | True copies bank records; false composes bank parent first |
| `parent_position`, `parent_rotation` | Four-lane parent values; may be null for direct mode |
| `context` | Omit/null for no visible context target; otherwise one of the forms below |
| `normalization` | Required explicitly when context is present |

A raw context is `{ "kind": "raw", "basis_rows": [row4,row4,row4], "position": position4 }`.
The pipeline extracts/normalizes its rotation, masks position W, inverts it, then
converts the gathered records. A converted context is `{ "kind": "converted",
"position": position4, "rotation": rotation4 }`. It bypasses raw conversion, so
its supplied position W is the scale used by the gather kernel.

Two normalization policies are accepted:

- `{"mode":"provided_seeds","seeds":[...]}` supplies one RSQRT estimate per
  final output rotation, plus one initial estimate for raw-context conversion.
  Estimates are consumed in that order. Matching the count is mandatory. Supplying
  a seed does not establish that it came from a CPU or live game observation.
- `{"mode":"exact_rsqrt_substitute"}` uses float32-rounded `1/sqrt(n)` as the
  estimate before the recovered refinement step. This is an explicit numerical
  substitute and does not promise native bit parity.

With no context, no normalization occurs and a normalization policy is rejected
as unused. The input is bounded to 4,096 records/selections and the CLI to 4 MiB.
Bounds, schema validation and rejection of nonfinite output are inspection policy,
not recovered game error handling.

## Results and evidence

Output schema is `animation-work-output-v1`. It contains transforms, the selected
path, and a log of each squared norm and supplied/substitute RSQRT estimate.
Evidence flags explicitly deny live memory access, pose publication, scheduler
execution, lifetime proof and original-engine equivalence. The API does not
upgrade caller-provided input into game-verified data.

The CLI returns exit code 2 with a JSON error on invalid input. It writes an output
file only after evaluation and strict JSON serialization succeed.

The underlying instruction checks cover:

| Kernel | Cases | Boundary |
| --- | ---: | --- |
| No-visible-context gather | 256 | Complete original loop, no stubs |
| Context-present gather | 192 | Converted context supplied; observed emulator RSQRT seeds |
| Transform inverse | 280 | Complete helper, no stubs |
| Raw context conversion | 128 | Scalar sqrt supplied; observed emulator RSQRT seeds |

See [detailed equations and receipts](CENTRAL_IMPULSE.md#context-free-animation-work-transforms)
and the subsequent context conversion sections. The CLI is our adapter around
those kernels; no additional original-game coverage is implied by its tests.
The live accessor reader and copy-out candidate solve different problems. Their
[remaining lifetime requirements](CENTRAL_IMPULSE.md#caller-owned-transform-copy-and-bypass-initialization)
remain prerequisites for feeding live snapshots into this testbench safely.

## Inspect a complete animation update

Run the synthetic example with the existing CLI:

```sh
python3 -m engine.animation_workbench engine/examples/animation_update_input.json
```

The `animation-update-input-v1` schema selects update inspection. It requires
`records`, `indices`, `saved`, `parent_position`, `parent_rotation`, `direct`,
`elapsed`, `duration`, `dt`, `bank_flags`, `saved_flag`, `bank_present`, `context`
and `numerics`. Records and saved entries are `[position4, rotation4]` pairs.
The saved array is ordered by selection, not indexed by bone ID. Duplicate
indices read preceding writes. The example writes bone zero twice, yielding
X=2 from X=8 at alpha=0.5. It does not move a game character.

`context` is null for context-free application, or an object with three
four-lane `basis_rows` and four-lane `position`. Unlike the gathering schema,
this context is the forward application matrix. Its fourth position lane is
masked to zero by recovered behavior. The API requires direct mode to agree
with bit 26 of `bank_flags`; composed banks require parent transforms.

Choose numerical policy explicitly:

```json
{"rsqrt":"exact_rsqrt_substitute","trig":"host_math_substitute"}
```

Or supply `{"rsqrt":"provided_seeds","seeds":[...],"trig":"host_math_substitute"}`.
Seed count depends on executed branches. Missing and unused seeds are errors.
Output records each normalization and transcendental service call. Supplied seed
provenance is not verified. Host trigonometry and exact reciprocal-square-root
seeds are substitutes, not claims about native library implementations.

Output `result` contains updated records, clock, bank flags, branches and a
`handoff` boolean. A handoff requests deferred evaluation; the evaluator is
**not executed**, so the state describes the boundary before its effects.
No pointers, game memory, scheduling or asset data are required. Input arrays
are limited to 4096 records/selections; finite shape/range checks are inspection
policy, not recovered native guards. CLI files retain the 4 MiB limit.

Tests replay all 256 context-free and 512 context-bearing synthetic update
receipts through this API with recorded RSQRT seeds and host math services.
See the [complete update evidence](CENTRAL_IMPULSE.md#complete-inline-context-update).

## Stateful work sessions

`engine.animation_work_session.AnimationWorkSession` exposes explicit
`request(duration, context_token)`, `advance(dt, bank_present=True)` and
`snapshot()` operations. Construct it with a bank, existing work state, selected
indices, context resolver and numerical services. Work state must include an
explicit `active_context_token`. Bank fields are `records`, `parent_position`,
`parent_rotation`, `direct` and `flags`. Work fields follow the evaluator contract:
`count`, `records`, `elapsed`, `duration`, `saved_flag`, `saved_scalar_bits`,
`saved_context_token`, `active_context_token`.

Run a synthetic request/defer/replace/expire example:

```sh
python3 -m engine.examples.animation_work_session_demo
```

The demo uses host math and exact reciprocal-square-root substitutes. It neither
loads assets nor connects to a game. The runner uses active count rather than
backing-record length, resolves the active context only when application reaches
that branch, completes deferred evaluation using the updated bank, and preserves
the new active context token. Inputs and returned snapshots are copied.

All 512 connected-cycle receipts replay through this session adapter. A separate
multi-call test verifies request, deferral, replacement and expiry transitions;
that test is an independent reconstruction test, not a multi-frame native replay.
Call order, timestep selection and context visibility are external inputs. This
class does not install a scheduler, allocate native work, retain native objects,
refresh indirect targets or make original-engine equivalence claims. A resolver
or numeric-service failure leaves the session's stored bank/work uncommitted;
external service side effects are not rolled back.

### Consecutive original-instruction validation

The [sequence receipt](../../native/snow_host/work_sequence_validation.json)
contains 32 scenarios of five successive original update calls, 160 calls total.
Bank/work storage and installed context holders are not reset between calls.
After the first call, synthetic context translations change before each next
call, and supplied timesteps advance the retained work state. The session runner
matches bank bytes/flags, active work records/count, clock, saved request fields
and installed context selection after every call. Original deferred evaluators
execute when reached; allocation capacity and numerical services retain their
previous interception boundaries.

These are multi-call native-instruction sequences, not live frame replay. No
world scheduler, renderer, physics step, animation graph producer or concurrent
context writer runs between calls. Context motion is an explicit synthetic
independent variable. The receipt strengthens state continuity evidence without
establishing original-game determinism or general thread safety.

### Supplying skeleton metadata

The [initial skeleton assembly adapter](ANIMATION_SKELETON.md) produces hierarchy
metadata and selected work indices from explicit source and lookup inputs. It
keeps merged-rig construction and unknown storage bytes outside its claims.

### Preparation with a visible context

The [context preparation receipt](../../native/snow_host/preparation_context_validation.json)
extends the integrated preparation check with a visible inline active context.
All 128 synthetic cases execute the original preparation entry and reached local
callees. Twenty-two reach context conversion/application math; the remaining
cases exercise request, work-count, mask or expiry gates that bypass it. Both
primary and current hierarchy branches and independently varied processed
prefix counts are included.

The comparison checks both bank byte arrays and flags, work count/active records,
elapsed/duration, pending publication, scalar reset, saved-request flag, and
lock/apply/process/unlock event order. It consumes every captured RSQRT seed and
trigonometric service result in order. New requests and queued handoffs in this
receipt carry null context, so it does not establish preparation-level switching
to a second visible target. It also does not check all holder reference counts.

Locks and allocation capacity are intercepted; trigonometric and square-root
services use host math. Inline context storage has no concurrent writer. The
result supports composition of recovered local math and preparation control
flow, not live locking, indirect accessor lifetime or scheduler safety.

### Context replacement through preparation

A separate [switching receipt](../../native/snow_host/preparation_context_switch_validation.json)
runs 128 preparation cases whose immediate and saved requests reference a second
visible inline context. Fifty-three cases replace the installed holder; 46 reach
context application math. These counts describe different events and overlap.
The previous null-request-context receipt remains a distinct baseline.

Besides the bank, work, timing and event-order comparisons above, this experiment
checks the installed holder, saved scalar bits and saved context pointer against
the reconstructed state. It checks old/new holder reference counts: replacement
changes the supplied counts from 20/20 to 19/21, while cases without replacement
retain 20/20. Original retention/release instructions execute, but no count
reaches zero and no destruction or retirement path is exercised. Numeric services,
capacity and lock interception remain unchanged. This closes a preparation-level
context-switch validation gap without proving concurrent lifetime safety.
