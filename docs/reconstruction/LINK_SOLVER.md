# Link row construction and numerical solving

This guide continues the [central impulse and pose research](CENTRAL_IMPULSE.md).
It covers recovered link-row construction, the supported numerical solver categories,
body buffers and feedback. Each section states its native evidence and remaining
boundaries. It is an independent reconstruction, not original engine source.

### Link profile combination and response gate

`engine.pose_link_coefficients.combine_link_scalar` reconstructs0x1990830.
Its raw uint32 mode selects min0, max1, sum2, product3, arithmetic mean4 or
sqrt(product)5; other modes return positive zero. Minimum/maximum use rounded
`second-first` comparisons. On equality minimum retains the first operand and
maximum retains the second, preserving signed-zero distinctions. Every arithmetic
step rounds to float32. The independent API excludes nonfinite inputs and negative
geometric-mean products rather than inventing native exception behavior.

The connected0x19935ee..0x1993701 fragment combines profile fields+0x30,+0x40,
+0x60 and conditionally+0x64 using four separately supplied mode values. Earlier
code resolves the profiles through per-entry/resource branches, now reconstructed
in the paired lookup below. Physical meanings of these fields remain unresolved.
`link_response_coefficients` preserves the following arithmetic:

```
s = context.scalar_c
k = combine(profileA.field60, profileB.field60, mode60)
response = -float32(s * context.factor14)
seed_gate = +0
if k < float32(1e12):
    n = (context.flags38 >> 2) & 0x3fff
    scaled = float32(float32(n) * s)
    c = combine(profileA.field64, profileB.field64, mode64)
    denominator = float32(float32(c * scaled) + k)
    ratio = float32(s / denominator)
    response = -float32(ratio * k)
    seed_gate = float32(ratio * scaled)
```

Combined field30/field40 are produced before this branch and returned separately.
The actual threshold float is999999995904.0. Equality takes the initial-response,
zero-gate branch and never reads field64. The gate is the value subsequently
compared against zero in the cached-result seeding fragment. Under positive,
nonzero inputs the below-threshold branch produces a nonzero gate and bypasses
that seed, whereas the at/above-threshold branch permits it. Zero factors/counts,
rounding and exceptional values must not be generalized from that ordinary case.
No stiffness/damping, time-step or material interpretation is assigned solely from
the formula's shape.

[512 complete combiner and512 connected response-fragment comparisons](../../native/snow_host/pose_link_coefficients_validation.json)
execute original instructions without interception, matching float32 bits for
combined values, response and both gate storage locations. Modes, profiles and
context inputs are supplied. Cases include default modes, signed-zero ties and
threshold branches. An independent composition test feeds the derived gate into
cache seeding and checks both admission outcomes. Singular denominators, negative
root products and other exceptional arithmetic remain outside the Python domain;
resource ownership, row assembly and solver iteration remain unresolved.

### Paired link profile resolution

`engine.pose_link_profiles.resolve_pose_link_profiles` reconstructs the complete
paired lookup fragment at0x1993514..0x19935ee for the0x19933d0 builder family.
Each body supplies an entry array through+0xb8. Payload uint16 indices at+0x48
and+0x4a select72-byte entries, whose+0x10 pointers select resource descriptors.
Both resource pointers are captured before either profile is resolved.

Both endpoints use the same payload selector. This is a structural observation,
not evidence that the two bodies have the same material or resource kind.

```python
resource_a = first_body.entries[payload.u16(0x48)].resource
resource_b = second_body.entries[payload.u16(0x4a)].resource

def profile(resource):
    kind = resource.kind28 & 0x7fff
    if kind == 6 and resource.map60 is not null:
        return resource.table50[resource.map60[payload.u16(0x3e)]]
    if kind == 7 and resource.mapb0 is not null:
        return resource.tablea0[resource.mapb0[payload.u32(0x3c) >> 1]]
    return resource.default20
```

Maps contain byte indices into pointer tables. The short selector is the high
half of the same raw32-bit word used by kind7. Kind7 discards only its low bit.
A null map falls back to the default profile; a selected null profile does not.
The independent API returns opaque profile tokens. Callers retain the resources,
map storage, tables and profile objects and pass the selected profile fields to
`link_response_coefficients`. Resource-kind names, asset ownership and lifetime
rules remain unknown. No memory synchronization or live lookup is implemented.

[512 offline native lookup comparisons](../../native/snow_host/pose_link_profiles_validation.json)
execute the entire paired fragment without intercepted calls. Cases vary both
entry indices, resource kinds, map presence, byte selections and raw profile
pointers. Unselected entries contain different pointers to catch wrong indexing.
Both outputs and retained input bytes match. A synthetic composition test passes
the selected profiles into coefficient evaluation, independently checking that
default profiles are not substituted. This does not validate other builder
families or establish physical units.

### Link builder dispatch

`engine.pose_link_dispatch.dispatch_pose_link_builders` reconstructs0x1994970.
It visits a supplied retained link-pointer range in order. A link participates
only when its flag byte+0x84 has bit0 set. The dispatcher captures first/second
body pointers, context flags+0x38 low two bits and the link payload count. It then
reads bit15 of the second body's metadata word, reached through body+0x30 and
metadata+0x50. That bit chooses a builder pair for the whole link.

For each captured payload slot, the original getter reloads the payload array
pointer and returns the payload pointer from the16-byte key/pointer entry. Payload
flag+0x114 bit0 gates the call. With captured context mode zero, a payload count
at+0x110 greater than one selects the multi path. Every other case selects the
single path, including an enabled payload with count zero.

| Second metadata bit15 | Captured mode zero and payload count >1 | Service | Native builder |
| --- | --- | --- | --- |
| Clear | Yes | `metadata_clear_multi` |0x1991da0 |
| Clear | No | `metadata_clear_single` |0x19933d0 |
| Set | Yes | `metadata_set_multi` |0x1991110 |
| Set | No | `metadata_set_single` |0x1992800 |

Every service receives `(context, first_body, second_body, payload)`. These names
describe branch conditions, not physical classes. The profile lookup, response
coefficients and result binding reconstructed above belong to
`metadata_clear_single`; they must not silently stand in for the other three
builders. In particular, a nonzero context mode can send a multi-row payload to
that builder.

Captured link gates, count, body pointers and mode remain unchanged for the
current traversal even when a builder callback changes their source fields.
Upcoming slot pointers, payload flags and payload row counts are read as traversal
advances. A later link captures its own current context mode. The independent API
requires retained storage and supplied builder services; it does not reconstruct
all four builder bodies or permit freeing the traversed range from a callback.

[512 full offline dispatcher comparisons](../../native/snow_host/pose_link_dispatch_validation.json)
run original array accessors and intercept only the four builder calls with
recording services. They compare ordered service selection, all call arguments,
retained payload bytes and callback-mutated state. The last128 cases enable
callbacks that replace payload slot storage and change mode, metadata, link count
and enable flags. These cases distinguish captured state from subsequent reads.
This validates dispatch, not solver output, concurrent mutation or live safety.

### Link point-motion tangent basis

`engine.pose_link_tangents.link_tangent_basis` reconstructs the tangent calculation
inside the metadata-clear/single builder. The continuous native fragment is
0x199381b..0x1993a35. Prologue0x199341e..0x19934d4 supplies the first body's basis
rows+0x40/+0x50/+0x60, local offset+0x128, and vectors+0x1a0/+0x1ac. The payload
row supplies its first local point at row+0x10 and direction at row+0. XYZ masks
exclude their fourth lanes. No second-body motion vector enters this calculation.

In the following structural pseudocode, every multiply, add, subtraction, square
root and division rounds to float32. The implementation preserves the original
sum order, including the final zero lane in horizontal dot reductions.

```python
local = first_point - first_body.offset128
r = basis_z * local.z + (local.x * basis_x + basis_y * local.y)
opposite_motion = -(cross(first_body.vector1ac, r) + first_body.vector1a0)
t = opposite_motion - dot(opposite_motion, normal) * normal
if float32(dot(t, t) - float32(1e-6)) < 0:
    x, y, z = normal
    if float32(min(abs(x), abs(y)) - abs(z)) < 0:
        t = [z, 0, -x] if float32(abs(y) - abs(x)) < 0 else [0, z, -y]
    else:
        t = [y, -x, 0]
first_direction = t * float32(1 / float32(sqrt(dot(t, t))))
second_direction = cross(normal, first_direction)
```

The arithmetic supports linear-like and angular-like roles for the two motion
vectors, but their units and complete producer contract remain unresolved. The
normal is not normalized here. Consequently the projection is only the usual
orthogonal projection when its normal has unit length, and the second direction
is not explicitly normalized. The native code subtracts the float32 threshold
before comparing against zero; the API preserves that operation rather than
replacing it with a differently rounded test. It rejects zero/nonfinite tangent
lengths instead of inventing fallback output for degenerate inputs.

Later stores place these first/second directions at+0x20 in the two secondary
solver rows. Their full equations and the primary row's response remain separate
work. This finding establishes direction construction, not a complete friction
model or second-body relative-velocity model.

[768 continuous offline native comparisons](../../native/snow_host/pose_link_tangents_validation.json)
match both output vectors bit-for-bit without intercepted calls. Caller registers
and runtime masks are supplied. Cases cover arbitrary nonorthogonal bases,
unnormalized normals, zero motion and motion near the fallback threshold. Unit
tests also distinguish point rotation from linear motion, local center subtraction,
parallel motion and degenerate input. No live capture or original-engine
equivalence is claimed.

### Primary link row response selection

`engine.pose_link_primary_response.link_primary_response` reconstructs
0x1993d1e..0x1993d9e in the metadata-clear/single builder. It consumes the paired
world-point separation, payload normal and the first-body opposite-motion
projection used before tangent removal. Every arithmetic step below rounds to
float32, with the XYZ dot reduced as `(x+y)+(z+0)`.

```python
delta = second_world_point - first_world_point
q = dot(normal, negative_first_body_point_motion)
position_candidate = (dot(delta, -normal) + context.field1c) * response_gain
motion_candidate = q * combined_profile40 if (q - context.field20) < 0 else +0
if (abs(position_candidate) - abs(motion_candidate)) < 0:
    selected = motion_candidate
else:
    selected = position_candidate
```

`response_gain` is the value recovered by `link_response_coefficients`, including
its threshold-dependent branch. `combined_profile40` is its `combined40` result.
The context fields come from+0x1c and+0x20. Gate equality rejects the motion
candidate. Magnitude equality retains the position candidate, including its sign.
The output is broadcast into all four lanes and stored at primary solver row+0x10.
This is selection by magnitude, not a scalar maximum or addition of candidates.

The preceding instructions form separation from both transformed local points
and their body translations. They also form the primary angular lever as the
first transformed local offset plus half the separation. Those producer and row
assembly instructions are static leads, not part of this fragment's validation.
No restitution, penetration tolerance or time unit is assigned to the raw fields
solely from the formula. The API requires finite arithmetic and does not reproduce
NaN selection or overflow exception behavior.

[768 offline native response comparisons](../../native/snow_host/pose_link_primary_response_validation.json)
execute the continuous fragment without interception. All four result lanes match
bit-for-bit, including threshold equality, opposite-sign magnitude ties and signed
zeros. Inputs are prepared register values; this does not prove full builder or
solver equivalence. A separate synthetic test connects recovered profile-response
coefficients to this selection formula.

### Link paired-point world geometry

`engine.pose_link_geometry.link_point_geometry` supplies the world geometry used
by the metadata-clear/single builder. It retains the first-body local offset
subtraction and world-space readdition. In this pseudocode, each operation rounds
to float32; `B.x`, `B.y`, `B.z` denote the stored basis rows, scaled as vectors.

```python
def transform(B, v):
    return B.z * v.z + (B.x * v.x + B.y * v.y)

first_center_world = first_translation + transform(first_basis, first_offset128)
first_arm = transform(first_basis, first_point - first_offset128)
second_arm = transform(second_basis, second_point)
first_world = first_arm + first_center_world
second_world = second_translation + second_arm
separation = second_world - first_world
```

Basis rows come from body+0x40/+0x50/+0x60, translations from+0x70, and the first
local offset from+0x128. Points are the already transformed local payload fields.
The first arm is also the offset used by the point-motion calculation. These sums
must not be simplified to a direct first-point transform. For example, with an
identity basis, point x=1 and offset x=2^25, the recovered subtraction/readdition
produces world x=0 in float32 rather than1. This example exposes operation order;
it is not a claim about ordinary game coordinate ranges.

The result's `separation` feeds `link_primary_response`. No inverse-transform or
orthonormal-frame assumption is imposed. Frame interpretation and units remain
caller obligations, and this API does not promise that transforming a payload
point back to world space reproduces its earlier source bits.

[512 offline geometry comparisons](../../native/snow_host/pose_link_geometry_validation.json)
execute original center-transform0x1993479..0x19934b3, point-subtraction
0x199381b..0x1993837 and paired-geometry0x1993a35..0x1993ada fragments. The validator
retains the native computed center and local offset between fragments but prepares
caller registers explicitly; it is not an uninterrupted full-builder comparison.
All XYZ bits match for both arms, both world points, center and separation.
Synthetic cases include nonorthogonal bases and large-offset cancellation. A
composition test connects separation to the recovered primary response formula.

### Connected single-family link row builder

`engine.pose_link_builder.build_pose_link_rows` now connects the recovered pieces
for the complete0x19933d0 metadata-clear/single builder. It resolves paired
profiles once, computes the shared coefficients and processes each retained
payload row. Each row consumes one primary112-byte slot, two secondary112-byte
slots and three sequential result indices. Context counters+0xa4/+0xbc count the
primary/secondary rows; +0x180 counts result indices. The independent API exposes
retained arrays and counters rather than process-relative storage addresses.

For each row it combines `link_point_geometry`, `link_tangent_basis`,
`link_primary_response`, result binding and conditional cached-result seeding.
The original first-body motion projection and tangent fourth lane are exposed as
diagnostics by the tangent helper so assembly preserves signed-zero lanes too.
With `r` the first arm, `delta` the paired separation and `n` the payload normal,
the primary angular lever is `r + float32(0.5 * delta)` componentwise. The primary
direction is `-n`; its angular direction is `cross(lever, -n)`. Both secondary
angular directions are `cross(r, tangent)`.

| Row field | Primary | Each secondary |
| --- | --- | --- |
| +0x00/+0x02 | First/second body uint16 indices | Same |
| +0x04 | Primary result index | Its own sequential result index |
| +0x10 | Selected response broadcast | First3 lanes `float32(dot(delta,tangent)*0)`, fourth lane FLT_MAX |
| +0x20 | Negated normal, fourth lane negative zero | Tangent direction with recovered fourth lane |
| +0x30 | Lever cross direction, fourth lane zero | First arm cross tangent, fourth lane zero |
| +0x50 | Eight zero bytes | Primary result index in first4 bytes |
| +0x60 | Cache-seeding gate broadcast | Combined profile field30 broadcast |

Other bytes remain untouched, including+0x40..+0x4f. Secondary response lanes are
not unconditionally assigned positive zero: multiplication by zero preserves a
negative sign for a negative finite dot product. The first tangent's fourth lane
also preserves the projection/fallback path's signed zero. These details matter
for byte-exact reconstruction even where they do not change ordinary arithmetic.

The first result index is published in the payload feedback field. A zero gate
seeds that result with the raw prior cache word broadcast to four lanes; a nonzero
gate leaves existing result bytes unchanged. The separate seeding helper retains
its previously established unordered comparison behavior, while this connected
API remains restricted to finite nonsingular coefficient arithmetic. It supplies
no solver iteration and does not synthesize the result subsequently fed back.

[512 uninterrupted full-builder comparisons](../../native/snow_host/pose_link_builder_validation.json)
execute0x19933d0 to return, including original profile combination calls, without
interception. They compare every retained primary/secondary row byte, complete
payloads, all result storage and three counters. Cases cover0..4 rows, nonzero
initial counters, zero/nonzero point motion, both coefficient branches, all six
combination modes and arbitrary cached bits. The native resource descriptors use
the default-profile branch; indexed resolution has separate fragment validation.
No builder calls, geometry helpers or coefficient arithmetic are replaced.

Unit tests cover preservation of unused rows/padding, both cache-seed outcomes,
zero-row allocation and a builder-to-feedback composition with an explicitly
supplied external solver result. This supersedes the earlier lack of connected
row assembly for this family only. Other three builder families, solver iteration,
live lifetime and physical units remain unresolved. Retained storage capacity,
valid indices and finite arithmetic are required; no native allocation failure or
concurrent mutation behavior is invented.

### Runnable link-builder inspection

`python3 -m engine.pose_link_builder_bench engine/examples/pose_link_builder.json`
runs the complete reconstructed metadata-clear/single row builder without game
files. `--output PATH` writes its JSON report. The bundled fixture is authored
synthetic data and produces one primary row, two secondary rows and a cached-word
seed. It does not execute the physics solver.

The `pose-link-builder-v1` schema requires explicit provenance and sequence
`reached_metadata_clear_single`. Inputs include complete prior payload bytes,
body frames and motion fields, symbolic resource/profile identities, scalar modes,
context fields/counters and complete retained primary/secondary/result storage as
hex arrays. Profile resources may use default pointers or the recovered kind6/7
byte-map/table branches. Maps use JSON lists of uint8 values; pointer tables use
symbolic identity lists. These are retained-data representations, not game heap
addresses. Dispatcher admission remains caller supplied.

The inspector copies inputs before execution. It reports initial/final counters,
readable newly written rows, updated payload bytes and every retained storage row
as hex. Result storage stays raw so cached NaN bit patterns are not mistaken for
JSON numeric values. Readable row fields must serialize as finite JSON numbers.
No missing prior bytes, capacities, profiles or resource defaults are invented.
Inspection limits of4096 storage rows and1048576 map entries, JSON validation and
error handling are authored safeguards rather than recovered native behavior.

Tests cover the sample's direction/response/cache outputs, padding preservation,
input immutability, indexed profile selection, insufficient storage, zero-row
behavior, provenance and CLI equivalence. The underlying builder has separate
uninterrupted native validation; JSON parsing and presentation do not gain native
equivalence from that evidence. Other builder families, physical units, solver
iteration and live object lifetime remain outside this tool.

### Solver preparation and iteration control

`engine.pose_solver_control.run_pose_solver` reconstructs the wrapper0x1994e80
and its internal control routine0x19e5aa0. Numerical preparation0x19e4710 and one
iteration0x19e4d10 remain supplied services. The wrapper captures the context flags
before invoking either service.

```python
phase = flags38 & 0x18000000
special = phase == 0x10000000
iterations = ((flags38 >> 16) & 0x7ff) if special else ((flags38 >> 2) & 0x3fff)
saved = raw_bytes(context[0x0c:0x14])
if special:
    context.scalar_c = 1.0
    context.scalar_10 = 1.0
descriptor = capture_storage_descriptor(context)
cursor = address_of(descriptor.result_pointer_slot)
prepare(descriptor, cursor_by_reference)
if iterations != 0:
    cursor = address_of(descriptor.result_pointer_slot)
    repeat iterations times:
        iterate(descriptor, cursor_by_reference)
if special:
    context[0x0c:0x14] = saved
```

Preparation runs even for zero iterations. The cursor is reset once before the
first iteration, not before every iteration. Changes made by an iteration persist
into the next call. Flag changes made by services cannot alter the already captured
iteration count or special-phase restoration decision. The two saved scalars are
restored as raw bits on normal return, preserving signed zeros and NaN encodings.
Other phases do not restore service writes to those fields. Exception unwinding
and recovery behavior have not been established.

The captured descriptor holds context+0x40 for row layout, and base plus uint32
relative offsets+0x16c, +0x178, +0x170 and+0x174 for rows, results and the two body
buffers respectively. Its final byte records the special phase. The API uses
`descriptor_result_slot` as the initial cursor identity instead of exposing the
native temporary stack address. Buffer labels describe the observed layout;
full buffer ownership and numerical preparation are separate dependencies.

[384 offline wrapper/control comparisons](../../native/snow_host/pose_solver_control_validation.json)
execute both complete native control routines and replace only preparation and
iteration with recording services. Those services mutate scalars, flags and the
cursor. Tests compare ordered calls, captured descriptors, cursor transitions,
scalar bytes seen by each service and the complete final context. All four phase
masks and zero/nonzero iteration counts are covered. This proves control flow and
normal-return restoration, not numerical convergence, solver equations or live
thread safety. The next numerical targets are the preparation and iteration
routines, particularly their consumers of the112-byte rows assembled above.

### Primary row numerical preparation and iteration

`engine.pose_primary_solver` reconstructs complete preparation0x19e55d0 and
iteration0x19e5710. Both operate on the first uint16 body index and the row's
uint32 result index. The second body index is not read by these routines.
Body data has64 bytes, body state32 bytes and each result16 bytes. The descriptor
result slot is followed by pointers to body data and body state.

Let `d` be row+0x20, `a` row+0x30, and `M0..M3` the four vectors in the selected
body-data record. All operations below round to float32. Dot products mask out
the fourth lane and reduce as `(x+y)+(z+0)`, while state updates use all four lanes.

```python
weighted_linear = M3 * d
weighted_angular = M2 * a.z + (M1 * a.y + M0 * a.x)
denominator = (dot(weighted_angular, a) + dot(d, weighted_linear)) + row60.x
row40 = broadcast(float32(1 / -denominator))
state_linear += cached_result * weighted_linear
state_angular += cached_result * weighted_angular
```

Preparation stores the reciprocal at row+0x40, filling the previously untouched
field in the builder output. The original calculates four reciprocal lanes then
broadcasts lane0; the finite independent implementation computes the surviving
lane. Cached results are applied componentwise to both state vectors. This makes
the earlier cache seeding observable as a body-state contribution, not merely
retained bookkeeping. The exact physical units and body-data producer are still
external dependencies.

One iteration performs:

```python
speed = dot(a, state_angular) + dot(d, state_linear)
candidate = row40 * (broadcast(speed) + row10) + old_result
new_result = max(candidate, +0)  # lane-wise, ties choose positive zero
change = new_result - old_result
state_linear += change * weighted_linear
state_angular += change * weighted_angular
if row50_u64 != 0:
    vector_at(row_base + 16 * row50_u64) += new_result
result = new_result
```

The optional accumulation adds the new result, not its increment. In our recovered
link builder the primary row's row50 is zero. The general routine nevertheless
supports a nonzero row-relative vector slot; the API requires enough retained
bytes to represent that storage and does not follow arbitrary pointers. Values
are restricted to finite nonsingular arithmetic. Native NaN/MAXPS behavior,
exception masks, aliases and invalid offsets have not been generalized.

[512 numerical sequences](../../native/snow_host/pose_primary_solver_validation.json)
execute complete original preparation followed by three complete iterations each,
with no intercepted calls. All row, body-state and result bytes match after every
stage, including untouched records and optional accumulation. That is512 native
preparations and1536 native iterations. A separate synthetic composition test now
runs builder output through actual reconstructed primary preparation/iteration
and then feedback; it does not substitute an external result. Secondary tangent
rows are deliberately outside that test's scope, so this is not a complete contact
solve or a whole-engine convergence claim.

The preparation dispatcher routes the layout's primary112-byte rows through this
pair. It reads the primary traversal count at layout+0xc8, corresponding to
context+0x108, and the secondary traversal count at layout+0xe0, context+0x120.
These are distinct from the builder's incrementing counters+0xa4/+0xbc. Their
population must be respected when connecting the whole dispatcher; equal counts
must not be assumed merely because the builder test filled that many rows. The
secondary112-byte preparation target is0x19ef170 and its numerical coupling
remains the next unresolved part of this row family.

### Tangent row numerical preparation and coupling

`engine.pose_tangent_solver` reconstructs complete preparation0x19ef170 and
iteration0x19f2050 for the one-body112-byte secondary rows. The preparation
uses the same weighted direction vectors and cached-result state application as
the primary routine, but its reciprocal denominator does not add row+0x60.
That field instead controls the subsequent primary-result-dependent bound.

With float32 rounding after each operation, preparation computes:

```python
weighted_linear = M3 * d
weighted_angular = M2 * a.z + (M1 * a.y + M0 * a.x)
denominator = dot(weighted_angular, a) + dot(d, weighted_linear)
row40 = broadcast(1 / -denominator)
state_linear += old_result * weighted_linear
state_angular += old_result * weighted_angular
```

The linked primary result index is the uint32 at row+0x50. Iteration computes each
lane independently, preserving SSE min/max operand selection on equal values:

```python
bound = row60 * results[row50_u32]
speed = dot(a, state_angular) + dot(d, state_linear)
candidate = broadcast(-speed) * row40 + old_result
new_result = max(min(candidate, bound), -bound)
change = old_result - new_result
state_linear += change * weighted_linear
state_angular += change * weighted_angular
result = new_result
```

Unlike the primary iteration, the state increment is old minus new. Row+0x10 is
not read by this routine, despite the builder storing response/limit-looking
values there. Do not apply a generic row solver that consumes those values here.
The two tangent rows each clamp against their linked primary result; this local
routine does not compute a joint two-dimensional magnitude limit. Negative bounds
retain the original sequential min/max behavior rather than being reordered.
Finite min/max ties take the second operand, preserving signed-zero behavior.

This closes the consumer of combined profile field30 for this builder family:
it scales the linked primary result to bound the tangent result. That is direct
arithmetic evidence for a friction-like coupling, while field naming, original
units and the wider material model still require their producers. The code does
not justify treating this coefficient as a universal snow grip parameter.

[512 tangent numerical sequences](../../native/snow_host/pose_tangent_solver_validation.json)
run complete native preparation and three complete native iterations per case
without interception. All retained row, state and result bytes match after every
stage, including unrelated records. Cases allow the linked index to equal the
current index and use negative linked results to exercise inverted bounds.
A synthetic integration test builds a primary/two-tangent triplet, prepares all
three and iterates them in primary-then-tangents order. Its primary result bounds
the tangent update and changes the first body's state. This composition is a
Python integration test, not yet an uninterrupted native whole-solver comparison.
Other row families, traversal-count production, body-data production, original
units and live identity remain unresolved.

### Connected primary and tangent solver slice

`engine.pose_link_solve.solve_pose_link_rows` connects the recovered phase/count
wrapper to numerical preparation and iteration for the primary112-byte and
secondary112-byte categories. It accepts explicit retained context bytes, row
arrays, body-data/state records and results. Primary traversal count comes from
context+0x108 and secondary count from+0x120. Builder append counters are not used
as a substitute. Other row-category counts must be zero or the API rejects the
request instead of silently dropping work.

Preparation visits all selected primary rows, then all selected tangent rows.
Each iteration repeats that order. Phase mask0x10000000 prepares and iterates only
primary rows; the other three phase masks include tangents. Zero iterations still
run preparation, which can modify state through cached results. The common wrapper
retains its temporary unit-scalar substitution/restoration and captured count policy.
The supported numerical routines do not alter the descriptor cursor.

[256 connected native cases](../../native/snow_host/pose_link_solve_validation.json)
first execute the complete original link builder, then supply explicit traversal
counts and body buffers and execute the original solver wrapper to return. The
wrapper, preparation dispatcher, iteration dispatcher and numerical row routines
run uninterrupted without intercepted calls. Every retained row, result,
body-state and context byte matches the independent implementation. Body data is
unchanged. Cases span all four phase masks, zero/nonzero iteration counts,0..4
built payload rows and traversal extents smaller than the built row ranges.

This supersedes the earlier lack of native composition evidence for these two
categories only. The handoff between builder and solver still supplies counts and
body buffers; their native production is not claimed reconstructed. Other row
categories stay empty in validation and are rejected by the independent API.
This is a verified solver slice, not an all-category engine solve or a live modding
contract. Unit tests separately check normal/special phases, cached-state effects
with zero iterations, distinct traversal versus append counts, and explicit
rejection of unsupported populated categories.

### Solver body-buffer production

`engine.pose_body_buffers.build_pose_body_buffers` reconstructs0x1994560 around
an explicit damping-library dependency. It emits64-byte solver-data and32-byte
initial-state records in input body-array order. It does not read or assign body
indices; the caller must preserve the association used by the row builders.

The tensor getter0x1990af0 selects body+0x170 unless metadata byte+0x52 has bit3
set. That branch selects a shared zero tensor initialized by the getter's static
initialization path. Let `B0..B2` be body basis rows+0x40/+0x50/+0x60 and `I0..I2`
the selected tensor rows. Fourth input lanes are masked to positive zero. For each
component `j` in XYZ, the producer computes the following float32 vector sequence:

```python
Tj = (I1 * B1[j] + I0 * B0[j]) + I2 * B2[j]
output_row_j = B2 * Tj.z + (B1 * Tj.y + B0 * Tj.x)
```

Every multiplication/addition rounds separately, retaining the stated order and
all output lane bits. The fourth solver-data vector broadcasts body+0x124, or
positive zero when metadata bit3 is set. These records supply the weighted tensor
and linear scalar vectors consumed by the recovered numerical solver. This
establishes their body-field source; their earlier producers and physical units
are not yet established here.

Initial state starts with XYZ from body+0x1a0 and+0x1ac, with zero fourth lanes.
When metadata bit3 is clear, the producer adds `selected_vector * scalar` to the
first vector. Body byte+0xaa bit3 selects a zero vector; otherwise the caller's XYZ
vector is used. If body+0x1b8 is nonnull and scalar compares nonzero, a four-lane
library call receives `1 - damping_vector` and the scalar broadcast. Its returned
four lanes multiply the first state vector componentwise. Its fourth lane
multiplies all lanes of the second state vector. When the call is not reached,
the multiplier is one. Metadata bit3 bypasses both the increment and damping.

The API requires `damping_response` when that branch is reached. It does not
substitute `pow`, exponential damping or a tuned approximation for the original
library routine0x1c453d0. Input scalar/vector and bodies must remain constant during
this independent call; native callback mutation and static/TLS initialization are
not reconstructed by this interface.

[512 complete producer comparisons](../../native/snow_host/pose_body_buffers_validation.json)
execute the original producer and tensor getter with explicit initialized TLS and
static state. The first384 cases use no intercepted calls; the final128 supply the
damping-library response and compare its exact input vectors and admission gates.
All produced data/state bytes and untouched output tails match. Synthetic cases
cover arbitrary finite basis/tensor rows, metadata and body flags, zero/nonzero
scalars and empty body arrays. This closes body-buffer construction around one
remaining numerical library dependency; whole producer-to-solver native composition
and source units still require validation.

### Solver body-state feedback

`engine.pose_body_feedback.write_pose_body_feedback` reconstructs0x1994240 for
valid retained body-pointer ranges. The original takes the state buffer from
context plus uint32 offset+0x174 and advances32 bytes per body-array entry. For
each entry it copies raw state bytes0..11 to body+0x1a0 and state bytes16..27 to
body+0x1ac. The two fourth lanes are ignored. No arithmetic, normalization,
metadata gate or body-index lookup occurs in this routine.

Body array order establishes the association, matching the producer's sequential
output order. Duplicate identities are not deduplicated; later state entries
replace earlier motion-field writes. Bytes outside+0x1a0..+0x1b7, including the
pointer at+0x1b8, remain unchanged. The independent API rejects incomplete retained
records and excludes overlapping source/destination storage and concurrent edits.
It does not reproduce malformed native pointer-range behavior.

[512 complete native feedback comparisons](../../native/snow_host/pose_body_feedback_validation.json)
execute without interception over0..18 entries, covering both the four-body
unrolled path and scalar tail, repeated identities and arbitrary raw words.
Complete body buffers match, and context/source state buffers remain unchanged.
Raw NaN, infinity and signed-zero encodings are copied without interpretation.

A synthetic integration test now builds body buffers from body fields, assembles
a link triplet, runs primary/tangent solving, and writes the resulting state into
retained body motion fields. The test explicitly associates producer output with
the builder's body index and supplies traversal counts. It proves independent
composition of this supported path, not native reconstruction of that association,
counts or the entire frame scheduler. Individual stages and the connected solver
have native evidence; one uninterrupted full engine-frame comparison remains open.

### Solver category layout and count initialization

`engine.pose_solver_layout.plan_pose_solver_layout` and
`initialize_pose_solver_storage` reconstruct the layout arithmetic and retained
buffer initialization of0x19908d0. The input is25 category counts from an earlier
prepass, plus a body count. Getter0x19e5a90 supplies this fixed table of row strides
in16-byte units, in category order:

```
7, 8, 7, 8, 13, 16, 7, 8, 7, 8, 8, 11, 5,
5, 5, 6, 6, 7, 4, 5, 5, 6, 16, 22, 57
```

Category starts are prefix sums of `count * stride`, with uint32 wrap. Context
+0x40 stores these25 start offsets in16-byte units. Context+0xa4 stores25 builder
append counters, initially zero. Context+0x108 stores the25 planned/traversal
counts unchanged. This proves why traversal and append counts are distinct;
traversal counts are not copied from the builder counters after construction.

Rows begin at+0x190. After the row region come64-byte body-data records,32-byte
body-state records and16-byte result records. Body slots use only the low16 bits
of the input body count. Result count is the uint32 sum of all category counts.
The original rounds each region to16-byte alignment, using uint32 arithmetic.
The planner preserves those operations. The initializer requires enough retained
storage and rejects wrapped layouts rather than emulating out-of-bounds writes.

Initialization stores region offsets at+0x16c/+0x170/+0x174/+0x178, total size at
+0x17c, and clears the result append count at+0x180. It zeroes context+0x0c..+0x13
and+0x30..+0x37, and updates flags to `(previous & 0x98000003) | 0x18000000`.
Only result storage is cleared; prior row/body contents and unnamed header bytes
are retained. Native allocation, release and failure behavior are outside this API.

[256 native retained-buffer comparisons](../../native/snow_host/pose_solver_layout_validation.json)
execute the complete original routine and stride-table getter, supplying only
`memset` as a byte-fill service. The complete allocation, returned buffer identity
and unchanged retained capacity match. Cases include all categories, zero counts,
old header bits, preserved region contents and high bits in body count. Allocation
branches and dangerous overflow execution are not part of this validation.

Static caller0x1994da0 establishes the remaining count-producer leads. It clears a
25-counter temporary block, counts links through0x1994bb0 when settings field+0x24
is zero or0x1994cc0 otherwise, then counts poses through0x1994ad0. It passes those
counts and the group's body count to0x19908d0, initializes context settings through
0x1990ba0, and calls the solve orchestrator0x1993ed0. These prepass and body-index
assignment details remain open; the layout reconstruction does not infer counts
from already built rows.

### Link category-count prepasses

`engine.pose_link_counts.count_pose_link_rows` reconstructs0x1994bb0 for zero
settings mode and0x1994cc0 for nonzero mode. Both traverse retained links in order,
skip link flag84 bit0 clear, capture payload-array count, and include only payloads
with flag114 bit0 set. They sum raw uint32 payload row counts at+0x110 with wrap.
After the payload loop, second-body metadata word+0x50 bit15 selects category
branch `b=0` when clear or `b=1` when set.

For each enabled link, let `total` be the sum of enabled payload row counts,
`single` the number whose count equals1 and `multiple` the number whose count is
greater than1. The prepasses accumulate, rather than replacing prior counters:

```python
counts[b] += total
if settings_mode == 0:
    counts[6+b] += 2 * single
    counts[4+b] += multiple
else:
    counts[6+b] += 2 * total
```

Every counter operation wraps to uint32. A zero-row enabled payload contributes
nothing. Other categories remain untouched. In zero mode, categories4/5 represent
one grouped record per multi-row payload, rather than a pair of tangent records
per point. Their corresponding row sizes are208/256 bytes from the recovered
stride table, and their numerical equations are not supplied by the completed
single-family builder.

The caller selects the prepass using the entire raw settings uint32 at+0x24.
Builder dispatch later tests only the context mode's low two bits. The API keeps
this distinction; arbitrary mode values such as4 must not silently be reduced to
zero before counting. Valid configuration-domain constraints beyond the observed
branches remain unresolved.

[1024 full native prepass comparisons](../../native/snow_host/pose_link_counts_validation.json)
run both routines and original array getters without interception. All25 output
counters match and retained link/payload storage is unchanged. Cases include
metadata branches, disabled links/payloads, zero/single/multiple point counts,
nonzero prior counters and uint32 overflow. Oversized raw row counts appear only
in arithmetic validation; they do not extend the four-row builder contract.
Independent composition tests feed derived counts to layout and check the
single-payload counts against actual completed-builder output.

This closes link planned-count production around the retained link/payload
inputs. Pose-count contributions, body-index assignment, multi-row builder
families and configuration validation remain separate work.

### Pose category-count prepass

`engine.pose_category_counts.count_pose_categories` reconstructs0x1994ad0 and
its six recognized counting paths. It accepts the resolved uint32 result of each
pose's virtual slot+0x10 as explicit input. The native dispatcher subtracts one
and uses a six-entry jump table; values outside1..6 contribute nothing. Type4
increments category24 without reading a second body. All other recognized types
use second-body metadata word+0x50 bit15 to choose `b=0` when clear or `b=1` when set.

| Raw type | Category contributions |
| --- | --- |
|1 | `counts[10+b] += 1` |
|2 | Six-row classifier contributions below |
|3 | `counts[22+b] += 1`, `counts[8+b] += 2`, plus `counts[14+b] += 1` if storage uint32+0x68 is nonzero |
|4 | `counts[24] += 1` |
|5 | `counts[10+b] += 1`, `counts[8+b] += 1 + 4*(storage byte+0x68 != 0)`, plus `counts[12+b] += 1` if byte+0x70 is nonzero |
|6 | `counts[2+b] += 1` |

Type2 uses the previously recovered six-row classifier in
`engine.snow_pose_solver_counts.pose_solver_counts`. Its named count deltas map
to categories8+b for doubled rows,10+b for hard-triple blocks,14+b for flagged or
hard rows,16+b for first soft rows,18+b for second hard rows, and20+b for second
soft rows. Every addition wraps to uint32 and preserves preexisting counters.
This connects the classifier to actual planned category indices without changing
its threshold/state logic.

The inline storage getter0x1942bf0 returns pose+0x70. Type3 snapshots144 bytes;
type5 copies a larger structured record through0x1943190 before inspecting the
two bytes. Those bytes are copied unchanged, so the independent count API reads
them directly from retained inline storage. The cleanup target used by both is
0x75e600, inspected as `ret 0`; no hidden destruction effect is substituted.
The type3+0x68 test is a full uint32 test, while type5 tests only a byte. These
must not be merged into a common boolean interpretation.

[512 complete native prepass comparisons](../../native/snow_host/pose_category_counts_validation.json)
execute the original dispatcher, all six counting routines, inline getter,
type5 copy and cleanup. Virtual type methods are supplied as synthetic constant
return stubs. All25 accumulated counters match, and complete retained pose bytes
stay unchanged. Cases cover all recognized/unknown types, metadata branches,
flags, type2 thresholds and nonzero initial counters. This supplies counts, not
original class construction, animation equivalence or physical names for raw types.

Together with `count_pose_link_rows`, this fills the planned-count input consumed
by the reconstructed layout initializer for retained link and pose records. Body
index assignment, production of those records and the still unsupported numerical
row categories remain separate boundaries.

### Solver context settings initialization

`engine.pose_solver_settings.initialize_pose_solver_settings` reconstructs the
complete initializer0x1990ba0. It writes the supplied scalar to context+0x10 and
`float32(1 / scalar)` to+0x0c. This establishes a producer relationship between
two previously explicit inputs: body-buffer construction receives the stored
scalar through context+0x10, while profile-response equations use its reciprocal
from+0x0c. They are not independent settings in this native path. Physical units
of the original supplied scalar remain unresolved; the API does not label it as
seconds solely from this reciprocal relationship.

The following settings-to-context transfers copy raw four-byte words, including
any nonfinite encodings, without arithmetic:

| Settings offset | Context offset |
| --- | --- |
|+0x08,+0x0c,+0x10 |+0x00,+0x04,+0x08 |
|+0x2c,+0x30 |+0x14,+0x18 |
|+0x1c,+0x18 |+0x1c,+0x20 |
|+0x34,+0x38,+0x3c |+0x24,+0x28,+0x2c |

The supplied group token is stored at context+0x30. Flags become:

```python
flags = (previous_flags & 0x80000000)
flags |= settings.u32(0x24) & 3
flags |= (settings.byte(0x21) & 1) << 29
flags |= (settings.byte(0x14) & 1) << 30
flags |= (settings.u16(0x2a) & 0x7ff) << 16
flags |= (settings.u16(0x28) & 0x3fff) << 2
```

Only the low bit of each byte source is used, not a generic nonzero test. Phase
bits27/28 are cleared here; the orchestrator subsequently sets them for its
passes. The packed iteration fields feed `run_pose_solver` directly. The low-two-bit
mode copy also explains why builder dispatch uses a narrower mode than the earlier
full-word zero/nonzero prepass selection. Configuration-domain checks that make
those selections consistent remain upstream.

[512 complete native initializer comparisons](../../native/snow_host/pose_solver_settings_validation.json)
match all context bytes without interception, using arbitrary settings/header
bits, opaque group tokens and finite positive/negative scalars. Settings remain
unchanged. Tests connect layout initialization, settings and solver control, and
verify phase reset, raw copies, low-bit flags and reciprocal values. Zero/nonfinite
scalar inputs, reciprocal overflow, overlapping buffers and live pointer lifetime
are outside the independent API domain. No row storage is reset by this initializer.

### Group membership and solver body indices

The previously recovered body append routine, `0x19573c0`, supplies the body
index consumed by row builders. It stores the current group count at body+0x1c,
then inserts the body into the group's slot array. Body-buffer production at
`0x1994560` traverses that array in order. The reconstructed single-family builder
copies the low 16 bits of body+0x1c into its row header, and the numerical routines
use that index to select the body-data/state records. Writeback traverses the
same group order. This connects membership, row selection and writeback without
requiring a separately guessed index map.

This association is conditional on consistent retained membership. Append
publishes the index before capacity growth, then reloads the insertion count.
A growth service that changes the count can break the association. Removal and
migration repair indices when they move a body into another slot, but that does
not establish atomicity under concurrent changes. See
[body group append](CENTRAL_IMPULSE.md#body-group-append) for the original ordering
and its validation.

`engine.pose_group_body_buffers.build_pose_group_body_buffers` is an authored
adapter over these recovered operations. It checks every active body's token,
group and index against its slot, then calls the existing buffer producer in that
order. It returns ordered body tokens plus index-keyed data/state buffers usable
by `solve_pose_link_rows`. It does not rewrite stale indices or assign ownership.
It rejects body counts above65535 because the retained solver layout truncates
body count to16 bits. This check is an API restriction, not a claim that native
append always enforces that limit for every metadata class.

[128 offline native composition cases](../../native/snow_host/pose_group_body_buffers_validation.json)
run the original append routine and original buffer producer in harness-selected
sequence without interception, with shuffled body addresses and retained
capacity. Membership, active slot order and every produced buffer byte match.
Initialized TLS/static state is supplied. These checks do not run the complete
native orchestrator, allocation, damping or concurrent mutations.

Independent integration tests cover append, swap removal, buffer production and
writeback; stale membership rejection; and a builder→solver→writeback sequence
whose body indices come from append. The latter changes the selected body's
motion while preserving another body's state. Numerical categories beyond the
supported primary/tangent rows, cross-group endpoints, allocation safety and live
ownership remain unresolved. Earlier isolated buffer tests supplied index maps;
this adapter closes that boundary for consistent retained groups only.

### Secondary-pass temporary body update

`engine.pose_body_secondary_update.apply_pose_secondary_body_state` reconstructs
`0x19906b0` through its return at0x1990826. After the optional secondary solve,
this helper uses the state region selected by context+0x174 and processes bodies
in the supplied group-array order. It performs a temporary assignment around a
virtual call, rather than retaining the secondary motion as ordinary writeback:

```python
count = entry_body_count
for i in range(count):
    body = reload_body_slot(i)
    previous_motion = raw_bytes(body, 0x1a0, 24)
    body.xyz_at_1a0 = raw_xyz(state[i], 0)
    body.xyz_at_1ac = raw_xyz(state[i], 16)
    body.virtual_slot_10(1.0)
    raw_bytes(body, 0x1a0, 24) = previous_motion
```

The constant argument is exactly float32 `1.0`, loaded from RVA0x1df3150.
Neither fourth state lane is copied. All six previous motion components are
restored as raw bytes, including changes the method itself made to those fields.
Other method effects survive. The method target is read from the current body's
vtable before installing the temporary values; the body identity remains captured
across the call. The array length is captured once, while later body slots and
state records are reloaded. Repeated body identities are processed independently.
The API supplies the selected virtual method through `update_body`; its normal
return is required. It adds no exception-safe rollback.

The caller at0x1993ed0 first performs ordinary solver feedback, then, if the
secondary iteration field is nonzero, switches phase bits, zeroes the body-state
region, builds secondary link rows and solves again. It rechecks the iteration
field before invoking this temporary-update helper. The group poststep follows.
This ordering suggests a separate correction application, but neither position
correction nor a particular integration equation is established until the body
virtual method is identified. The value1.0 alone does not establish a duration or
an animation parameter.

[512 full native helper comparisons](../../native/snow_host/pose_body_secondary_update_validation.json)
match callback order, raw installed motion, exact scalar argument and all retained
body bytes. The virtual method is a supplied recording/mutating service. Cases
include zero through18 entries, repeated bodies, arbitrary raw float encodings,
method-side motion overwrites and changes to later slots/state. The checks prove
the temporary assignment and restoration around that service, not its native
implementation or a complete secondary solve. No live game session was used.

### Constructor-selected body transform integration

The secondary-pass virtual method is now resolved for a concrete constructor
path. Constructor0x18a8e70 installs table0x29c99a8 at body+0. Its slot+0x10 contains
0x18befb0. The same routine is called directly by group poststep helper0x1957a90.
This is evidence for this constructed class, not proof that every live body uses
that table. Destructor0x18be6b0 also reinstalls the table.

`engine.pose_body_integration.integrate_pose_body` reconstructs0x18befb0 through
0x18bf429. Its inputs are basis XYZ rows at+0x40/+0x50/+0x60, translation+0x70,
local offset+0x128, linear motion+0x1a0, angular motion+0x1ac and a supplied scalar.
It writes only the basis and translation XYZ components. In simplified algebra:

```python
center = position + transform(basis, local_offset)
speed = length(angular_motion)
if speed > float32(2**-23):
    axis = angular_motion / length(angular_motion)
    half_angle = float32(float32(speed * scalar) * 0.5)
    sine, cosine = supplied_scalar_library(half_angle)
    rotation = quaternion_basis(axis * sine, cosine)
    rotated = [transform(rotation, row) for row in basis]
    first = normalize(rotated[0])
    orthogonal = rotated[1] - first * dot(first, rotated[1])
    third = normalize(cross(first, orthogonal))
    basis = [first, cross(third, first), third]
position = center + scalar * linear_motion - transform(basis, local_offset)
```

The implementation preserves the inspected float32 operation order. The axis
normalization denominator and the initial speed use separately evaluated square
sums. The exact threshold does not enter the rotation branch. When the branch is
skipped, the basis is not normalized. Offset subtraction is performed even then,
so it must not be algebraically cancelled against the earlier addition.
The supplied scalar's application is explicit; this alone does not assign units
to every caller's input.

Axis-angle helper0x18c10c0 calls scalar sine0x1c808c0 and cosine0x1c803c0, then the
already reconstructed quaternion helper0x18c1140. Basis composition0x18c16e0 and
orthonormalization0x18bb100 stay native in the comparison harness. General scalar
sine/cosine internals are not yet reconstructed: the public API requires a
`half_angle_trig` service when the rotation branch is reached. Test use of host
sine/cosine supplies comparison values; it is not silently claimed as the native
library implementation.

[512 complete native integration comparisons](../../native/snow_host/pose_body_integration_validation.json)
match every retained body byte and both scalar-library arguments, with only the
sine/cosine responses supplied. Cases include positive/negative scalars,
non-orthonormal input bases, nonzero offsets, zero angular motion and the exact
threshold. Inputs and intermediate arithmetic are finite and nondegenerate;
exceptional numeric behavior remains outside the API contract.

For this body class, composing the secondary wrapper with this method changes
position/orientation while restoring ordinary motion. An independent composition
test verifies translation changes and motion restoration. The full native
secondary wrapper plus this method has not yet been compared as one uninterrupted
execution. Row production, other body classes and whole-group orchestration remain
separate boundaries. The earlier section's unresolved virtual-method effects are
therefore narrowed to class coverage and integration evidence, rather than an
unknown effect for this constructor-selected path.

### Connected secondary application and native integration

The preceding uninterrupted-execution boundary now has a dedicated comparison.
[256 native composition cases](../../native/snow_host/pose_secondary_integration_validation.json)
enter0x19906b0, dispatch through the actual constructor-selected table0x29c99a8,
execute0x18befb0 and its original matrix and scalar-library helpers, and return
without call interception. Observation hooks record sine/cosine arguments and
results; the independent implementation replays those results through its explicit
service. Every retained body byte matches after the sequence, including ordinary
motion restoration and persistent transform changes.

Cases contain zero through six entries, repeated body identities, nonzero local
offsets, and both translation-only and angular updates. Repeated identities
accumulate transform updates while retaining the prior ordinary motion after each
call. This strengthens the composed-method evidence, but does not reconstruct the
scalar library, prove other body-class dispatch, or execute secondary row building
and solving. It is an offline emulation check, not live scheduler validation.

### Runnable body integration inspection

```sh
python3 -m engine.pose_body_integration_bench engine/examples/pose_body_integration.json --output /tmp/body-integration.json
```

The `pose-body-integration-v1` JSON schema requires explicit provenance and one of
two sequences: `body_integration` applies a supplied scalar directly;
`secondary_application` installs a supplied32-byte state, applies the recovered
fixed scalar1.0 and restores ordinary motion. Both operate on a copied complete
retained body byte array, return before/after basis, translation and motion, and
include all output body bytes. No source fixture is modified.

`trig_responses` explicitly supplies each reached half-angle, sine and cosine.
The inspector checks the half-angle's float32 bits and rejects missing, mismatched
or unused responses. It does not evaluate an undeclared host-math substitute.
The included example is authored synthetic, including its host-math-generated
response values. It demonstrates a rotating and translating secondary update
that preserves ordinary motion. The schema, size bounds and input errors are
inspection policy, not recovered native validation.

The inspector uses the constructor-selected integration method directly; it does
not identify a native class from input bytes. Arbitrary game state is not enough
to justify that choice. Row generation, solving, collision handling, native object
lifetime and the scheduler remain outside this entry point.

### Secondary link row refresh

`engine.pose_link_secondary_rows.refresh_pose_secondary_link_rows` reconstructs
secondary dispatcher0x1993e50 and both branches of0x1990c70. This is a refresh of
existing primary rows, not a fresh geometric row build. The dispatcher zeros
context append counters+0xa4/+0xa8, traverses enabled links, and processes enabled
payloads in order. Second-body metadata bit15 selects category0, stride112, or
category1, stride128. The original row result indices and geometric fields must
already be present from the preceding build.

For each payload row, define `N` as its normal and `P1/P2` as its two local points.
The first body always uses its local offset `C1`. Category1 also uses the second
body offset `C2`; category0 uses zero for that second offset. Each relevant center
is translation plus the basis-transformed offset. The native float32 order for
each point is deliberately retained:

```python
center = translation + (Bz*Cz + (By*Cy + Bx*Cx))
local = point - offset
world = ((Bx*local.x + center) + By*local.y) + Bz*local.z
error = dot(-N, world2 - world1) + float32(2 * context.field1c)
response = min(float32(-context.field18 * error), positive_zero)
```

For category0, `center2` is the second translation directly. The dot product uses
XYZ masking followed by two horizontal additions. The clamp preserves the SSE
minimum's second-operand zero at equality. The implementation's supported domain
is finite retained arithmetic; exceptional floating-point behavior is not claimed.
The point expressions must not be replaced with an algebraically simplified
transform, or with the first-pass helper's different addition grouping.

The selected retained row receives the response broadcast at+0x10 and eight zero
bytes at+0x50. The16-byte result selected by its existing uint32 index at+4 is
cleared. Body headers, direction/angular-direction vectors, inverse coefficients,
remaining padding, other result entries and planned traversal counts are left
alone. Payloads are not rewritten. The independent adapter exposes the two
category counters and retained row arrays explicitly; it does not allocate them.

[512 full native dispatcher/refresh comparisons](../../native/snow_host/pose_link_secondary_rows_validation.json)
match all context, row and result bytes with both metadata branches, multiple
links/payloads, disabled gates and zero through four payload rows. Original array
getters execute without interception. Existing headers and row storage are supplied
as test inputs. This establishes the refresh behavior, not their first-pass
production or a whole secondary solve. Category1 numerical solving remains an
explicit unsupported boundary in `solve_pose_link_rows`.

### Paired-body primary numerical solver

`engine.pose_paired_primary_solver` reconstructs preparation0x19e5310 and
iteration0x19e5840. These use both uint16 body indices, the shared direction at
row+0x20, first angular direction+0x30 and second angular direction+0x70. Rows
are128 bytes, with any optional accumulator retained beyond that extent.

Let `d` be the shared direction, `a/b` the two angular directions, `M1/M2` the
body tensor mappings and `m1/m2` the body-data fourth vectors. The weighted
updates are `L1=m1*d`, `L2=m2*(-d)`, `A1=M1*a`, `A2=M2*b`. XYZ dot products are
masked and float32-rounded. Preparation writes the broadcast negative reciprocal:

```python
q = dot(d, d)
k1 = dot(A1, a) + m1.x * q
k2 = dot(A2, b) + m2.x * q
inverse = -float32(1 / float32(float32(k1 + k2) + row60.x))
```

It then applies the cached result independently to both weighted updates.
Iteration computes the combined motion in this exact grouping:

```python
angular = dot(b, state2.angular) + dot(a, state1.angular)
linear = dot(-d, state2.linear) + dot(d, state1.linear)
speed = linear + angular
new_result = max(inverse * (speed + response) + old_result, positive_zero)
delta = new_result - old_result
```

The last two equations operate lane-wise. Each body receives its weighted delta;
row+0x50, when nonzero, identifies a row-relative16-byte accumulator to which the
new result is added. The result record is then replaced. Existing operation order
and float32 rounding are retained in code rather than algebraically simplified.

Native code captures the second body's old motion before updating the first.
When the two indices coincide, the second update therefore overwrites the first,
using the captured state. The implementation preserves that behavior. It does not
silently turn a repeated index into a summed self-constraint. Other buffer aliasing,
nonfinite arithmetic and singular denominators remain outside its contract.

[512 preparations and1536 iterations](../../native/snow_host/pose_paired_primary_solver_validation.json)
match complete native routines without interception, checking all retained rows,
states, results and unchanged data after each stage. Cases include distinct and
coincident indices, nonuniform fourth data vectors and optional accumulators.

`solve_pose_link_rows` now accepts `paired_primary_rows` and planned category1
count from context+0x10c. It prepares and iterates category1 before category0,
then category6 outside the special phase. Other populated categories still reject.
[256 uninterrupted mixed-category wrapper comparisons](../../native/snow_host/pose_mixed_primary_solve_validation.json)
match categories1/0/6 together across all four phase masks and zero through three
iterations, including row, context and result bytes. This supersedes the earlier
category1 numerical-solve boundary. Paired first-pass geometry production, paired
tangent category7, other row categories and whole-group orchestration remain open.

### Paired tangent numerical solver

`engine.pose_paired_tangent_solver` reconstructs preparation0x19eeec0 and
iteration0x19f1e00 for category7, with128-byte rows. Its layout differs from the
paired primary row: the second angular direction is at+0x50, the linked primary
result's uint32 index is at+0x60, and the four-lane limit coefficient is at+0x70.
The direction+0x20, first angular direction+0x30 and inverse+0x40 retain their roles.
Response storage+0x10 is not consumed by these numerical routines.

Using `d`, angular directions `a/b`, tensor mappings `M1/M2`, and body fourth
vectors `m1/m2`, preparation computes the following float32 sequence:

```python
L1 = m1 * d
L2 = m2 * (-d)
A1 = M1 * a
A2 = M2 * b
denominator = ((dot(A1, a) + dot(d, L1)) + dot(m2*d, d)) + dot(A2, b)
inverse = 1 / (-denominator)
```

The inverse is broadcast, and the cached result is applied to both weighted
body updates. The row limit coefficient is not added to the denominator.
Iteration groups projected motion per body before adding the two contributions:

```python
first = dot(a, state1.angular) + dot(d, state1.linear)
second = dot(b, state2.angular) + dot(-d, state2.linear)
speed = first + second
bound = row70 * linked_primary_result
candidate = (-speed) * inverse + old_result
new_result = max(min(candidate, bound), -bound)
delta = old_result - new_result
```

The bound, candidate and clamp are lane-wise. Sequential native minimum/maximum
operand selection is preserved at ties and inverted bounds; this is not a joint
norm constraint. Both bodies receive their weighted delta with opposite linear
directions. The coincident-index second-write-wins behavior is shared with the
paired primary path. No optional accumulator is used here: row+0x50 is the second
angular direction, not a pointer or accumulator index.

[512 preparations and1536 iterations](../../native/snow_host/pose_paired_tangent_solver_validation.json)
match the complete original routines without interception, including coincident
indices, linked-result aliasing, inverted limits and retained row padding. Inputs
are finite and nonsingular. The original body data and rows are supplied.

The connected solver now accepts `paired_tangent_rows` from planned count+0x124
and traverses categories1,0,7,6 in that order. Special phase0x10000000 skips both
tangent categories. [256 uninterrupted four-category comparisons](../../native/snow_host/pose_four_category_solve_validation.json)
match native context, rows, states and results across all four phase masks and
zero through three iterations. This closes the category7 numerical boundary;
paired first-pass builders, multirow builder families, remaining numerical
categories and complete group orchestration are still unresolved.

### Group-step orchestration and phase transitions

`engine.pose_group_step.run_pose_group_step` reconstructs the complete control
flow at0x1993ed0. It requires explicit downstream services rather than supplying
no-op defaults or substituting an incomplete numerical model. Its native-shaped
arguments use opaque storage tokens; the adapter does not dereference live memory.
The context is a retained byte array, and `groups` supplies retained raw headers.

```text
capture group from context+0x30
build body data/state using captured offsets and bounded initial body count
build link rows
clear phase bit28; set phase bit27
build pose rows
solve
write link feedback
write body feedback
write pose feedback
if current secondary-iteration field is nonzero:
    clear phase bit27; set phase bit28
    zero body-state storage in32-byte blocks
    refresh secondary link rows
    solve
if current secondary-iteration field is nonzero:
    temporarily apply secondary body state
poststep(captured_group, current_scalar10, current_flag30,
         current_field24, current_field28, current_field2c)
```

The group identity is captured before any downstream call, even if a service
later changes context+0x30. Its body/link/pose array pointer and count fields are
reloaded before each subsequent span-taking service. The first body producer
receives the smaller of the group count and
`uint32(state_offset - data_offset) >> 6`, using a signed comparison for the group
count. That initial bound does not constrain the later body-feedback span, which
uses the then-current full group count.

The first secondary gate follows pose feedback. It is re-evaluated separately
before temporary state application; changes during row refresh or the second
solve can suppress application. The second solve is unconditional once the first
gate has admitted the refresh sequence. Scalar10 and poststep fields are read
at the final call, rather than captured at entry. Phase writes preserve unrelated
flags. Zero-fill uses successive32-byte blocks while the block start is below the
result offset; the API requires backing storage for every reached block.

The supplied services are `build_body_buffers`, `build_link_rows`,
`build_pose_rows`, `solve`, `link_feedback`, `body_feedback`, `pose_feedback`,
`refresh_secondary_rows`, `apply_secondary_state` and `poststep`. Their argument
order follows the inspected calls. The initial producer receives data/state tokens,
body-array token, selected count, scalar pointer token and vector pointer token.
Span services receive the context token and begin/end tokens. The solver receives
only the context token. The poststep signature is shown above.

[384 complete native orchestration comparisons](../../native/snow_host/pose_group_step_validation.json)
match call order, every argument, the entire context at every service boundary,
and final context/group bytes. Downstream routines are supplied recording/mutating
services in this validation;192 cases change fields between stages to distinguish
captured state from reloaded state. This does not establish a fully connected
native group simulation. The independently validated row solvers, body production,
feedback, secondary refresh and integration can now be bound to this explicit
ordering. Pose builders/feedback, poststep details, remaining link families and
numerical categories still prevent a complete all-input group implementation.

### Body low-motion timer and threshold overrides

`engine.pose_body_quiet_state.update_pose_body_quiet_state` reconstructs complete
routine0x18c0190, called by the group poststep's conditional checker0x1958460.
Body+0x1c0 optionally points to three overrides in linear/angular/duration order.
Each exact float32-1.0 independently selects the corresponding caller default.
The inspected sentinel at0x1e023c8 is-1.0. For the supported finite domain:

```python
linear_limit, angular_limit, duration_limit = resolved_overrides_or_defaults
if body.flagsaa & 2 or squared_length(linear_motion) >= linear_limit**2 \
                      or squared_length(angular_motion) >= angular_limit**2:
    body.timer28 = positive_zero
    metadata.byte53 &= 0xf0
else:
    body.timer28 = float32(supplied_scalar + body.timer28)
    if body.timer28 > duration_limit:
        metadata.byte53 = (metadata.byte53 & 0xf1) | 1
```

Squares and sums retain float32 rounding and `(x²+y²)+z²` order. Both motion
comparisons reject equality; the duration comparison requires strict greater-than.
When motion remains below threshold but duration does not cross, the old metadata
nibble is left untouched. Negative thresholds other than the sentinel are squared
normally. A negative scalar decreases the timer; the routine does not clamp it.
These are native arithmetic facts, not recommended parameter validation policy.
No physical time unit is assigned solely from this accumulation.

[512 cases with2048 sequential native updates](../../native/snow_host/pose_body_quiet_state_validation.json)
match all retained body and metadata bytes without interception. Cases include
missing/partial overrides, negative overrides, motion-threshold equality,
inhibition, repeated accumulation and positive/negative scalars. Nonfinite or
overflow arithmetic remains outside the independent API domain.

The caller0x1958460 evaluates this routine for each captured body span, then checks
whether every reached body's metadata low nibble equals1. If so, it reloads the
group body span, invokes virtual slot+0x20 on each body and sets group+0xa0 to1.
An empty captured body span also admits that branch. Poststep0x19574f0 subsequently
skips ordinary integration/resource refresh when group+0xa0 is nonzero. This is a
lead toward group inactivity behavior, not yet a full live sleep/wake contract.
The group aggregation, concrete slot+0x20 effects and reactivation path remain
separate reconstruction work.

### Group quiet aggregation and poststep integration gate

`engine.pose_group_poststep` reconstructs group checker0x1958460, poststep0x19574f0
and constructor-selected inactive method0x18bebd0. Constructor table0x29c99a8
places the latter at virtual slot+0x20, the slot called by the group checker.

The checker captures the body-array identity and count, runs the recovered
low-motion timer on every body, and requires each resulting metadata low nibble
to equal1. A failed aggregate does not short-circuit later timer updates. If all
qualify, it reloads the body span, invokes slot+0x20 for each body, then writes
1 to group+0xa0. An empty captured span passes. A failed aggregate leaves the
existing group flag unchanged; it does not supply a reactivation path.

For this constructed body class, the virtual action is:

```python
metadata.byte53 = (metadata.byte53 & 0xf2) | 2
body.linear_motion = raw_positive_zero_xyz
body.angular_motion = raw_positive_zero_xyz
first = body.link_head80
if first:
    current = first
    while True:
        clear_link_payloads(current)
        # Endpoint and successor are re-read after clearing.
        current = current.next20 if current.first_body == body else current.next30
        if current == first:
            break
```

Getter0x12f2f20 reads body+0x80 directly. The clearing call is0x1958b90, whose
payload-array behavior is documented in the earlier link-clearing research.
Protected pool release remains an explicit service. The independent transition
accepts retained link headers and `clear_link`; malformed-ring detection is an
authored error after reached mutations, not native rollback. A valid circular
ring is required. Timer28 and other body fields are preserved by this action.

Poststep optionally runs the group checker, then reads group+0xa0. If nonzero it
returns. Otherwise it integrates every body in a captured span through0x18befb0,
then reloads the group span and calls resource refresh0x18bcee0 on every body.
Within each traversal the array identity/count remain captured; slot values are
read as each iteration is reached. `poststep_pose_group` exposes the integration,
resource refresh and per-class inactive action as required services rather than
assuming native class identity or inventing resource behavior.

[384 complete native composition comparisons](../../native/snow_host/pose_group_poststep_validation.json)
run poststep, aggregation, the original timer, the actual class-selected inactive
method and the original link-head getter. Payload clearing, integration and
resource refresh are supplied recording/mutating services. Call order/arguments
and every retained group/body/metadata/link byte match. Native fixtures cover zero
through five bodies, mixed eligibility, pre-existing group flags and one-link
circular lists. Independent tests additionally cover multiple-link traversal,
endpoint mutation after clearing and array replacement between integration and
resource refresh. These service-mutation tests are not live concurrency evidence.

This closes the previously open aggregation/action boundary for the inspected
class. Full resource refresh, protected payload release, other virtual classes,
reactivation and live synchronization remain unresolved. The observed behavior is
consistent with a group inactivity transition, but no complete sleep/wake lifecycle
or thread-safe mod API is claimed.

### Body reset and ordinary-group reactivation

The previously supplied `virtual40` callback in `finalize_pose_group` means byte
slot40 decimal, or0x28. Constructor table0x29c99a8 resolves it to0x18be770.
`engine.pose_body_quiet_state.reset_pose_body_quiet_state` reconstructs its entire
body: clear metadata+0x53's low nibble and write positive zero to body timer+0x28.
Motion, transform and the metadata high nibble are preserved.

The existing ordinary-group finalizer0x18e11b0 now has a concrete class-specific
reset implementation. It first queues links whose first endpoint has metadata
state2, before resetting those bodies. Its helper0x1957340 invokes slot+0x28 for
every body and clears group+0xa0. The finalizer then removes the group from the
context+0x428 collection with swap/index repair, appends it to context+0x418,
and appends its bodies to the tracked-body array. The routine skips groups whose
flag is already zero and the two special context group identities.

[320 uninterrupted native reactivation-path comparisons](../../native/snow_host/pose_group_reactivation_validation.json)
execute the original finalizer, original body-loop helper, actual constructor
vtable reset and tracked-body append. Observation hooks record calls without
replacing them. All body/metadata bytes, context/group headers and array contents
match. Retained capacity suffices in every case, so growth allocation is not
validated. This supersedes the earlier finalizer receipt's supplied body-virtual
boundary for this class only.

An independent composition test verifies state2 link queuing before reset,
metadata/timer reset, group collection transfer and subsequent admission to
poststep integration/resource refresh. That later poststep is not included in
the uninterrupted native receipt. The observed reset and group transfer provide
a concrete reactivation path; identifying all automatic triggers, other body
classes and safe cross-thread entry points remains separate work. Clearing only
a metadata nibble is not equivalent to this full group operation.

### Body resource bounds refresh

`engine.pose_body_bounds.refresh_pose_body_bounds` reconstructs poststep's refresh
routine0x18bcee0. It captures the body's uint16 resource count, traverses72-byte
entries, skips null resources and composes each local transform with the current
body transform. Each resource's virtual slot+0x10 supplies six bounds floats.
The routine unions those bounds and writes metadata minima XYZ at+4 and maxima
XYZ at+0x10. With zero entries, both endpoints equal body translation. A nonempty
all-null span is outside the valid native domain: its search can read one past
the span and then attempt a resource call. The independent API rejects it with
an authored guard instead of inventing a fallback.

For parent basis P, local basis L, and translations p/l, transform helpers
0x18b2880 and0x18c16e0 implement the following. Every multiplication and addition
rounds to float32; no fused operation is substituted.

```text
basis[i][j] = ((L[i].x * P[0][j]) + (L[i].y * P[1][j]))
              + (L[i].z * P[2][j])
translation[j] = (((l.x * P[0][j]) + (l.y * P[1][j]))
                  + (l.z * P[2][j])) + p[j]
for each later resource bounds:
    min[j] = new_min[j] if float32(new_min[j] - min[j]) < 0 else min[j]
    max[j] = new_max[j] if float32(new_max[j] - max[j]) >= 0 else max[j]
```

Equal minima retain the prior bits; equal maxima retain the new bits, including
signed zero. Transform fourth lanes are unwritten scratch bytes, so the API
exposes only the twelve meaningful floats. This is not a homogeneous4x4 matrix.
The entry-array pointer is reloaded between resources, and final metadata is
resolved after callbacks. Captured count persists even if a callback changes it.
The public identity maps model these sequential mutations, not concurrent access.

[512 offline native comparisons](../../native/snow_host/pose_body_bounds_validation.json)
execute the original refresh and both transform helpers with only the resource
bounds callback supplied. They compare all twelve transform float bit patterns,
callback identities, all body bytes, both metadata buffers and both entry arrays.
Cases cover empty spans, null slots, signed-zero ties and callback replacement of
arrays, metadata, body translation and count. A separate composition test feeds
body integration into resource refresh with a clearly supplied point-bounds
service. No particular resource geometry, broadphase registration or live thread
safety is established. Resource-specific bounds implementations remain the next
consumer boundary to decode.

### Kind-7 grid resource bounds

Constructor0x18c1d50 writes kind7 to word+0x28 and installs table0x29ca138.
Slot+0x10 is0x18c2390, the exact virtual slot used by body refresh.
`engine.pose_grid_resource_bounds.grid_resource_bounds` implements that complete
method, closing the supplied bounds boundary for this constructor-selected class.

With stored `low = resource[0x7c:0x88]`, `high = resource[0x88:0x94]`:

```text
half_extent[i] = float32(float32(high[i] - low[i]) * 0.5)
height_center = float32(float32(resource.f98 + resource.f94) * 0.5)
world_radius[j] = abs(basis[0][j]) * half_extent.x
                + abs(basis[1][j]) * half_extent.y
                + abs(basis[2][j]) * half_extent.z
world_center[j] = ((basis[0][j] + basis[1][j]) * 0
                  + height_center * basis[2][j]) + translation[j]
minimum[j] = world_center[j] - world_radius[j]
maximum[j] = world_radius[j] + world_center[j]
```

Each operation rounds to float32, with radius sums evaluated left-to-right.
Absolute value clears the sign bit. The zero product is retained because it can
affect signed-zero results. This is not generic midpoint-based AABB transformation:
XY center is zero, and stored Z extent and the separate height-center pair remain
distinct inputs. Their initializer assumptions are still to be traced. The method
does not normalize or check the frame's orthogonality.

[512 uninterrupted native comparisons](../../native/snow_host/pose_grid_resource_bounds_validation.json)
run the original body refresh, transform helpers and actual kind-7 vtable method.
No callback is replaced. All body, metadata and entry-array bytes match for zero
to three resources, null slots, arbitrary finite transforms and independent
extent/height-center values. Synthetic tests cover asymmetric XY endpoints,
rotation/scale and public body-refresh dispatch. Constructor/table association is
static evidence; these runs initialize synthetic objects with that table, without
loading original terrain assets.

Adjacent routine0x18c25d0 is a concrete grid lead. It reads float samples from
resource+0x48 at `row * u16(resource+0x68) + column`, then writes four XYZ vertices
for neighboring positions. X/Y use spacings at0x70/0x74 and offsets at0x7c/0x80;
Z comes directly from each sample. Later topology/flag handling remains to be
reconstructed. This supports the grid-backed description, but does not establish
terrain archive decoding, selected map resources, triangle contact generation or
broadphase insertion. Other resource kinds still need their bounds methods.

### Grid cell vertices and triangle identities

`engine.pose_grid_cell` reconstructs complete methods0x18c25d0 and0x18c2760.
The former reads four float grid samples and emits four local XYZ vertices plus
six triangle-local indices. With column c, row r and sample stride S at0x68:

```text
corners = [(c,r), (c+1,r), (c+1,r+1), (c,r+1)]
vertex(x,y) = [float32(float32(float32(x)*spacing_x)+offset_x),
               float32(float32(float32(y)*spacing_y)+offset_y),
               samples[y*S+x]]
indices = [0,1,2, 2,3,0] if byte58 == 0 else [0,1,3, 1,2,3]
```

Spacing is stored at0x70/0x74, XY offsets at0x7c/0x80, and the float-sample
pointer at0x48. Z samples are used directly without scaling or offset in this
method. Byte58 selects a diagonal, with every nonzero byte taking the same branch.
No checkerboard/parity-dependent diagonal is selected here.

The second method decodes a uint32 triangle identity:

```text
cell_id = triangle_id >> 1
row, column = divmod(cell_id, u16(resource+0x9c))
corner_samples = [row*S+column, row*S+column+1,
                  (row+1)*S+column+1, (row+1)*S+column]
half = triangle_id & 1
result = corner_samples[indices[3*half : 3*half+3]]
```

Result indices use native uint32 wrapping. The divisor at0x9c is distinct from
sample-row stride0x68; the implementation does not assume their relationship.
The public cell API rejects missing samples and out-of-row columns as authored
storage guards; the triangle-index API rejects a zero divisor. Those rejections
are not recovered native validation behavior.

[Offline native comparison](../../native/snow_host/pose_grid_cell_validation.json)
passes512 cell evaluations and1536 triangle-identity evaluations without call
replacement. It compares every vertex float bit, local index, global sample
index and unchanged resource byte, using both diagonal branches, negative spacing
and arbitrary uint32 triangle identities. Synthetic tests cross-check that cell
triangles and triangle IDs select the same samples, including the last valid cell.

Static callers of the cell method include0x18c3720 and the split routine around
0x18c3ee9; a caller of the index method is0x1996e98. Their full query/contact
contracts remain unresolved. These methods supply geometry from an already
available float grid, not archive decoding, selected map loading, collision
broadphase or a complete terrain contact generator.

### Grid triangle vertex consumer boundary

The split caller segment at0x1996e98 first invokes0x18c2c70 to obtain three
triangle vertices. It subtracts edges, forms cross-product terms and computes a
reciprocal squared magnitude, then invokes the previously recovered sample-index
method0x18c2760. Its later per-record contact calculations are not yet reconstructed.
This establishes a consumer connection for the geometry endpoints, not completion
of the caller's collision contract.

`grid_triangle_vertices` in `engine.pose_grid_cell` implements0x18c2c70's output
using the already recovered cell coordinates, diagonal and triangle-half rules.
The native method computes the vertices independently rather than calling the
cell helper. Each output is a16-byte XYZ0 vector. The original code masks its
scratch fourth lane with the initialized XYZ mask at0x3336890; the independent
API returns positive zero explicitly. This differs from the unspecified fourth
lanes of the resource transform helper.

[512 cases /1024 complete native vertex calls](../../native/snow_host/pose_grid_triangle_vertices_validation.json)
validate both halves and both diagonal branches, including negative spacing and
poisoned scratch/output storage. All twelve output words match bitwise and
resource bytes remain unchanged. The validator explicitly supplies the XYZ mask
as `[ffffffff,ffffffff,ffffffff,00000000]`; it does not execute its initialization
producer. No native call is intercepted. The Python reuse of cell geometry is a
validated equivalent composition within the finite, complete-cell domain, not a
claim about original function boundaries. Asset sampling, invalid native reads,
mask initialization and the remaining caller contact calculation stay separate.

### Grid vertex neighborhood and contact-filter lead

`grid_vertex_neighbors` reconstructs helper0x19959e0. Its incoming context in RCX
is unused. Resource width/height are uint16 fields0x68/0x6a; a sample identity is
split into row/column using sample width, not the triangle-cell divisor0x9c.
It emits up to six XYZ vertices, clipping individual neighbors at grid boundaries
without sorting or changing order. Offsets relative to the selected column/row:

```text
byte58 == 0: [(0,+1),(+1,+1),(+1,0),(0,-1),(-1,-1),(-1,0)]
byte58 != 0: [(0,+1),(+1,0),(+1,-1),(0,-1),(-1,0),(-1,+1)]
```

Each valid neighbor uses the same float32 spacing/offset and direct height-sample
formula as the cell method. It does not include the selected vertex itself.
The public API requires nonempty dimensions, a valid selected sample and complete
storage as authored guards. Native invalid dimensions/identities are not modeled.

[5184 uninterrupted native comparisons](../../native/snow_host/pose_grid_neighbors_validation.json)
cover every vertex of every width/height combination1..8, repeated with both
zero/nonzero diagonal modes. Counts, ordered vertex bits, untouched output tail
and resource storage match. This includes isolated points, one-dimensional grids,
corners, edges and full six-neighbor interiors.

Further inspection identifies the caller's full entry at0x1996e50. It receives
resource, transform, triangle ID, a mutable record array and count. Its loop uses
48-byte records. A rejection decrements count, copies the last record into the
current slot and retries that slot; accepted records advance the cursor. This
is a filtering stage for existing records, not generation of new records.
The method returns the remaining count and has a zero-count early exit.

Static branch evidence: triangle-relative weights select a vertex neighborhood
or an edge check. Vertex branches call0x19959e0, normalize neighbor-minus-vertex
directions and compare dot products with the transformed record direction against
a threshold. Edge branches call0x1995800, which in turn requests neighboring
geometry through0x1996500. Exact weight thresholds, degenerate behavior, record
semantics and the edge service still require reconstruction and native validation.
No complete contact-filter implementation is claimed by the neighborhood receipt.

### Grid edge neighborhood

`write_grid_edge_neighbors` reconstructs0x1996500, the geometry dependency used
by edge rejection helper0x1995800. Its first context argument is unused. It sorts
the two sample identities numerically, decodes the lower identity into column c
and row r using width0x68, and branches on their difference d. Height is0x6a.
The two selected offsets relative to c/r are:

| Diagonal flag | Difference, checked in this order | Neighbor offsets |
| --- | --- | --- |
| zero | 1 | (0,-1), (+1,+1) |
| zero | width | (+1,+1), (-1,0) |
| zero | width+1 | (+1,0), (0,+1) |
| nonzero | 1 | (+1,-1), (0,+1) |
| nonzero | width | (+1,0), (-1,+1) |
| nonzero | width-1 | (0,+1), (-1,0) |

Each out-of-grid neighbor becomes the lower endpoint's XYZ position. Every valid
neighbor uses the established spacing/offset/direct-height formula. For an
unrecognized difference, no position is written. Finally, if the original first
identity was larger, the two retained XYZ outputs are swapped, even when no
branch wrote them. The API therefore accepts mutable retained output rather than
inventing an empty-result return. Tail bytes are preserved. Branch priority is
significant for width1 and width2, where difference categories can coincide.

[6050 complete native comparisons](../../native/snow_host/pose_grid_edge_neighbors_validation.json)
cover all ordered endpoint pairs for every width/height combination1..5 and both
diagonal modes, including equal endpoints, unsupported differences, narrow grids,
boundary fallback and reversed order. Every output byte and unchanged resource
byte matches. The public API requires valid endpoints and complete nonempty sample
storage as authored guards. The native routine tests numeric differences, not
full geometric adjacency, so matching a branch alone does not establish a valid
mesh edge. The calling edge-rejection mathematics remains a separate boundary.

### Grid edge rejection predicate

`engine.pose_grid_edge_filter.reject_grid_edge` reconstructs0x1995800 with the
actual grid edge-neighbor helper0x1996500. Let A/B be the supplied endpoint XYZ
vectors, D the supplied record direction, N0/N1 the ordered neighbor positions,
and T the four-lane threshold. The initialized XYZ mask clears fourth lanes.

```text
E = normalize(A - B)
U = N0 - B
V = N1 - A
for X in [U,V]:
    if not all(abs(X.xyz0[lane]) <= T[lane] for lane in 0..3):
        X = normalize(X)
first = dot(cross(cross(E,U),E), D)
if all(first > T[lane] for lane in 0..2): return true
second = dot(cross(E,cross(V,E)), D)
return all(second > T[lane] for lane in 0..2)
```

All multiplies, additions/subtractions, reciprocal and square root round to
float32. Dot reduction follows SIMD horizontal addition `(x+y)+(z+0)`.
Cross products preserve the inspected operand order. The expressions can be
interpreted as testing components perpendicular to the edge, but the implementation
does not replace them with a differently rounded projection formula. Near-zero
neighbor vectors are left unchanged, not forced to zero. Equality passes the
near-zero gate but does not reject at the final strict threshold comparison.
The caller's inspected constant at0x1e252b0 is a four-lane float32 value near1e-5;
the API keeps thresholds explicit so the local helper contract stays inspectable.

[1024 complete native comparisons](../../native/snow_host/pose_grid_edge_filter_validation.json)
execute the predicate and neighbor helper without interception. Boolean outcomes
match:587 rejected,437 retained. Cases include both diagonal modes, both triangle
halves, all three edge positions, boundary fallback, reversed endpoints and
nonuniform thresholds. The XYZ mask is initialized explicitly in the emulator.
This receipt validates decisions, not every intermediate floating-point value.

The API requires finite inputs, a nondegenerate edge and a recognized numeric
index difference. Unsupported differences in the native helper leave scratch
positions unchanged, so the predicate must not silently invent them. Zero-length
normalizations and unordered/nonfinite IEEE behavior remain outside this validated
domain. The full record filter's vertex branches, selection gates and swap-removal
composition still need implementation and native comparison.

### Complete grid record filter

`engine.pose_grid_contact_filter.filter_grid_records` reconstructs0x1996e50,
composing triangle vertices, sample identities, vertex neighborhoods and edge
rejection. It mutates retained48-byte records and returns the remaining count.
XYZ direction is at record+0; XYZ position at+16. Other bytes are copied opaquely.
No records are generated. Zero count returns before geometry is consulted.

For triangle vertices A/B/C, form `N=cross(B-A,C-A)` and `inv=1/dot(N,N)`.
Transform each record position P with the supplied frame, in float32 order
`((basis0*x + translation) + basis1*y) + basis2*z`. Transform its direction D as
`(basis1*y + basis0*x) + basis2*z`, without translation. Then:

```text
WA = dot(cross(B-P,C-P),N) * inv
WB = dot(cross(C-P,A-P),N) * inv
WC = dot(cross(A-P,B-P),N) * inv
if WA > upper: test vertex A
else if WB > upper: test vertex B
else if WC > upper: test vertex C
else if WC < lower: test edge A,B
else if WA < lower: test edge B,C
else if WB < lower: test edge C,A
else: retain
```

Upper is float32(.9999), lower float32(.0001). A vertex rejects if any ordered
neighbor satisfies `dot(normalize(neighbor-vertex),D) > float32(.00001)`.
An edge uses the recovered predicate with all four threshold lanes equal to
float32(.00001). Comparisons are strict and branch order is retained. A rejection
copies the last active48-byte record into the current slot, decrements count and
retries that slot. Retention advances the cursor. Removed/tail storage is not
cleared and the operation does not preserve original record order.

[512 uninterrupted native comparisons](../../native/snow_host/pose_grid_contact_filter_validation.json)
execute the full original filter with its actual geometry and rejection methods,
without intercepted calls. They process3052 input records, retaining685. Returned
counts and all record bytes, including removed and tail storage, match. Coverage
includes both diagonal modes, all triangles in a5x5 grid, vertex/edge/centroid
positions, displaced positions, zero-to-twelve records and translated frames.
The XYZ mask is supplied as initialized state. Arbitrary rotation/scale and
degenerate IEEE cases are not covered by this receipt. The public API rejects
zero-length triangle/neighbor normalization rather than claiming native NaN
behavior. Upstream record production, live ownership and broadphase integration
remain outside this reconstructed filter.

### Grid filter transformed-frame validation and caller gates

[1024 further uninterrupted native comparisons](../../native/snow_host/pose_grid_contact_filter_transforms_validation.json)
exercise the complete filter with Z-axis rotations, translations, nonuniform
signed axis scales and reflections. They process6129 records, retaining1308;
returned counts and every retained-buffer byte match. Positions are generated
near vertices, edges and centroids and mapped back into the supplied frame,
with additional displaced cases. This extends the earlier identity/translation
receipt without replacing it. It is sampled transform coverage, not an exhaustive
affine or degenerate-input proof. A synthetic test independently checks matching
selected record identities under an exactly representable quarter-turn, scaling,
reflection and translation.

Six static call sites lead back to routines beginning0x19dde20,0x19de7c0,
0x19e0430,0x19e0e20,0x19e2600 and0x19e3460. In the inspected first caller,
0x19de6d9..0x19de70d gates the filter on both a separate object's byte+0x92 being
nonzero and the resource at R14 having dword+0x40 equal to2. It passes the current
triangle identity in EBX, a local transform, the new record span and its count.
The returned filtered count is added to the outer accumulated count. This is
conditional filtering, not evidence that every generated contact uses this path.
The identity/meaning of the separate gate object remains unresolved.

Immediately preceding this call, an inspected branch swaps each new record's
XYZ fields+0x10 and+0x20, negates direction XYZ at+0 by sign-bit XOR, and writes
the triangle identity at+0x2c. This explains why the downstream filter must retain
opaque record bytes and why naming+0x10 a universal world-space point would be
premature. The branch condition, upstream record-generation call, remaining five
callers and complete outer traversal remain to be reconstructed and validated.
These caller observations are static evidence, not covered by the filter receipt.

### Grid triangle candidate enumeration

`engine.pose_grid_candidates.write_grid_triangle_candidates` reconstructs
0x18c4cc0. It intersects a supplied six-float query box with stored resource
bounds0x7c..0x90 using float32 subtract-and-compare selection. Disjoint Z returns
zero, with equality accepted. XY values are converted to cell ranges:

```text
start_x = max(trunc(float32((clipped_min_x-origin_x) * float32(1/spacing_x))),0)
end_x = min(trunc(float32((clipped_max_x-origin_x) * float32(1/spacing_x))),cell_width-1)
# Same for Y; each subtraction also rounds to float32.
for row in inclusive(start_y,end_y):
    for column in inclusive(start_x,end_x):
        emit uint32(2*(row*cell_width+column))
        if capacity reached: return written
        emit uint32(2*(row*cell_width+column)+1)
        if capacity reached: return written
```

Cell dimensions come from0x9c/0x9e, spacings0x70/0x74 and origins0x7c/0x80.
The routine does not read height samples or test each triangle. Output ordering
is rows, columns, then the two halves. Odd capacity can stop after the first half.
The public API guards nonpositive capacity: native code writes before checking
capacity, so a zero-capacity empty-output policy would invent behavior. Positive
spacings, nonempty cell dimensions and finite int32-convertible coordinates are
also explicit supported-domain requirements.

[1024 uninterrupted native comparisons](../../native/snow_host/pose_grid_candidates_validation.json)
match count and all output bytes, including untouched tails, with fractional
spacings, dimensions1..9, capacities1..39 and overlapping/disjoint/inverted query
boxes. Synthetic tests cover height separation, exact-boundary inclusion and
capacity truncation between triangle halves.

The first upstream caller0x19dde20 invokes this enumerator, selects the triangle's
profile using map+0xb0 indexed by `triangle_id>>1` and table+0xa0, or default+0x20
when no map exists. It admits a candidate when
`(triangle_profile.mask50 & other_profile.mask48) |
 (other_profile.mask50 & triangle_profile.mask48)` is nonzero. These are inspected
static mask relationships, not yet a validated outer pipeline.

The actual record producer is0x190f8b0. The caller supplies transformed triangle
vertices, remaining record capacity, flags from the separate object's bytes0x90
and0x91, and a receiver from that object's+0x88. The optional filtering flag+0x92
is adjacent but its higher-level owner remains unknown. The producer begins by
reading receiver floats+0x40/+0x44/+0x48 and building signed corner combinations;
this is a box-like geometry lead, not yet a proved resource type or reconstructed
contact generator. The caller's transform setup, allocation fallback and complete
production/filtering traversal still need validation.

### Contact producer axis selection

`engine.pose_contact_axis_selection.select_contact_axis` reconstructs0x190f700,
called by the record producer0x190f8b0. Face-query0x19243e0 and edge-query0x1923dd0
remain explicit services. The first face query receives frame/shape pairs in input
order; the second reverses the pairs. Each returns distance and feature index.

```text
F0,I0 = face_query(frame0,shape0,frame1,shape1)
if F0 > 0: return {kind:3, first:I0, second:UINT_MAX, distance:F0}
F1,I1 = face_query(frame1,shape1,frame0,shape0)
if F1 > 0: return {kind:3, first:UINT_MAX, second:I1, distance:F1}
bias(x) = float32(float32(x * float32(.98)) + float32(.01))
if edge_enabled:
    edge = {distance:-FLT_MAX, first:UINT_MAX, second:UINT_MAX}
    edge_query(frame0,shape0,frame1,shape1,edge)
    if edge.distance > bias(F0) and edge.distance > bias(F1):
        return {kind:2, **edge}
if F0 > bias(F1): return {kind:0, first:I0, second:UINT_MAX, distance:F0}
return {kind:1, first:UINT_MAX, second:I1, distance:F1}
```

The comparisons are strict; equality favors the later face choice rather than
edge selection. Constants are observed float32 values0.9800000190734863 and
0.009999999776482582, not exact real-number arithmetic. An edge service receives
initialized seed fields and can leave them unchanged. No contact distance units
or query geometry are inferred from this selector alone.

[1024 offline native selector comparisons](../../native/snow_host/pose_contact_axis_selection_validation.json)
match query call order, reversed argument identities, edge seed bytes and all16
result bytes. All four kinds occur. Only the face/edge query responses are supplied;
this is not uninterrupted original geometry-query validation.

The producer dispatches kind2 to0x18e3aa0; kinds0/1 to0x18e4060 with reversed
shape/frame ordering and different orientation flags. Kind3 takes the zero-record
return path. Before selection, it constructs eight signed corner combinations
from receiver+0x40/+0x44/+0x48 and six plane descriptors, plus a two-sided triangle
descriptor. These observations strengthen the box-versus-triangle interpretation,
but complete descriptor construction, TLS initialization, geometry queries and
record emission still need reconstruction. The new module implements the proven
selection policy without substituting guessed query results.

### Contact face-distance query

`engine.pose_contact_face_query.query_contact_faces` reconstructs0x19243e0.
First-shape planes use20-byte stride at descriptor+8 and uint16 count+0x22.
Second-shape vertices use12-byte stride at descriptor+0 and uint16 count+0x20.
The public API exposes planes `[nx,ny,nz,d]` and vertices XYZ; unused descriptor
fields remain outside the local query contract.

For each plane in order, transform its normal as
`N=(basis1*ny + basis0*nx)+basis2*nz` and its scalar as
`D=dot(translation,N)+d`. Project `-N` onto each second-frame basis row to obtain
a local support direction. Scan second-shape vertices for the greatest dot with
that direction, using a strict comparison and therefore retaining the first tie.
Transform that selected vertex V with the second frame in order
`((basis0*V.x + translation)+basis1*V.y)+basis2*V.z`. Its separation is
`dot(transformed_V,N)-D`.

The first strictly positive separation returns immediately with its plane index.
Otherwise, retain the greatest separation using a strict comparison; equal planes
keep the first selected index. Empty plane lists return negative FLT_MAX and
UINT_MAX. Nonempty planes with empty support vertices cause invalid native access;
the independent API rejects that input as an authored guard. Every arithmetic
operation uses float32, with dot reduction `(x+y)+(z+0)`. Normals are not normalized
and no inverse-transpose substitution is made for nonrigid frames.

[1024 complete native queries](../../native/snow_host/pose_contact_face_query_validation.json)
match distance bits and plane indices without interception. Coverage includes
zero-to-eight planes, one-to-twelve vertices, general finite basis/translation
fields, duplicate planes and duplicate vertices. XYZ-mask initialization remains
supplied state. Synthetic tests confirm first-positive early exit, plane tie
precedence and composition into the axis selector with the real face query.
This closes the selector's supplied-face boundary locally; the edge query,
producer descriptor setup and contact emitters remain unresolved.

### Contact edge-distance query

`engine.pose_contact_edge_query.query_contact_edges` reconstructs0x1923dd0.
Each shape supplies vertices, planes and8-byte edges containing four uint16
indices: vertex0, vertex1, plane0, plane1. Descriptor+0x10 points to edges and
uint16+0x24 gives their count. The native query resets its output to negative
FLT_MAX/UINT_MAX/UINT_MAX, regardless of incoming seed.

It transposes the second frame basis and forms a relative first frame in that
coordinate system. Translation uses the dot of negated second translation with
each second basis row, followed by the transformed first translation. This is
not a general inverse for arbitrary scaled/sheared matrices. First-shape edge
endpoints and adjacent normals are transformed into that relative frame; second
shape data remain local. Every operation preserves float32 rounding/order.

For transformed first adjacent normals A/B, second normals C/D, and normalized
second edge direction E = normalize(second_vertex0-second_vertex1):

```text
NA = -A; NB = -B
N = cross(NB,NA)
b = dot(NB,E); a = dot(NA,E)
c = dot(N,C); d = dot(N,D)
eligible = float32(b*c) > float32(1e-6)
       and float32(d*c) < -float32(1e-6)
       and float32(a*b) < -float32(1e-6)
```

Eligible pairs form `axis=cross(first_vertex0-first_vertex1,
second_vertex0-second_vertex1)`. Length below float32(.001) gives no update.
Otherwise divide each component by length and negate axis if
`dot(A+B,axis)<0`. Separation is `dot(axis,second_vertex0)-dot(axis,first_vertex0)`.
Only a strictly negative separation strictly greater than the running best
updates the output indices. Thus zero/positive distances are not selected by
this edge query, and equal results keep the first pair. The face query's positive
separation early-exit policy is different.

[1024 uninterrupted native edge queries](../../native/snow_host/pose_contact_edge_query_validation.json)
match all distance/index bits and the untouched output tail;363 select a pair.
Cases use zero-to-six edges, arbitrary finite frames, vertices and adjacent plane
normals. These are synthetic descriptor tests, not a proof of convex-asset validity.
XYZ mask initialization is supplied. Tests also cover an explicit eligible pair,
first-tie precedence, zero separation and resetting a prior seed. The supported
API domain excludes zero second-edge length and nonfinite/overflow arithmetic.
Both face and edge query implementations are now available for axis selection;
producer descriptor setup and contact-record emission remain unresolved.

### Connected geometry axis selection

`select_geometry_contact_axis` in `engine.pose_contact_axis_selection` connects
both recovered geometry queries to the selection policy. No caller-supplied query
responses are needed. The service-oriented selector remains available for boundary
inspection, while this entry point performs the complete local calculation.

```python
from engine.pose_contact_axis_selection import select_geometry_contact_axis
result = select_geometry_contact_axis(
    first_frame, first_shape, second_frame, second_shape,
    edge_enabled=True,
)
# result has kind, first, second, distance
```

Each frame contains four XYZ rows: three basis rows followed by translation.
Each supplied shape contains `vertices` XYZ, `planes` normal XYZ plus scalar,
and `edges` as four indices vertex0/vertex1/plane0/plane1. Kind0 selects the first
shape's face, kind1 the second face, kind2 an edge pair, and kind3 denotes a
positive face separation. UINT_MAX remains the unused-index sentinel. Geometry
must satisfy the query modules' finite/nondegenerate supported domains. These
schemas and Python entry points are independent API choices, not original names.

[1024 uninterrupted native composition cases](../../native/snow_host/pose_contact_axis_composition_validation.json)
execute the original selector and both original queries with no interception.
All16 result bytes match. Outcomes include155 first-face,154 second-face,35
edge-pair and680 separation results, with edge querying both enabled and disabled.
This supersedes the supplied-query boundary of the earlier selector receipt for
this tested composition. Initialized XYZ mask remains supplied state, and random
synthetic descriptors do not establish original-asset validity. Producer setup,
contact-record emission and full live collision behavior remain unresolved.

### Edge contact record emission

`engine.pose_contact_edge_emit.emit_edge_contact` reconstructs0x18e3aa0. Zero
capacity returns0 before reading geometry. Otherwise it transforms the selected
edge endpoints of both shapes, and the first edge's two adjacent plane normals.
It computes closest points on the two segments with clamped parameters.

Let U=A1-A0, V=B1-B0, W=A0-B0, and float32 dot products
`a=U.U, b=V.U, c=V.V, d=U.W, e=V.W`. Define `det=c*a-b*b`.
If `abs(det)<=a*float32(1e-5)`, seed s-numerator0 and t-numerator e with
both denominators c. Otherwise seed `sN=e*b-d*c`, `tN=e*a-d*b` with denominator
det; clamp sN to0/det and adjust tN/denominator to e/c or (e+b)/c.
Then clamp t: below0 selects t=0 and clamps s=(-d)/a; above its denominator selects
t=1 and clamps s=(-d+b)/a. Otherwise divide both numerators by their denominators.
The code retains these branches and float32 arithmetic rather than substituting
a generic geometry-library closest-points function.

Closest points are `PA=A0+s*U` and `PB=B0+t*V`. The record normal is normalized
`cross(U,V)`, negated when its dot with the sum of the first edge's transformed
adjacent normals is negative. It writes:

| Offset | Written value |
| --- | --- |
| 0x00 | normal XYZ |
| 0x0c | negative squared length of `(s*U+W)-t*V` |
| 0x10 | PA XYZ |
| 0x1c | uint32 zero |
| 0x20 | PB XYZ |
| 0x2c | uint32 0xffff0000 |

Return value is1 and storage beyond48 bytes persists. The value at0x0c has no
square root and must not be described as ordinary linear penetration depth.
The selected-axis distance is not copied into this record. Parallel/zero-length
edge behavior remains outside the independent API domain because native normal
construction can divide by zero; no invented fallback normal is supplied.

[1024 complete native emitter comparisons](../../native/snow_host/pose_contact_edge_emission_validation.json)
match return count, all record bytes and output tail, with963 emitted records
and61 zero-capacity returns. Inputs use finite synthetic selected pairs and general
frame fields. They are not all guaranteed to have been selected by the preceding
query. XYZ mask initialization remains supplied. A synthetic endpoint case checks
that two units of separation produce-4 in the squared-distance field.
The face-contact emitter and complete producer descriptor construction remain open.


### Face polygon vertices and tags

`engine.pose_contact_face_polygon.append_face_polygon` reconstructs the complete
polygon builder at 0x18e3980. It appends indexed vertices to retained storage with
128 sixteen-byte slots and a uint32 count at 0x800. Each slot contains XYZ float32
coordinates and a packed uint32 feature tag. Existing slots and unused bytes persist.

The supplied frame contains three basis XYZ rows and a translation XYZ row.
For each indexed vertex, the builder computes each world component in this order,
rounding every multiply and add to float32:

```text
world[j] = ((basis[0][j] * x + translation[j]) + basis[1][j] * y)
           + basis[2][j] * z
feature = ordinal & 63
prefix = feature | (0x180 if flipped else 0x80)
tag = (((prefix << 12) | (incident_face & 0xfff)) << 12)
      | (reference_face & 0xfff)
store_uint32(tag)
```

Ordinal starts at zero for each call, independently of the existing count. It
wraps after 63. The extra orientation bit in 0x180 falls beyond the stored 32 bits,
so changing `flipped` produces the same stored tag. This is observed arithmetic,
not evidence that orientation has no effect elsewhere in face emission.

The native descriptor supplies vertices at pointer +0 with twelve-byte stride,
planes at +8 with twenty-byte stride, and uint16 vertex indices at +0x18.
The selected incident plane stores its index count at +0x10 and list offset at
+0x12. The independent API accepts these indices explicitly; it does not decode
an asset or construct the shape descriptor. Its capacity rejection is authored;
the native helper has no corresponding overflow check.

[512 complete native comparisons](../../native/snow_host/pose_contact_face_polygon_validation.json)
match the entire retained storage, including XYZ, tags, count and unused bytes.
Synthetic cases include arbitrary finite frames, duplicate indices, existing
records, ordinal wrap, and both orientation flags. The XYZ mask is supplied to
the offline emulator. Clipping, point reduction and complete face emission remain
separate unresolved stages.

### Reference side-plane construction

`engine.pose_contact_side_planes.append_side_planes` reconstructs 0x18e3450. It seeds
`previous` from the last indexed vertex, then visits indices in stored order.
For each `current`, it computes the following with float32 operations:

```text
edge = current - previous
raw = cross(edge, face_normal)
normal = raw * (1 / sqrt(dot(raw, raw)))
local_distance = dot(normal, previous)
world_normal = (basis[1] * normal.y + basis[0] * normal.x)
               + basis[2] * normal.z
world_distance = dot(world_normal, translation) + local_distance
append(world_normal.xyz, world_distance)
previous = current
```

The output uses the same sixteen-byte slot size and count at 0x800, but the fourth
component is a plane scalar, not a feature tag. Normalization occurs before the
frame transform; the routine does not renormalize the transformed normal. This
implementation rejects empty lists, excess capacity and degenerate cross
products through authored guards. Native empty lists are unsafe because the last
index is read before the loop count check. Degenerate IEEE behavior is excluded.
A later degenerate edge can leave earlier appended planes in place; the API does
not promise transactional failure. These planes feed polygon clipping; their sign convention
must be checked against that consumer before describing inside/outside behavior.

[1024 complete native comparisons](../../native/snow_host/pose_contact_side_planes_validation.json)
match all plane normal/scalar fields, counts, existing records and unused bytes.
Inputs include three to 98 vertices, nonzero initial counts, general finite frames
and arbitrary finite face normals. Synthetic polygons need not be planar or convex;
these comparisons validate the local arithmetic, not physical descriptor validity.
The offline emulator supplies the XYZ mask. A square fixture checks closing-edge
order, translated plane scalars and the absence of post-transform normalization.
Polygon clipping and complete face-contact emission remain unresolved.

### Single-plane polygon clipping

`engine.pose_contact_polygon_clip.clip_polygon_plane` reconstructs 0x19980f0.
Inputs are distinct output/source buffers, a source count and a plane XYZ/scalar.
Records contain XYZ float32 and uint32 feature tags. It returns the written count
and preserves output bytes beyond those records.

For each point, compute `distance = ((scalar - nx*x) - ny*y) - nz*z`, rounding
every multiply and subtraction to float32. If `abs(distance) < float32(1e-5)`,
replace distance with positive zero. Negative distances are rejected; zero and
positive distances are retained. Snapping affects classification only, not stored
point coordinates. The implementation requires finite inputs.

Start with the last point as previous, then visit points in source order. If
previous and current distances have different signs, emit an intersection before
any retained current point. With previous distance A and current distance B:

```text
inverse = float32(1 / float32(A - B))
intersection[j] = float32(
    float32(float32(float32(current[j] - previous[j]) * A) * inverse)
    + previous[j])
tag = previous.tag if A < 0 else current.tag
```

The tag comes from the rejected endpoint. Retained points are copied byte for
byte. The native capacity argument is unused; the independent API requires room
for twice the input count before writing. It also requires 1..128 source records
and distinct buffers. These are authored bounds, not recovered rejection paths.
The native distance scratch array is finite, and zero source count reads before
the source start. No empty-input native safety is claimed.

[1024 uninterrupted native comparisons](../../native/snow_host/pose_contact_polygon_clip_validation.json)
match counts and every output byte. Cases cover 1..128 points, arbitrary tags and
planes, signed zero, half-tolerance and exact-tolerance distances. Native calls use
capacity zero with sufficient backing memory, confirming that argument does not
limit writes. The emulator supplies the XYZ mask. Synthetic polygons need not be
convex, so this validates local execution rather than physical shape validity.

The multi-plane wrapper at 0x1996bf0 clips into two alternating temporary buffers,
returns zero if an intermediate result has fewer than three points, and writes
the final stage back to the caller buffer. It unconditionally uses a first and
final plane; zero/one-plane semantics must not be inferred from a generic loop.
The wrapper is implemented below; final contact-point selection remains open.


### Multi-plane polygon clipping

`engine.pose_contact_polygon_clip.clip_polygon_planes` reconstructs 0x1996bf0
for at least two planes. It clips the caller polygon through the first plane into
a temporary buffer. A result below three points returns zero immediately without
writing caller storage. Each intermediate plane clips into the other temporary
buffer, applies the same count check, then swaps temporary roles. The final plane
writes directly into caller storage; the return count is zero if below three.
The helper's capacity argument is unused throughout this composition.

The independent implementation requires 4096 bytes of caller storage, 1..128
initial points and at least two planes. It rejects intermediate counts above 128,
the native temporary capacity. These guards are authored. The single-plane
helper's finite-input and float32 rules apply. No zero/one-plane wrapper behavior,
native overflow or NaN handling is claimed.

[1024 complete native wrapper comparisons](../../native/snow_host/pose_contact_polygon_planes_validation.json)
execute the actual clipping helpers without interception and match returned counts
and all caller bytes. Fixtures cover 3..52 source vertices and 2..10 planes, with
540 nonzero results and 484 zero results. All observed zero results preserve caller
storage. The final count check occurs after the helper writes, but these tests do
not demonstrate a partial-write zero result. The emulator supplies the XYZ mask
and a mapped stack-limit value for the native stack probe. Tests also cover
rejection at first, middle and final stages, and two-plane intersection tag flow.

This connects plane-by-plane clipping only. Contact-point selection, final face
record emission and complete box/triangle descriptor construction remain open.

### Contact plane and proximity filtering

`engine.pose_contact_point_filter` implements the first two stages of 0x19984f0.
`filter_plane_points` reconstructs 0x19986e0 and `remove_near_points` reconstructs
0x1998e80. Point buffers contain sixteen-byte XYZ/tag records; a separate buffer
contains one float32 separation per retained point.

Plane filtering computes `(((nx*x + -scalar) + ny*y) + nz*z)` with every operation
rounded to float32. It tests the result's bits as a signed int32 and retains values
whose signed bits are <=0. For finite values this keeps negative separation and
both zeros. There is no tolerance snap here. Accepted points compact forward in
source order, copying all sixteen bytes, while their computed separations fill
the parallel output. Unwritten point and distance bytes persist. Count0 is valid;
the independent API bounds the native distance scratch domain to128 points.

Proximity filtering visits each current anchor i and candidates j=i+1 onward.
For each candidate, compute float32 `residual = radius*radius`, then subtract
`dx*dx`, `dy*dy`, `dz*dz` in order, rounding each operation. If residual>0, remove
candidate j by copying the last active point and its separation into j, shrink
the count, and retry the replacement. Equality retains the candidate. It does
not average positions, combine tags, choose the deeper point, or preserve order.
The caller supplies radius `float32(0.0001)`.

[1024 complete native selection calls](../../native/snow_host/pose_contact_point_filter_validation.json)
with optional reduction disabled match returned counts, entire point buffers and
entire distance buffers. The native wrapper calls both actual helpers without
interception. Synthetic cases cover 0..128 points, arbitrary tags/planes, exact
duplicates and nearby clusters, retaining33007 points in total. Finite-input
comparisons do not establish NaN behavior or physical contact validity.

When reduction is enabled and more than four points remain, the wrapper calls
0x19989d0 to select four indices, then gathers both points and separations into
the first four slots. That selector is connected below. Final face-contact record emission and complete
producer construction remain separate dependencies.


### Complete contact point selection

`engine.pose_contact_point_filter.select_contact_points` connects the complete
0x19984f0 sequence: plane filtering, proximity removal, then optional reduction
when the surviving count exceeds four. Reduction calls the same 0x19989d0 selector
already implemented by `engine.pose_link_selection.select_pose_link_rows`. This
caller uses sixteen-byte point records rather than the earlier forty-eight-byte
link records. The selection normal comes from the supplied reference plane.

The selector sums points in order with float32 rounding and divides by a float32
count to obtain the center. For normal N=(x,y,z), it chooses a local tangent:

```text
if min(abs(x), abs(y)) - abs(z) < 0:
    tangent = (z,0,-x) if abs(y)-abs(x) < 0 else (0,z,-y)
else:
    tangent = (y,-x,0)
```

After normalization, it rotates the tangent using the recovered quaternion-matrix
path at fixed angle 0.6456422805786133. It finds low/high point positions along
that axis relative to the center, choosing later ties. Let `span=low-high` and
`cross_axis=cross(normal,span)`. A second scan selects the minimum and maximum
projection indices along span, then minimum and maximum along cross_axis, again
choosing later ties. There is no deepest-point preference or uniqueness check.
The existing selector preserves float32 order, including the subtraction-based
comparisons. See CENTRAL_IMPULSE.md, "Geometric four-record selection" and
"Fixed-angle selector rotation" for the prior selector/rotation evidence.

The contact wrapper snapshots all four selected point records and their matching
separation scalars before copying them into slots0..3. Remaining point/distance
bytes persist, including values written by the earlier filtering stage. If the
reduction flag is false or at most four points survive, it returns the filtered
count without invoking the selector. A nonzero finite normal is required only
when the selector runs; no invented fallback is used for degenerate normals.

[1024 complete native selection comparisons](../../native/snow_host/pose_contact_point_selection_validation.json)
match returned counts and complete point/distance buffers with reduction on and
off. There are454 four-point outputs with reduction enabled. Native execution
includes the actual selector, quaternion matrix and scalar trigonometry without
interception. XYZ mask and zero comparison state are supplied; the fixed-angle
specialization is validated for scalar trig dispatch zero. Other dispatch paths,
nonfinite geometry and full face-contact emission remain outside this evidence.

### Connected face-contact emission

`engine.pose_contact_face_emit.emit_face_contacts` reconstructs 0x18e4060 with
explicit frames and shape descriptors. A shape supplies vertices, four-component
planes and a list of vertex indices for each face. Frames supply three basis XYZ
rows and translation. Capacity limits emitted records; unlike the edge emitter,
zero capacity does not bypass geometry work.

Transform the selected reference plane with the same normal/scalar arithmetic as
the side-plane builder. Project its world normal onto each incident-frame basis
row. Choose the incident plane having the smallest dot product of its local normal
with that projected normal. The first plane seeds the minimum; strict comparisons
retain the first tie. Incident planes must be nonempty.

Build the chosen incident polygon in world coordinates, build reference side
planes, clip the polygon against all side planes, then run complete point selection
against the transformed reference plane. These stages use the reconstructed helpers
directly; no supplied query responses stand in for their arithmetic.

For each selected point Q and separation S, compute `P[j]=Q[j]-N[j]*S` with
float32 multiplication and subtraction. Emit up to capacity records:

| Offset | Value |
| --- | --- |
| 0x00 | N XYZ, or sign-negated N if flipped |
| 0x0c | S, the linear plane-separation scalar |
| 0x10 | P XYZ, or Q if flipped |
| 0x1c | uint32 zero |
| 0x20 | Q XYZ, or P if flipped |
| 0x2c | uint32 0xffff0000 |

The final record does not copy the polygon feature tag. The edge emitter's field
at0x0c contains negative squared separation; this face emitter stores S directly.
Normals are not renormalized here, and no division by squared normal length is
added to the point projection. All output beyond the emitted records persists.

[1024 complete native emitter comparisons](../../native/snow_host/pose_contact_face_emission_validation.json)
match counts and every output/tail byte, including1622 emitted records in448
nonzero cases. The native routine executes all polygon, side-plane, clipping,
selection, rotation and scalar-trig helpers without interception. Synthetic cases
cover 3..11 reference vertices, 3..13 incident vertices, z-axis rotated/translated
frames, both orientation modes, reduction on/off, tied incident plane scores and
capacity0..9. These are local planar fixtures, not complete game collision scenes.
XYZ mask, zero comparison state and mapped stack-limit state are supplied; trig
dispatch zero is the validated path. General-frame composition remains to be
broadened, and degenerate helper domains remain excluded.

Face and edge emission now have executable implementations. The upstream producer's
box/triangle descriptor construction and its complete connection to terrain
candidate enumeration, profile gates and record filtering remain unresolved.

### Box and triangle descriptors

`engine.pose_contact_shapes` reconstructs the geometry descriptors built by the
0x190f8b0 producer before contact-axis selection. `box_contact_shape` accepts the
three scalar extents read from receiver fields0x40/44/48. Corner order is:

```text
(+x,-y,+z), (+x,-y,-z), (-x,-y,-z), (-x,-y,+z),
(+x,+y,+z), (+x,+y,-z), (-x,+y,-z), (-x,+y,+z)
```

Face normals are +X,-Z,-X,+Z,-Y,+Y with plane scalars x,z,x,z,y,y.
Face index lists in order are `(0,1,5,4)`, `(1,2,6,5)`, `(2,3,7,6)`,
`(3,0,4,7)`, `(2,1,0,3)`, `(7,4,5,6)`. `BOX_EDGES` records the twelve
native endpoint/adjacent-face tuples in their original order. These tables are
geometry/topology findings, not an extracted mesh asset.

`triangle_contact_shape(A,B,C)` stores the three vertices in argument order.
It computes U=B-A and V=C-A, then their cross product with float32 rounding at
each operation. Normalize with reciprocal multiplication, using squared-length
sum `(ny*ny + nx*nx) + nz*nz`. The two planes are N and sign-negated N. Each plane
scalar is separately computed as `(normal.y*A.y + normal.x*A.x) + normal.z*A.z`.
The reverse scalar is not substituted by negating the forward scalar. Face
windings are `(0,1,2)` and `(2,1,0)`; edges are `(0,1,0,1)`, `(1,2,0,1)`,
`(2,0,0,1)`. Degenerate triangle rejection is an authored guard.

[1024 producer-prefix comparisons](../../native/snow_host/pose_contact_shapes_validation.json)
match all descriptor vertex/plane bytes, face index lists, edge adjacency and
counts. The emulator runs the original producer to its selector call. The original
constant-table store sequences execute separately before the trials; initialized
TLS state is supplied to skip CRT once-initialization bookkeeping. This proves
local descriptor construction for finite positive extents and nondegenerate
synthetic triangles, not the initialization protocol or full producer execution.
The next integration step is dispatching these descriptors through axis selection
and the face/edge emitters, then validating the complete producer.

### Connected box-triangle producer

`engine.pose_box_triangle_contact.emit_box_triangle_contacts` reconstructs the
complete 0x190f8b0 producer. Inputs are box extents, box frame, three world-space
triangle vertices, output capacity, reduction flag and edge-query flag. It builds
the recovered box/triangle descriptors and uses an identity frame for the triangle.
The independent API avoids native pointers and runtime TLS bookkeeping.

Dispatch follows the recovered axis selector:

| Kind | Action |
| --- | --- |
| 0 | Box is reference face; emit against triangle with flipped=false |
| 1 | Triangle is reference face; emit against box with flipped=true |
| 2 | Emit selected box/triangle edge pair |
| 3 | Return zero for separation |

Both face paths pass the reduction flag through. The edge flag controls whether
the selector runs the edge query. Capacity limits record output, not descriptor
construction or selection. The producer has no additional record mutation after
its emitter returns. Helpers retain their finite/nondegenerate preconditions;
no fallback geometry is invented for invalid inputs.

[2048 complete native producer comparisons](../../native/snow_host/pose_box_triangle_contact_validation.json)
match returned counts and every output/tail byte. Selection covers320 box-reference
faces,493 triangle-reference faces,519 edges and716 separation results. There are
1949 emitted records. Native execution runs the original descriptor construction,
queries, selector, clipping, reduction and emitters without interception. The
original constant-table stores execute before trials; initialized TLS state, XYZ
mask, zero comparison vector and mapped stack-limit state are supplied. Scalar
trig dispatch zero is validated. These conditions do not establish CRT once-init
behavior or compatibility with another executable build.

Synthetic cases use positive extents, nondegenerate triangles, z-axis rotations,
translations, capacity0..8 and both flags. This is a connected local collision
producer, not a complete terrain collision simulation. The upstream candidate
iteration, per-triangle profile-mask gate, record-role conversion and optional
terrain filtering still need to be composed and validated. Full 3D rotation
coverage and degenerate native behavior remain separate validation work.

### Full 3D producer validation

[4096 additional complete native comparisons](../../native/snow_host/pose_box_triangle_contact_3d_validation.json)
exercise arbitrary quaternion-derived box rotations and translations. Counts and
all output bytes match across722 box-face selections,1022 triangle-face selections,
1001 edge selections and1351 separation results, producing3947 records. This
broadens the earlier z-axis-only composition evidence without changing the
implementation. Supplied runtime state, finite synthetic geometry and scalar-trig
dispatch restrictions remain. Scale/shear and native exceptional arithmetic are
not established by these rotation fixtures.

### Runnable box-triangle inspection

Run the independent producer without a game executable or private validator:

```sh
python3 -m engine.pose_box_triangle_bench engine/examples/pose_box_triangle.json
```

Use `--output result.json` to save the result. The authored synthetic fixture places
a unit-half-extent box across a triangle plane and produces four contacts. Inputs
specify XYZ extents, four XYZ frame rows, three world-space triangle vertices,
capacity and boolean reduction/edge flags. Provenance must be explicitly
`authored_synthetic` or `caller_supplied_observation`; neither label claims native
verification of the caller's data.

Output contains selected kind/indices/distance, emitted count and decoded contact
records with exact record hex. Each record labels its separation as `linear_plane`
or `negative_squared`, preserving the face/edge distinction. Selection is computed
again for inspection; it is not a live trace. CLI guards bound capacity to128 and
reject nonfinite fields, nonpositive extents and nonboolean flags. Those guards
are authored. The helper geometry domains still apply, and this command does not
supply terrain, integration, a solver or a live mod entry point.

### Terrain record roles

`engine.pose_grid_contact_records.convert_grid_contact_records` reconstructs the
reached conversion block at0x19de481..0x19de6d9 within caller0x19dde20. For every
record just emitted by the box-triangle producer, it swaps twelve-byte point
fields0x10 and0x20, XORs each normal component's raw bits with0x80000000, and writes
the current triangle ID at0x2c. Separation0x0c and field0x1c persist. Conversion
begins at the caller's existing accumulated record count, not at buffer zero.
The helper accepts that start index explicitly.

[1024 native block comparisons](../../native/snow_host/pose_grid_contact_records_validation.json)
match the complete retained buffer for0..32 records, nonzero starts and arbitrary
uint32 identifiers. Random raw words include nonfinite representations; the helper
performs bitwise sign flips rather than float conversion, preserving payload bits.
Both unrolled four-record and remainder loops execute in the native comparison.
Entry registers are supplied. This is not validation of the complete caller.

The surrounding caller chooses a terrain profile through resource map0xb0 indexed
by `triangle_id >> 1`, then pointer table0xa0; absent map uses default pointer0x20.
It admits a triangle when `(terrain.mask50 & other.mask48) |
(other.mask50 & terrain.mask48)` is nonzero. These are 64-bit masks. This gate is
currently a static lead, not part of the record conversion helper.

After conversion, descriptor byte0x92 and terrain resource field0x40==2 jointly
enable the recovered grid-record filter. The filter receives the inverse terrain
frame, current triangle ID and just-produced record batch. Its returned count
increments the accumulated count. Reaching capacity ends enumeration.

Further inspection identifies an earlier optional branch controlled by descriptor
byte0x90. It derives a query center from the box's local bounds and a scalar from
the minimum of its three extents, calls0x19969e0, and can return1 before candidate
enumeration. Its semantics remain unresolved; it must not be silently omitted
when claiming full caller reconstruction. The caller also constructs a full inverse
terrain frame, obtains box bounds through a virtual call and retries candidate
collection when the initial count reaches128. Allocation ownership and these
entry/query stages remain separate work.

### Terrain profile admission

`engine.pose_grid_profile_gate.grid_triangle_profile_gate` reconstructs the reached
lookup/admission block at0x19de310..0x19de355. It returns the selected terrain profile
identity and a boolean admission result. Resource/profile tokens are explicit
caller-owned identities, not saved native heap pointers.

```text
if terrain.mapb0 is absent:
    terrain_profile = terrain.default20
else:
    cell = triangle_id >> 1
    terrain_profile = terrain.tablea0[terrain.mapb0[cell]]
other_profile = other.default20
admit = ((terrain_profile.mask50 & other_profile.mask48)
         | (other_profile.mask50 & terrain_profile.mask48)) != 0
```

The map entry is uint8 and masks are uint64. Both halves of a grid cell share the
same profile selection. Either direction suffices; this is not a requirement for
mutual overlap. No kind discriminator is checked in this reached terrain caller,
and the other resource always uses its default profile. An absent map falls back;
an empty present map does not. The independent API validates unsigned field widths
and lets missing map/table/profile entries fail rather than inventing defaults.

[2048 native block comparisons](../../native/snow_host/pose_grid_profile_gate_validation.json)
match the selected profile pointer identity and mask result, with722 admitted
cases. Inputs cover absent/present maps, sparse/dense masks, high32-bit overlap and
both triangle halves. Entry resource identities are supplied, so this validates
the local lookup/gate rather than full caller reachability or object lifetime.
Profile contents are synthetic. The optional preliminary query, local bounds,
candidate allocation/retry and complete terrain batch orchestration remain open.

### Preliminary height contact

`engine.pose_grid_height_contact.query_grid_height_contact` reconstructs wrapper
0x19969e0 with an explicit unresolved `height_query(resource,x,y)` service returning
height H and triangle ID. It calls that service at center XY and returns false
without output mutation unless center.z<=H. Radius R does not enter this admission
test. On success, separation is `S=float32(float32(center.z-H)-R)`.

Set local normal N=(0,0,1), Q=center and P=Q-N*S, retaining float32 operation order.
Transform N with the frame basis and transform P/Q as points using the usual
`((basis0*x+translation)+basis1*y)+basis2*z` order. If output is provided, write a
48-byte record: normal at0, S at0x0c, transformed P at0x10, zero at0x1c, transformed
Q at0x20 and the service's triangle ID at0x2c. Otherwise return true without writing.
This is not a sphere-overlap admission test: a center above height is rejected even
if its radius extends below the surface. No normalization or surface-slope normal
is substituted for the transformed local +Z direction.

[1024 native wrapper comparisons](../../native/snow_host/pose_grid_height_contact_validation.json)
match boolean results, service arguments and all output bytes, with611 accepted
cases. Height/ID results are supplied by intercepting0x1997af0. This evidence is
explicitly weaker than uninterrupted full-query execution: it validates the
wrapper's downstream behavior, not height interpolation or triangle selection.
Cases cover general finite frames, above/equal/below heights and nullable output.

Static inspection of0x1997af0 shows grid-cell selection using floored, biased XY
coordinates, bounds rejection and topology-dependent piecewise interpolation.
It can also return a triangle ID through an output pointer. Exact interpolation,
boundary bias and outside-grid return semantics remain the next dependency to
recover. The terrain caller's inverse/bounds and allocation paths remain separate.

### Grid height query

`engine.pose_grid_height_query.query_grid_height` reconstructs0x1997af0. It returns
height and triangle ID from supplied grid samples. Width/height are uint16 fields
0x68/6a, spacing is0x70/74, XY bounds start at0x7c/80 and end at0x88/8c.
For each axis, compute with float32 at every operation:

```text
cell = floor(((coordinate - lower - 2^-23) * (dimension - 1)) / (upper - lower))
```

Reject cells outside0..dimension-2. Outside returns negative FLT_MAX and preserves
the supplied triangle ID; the contact wrapper initializes that ID to0xffffffff.
The coordinate bias applies before scaling, not to the final cell index. At exact
lower bounds it can select-1. No clamp or extrapolation fallback is substituted.

Within the cell, derive X0/X1/Y0/Y1 from index*spacing+origin using float32. Let
A/B/C/D be heights at lower-left, lower-right, upper-right, upper-left. Let
`tx=(x-X0)/spacingX`, `ty=(y-Y0)/spacingY`. The following formulas retain separate
multiply/divide/add operations rather than replacing them with barycentric code:

| Orientation and branch | Height | ID half |
| --- | --- | --- |
| zero, tx>ty | A+(B-A)*(x-X0)/(X1-X0)+(C-B)*(y-Y0)/(Y1-Y0) | 1 |
| zero, tx<=ty | A+(C-D)*(x-X0)/(X1-X0)+(D-A)*(y-Y0)/(Y1-Y0) | 0 |
| nonzero, 1-tx>ty | A+(B-A)*(x-X0)/(X1-X0)+(D-A)*(y-Y0)/(Y1-Y0) | 0 |
| nonzero, 1-tx<=ty | C+(D-C)*(x-X1)/(X0-X1)+(B-C)*(y-Y1)/(Y0-Y1) | 1 |

In every row, the first quotient is added to its base height before adding the
second quotient. The ID is `2*(row*cell_width+column)+half`, where cell_width is
field0x9c. For orientation zero, returned halves disagree with the triangle
geometry enumerator's half ordering. This observed discrepancy is preserved;
its downstream consequence is not resolved by renumbering the query output.

[4096 uninterrupted native query comparisons](../../native/snow_host/pose_grid_height_query_validation.json)
match height bits and retained/updated IDs, including1218 outside-grid cases.
Inputs cover both orientations, dimensions2..10, nonunit spacings, translations,
arbitrary heights and interior/exterior coordinates. The independent API requires
finite inputs and positive complete grid geometry; native exceptional int32
conversion and zero-span behavior are excluded. No original samples are included.
The complete height-contact wrapper still needs an uninterrupted composed check.

### Connected preliminary grid contact

`engine.pose_grid_height_contact.query_sampled_grid_contact` connects the recovered
height interpolation to the preliminary contact wrapper. It accepts raw resource
metadata and caller-supplied sample floats, plus frame, center, radius and optional
output. The explicit-service wrapper remains available for isolated observations;
this connected API uses `query_grid_height` directly with the native initial ID
0xffffffff. No interpolation response is invented or supplied externally.

[4096 uninterrupted native comparisons](../../native/snow_host/pose_sampled_grid_contact_validation.json)
execute both original routines and match booleans plus all output/tail bytes.
There are1682 accepted queries,1147 writes and1270 outside-grid coordinates. Cases
include both orientations, dimensions2..10, nonunit spacing, translated grids,
general finite frames, above/equal/below heights and null output. Unlike the earlier
wrapper-only receipt, this comparison does not intercept the height service.

The connected wrapper preserves the height query's orientation-zero triangle ID
discrepancy. It also adds no explicit outside-grid rejection: the native negative
FLT_MAX height sentinel flows into the ordinary center.z<=height comparison.
Observed outside cases at ordinary finite heights reject; extreme-sentinel inputs
and exceptional arithmetic are not covered by this receipt. Caller bounds/frame
construction, allocation and complete terrain candidate orchestration remain open.

### Terrain inverse and relative frames

`engine.pose_grid_contact_frames.grid_contact_frames` reconstructs the frame
arithmetic in0x19dde20 before its virtual bounds call at0x19de117. Input frames
have three basis XYZ rows and a translation. It returns the inverse terrain frame
and the other object's frame expressed in terrain coordinates.

For terrain basis rows A,B,C, compute cofactors `cross(B,C)`, `cross(C,A)`,
`cross(A,B)`. Determinant is `dot(A,cross(B,C))`. Scale each cofactor component by
the float32 reciprocal determinant, then transpose those scaled rows into inverse
basis rows I0/I1/I2. This is a full inverse, not a transpose-only shortcut.
All products, differences, sums and reciprocal operations round to float32.

```text
transform_direction(v) = (I1*v.y + I0*v.x) + I2*v.z
inverse_translation = transform_direction(-terrain_translation)
relative_basis[k] = transform_direction(other_basis[k])
relative_translation = ((I0*other_translation.x + inverse_translation)
                        + I1*other_translation.y) + I2*other_translation.z
```

The translation grouping differs from the direction grouping and is preserved.
The inverse feeds terrain filtering; the relative frame is passed to the other
resource's virtual bounds query. Singular rejection is an authored guard.

[2048 native prefix comparisons](../../native/snow_host/pose_grid_contact_frames_validation.json)
match every XYZ float bit in both frames across general finite nonsingular bases,
including scale, shear, reflection and translation. Execution stops before the
virtual bounds call. XYZ mask initialization is supplied. The native fourth SIMD
lanes can contain signed zero; the independent XYZ frame interface does not expose
those lanes, so this receipt does not claim full64-byte frame equality. A failed
initial full-lane comparison identified that limitation. Bounds calculation and
complete terrain caller execution remain separate validation work.

### Box resource bounds query

`engine.pose_box_resource_bounds.box_resource_bounds` reconstructs0x18c5420.
Resource construction/copy path0x18c5370 sets kind0x8003, assigns table0x29c9ac8
and copies the three extent fields0x40/44/48. That table's slot0x10 points to this
bounds method. This identifies the box implementation of the virtual bounds
service used by the terrain caller; other resource kinds remain separate.

For each output axis j, with basis rows B0/B1/B2 and extents e:

```text
radius[j] = (abs(B0[j])*e.x + abs(B1[j])*e.y) + abs(B2[j])*e.z
low[j] = translation[j] - radius[j]
high[j] = radius[j] + translation[j]
```

Every multiply and add/subtract rounds to float32. The method writes six floats
in lowXYZ/highXYZ order. In the terrain caller, the frame supplied here is the box
frame expressed in terrain coordinates, so these are local query bounds for grid
candidate enumeration. No geometric midpoint or arbitrary resource origin is
added. Extents are assumed finite positive values in the validated composition.

[2048 composed native prefix comparisons](../../native/snow_host/pose_box_resource_bounds_validation.json)
execute terrain inverse/relative-frame construction and the actual virtual method
through a constructed box resource's vtable. All frame XYZ bits and six bounds
float bits match across general nonsingular bases, including shear, scale,
reflection and translation. No service is intercepted. XYZ mask and resource
identity are supplied; fourth SIMD lanes and later caller stages are outside this
receipt. The construction/copy routine itself is static dispatch evidence, not
validated allocation or object-lifetime behavior.

### Terrain candidate collection and ownership

`engine.pose_grid_candidates.collect_grid_triangle_candidates` reconstructs the
query/retry policy in0x19de1f0..0x19de2f1. Total candidate capacity is twice the
uint16 cell-width times cell-height. The first query uses min(total,128) entries.
If and only if that query returns128, the caller allocates total*4 bytes and reruns
the entire query from the beginning. It replaces the initial list, not appends to
it. A grid with exactly128 triangles therefore queries twice at capacity128.
The independent API returns IDs, queried capacities and whether retry occurred.

Native initial allocation uses a marked temporary block. Because first capacity
never exceeds128, its bytes never exceed512, so the observed branch uses stack
storage with marker0x79cb0723. The generic alternate path for blocks above0x800
bytes is not reached under these positive grid dimensions. Retry requests an
unmarked full-grid buffer through0x18c9140 and clears the temporary ownership flag.
Cleanup at0x19de729 releases a marked heap block only for marker0x79cb0724, leaves
marked stack storage alone, or passes the retry buffer to0x18c8f50. The underlying
allocator/free implementation and its lifetime guarantees are not reconstructed.

[1024 reached native collection comparisons](../../native/snow_host/pose_grid_candidate_collection_validation.json)
match candidate IDs/counts, query capacities, retry allocation size and ownership
flag, including489 retries. Queries execute the actual enumerator. A hook supplies
storage for the full-grid allocator; query hooks only observe arguments. This
validates allocation requests and selection policy, not the allocator itself.
Tests cover small grids, exactly128 triangles, larger grids and empty Z overlap.
Python owns independent buffers. The API's positive bounded-grid guard is authored;
zero dimensions, huge allocation behavior and full terrain orchestration remain open.

### Connected terrain-box contact caller

`engine.pose_grid_box_contact.emit_grid_box_contacts` connects caller0x19dde20 for
a grid and kind3 box. It computes inverse/relative frames and box bounds, optionally
runs preliminary height contact, collects candidate IDs, resolves profile masks,
transforms each admitted triangle into world coordinates, generates box-triangle
contacts, converts point roles/IDs and optionally filters the batch. It stops when
the accumulated retained count reaches capacity. Python owns temporary buffers;
native allocator internals are not reproduced.

Descriptor byte0x90 controls both the preliminary path and face-point reduction.
The preliminary center is the float32 midpoint of local box query bounds. Its
radius is the minimum box extent, selected in native comparison order. On success
this path returns1 immediately, before profile gating and candidate collection.
With capacity0 it supplies a null output yet can still return1. Therefore the
return value is not unconditionally a count of written records. The independent
API preserves this behavior rather than forcing zero at zero capacity.

Byte0x91 controls edge queries. Byte0x92 enables terrain record filtering only when
resource field0x40==2. Filtering acts on each newly produced batch using inverse
terrain coordinates. Discarded-tail bytes persist, including records written by
production before filtering; later batches can overwrite that tail. The API uses
views into the caller buffer to retain these effects.

[512 complete native caller comparisons](../../native/snow_host/pose_grid_box_contact_validation.json)
match returned values and entire output/tail buffers. The original caller executes
all helpers without interception on synthetic3..6 grids, using its stack-candidate
path. Cases include uneven samples, both diagonals, translated frames, default
profile admission/rejection, all three flags and capacity0..8. There are157 positive
results, summing to382; this sum is deliberately not labeled emitted records due
to the zero-capacity preliminary behavior. Initialized TLS/topology, XYZ/zero state
and stack limit are supplied. Allocation retries, mapped profiles and general frame
rotations have separate helper evidence but are not yet covered in this complete
caller receipt. Live collision integration and broader resource pairs remain open.

### Broader terrain-caller composition evidence

[1024 rotated/mapped-profile native comparisons](../../native/snow_host/pose_grid_box_contact_rotated_validation.json)
extend complete-caller validation to independently rotated terrain and box frames,
uneven samples, both diagonal orientations, per-cell byte maps and high-bit profile
masks. Every returned value and output/tail byte matches without interception.
There are544 positive results summing to1057; this includes preliminary semantics
and is not an emitted-record total. Small grids use the native stack-candidate path.

[256 larger-grid retry comparisons](../../native/snow_host/pose_grid_box_contact_retry_validation.json)
exercise the same caller on9..11 sample dimensions with larger boxes. All output
bytes and returns match, with90 positive results summing to361. Every case requests
one full-grid candidate allocation and later frees that exact buffer. The validator
supplies allocation/free services, checking requested byte size and released pointer;
all geometric routines, retry decisions and cleanup call sites execute natively.
There are256 allocations and256 frees. Preliminary contact is disabled in this
receipt to force candidate processing; edge/filter flags and capacity0..8 vary.

These receipts close the earlier full-call rotation, mapped-profile and retry-policy
validation gaps for the tested finite synthetic domains. They do not recover the
allocator internals, asset samples, live scheduler integration, arbitrary resource
pairs or degenerate arithmetic. Existing XYZ/TLS/topology/stack initialization and
fixed-angle scalar-trig restrictions still apply. No implementation adjustment was
needed for these expanded comparisons.

### Runnable terrain-contact inspection

The independent complete caller can be exercised without original assets or a
private executable:

```sh
python3 -m engine.pose_grid_box_bench engine/examples/pose_grid_box.json
```

Use `--output result.json` to save inspection output. The synthetic fixture supplies
a3x3 uneven grid, box/terrain frames, extents, profile masks and caller flags.
It produces15 contacts with filtering disabled. Enabling filtering retains zero
for this particular fixture; discarded record bytes remain visible in output hex.
This illustrates stage effects, not a calibrated game scene.

The authored JSON adapter packs grid metadata from width/height, positive spacing,
XY origin, supplied samples, enclosing Z bounds, orientation and filter mode. It
requires explicit provenance, complete samples, resolvable profile maps and bounded
capacity. Limits are64x64 samples and128 output slots. These are inspection guards,
not native resource limits. Caller flags remain independently configurable.

Output separates `return_value` from `retained_record_count` and reports
`success_without_record` for preliminary success at zero capacity. Retained records
include normals, point pairs, triangle IDs and exact hex. The scalar is named
`separation_field`: final terrain records do not identify face versus edge origin,
so the adapter does not mislabel every scalar as linear depth. Full output hex also
includes inactive/discarded bytes. This command performs contact generation only;
it does not advance bodies, invoke the solver, decode assets or attach to a game.

### Reversed contact pair adapter

Static caller tracing finds0x198a780 calling terrain/box routine0x19dde20. The
adapter copies descriptor frame1 into frame0 and frame0 into frame1, swaps resource
pointers0x80/88, and preserves flag bytes0x90/91/92. After generation it calls
0x1994f60 over `[output, output+returned_count*48)` and returns the same count.
This is an ordering adapter, not yet the bridge to persistent pose-link payloads.
Its registration/dispatch and later grouping need further tracing.

`engine.pose_contact_reverse.reverse_contact_records` reconstructs0x1994f60. It
swaps the two XYZ point fields at0x10/20 and XORs each normal word with0x80000000.
It preserves separation0x0c, feature word0x1c and triangle/detail word0x2c. Applying
it twice restores every byte. Unlike terrain record conversion, it does not replace
an identifier. Raw bit operations preserve signed-zero and NaN payload patterns.

[1024 complete native reversal comparisons](../../native/snow_host/pose_contact_reverse_validation.json)
match every retained byte for empty through64-record ranges, nonzero starts and
arbitrary word patterns, with no interception. The independent API validates a
complete record range. Native count/range construction is caller-owned.

The complete adapter is now implemented as
`engine.pose_grid_box_contact.emit_box_grid_contacts`. Its inputs put the box frame
before the terrain frame; profiles, samples and flags retain their terrain-caller
meaning. It calls the terrain-first producer, reverses the returned record range,
and returns the same value. This supersedes the earlier unvalidated adapter boundary.

[1024 complete adapter comparisons](../../native/snow_host/pose_box_grid_adapter_validation.json)
match return values and every output/tail byte without intercepted calls. Cases use
independent 3D rotations, both terrain diagonals, mapped profiles with high-bit
masks, all caller gates and capacities zero through eight. Supplied initialization
includes TLS, topology, masks and stack state. These small grids do not exercise
allocator retry through the adapter.

At zero capacity, preliminary terrain success returns one without producing a
record, then the adapter reverses the existing first record. The independent API
therefore requires at least one backing record even at zero capacity. This is an
authored storage guard preserving the observed mutation, not evidence that the
native caller checks storage. A positive return does not establish a newly produced
contact. Tests preserve scalar/identifier words and trailing bytes in this case.
Registration, dispatch ownership and downstream persistent grouping remain open.

### Resource-pair dispatch lookup

The terrain callers belong to an ordered 8x8 handler table. Lookup0x18de680 reads
uint16 kind at resource+0x28 for each resource, masks each with0x7fff, then returns
`table[8 * first_kind + second_kind]`. Storage starts at receiver+8. There is no
swap, null fallback or range check in the original lookup. High bit15 does not
participate in dispatch. Its other meaning is not established here.

`engine.pose_contact_dispatch.select_contact_handler` implements that selection
using supplied handler identities. It preserves empty slots and rejects masked
kinds outside0..7 as an authored safety guard. It does not call the handler or
pretend that a supplied identity establishes native lifetime.

[256 original lookup comparisons](../../native/snow_host/pose_contact_dispatch_validation.json)
cover all64 pairs with all four combinations of bit15, including zero and arbitrary
64-bit handler identities. The complete original function executes without call
interception. This receipt validates selection, not constructor allocation.

Static constructor0x198cf70 clears512 bytes at receiver+8, then allocates8-byte
handler objects through a supplied allocator, with alignment16 and argument10.
It installs32 ordered entries. Rows2..5 have columns2..7; rows6..7 have columns2..5.
All remaining slots stay zero. Allocation failure stores a zero slot. Two relevant
registrations connect directly to the reconstructed contact callers:

| Pair | Receiver slot | Handler vtable | Contact method at vtable+0x18 |
| --- | --- | --- | --- |
| kind7 terrain, kind3 box | +0x1e0 | 0x29cb350 | 0x19dde20 |
| kind3 box, kind7 terrain | +0x100 | 0x29cb490 | 0x198a780 |

Each table has five observed function entries. Names and full semantics of the
other method slots remain unresolved. Resource kind naming comes from the earlier
resource/bounds evidence; this lookup alone supplies only numeric kinds.

The containing object has observed size0x208. Constructor callers0x18dc300 and
0x1927590 install its vtable0x29ca780 and retain it at owner+0x68 and owner+0x10,
respectively. These are static ownership links, not runtime lifetime guarantees.
The vtable exposes lookup0x18de680 and replacement0x198f8b0. Replacement indexes
raw numeric arguments as `8 * first + second`, calls the old handler's first
virtual method with argument1 when nonzero, then stores the new handler. Unlike
resource lookup, this method does not mask its numeric arguments. Its destruction
and concurrency contracts still need validation before a replacement API is safe.

This closes registration and selection for the two terrain orders. The specific
call site invoking the selected contact method, subsequent record grouping/cache
acquisition and scheduled solver ownership remain separate tracing targets.

### Contact generation to persistent-group handoff

Wrappers0x18e08a0 and0x18e0980 connect resource lookup and virtual contact production
to the previously reconstructed record-group consumer0x198f910. Pair descriptor
fields+0/+8 select two bodies; uint16 fields+0x10/+0x12 select their72-byte entries
from body+0xb8. Each selected entry's+0x10 resource supplies the kind for lookup.
The dispatch object is reached through context's first pointer, then owner+0x68.
The selected handler's virtual+0x18 receives the supplied geometry descriptor,
context+0x58 output buffer and fixed capacity500.

Pseudocode for both wrappers:

```text
first_resource = pair.first_body.entries[pair.first_index].resource
second_resource = pair.second_body.entries[pair.second_index].resource
handler = dispatcher.lookup(first_resource, second_resource)
count = handler.contact(geometry_descriptor, context.records, 500)
if count != 0:
    process_groups(cache, span(context.records, 500), count, pair,
                   context.recycled, use_full_detail_key)
else:
    clear_pair(cache, pair.first_index, pair.second_index, context.recycled)
```

The first wrapper passes full-detail-key=true, the second false. Consumer0x198f910
therefore sorts/groups record+0x2c using32 or16 bits, respectively. Upstream calls
at0x18ddb54/5b choose the16-bit wrapper when the OR of two caller-local bytes is
nonzero, otherwise the32-bit wrapper. The producers/meaning of those bytes remain
unresolved; do not infer key width from sport or resource kind alone.

`engine.pose_contact_dispatch.dispatch_contact_pair` reconstructs this handoff.
Resources and handlers are supplied Python objects; grouping and clearing are
required services. Its returned count is authored diagnostics, not a native wrapper
return contract. It requires500 backing records and rejects missing handlers,
out-of-range counts and invalid indices. The original wrappers dereference the
selected handler without a null guard. Native downstream routines still own cache
mutation, allocation and recycling; this adapter does not invent those policies.

[84 complete wrapper comparisons](../../native/snow_host/pose_contact_handoff_validation.json)
execute both original wrappers and original lookup. Supplied services intercept
contact production, grouping and clearing. Checks cover selected resource entries,
argument forwarding, buffer visibility, fixed capacity, both key widths, indices,
high kind bits and returned counts0/1/2/4/128/499/500. They establish the orchestration
boundary, not uninterrupted geometry-to-cache execution or live scheduling.

This gives a static connection from registered terrain contact handlers to the
persistent record-group consumer. Earlier notes leaving that invocation unknown
are superseded. Full cache acquisition/removal and the caller's scheduling/lifetime
contract remain open before this can be treated as an integrated physics update.

### Empty-pair cache recycling

`engine.pose_contact_cache` reconstructs pair clearing0x19904e0 with removal helper
0x1958fa0 and count reset0x1986020. Cache slots contain16 bytes: uint16 first/second
indices, uint32 detail, uint64 payload identity. The removal helper scans backward
for the last matching pair, ignoring detail, decrements count, copies the last
active slot over the removed slot and returns the removed payload identity.
Inactive storage remains intact. Comparison arguments are uint32; the helper does
not truncate an out-of-range argument to the slot's16-bit field.

Clearing repeats removal until it returns zero. For each nonzero payload it writes
zero only to the uint32 active count at+0x110, leaving all cached rows, flags and
other bytes untouched. It appends that identity to the recycled-pointer collection.
When full, the collection grows from zero capacity to8, otherwise doubles capacity.
Native allocation requests capacity*8 bytes with alignment16 and argument0x28;
existing storage uses the reallocation service. No payload is freed here.

A removed null payload and absence both return zero. Therefore a null matching
entry is removed but terminates clearing before any remaining matches are visited.
This is preserved rather than silently converted into a skip-null policy.

```text
while true:
    payload = remove_last_pair_match(cache, first, second)
    if payload == 0: return
    payload.active_count = 0
    if recycled.count == recycled.capacity:
        grow(recycled, 8 if capacity == 0 else 2 * capacity)
    recycled.slots[recycled.count] = payload
    recycled.count += 1
```

The independent API accepts caller-owned payload buffers indexed by opaque integer
identity. Python list growth replaces allocator execution. New reserved list slots
are authored zero placeholders, not recovered native initialization. Its processed
count return is diagnostic. Supplied cache/payload validity and serial mutation are
preconditions; the implementation does not add an ownership or concurrency claim.

[512 complete original clear comparisons](../../native/snow_host/pose_contact_cache_clear_validation.json)
execute original removal and reset helpers with supplied allocator services.
They match every retained cache slot, recycle slot/count/capacity, all288 payload
bytes and allocation sizes. Cases process3846 payloads and exercise739 growth calls,
including mixed details, unmatched pairs, empty collections and null termination.
New allocator storage is zeroed fixture data. Allocation failure, overflow and
runtime synchronization remain outside this validation.

This replaces the pair-clear service's numerical/storage policy with executable
reconstruction. The nonempty path still needs cache lookup/acquisition and full
integration with contact generation. Caller adapters may bind `payloads` explicitly
to use `clear_contact_pair` as the handoff's clearing service.

### Nonempty-group payload acquisition through a recycler

Reached block0x198fbcc..0x198fd21 first calls lookup0x1958a40 with the pair and
current detail key. Lookup packs low16(first), low16(second), low32(detail), scans
forward and returns the first matching payload identity. Unlike pair removal,
lookup truncates comparison arguments. A matching null payload is indistinguishable
from a miss and does not cause the lookup to continue to later duplicates.

On a nonzero hit the block preserves payload and recycler bytes and proceeds to
the existing flag/reduction/update path. On a miss with a non-null recycler:

```text
if recycled.count == 0:
    required = recycled.count + 10
    if required > recycled.capacity:
        grow(recycled, max(required, 2 * recycled.capacity))
    start = recycled.count
    recycled.count += 10
    supply_initialized_payloads(recycled.slots + start, 10)
recycled.count -= 1
payload = recycled.slots[recycled.count]
payload.owner = cache.owner
append_key_and_payload(cache, first, second, detail, payload)
```

The count increment precedes batch supply. Pop leaves the inactive slot intact.
A recycled payload's rows, active count and flags are not reset by this acquisition
block. A fresh batch service separately initializes owner/count/flag bit0 before
returning identities. The caller then replaces the selected payload's owner.
Do not clear every reused payload or rebuild its cached rows at this boundary.

`pose_contact_cache.find_contact_payload` and
`acquire_recycled_contact_payload` implement lookup and the recycler branch.
Python list growth replaces allocator execution. Batch supply must return ten
initialized identities, and append is an explicit service responsible for cache
storage capacity. A null popped identity is rejected as an authored guard; the
original continues to an invalid dereference. The no-recycler branch instead uses
global pool allocation and protected synchronization calls; that branch is not
silently replaced by this API.

[512 reached-block comparisons](../../native/snow_host/pose_contact_acquisition_validation.json)
include original lookup and original append with preallocated cache capacity.
Only recycler allocation/reallocation and batch supply are intercepted. All retained
cache/recycle bytes, counts, capacities, supplied payload bytes, selected identities
and growth/batch requests match. Cases include85 cache hits and290 ten-item refills.
The remaining misses pop existing recycler entries. This is serial synthetic
validation, not proof of pool initialization, locks or global owner lifetime.

The previous contact handoff's nonempty service now has a reconstructed acquisition
policy for a non-null recycler. Sorting, obsolete-key retirement, grouping and the
already reconstructed row updater still need a continuous integration comparison.

### Stale contact-group retirement scan

`pose_contact_cache.retire_stale_contact_groups` reconstructs the reached scan at
0x198f995..0x198fb1e before new group acquisition. It accepts already-sorted48-byte
records, a retained cache collection, pair indices, explicit16/32-bit detail width,
payload buffers and a recycler. This does not implement the preceding native sort.

The scan walks cache indices forward. For each entry of the current pair it walks
runs of equal record detail values, comparing the cache's full32-bit detail key
against the selected16/32-bit record value. Missing keys are removed with the
existing full-key swap-last helper; the scanned payload's active count is reset,
and that identity is appended to the recycler with0->8/doubling capacity growth.

Two cursor rules are observable and must not be replaced by a generic set filter:

- The record cursor persists across cache entries. Matching leaves it at that
  group's start; scanning a missing key exhausts it for subsequent entries.
- The cache index increments even after swap-last removal. The moved entry at
  that index is not revisited in this pass.

For example, cache keys[2,1] against sorted record keys[1,2] retain key2 then retire
key1, because the record cursor does not rewind. Cache keys[9,8,7] against records[1]
retire9 and8 but leave the moved7 entry active. These are synthetic examples of
local mechanics, not proof that normal game inputs violate a cache-order invariant.
With duplicate cache keys, removal targets the last matching key while reset and
recycling target the payload at the scanned index. Do not assume those identities
must coincide without establishing uniqueness upstream.

Pseudocode preserving the cursors:

```text
record_cursor = 0
cache_index = 0
while cache_index < cache.count:
    entry = cache[cache_index]
    if entry.pair == current_pair:
        while record_cursor < record_count:
            end = end_of_equal_detail_run(record_cursor)
            if entry.detail == record_detail(record_cursor): break
            record_cursor = end
        if record_cursor == record_count:
            remove_last_full_key_match(cache, entry.key)
            entry.payload.active_count = 0
            append_recycled(entry.payload)
    cache_index += 1
```

[1024 uninterrupted original retirement-block comparisons](../../native/snow_host/pose_contact_retirement_validation.json)
match all retained cache/recycle slots and all supplied payload bytes, including
3894 retired payloads. They cover sorted records, arbitrary cache order, duplicates,
unrelated pairs and both key widths. Original lookup/removal/reset helpers execute
without interception; preallocated recycler capacity64 avoids allocator calls.
The implementation's growth formula is inspected but not exercised by this receipt.
No cache-order invariant, upstream sort equivalence or live scheduling is claimed.

### Contact record sort ordering

Before retirement, consumer0x198f910 calls sort0x1c8fd50 on48-byte records with
comparator0x198f8f0 for full detail keys or0x198f900 for low16-bit keys.
`engine.pose_contact_sort.sort_contact_records` reconstructs the sort's record
permutation, including its unstable equal-key ordering. A stable Python sort would
change the first record used for normal selection and geometric reduction.

The16-bit comparator zero-extends each key before subtraction. The32-bit comparator
subtracts modulo2^32 and interprets the result as signed32. For example, comparing
key0 against0xffffffff returns+1, not a negative unsigned-order result. Arbitrary
widely separated keys can violate comparator transitivity. The reconstruction
preserves this behavior; it does not promise a globally ascending unsigned order.

For ranges of at most8 records, helper0x1c8fc90 repeatedly finds the first strict
maximum and swaps it with the last active slot. Equal keys do not replace the
selected maximum. Three equal-key records with identities[0,1,2] consequently become
[1,2,0]. Larger ranges select a middle pivot after low/middle/high comparisons,
scan/partition while tracking a moved pivot, skip the equal-key region and process
the smaller remaining range first while stacking the larger. Whole records move;
field bytes are never normalized or regenerated.

[1024 complete original sort comparisons](../../native/snow_host/pose_contact_sort_validation.json)
match every record byte and trailing bytes for counts0,1,2,7,8,9,10,16,31,64,127,256,
and500. Cases cover duplicates, ascending/descending/all-equal keys and arbitrary
uint32 keys under both comparators. Original sort, small-range helper, comparator,
indirect-call trampoline and security-cookie check all execute without interception.
The receipt proves local permutation behavior, not integrated cache processing.

The independent module is limited to48-byte records and explicit16/32-bit key width.
These domain guards avoid exposing an unrelated generic native sorting API. The
next integration can now use the recovered permutation before retirement,
acquisition and per-group reduction instead of assuming stable sorting.

### Connected nonempty contact-cache consumer

`pose_contact_cache.process_contact_cache` connects the complete nonempty consumer
0x198f910 for a supplied non-null recycler. It mutates records/cache/recycler and
caller-owned payloads through the recovered sequence:

1. Sort whole records with the selected detail comparator and native permutation.
2. Retire stale groups with the persistent record cursor and swap-last semantics.
3. Derive the paired-entry gate from each entry's raw flag byte.
4. Scan contiguous equal-detail groups, acquire each cached/recycled payload,
   replace flag bit0, optionally reduce to four records and update payload rows.

Group boundaries use the original span, even when reduction overwrites its first
four records. Inactive record tails stay in storage. Acquisition uses the selected
16/32-bit group key, while individual record detail words remain unmodified.
Returned group counts/identities and retired identities are authored diagnostics.
Input is explicitly nonempty; the zero-contact wrapper uses pair clearing instead.
Batch supply and cache append remain explicit storage services in the Python API.

[512 complete original consumer comparisons](../../native/snow_host/pose_contact_consumer_validation.json)
run0x198f910 from entry to return without call interception. Original sorting,
retirement, lookup, append, grouping, four-record selection, scalar trig and payload
update all execute. Every input record byte, retained cache/recycler slot and all64
supplied payload buffers match the independent implementation. Cases cover1815
groups,700 retired payloads and783 groups reduced to four records, under both key
widths, mixed entry flags, duplicate cache keys and arbitrary cache ordering.

These executions preallocate32 cache slots and supply32 recycled payloads, with
1..36 incoming records. No allocator growth or batch refill is reached. Runtime
XYZ/zero masks and scalar trig dispatch state are supplied. Geometry generation,
no-recycler global allocation/locking and live scheduling remain separate boundaries.
Earlier per-helper and reached-block receipts remain useful for those paths they
cover, but they must not be presented as one uninterrupted allocating execution.

A public synthetic lifecycle test creates a six-record group, reduces it to four,
clears the pair, and recontacts using the same recycled payload. It checks owner,
entry flag, active count and cleared cached-word eligibility. This demonstrates
independent storage continuity without game assets or process access.

### Terrain generation through contact-cache processing

`pose_contact_dispatch.process_dispatched_contact_pair` connects handler lookup,
contact generation and either the nonempty cache consumer or empty-pair clearing.
It packs the generated span into retained48-byte records for the consumer and
writes the resulting permutation/reduced records back to the same byte buffer.
Bytes outside that generated span retain the producer's values. This matters when
geometry filtering discarded contacts but left their bytes in inactive storage.

Handlers remain caller-supplied bindings for descriptor-specific geometry. Binding
the recovered terrain-box or box-terrain producer requires explicit terrain samples,
profiles, frames and flags. Pair frames and entry flags for payload updating are
also supplied; the adapter does not resolve native bodies or infer lifetime.
Batch supply and cache append retain the previously documented service boundaries.

[256 full original wrapper comparisons](../../native/snow_host/pose_terrain_cache_integration_validation.json)
execute resource lookup, the selected terrain geometry routine, sorting, retirement,
acquisition, reduction and payload updating, or zero-contact pair clearing, without
call interception. They match all24000 output bytes, cache/recycle storage and all64
supplied payload buffers. Both terrain/box orders and key widths are exercised;
317 groups,208 nonempty-path retirements,4 reductions and117 zero-contact cases
occur. These counts describe this fixture suite, not gameplay prevalence.

The suite uses synthetic3x3 uneven grids, translated identity frames, matching
profiles and varied preliminary/edge/filter flags. Storage is preallocated to avoid
allocation/refill. TLS, topology and vector masks are supplied initialized state.
This connects collision production to persistent contact records, but does not
execute solver rows, advance bodies or prove scheduled live-game ownership.

The first harness attempt failed because its newly expanded24000-byte output buffer
overlapped synthetic body/pair storage. Relocating that fixture buffer resolved the
fault without runtime changes. The receipt records only the completed comparisons.
A public synthetic lifecycle test runs actual terrain generation, then moves the
box above the terrain and verifies the zero-contact path clears and recycles its
payload. No game files or native process are needed for that test.

### Terrain-cache inspection CLI

Run the connected inspection without game files:

```sh
python3 -m engine.pose_terrain_cache_bench engine/examples/pose_terrain_cache.json --output result.json
```

Schema `pose-terrain-cache-v1` requires provenance, explicit initial state, pair
indices/entry flags/order/key width and1..64 geometry steps. Each step uses the
terrain-contact inspection input layout, but capacity must be500 as in the native
handoff. Both `terrain_box` and `box_terrain` orders are supported. Geometry packing
and bounds checks share `pose_grid_box_bench.prepare`; its original standalone
inspector keeps its128-record bound.

Initial state provides an opaque owner ID, retained16-byte cache slots/count/capacity,
recycled identity slots/count/capacity, complete288-byte payloads keyed by opaque ID,
and all24000 output-buffer bytes. The command deep-copies that state. IDs are local
inspection identities, not native heap addresses. Active identities must resolve
to supplied payloads. Cache/recycler initial capacities are bounded to256 by the
inspection adapter. Each geometry step still supplies its own frames and profiles.

The included fixture is wholly authored synthetic data. It places a box against
uneven terrain, moves it above the terrain, then restores contact. Generated/cache
counts are[1,0,1], recycled counts[0,1,0], and the same payload ID is reused. Output
includes per-step groups/retirements or cleared counts, active entries, complete
retained output and payload hex, plus `final_state` suitable as a later invocation's
`initial_state`. A continuation test confirms split and uninterrupted runs produce
the same retained final state. This is independent snapshot continuation, not an
original-game save state or reverse stepping.

The CLI intentionally requires enough initial payloads and cache slots. Exhaustion
raises an explicit missing-storage error; it does not manufacture a global allocator
or batch-pool policy. Recycle-list growth still follows the reconstructed local
policy using Python storage. Input guards, JSON representation, diagnostics and
snapshot copying are authored interfaces. Numerical integration evidence remains
the separate native terrain-cache receipt, not the fixture's successful execution.
No solver, time advancement, native memory access or game launch occurs here.

### Contact payload pool

`pose_contact_pool.acquire_payload_slot` reconstructs slot acquisition0x18dcff0
for288-byte payload storage. The pool is distinct from the contact consumer's
recycled-pointer list. Structural fields are:

| Pool offset | Meaning in this routine |
| --- | --- |
| +0x08 | retained page-pointer array |
| +0x10 / +0x12 | uint16 page count / capacity |
| +0x18 | current page pointer |
| +0x20 / +0x22 | uint16 current page index / next slot index |
| +0x24 / +0x26 | uint16 slots per page / allocation alignment |
| +0x28 | uint32 active allocation count |
| +0x30 | free-list head |

If free_head is nonzero, the helper returns that identity, replaces free_head with
the first eight payload bytes and increments active_count modulo2^32. It does not
change page cursors or overwrite the popped payload's former next link.

Otherwise it uses the current page. If none exists, it sets page_index to the
current page count, requests `slots_per_page * 288` bytes with the stored alignment
and argument0x2c, and appends the returned page. A full page table requests capacity8
when empty or twice its previous capacity through a separate reserve service.
The helper returns `current_page + 288 * slot_index`, then increments the slot index.
At page exhaustion it selects the next registered page if available; otherwise it
clears current_page and page_index. Both cases reset slot_index to zero. Every
successful acquisition increments active_count.

These returned identities are raw slots. No owner/count/flag initialization occurs
in this routine. The batch supplier separately sets owner zero, active row count
zero and flag bit0 for nonnull slots. Separating these operations preserves reused
payload bytes until the actual initialization boundary.

[1024 complete original slot-acquisition comparisons](../../native/snow_host/pose_contact_pool_validation.json)
match returned identity, all56 pool-state bytes, retained page-table slots and free
payload bytes. They include358 page allocations and256 free-list cases. Page byte
sizes, alignment, allocation argument and reserve-capacity requests also match.
Page allocation and page-table reserve are supplied services. Positive page sizes,
valid metadata and successful allocation are fixture preconditions; capacity
overflow, allocation failure and synchronization are outside this receipt.

The independent API uses caller-supplied integer identities/page bases and payload
buffers. Page-table reserve is responsible for capacity and storage changes.
It rejects null allocation and uint16 capacity overflow as authored guards rather
than reproducing invalid memory access. Neither opaque identities nor passing
comparisons establish native pool ownership or a safe concurrent modding allocator.

### Payload batch initialization boundary

`pose_contact_pool.supply_payload_batch` connects repeated slot acquisition to the
reached batch core0x18de07c..0x18de1bb. It returns identities in acquisition order.
For each successful nonnull slot the original inlined pool code increments the
pool's active allocation count and then performs exactly three initialization writes:

```text
payload.flag_byte_114 |= 1
payload.owner_word_00 = 0
payload.active_count_110 = 0
output[next] = payload
```

All cached rows, feature IDs, cached-word bits, inactive padding and flag bits other
than bit0 survive. On the free-list path, the old first word is read as the next
link before owner initialization clears it. A batch of zero skips pool mutation
and output writes, but this does not imply that the enclosing native function skips
its entry/exit services.

[512 continuous original batch-core comparisons](../../native/snow_host/pose_contact_pool_batch_validation.json)
cover counts0..20, free-list prefixes, existing page traversal, fresh page allocation
and page-table growth. All56 pool bytes, retained table slots, every supplied288-byte
payload and output prefix/tail guards match. Allocator and table-reserve services
are supplied; new page bytes are arbitrary fixture state. The comparison runs the
original inlined acquisition and initialization loop without replacing those steps.

The enclosing function calls protected entry service0x3f253d5 before the reached
block and protected exit service0x3e278b9 after it. The loop reads the pool pointer
from global0x3336bb0; entry/exit use the adjacent holder at0x3336bb8. These are static
boundary observations. Their complete synchronization and lifetime contracts have
not been established by this batch comparison. The independent API therefore
requires caller-serialized pool access and does not invent a lock implementation.

`supply_payload_batch` can now be bound as the contact acquisition's ten-item batch
service when explicit pool state, page allocation, page-table reserve and payload
buffers are supplied. This is a serial reconstruction path. The existing JSON
inspector still uses preallocated payloads; it has not silently gained a native
pool allocator or concurrent game integration. Allocation failure and invalid/null
slots remain outside the successful-allocation domain inherited from slot acquisition.

### Paired-builder relative point motion

The metadata-set/single builder0x1992800 differs structurally from the previously
reconstructed metadata-clear/single family. It allocates128-byte primary/secondary
slots using context counters+0xa8/+0xc0 and bases+0x44/+0x5c. The clear family uses
112-byte rows and different counters. Reusing its row packing for this family
would overwrite the wrong layout.

`pose_link_paired_motion.paired_link_point_motion` reconstructs the first paired
row's offset-relative arms, world centers and relative point motion. For each body
with basis rows B0/B1/B2, translation T, local offset C, payload point P and raw
motion fields V=motion1a0 and W=motion1ac:

```text
rotate(x) = B2*x.z + (B0*x.x + B1*x.y)
center_world = T + rotate(C)
arm = rotate(P - C)
point_motion = cross(W, arm) + V
relative_motion = second.point_motion - first.point_motion
```

All multiplies, additions and subtractions retain the inspected float32 order.
The code uses both offsets and both motion pairs. The earlier single-family
helper projects opposite first-body motion; it must not be used as an equivalent
paired-body motion rule. Structural names remain because complete units and all
field producers are not established by this local formula.

[1024 original paired-builder prefix comparisons](../../native/snow_host/pose_link_paired_motion_validation.json)
execute entry0x1992800 through0x1992dce, including original profile combiners,
without interception. Both world centers, first point motion and relative point
motion match bit-for-bit in XYZ. Cases use general finite bases/translations,
both offsets, varied local points and zero/nonzero motion. Initialized vector
masks are supplied, and resource setup uses default profiles. Fourth SIMD lanes,
later tangent/response branches and complete paired row assembly are excluded.
The arm outputs follow the inspected intermediate arithmetic but are not separately
captured by this prefix receipt.

The public tests distinguish the two offsets, show common linear motion cancellation
and retain input storage. This begins reconstruction of the missing paired builder;
it does not yet connect terrain-generated payloads to paired solver iteration.

### Paired-builder tangent directions

`pose_link_paired_motion.paired_link_tangent_basis` continues the paired builder
through0x1992f86. Given the recovered relative point motion V and supplied normal N:

```text
projection = dot(V, N)
tangent = V - projection * N
if float32(dot(tangent,tangent) - float32(1e-6)) < 0:
    tangent = fallback_axis_perpendicular(N)
first = tangent * float32(1 / sqrt(dot(tangent,tangent)))
second = cross(N, first)
```

Each dot uses float32 pairwise `(x_product + y_product) + (z_product + 0)` order.
The normal is not normalized by this path. For fallback, let ax/ay/az be absolute
normal components. If `float32(min(ax,ay)-az)<0`, use `(z,0,-x)` when
`float32(ay-ax)<0`, otherwise `(0,z,-y)`. Otherwise use `(y,-x,0)`.
Strict comparisons preserve equality behavior; a zero resulting tangent is outside
the independent finite/nondegenerate domain.

The paired relative-motion fourth lane begins as positive zero. Its projection
subtraction therefore differs from the single-family helper's negated-motion lane.
The returned first_lane3 preserves that arithmetic; the second tangent's lane3 is
positive zero in the compared domain. Do not reuse a single-family helper by merely
negating its motion input if complete row bytes must agree.

[1024 original paired-builder prefix comparisons](../../native/snow_host/pose_link_paired_tangent_validation.json)
execute entry through both tangent directions, including original profile
combiners, without interception. Both four-lane tangents and earlier world-center/
relative-motion values match.205 cases take fallback; the others use projected
motion. The suite uses finite general frames/points and nonzero normals with
initialized masks and default profiles. Complete row assembly, subsequent response
selection and solver execution remain outside this receipt. Public tests cover
projection/cross direction, signed-zero lane and a threshold crossing.

### Connected paired single builder

`pose_link_paired_builder.build_paired_pose_link_rows` connects the complete
metadata-set/single family0x1992800. It shares inspected profile resolution and
coefficient arithmetic with the earlier family, but uses both body offsets/motions
and128-byte retained solver rows. Each payload row consumes one primary row, two
secondary rows and three sequential result indices. Native counters are+0xa8/+0xc0
for primary/secondary allocation and+0x180 for result indices.

For arms r1/r2, world-point separation D, normal N and paired relative-motion
projection q, the scalar response is the existing primary-response rule with q
supplied from both-body motion. Let H=float32(0.5*D), L1=r1+H, L2=r2-H and direction
U=-N. The row layout is:

| Field | Primary | Secondary for tangent T |
| --- | --- | --- |
| +0x00/+0x02 | body indices | body indices |
| +0x04 | primary result index | its own result index |
| +0x10 | selected response broadcast | dot(D,T)*0 in XYZ, FLT_MAX in W |
| +0x20 | U, negative-zero W | T with recovered W |
| +0x30 | cross(L1,U), zero W | cross(r1,T), zero W |
| +0x50 | eight zero bytes | cross(T,r2), zero W |
| +0x60 | cache-seeding gate broadcast | primary result index in first word |
| +0x70 | cross(U,L2), zero W | combined profile field30 broadcast |

Unwritten bytes remain untouched, including+0x40..0x4f in all rows, primary+0x58..0x5f
and secondary+0x64..0x6f. The payload publishes the primary result index in its
feedback field. A zero seeding gate broadcasts the raw cached word into that result;
a nonzero finite gate preserves the previous result bytes. This implementation does
not interpret arbitrary cached bits as a measured impulse or invent solver output.

[512 complete original paired-builder comparisons](../../native/snow_host/pose_link_paired_builder_validation.json)
execute entry to return with original profile helpers and no call interception.
Every retained128-byte row, unused row storage, complete payload, result buffer and
all three counters match. Cases cover0..4 payload rows, nonzero initial counters,
both-body motion, general finite frames, all six combination modes and both seed
branches. Runtime masks are supplied and resources use the default-profile branch.
Finite nonsingular arithmetic is required; indexed lookup has separate evidence.

The public tests cover retained padding, zero-row behavior, both seed outcomes,
second-body secondary angular storage, and builder-to-feedback composition with
an explicitly supplied result. The latter is not a solver integration test.

This closes the second of four dispatcher-selected builder families locally.
Metadata-clear/multi0x1991da0 and metadata-set/multi0x1991110 remain unimplemented
in this connected row-building API. Mode-driven family selection must remain
explicit; do not force single-family mode merely to avoid missing multi builders.

### Multi-row contact patch geometry

The metadata-clear/multi builder0x1991da0 allocates one208-byte shared constraint
using context base+0x50 and counter+0xb4. It also emits one112-byte primary row per
payload contact. This is not repeated single-family construction: the later shared
constraint uses aggregate contact geometry. Full shared-row semantics and packing
remain under reconstruction.

`pose_link_patch_geometry.contact_patch_geometry` reconstructs its centroid/spread
block0x19924a7..0x19925c4. Inputs are the first-body basis, its already transformed
local-offset center C, and1..4 local arms previously formed as point-offset128.
For each arm A, with float32 arithmetic after each operation:

```text
P = (B2*A.z + (B1*A.y + B0*A.x)) + C
sum_points += P
count_float += 1
inverse_count = 1 / count_float
centroid = sum_points * inverse_count
sum_distance = sum(length(P - centroid))
centroid_arm = centroid - C
spread = max(sum_distance, float32(0.001)) * inverse_count
```

The lower bound applies to the sum before dividing. Four coincident contacts
therefore yield spread0.00025, not0.001. This is neither a maximum radius nor an
unconditionally clamped mean. Preserve world-space addition/averaging before
subtracting C, since simplifying to an average local arm changes float32 results
at large translations. No physical unit or friction interpretation is assigned
from this arithmetic alone.

[2048 original block comparisons](../../native/snow_host/pose_link_patch_geometry_validation.json)
match every transformed world point, centroid-relative arm and spread, including
the zero fourth lane. Cases use general finite bases/world centers,1..4 arms,
coincident points and near-coincident points below the sum clamp. Basis registers,
local-arm scratch storage and initialized masks are supplied. The initial harness
attempt omitted live basis registers at block entry; supplying the inspected entry
state resolved that fixture failure without changing the recovered math.

The native dispatcher normally reaches this family only for count>1 with mode0;
one-contact cases test the local arithmetic domain. Zero contacts are rejected by
the independent helper rather than inventing a zero-divisor fallback. Prior primary
rows, later shared-row orientation/packing and full solver behavior are not covered
by this reached-block receipt.

### Shared patch orientation and packing

`contact_patch_basis` recovers the next block,0x19925b2..0x19927ca:

```text
direction = -normal
motion = linear_motion + cross(angular_motion, centroid_arm)
candidate = cross(direction, motion)
if every(abs(candidate.xyz) < float32(.001)):
    candidate = cross(direction, [1,0,0])
    if every(abs(candidate.xyz) < float32(.001)):
        candidate = cross(direction, [0,1,0])
first = candidate * (1 / length(candidate))
second = cross(direction, first)
first_angular = cross(centroid_arm, first)
second_angular = cross(centroid_arm, second)
spread_direction = direction * spread
```

Each arithmetic operation rounds to float32. The fallback gate tests individual
components, not vector length; equality does not trigger fallback. The supplied
normal is not normalized. Finite inputs, positive spread and a nonzero resulting
candidate are authored helper guards, not recovered exception behavior.

`pack_contact_patch_directions` preserves a supplied208-byte row except+0x10..0x7f.
It zeros+0x10..0x1f. For world axis j, row+0x20+16*j receives
`[first[j], second[j], 0, 0]`, and row+0x50+16*j receives
`[first_angular[j], second_angular[j], spread_direction[j], 0]`.

[2048 original block comparisons](../../native/snow_host/pose_link_patch_basis_validation.json)
match all208 retained bytes:1317 motion cases,614 X-axis fallbacks and117 Y-axis
fallbacks. The comparison supplies aggregate geometry and live-in registers and
executes the original block without interception. Shared coefficient/result/index
fields and the complete multi-family builder remain outside this validation.

### Connected multi builder

`pose_link_multi_builder.build_multi_pose_link_rows` reconstructs the complete
metadata-clear/multi routine0x1991da0. It uses the single-family profile and primary
response formulas, but allocates one208-byte shared row first, followed by one
112-byte primary row per contact. The shared row reserves the first result index;
each primary then reserves one index and writes it to payload row+0x34. The shared
result slot itself is left untouched by this builder.

```text
shared.result_index = allocate_result()
accumulated = float32(0)
for contact in payload order:
    primary.result_index = allocate_result()
    contact.feedback_index = primary.result_index
    accumulated = float32(accumulated + contact.cached_value)
    if seed_gate == 0:
        results[primary.result_index] = broadcast(contact.cached_value)
    primary.link50 = (address(shared + 0xb0) - address(primary)) >> 4
shared.value_b0 = broadcast(accumulated)
shared.coefficient_c0 = broadcast(combined_profile30)
```

The accumulation occurs even when the gate disables result seeding. The relative
link is a signed64-bit count of16-byte units, not an absolute pointer or a result
index. The independent API expresses arena addresses as explicit `primary_base`
and `shared_base` byte offsets, with row strides112 and208 respectively. Bases
must preserve16-byte alignment. The shared orientation uses the first contact's
normal and the aggregate centroid/spread described above. Shared+0x80..0xaf and
other unreached bytes retain their supplied contents.

[512 uninterrupted original calls](../../native/snow_host/pose_link_multi_builder_validation.json)
match every primary/shared row byte, complete payload and result buffers, and all
three counters. Cases cover1..4 contacts, nonzero initial counters, general finite
geometry, all six profile modes and finite cached values. Native profile combiners
execute without interception. Indexed resource lookup has separate evidence; this
receipt uses default profile resources. The normal dispatcher selects this family
for multiple contacts and mode0. The helper's one-contact arithmetic test does not
change that gate. Zero-count behavior, exceptional floating-point values, native
allocation, paired multi construction and a complete solver iteration are not
claimed by this contract.

### Connected paired multi builder

`pose_link_paired_multi_builder.build_paired_multi_pose_link_rows` reconstructs
metadata-set/multi routine0x1991110. Its shared row is256 bytes (context base+0x54,
counter+0xb8); primary rows are128 bytes (base+0x44,counter+0xa8). It reserves one
shared result index followed by one per contact, as in the clear multi family.
Primary+0x50 instead links to shared+0xe0, still in signed16-byte units. Shared+0xe0
holds the float32 sum of cached values; shared+0xf0 broadcasts combined profile30.
The reserved shared result slot remains untouched. Each primary uses the paired
single-family response and both angular terms, including its distinct+0x70 field.

The aggregate centroid and spread still come from the first body's contact points.
For centroid C, transformed offset centers C1/C2 and body motions V/W:

```text
arm1 = C - C1
arm2 = C - C2
motion1 = cross(W1, arm1) + V1
motion2 = cross(W2, arm2) + V2
candidate = cross(-normal, motion1 - motion2)
```

Selection, X/Y fallback and normalization follow the shared patch basis rules.
Let t1/t2 be the resulting directions and S=(-normal)*spread. The shared row stores
three transposed blocks, one four-float row per world axis j:

```text
+0x20 + 16*j: [t1[j], t2[j], 0, 0]
+0x50 + 16*j: [cross(arm1,t1)[j], cross(arm1,t2)[j], S[j], 0]
+0x80 + 16*j: [cross(arm2,-t1)[j], cross(arm2,-t2)[j], -S[j], 0]
```

Shared+0x10 is zeroed; unreached storage, including+0xb0..0xdf, is retained.
[512 uninterrupted original calls](../../native/snow_host/pose_link_paired_multi_builder_validation.json)
match all retained rows, payloads, result storage and counters. Coverage includes
1..4 contacts, all six profile modes, general finite frames/motion, zero motion and
X-aligned normals exercising Y fallback. Default resource profiles and retained
storage are supplied; native profile combiners execute. This completes local
implementations of all four dispatch families, but does not establish connected
dispatch execution, solver iteration, live lifetime or full-engine equivalence.

### Unified build

`pose_link_build.build_dispatched_pose_links` connects the recovered dispatcher to
all four concrete builders. The public context holds six retained pools:
`clear_primary`, `clear_secondary`, `clear_shared`, `paired_primary`,
`paired_secondary`, `paired_shared`. Each contains `rows`, `count` and `base` (byte
offset in a common abstract arena). Scalar context fields, result rows and the
result counter are shared across all families. Bodies, links, payloads, resources
and profiles are explicit mappings; no native heap pointer is required.

The adapter preserves separate family counters while publishing each builder's
updated global result count. Dispatch mode and metadata selection retain their
existing captured-per-link behavior. Multi and single builders of one metadata
family share the same primary pool. The API is nontransactional: if supplied
storage or input fails, already performed row/payload writes and consumed counters
are not rolled back. It does not allocate missing storage or force mode to select
a preferred builder.

[512 complete dispatch comparisons](../../native/snow_host/pose_link_unified_build_validation.json)
execute original0x1994970 and all four original builder bodies uninterrupted,
without recording-service substitutions. Every byte of six retained row pools,
all payloads, the shared result buffer and all seven counters matches. Cases mix
metadata families and1..4 contacts, all four context modes, disabled links/payloads,
nonzero starting counters and all six profile modes. Synthetic preallocated arenas
and default resource profiles are supplied. This proves the connected local build
stage in that domain, not row solving, body integration or live engine lifetime.

### Primary accumulator arena addressing

Connecting multi builders exposed a storage limitation in the earlier primary
solver helpers: row+0x50 was decoded unsigned and assumed to target bytes after the
row. Both builders can encode negative offsets when shared storage precedes primary
storage. Both primary iteration APIs now accept optional `arena` and `row_offset`
arguments. A row may be a writable view into that arena. Resolution is:

```text
slot = signed_int64(row + 0x50)
if slot != 0:
    target = row_offset + 16*slot
    arena[target] += updated_projected_result   # four float32 lanes
```

The addition uses the full newly projected result, not its difference from the old
result. Only body-state updates use that difference. With no arena supplied, the
row buffer remains the storage origin, preserving prior positive-link use. A
negative/out-of-bounds target is rejected explicitly instead of allowing Python's
negative indexing. The caller owns arena lifetime, row placement and aliasing;
this helper does not allocate, relocate or clear accumulators between sweeps.

[512 one-body comparisons](../../native/snow_host/pose_primary_arena_validation.json)
and [512 paired-body comparisons](../../native/snow_host/pose_paired_primary_arena_validation.json)
each execute original preparation and three iterations, with forward and backward
links. Entire arenas, body states and result buffers match after every stage.
These extend local primary solver evidence; shared-row solving and traversal
integration with arena-backed rows remain separate requirements.

### Shared patch iteration

`pose_shared_solver.iterate_pose_shared_row` reconstructs the complete one-body
shared208-byte row iteration0x19f1c20. It requires a prepared inverse response
matrix at+0x80/+0x90/+0xa0. Preparation0x19f1430 remains to be reconstructed.
The row uses its first body index and result index. Let L/A be the transposed
linear/angular blocks, K the supplied inverse response block and old the result:

```text
limit = row.coefficient_c0 * row.accumulator_b0
row.accumulator_b0 = [0,0,0,0]
speed = L * body.linear_state + A * body.angular_state
candidate = old + K * (-speed)
length = sqrt(candidate.x^2 + candidate.y^2 + candidate.z^2)
if all(limit.xyz < length):
    candidate *= limit / length
change = candidate - old
result = old + change
```

All operations retain float32 order. Each matrix/vector transform evaluates
`z*row2 + (y*row1 + x*row0)`. Projection uses a shared XYZ length, not independent
axis clamps; all three strict comparisons must hold. Limits scale each of four
lanes when the gate is taken. The final add-back is preserved rather than directly
storing candidate, because subtraction/addition can round differently.

Body linear change is formed by dotting each L world-axis row against
`body_data.mass_lanes * change`; angular change is the body tensor applied to the
three dot products of A rows with change. These dot products include all four lanes
and use pairwise summation. XYZ masks clear the assembled fourth component before
state addition. No universal physical meaning is assigned to arbitrary fourth lanes.

[512 cases,1536 uninterrupted original iterations](../../native/snow_host/pose_shared_iteration_validation.json)
match all208 row bytes, all body-state/result lanes and unchanged body data after
each iteration. The accumulator reset means a repeated iteration without primary
reaccumulation has zero limits; the caller must preserve native traversal order.
Inputs are finite synthetic prepared rows with supplied K. This establishes local
iteration, not matrix preparation, paired shared solving or system convergence.

### Shared patch preparation

`pose_shared_solver.prepare_pose_shared_row` reconstructs0x19f1430, including
matrix inversion helper0x19c9530. Its output supplies the inverse response used by
the preceding iteration section. Using the builder's transposed blocks L/A and
body tensor T, the response is formed from a linear mass contribution and an
angular tensor contribution. Exact float32 construction, with rows treated as
four-lane vectors and `transform(R,v)=R2*v.z+(R1*v.y+R0*v.x)`, is:

```text
weighted_linear[j] = transform(L, axis[j] * body_mass_lanes)
K[i] = transform(weighted_linear, column(L,i))
weighted_angular[j] = transform(A, T[j])
K[i] += transform(weighted_angular, column(A,i))
K[0] *= [1,1,0,0]
K[1] *= [1,1,0,0]
K[2] *= [0,0,1,0]
r = 1 / length(K[2].xyz)
K[2] = (K[2] * r) * body_mass_lanes
inverse = cofactor_inverse(K)
inverse[2] = [0,0,r,0]
```

Thus coupling to the third component is removed before inversion. The third
inverse row is then overwritten with its separately computed reciprocal. The
cofactor inverse retains cross-product, pairwise determinant sum and reciprocal
multiplication order; an ordinary high-precision matrix library can change bytes.
The builder's cached result is applied to body state using the same linear/tensor
mapping as iteration, and shared+0xb0 is cleared. Result storage itself is retained.

[512 original preparation plus1536 iteration comparisons](../../native/snow_host/pose_shared_preparation_validation.json)
match all row bytes, body states and result lanes after every stage. Original
inversion executes without interception. Cases include finite general row blocks
and diagonally dominant body tensors with off-diagonal terms. Singular response
or zero third response is rejected by the independent helper; this is an authored
guard, not recovered native recovery. Paired shared preparation and integration
into full traversal remain outside this receipt.

### Paired shared patch iteration

`pose_paired_shared_solver.iterate_pose_paired_shared_row` reconstructs complete
iteration0x19f19d0 and relative-state helper0x19f18c0. Its256-byte row has linear
block L at+0x20, first angular block A1 at+0x50, second angular block A2 at+0x80,
prepared inverse block K at+0xb0, accumulator+0xe0 and coefficient+0xf0.
With operation order preserved:

```text
speed = transform(L, linear1) + transform(A1, angular1)
speed = speed - transform(L, linear2)
speed = speed + transform(A2, angular2)
correction = transform(K, speed)
candidate = -correction + old_result
```

Negation occurs after the inverse transform, unlike the one-body implementation's
negated transform input. Projection uses the same coupled XYZ-length/all-three-
strict-limits gate; the accumulator is cleared and the result is stored as
`old + (projected - old)`. Both bodies receive tensor-mapped angular changes from
their own angular blocks. Linear changes use opposite signs and each body's mass
lanes. All intermediate operations round to float32.

The original writes the first body's linear and angular state, then reads and
updates the second body's state. Coincident indices therefore accumulate both
updates sequentially. This differs from the paired primary solver's captured-state
second-write-wins behavior; its update helper must not be reused here.

[512 complete calls repeated three times](../../native/snow_host/pose_paired_shared_iteration_validation.json)
match all256 row bytes, all state/result lanes and unchanged data, including
random coincident body indices. Inverse response matrices are supplied finite
synthetic inputs. Paired preparation and connected traversal remain unvalidated.

### Paired shared patch preparation

`pose_paired_shared_solver.prepare_pose_paired_shared_row` reconstructs0x19f0b70
and its original inversion helper. It builds the inverse response at+0xb0/+0xc0/
+0xd0 for the256-byte paired shared row. Contributions are accumulated with float32
rounding in the order `linear(body1), angular(body1), linear(body2), angular(body2)`.
Each contribution uses the transform/transpose construction in "Shared patch
preparation". The same L block is used for both linear contributions; each body's
angular contribution uses its own A block and body tensor.

The first two response rows are masked to XY and the third to Z. The third row is
normalized by its XYZ length, then multiplied by `mass2 + mass1` before cofactor
inversion. After inversion its third row is replaced by `[0,0,1/length,0]`, retaining
the original operation order. Singular rejection is an authored helper guard.

Preparation clears shared+0xe0 and applies the cached result to both bodies: first
linear/first angular, then opposite second linear/second angular. Coincident body
indices therefore accumulate sequentially, matching iteration. Result storage is
not changed by preparation.

[512 preparations and1536 subsequent iterations](../../native/snow_host/pose_paired_shared_preparation_validation.json)
match complete rows, all body-state/result lanes and unchanged data after every
stage. Original preparation, inversion and iteration execute without interception.
Cases include general finite row blocks, off-diagonal body tensors and coincident
indices. Both shared families now have local preparation/iteration implementations;
full mixed-category traversal remains a separate validation requirement.

### Connected six-category solver traversal

`solve_pose_link_rows` now supports categories0/1 (primary),4/5 (shared) and6/7
(tangent), using their explicit traversal counts. Preparation and each normal
iteration execute in order: paired primary, one-body primary, paired shared,
one-body shared, paired tangent, one-body tangent. Special phase skips shared and
tangent categories. Primary rows still accumulate in that phase; callers must not
infer accumulator clearing merely from a completed wrapper call.

Optional `arena` storage is addressed relative to the context origin. Primary row
locations derive from context+0x16c plus16 times their category start, plus their
112/128-byte row stride. Caller-provided row views and arena must describe the same
retained storage. Shared row views then observe primary accumulation directly.
Absent arena preserves earlier standalone-row behavior. No rows, counts or results
are silently allocated or inferred from builder counters.

[256 uninterrupted six-category wrapper comparisons](../../native/snow_host/pose_six_category_solve_validation.json)
execute original0x1994e80 and every reached numerical routine without interception.
All context/row bytes, body state and results match across four phase masks and
zero through three iterations. Both primary families point into their shared
accumulators. The fixture supplies retained rows; this receipt does not yet execute
builders before solving or establish complete group lifecycle/convergence.

### Arena composition

`pose_link_arena.build_and_solve_pose_links` connects all four builders and the
six-category solver using caller-owned retained storage. Arena origin is the
solver context. Existing layout fields and planned traversal counts define row
views and result slots. Append counters and global result numbering are read from
the header and written back after building. Primary links and shared accumulators
therefore address the same bytes consumed during solving; no repacking is needed.

The API requires an initialized layout and valid counts. The separately recovered
`count_pose_link_rows`, `plan_pose_solver_layout` and
`initialize_pose_solver_storage` can supply those stages. It does not infer a new
count policy or allocate storage. Body data/state mappings remain explicit; callers
may supply writable views into the same arena. Body-index assignment, production
of body data, integration into position/orientation and group lifetime remain
external responsibilities. Failed building is nontransactional and publishes
consumed counters before propagating the error.

[256 original builder-to-solver comparisons](../../native/snow_host/pose_link_arena_composition_validation.json)
run original dispatch0x1994970 followed by original solver wrapper0x1994e80 with no
interception. The reconstruction matches every byte of the retained arena, including
all six row families, counters, result slots, body data/state and unused ranges,
plus complete payloads. Fixtures mix metadata families,1..4 contacts, modes0..3,
disabled gates and profile combination modes. Layout/body data are supplied and
counts come from the independent prepass. This is a connected contact build/solve
comparison, not a complete physics tick or full-engine equivalence claim.

### Contact pass with feedback

`pose_link_arena.run_pose_contact_pass` extends arena composition with the recovered
post-solve sequence: link cache feedback, then body motion feedback. The existing
context bit29 controls copying each primary result's first lane into its payload
cache versus clearing that cache. Body feedback copies solved linear/angular XYZ
into raw body+0x1a0/+0x1ac, preserving all other bytes. It does not integrate a new
position or orientation.

Callers supply raw body records and body token order matching solver state indices,
in addition to the parsed builder inputs. Those representations must describe the
same retained input state. This adapter intentionally does not invent body-index
assignment, membership validation or live-memory ownership. It also does not set
group phase flags, build pose constraints, run the secondary correction phase or
execute poststep; it is an explicit contact-only composition.

[256 native composed passes](../../native/snow_host/pose_contact_pass_validation.json)
run original dispatch, solve, link feedback and body feedback without interception.
Every arena byte, complete payload and complete raw body record matches. Cases
cover cache-copy and cache-clear flags, both metadata families, contact counts and
builder modes. Body data/state and layout are supplied, so this does not yet prove
a complete group step or physical position/orientation integration.

### Contact pass from body fields

`pose_link_arena.run_pose_contact_pass_from_bodies` prepends recovered body-buffer
production to the contact pass. Bodies combine the builder's frame and motion
fields with `tensor170`, `scalar124`, `metadata_flags52`, `flagsaa` and optional
`damping1b8`. Frame basis is passed to the existing producer. Scalar/vector inputs
remain explicit; no gravity unit or simulation timestep is inferred by the adapter.
Produced64-byte data and32-byte state records are written into the initialized
arena and exposed as writable views to the build/solve/feedback stages.

The supplied body order must match `index1c`; mismatch is an authored API error.
No body-index repair or membership change occurs. Reached damping still requires
an explicit `damping_response` service. There is no guessed power approximation.

[256 native five-stage comparisons](../../native/snow_host/pose_body_contact_pass_validation.json)
execute original body-buffer production, building, solving, cache feedback and
body feedback without interception. Every arena, payload and raw-body byte matches.
Fixtures include fixed-body metadata and external-increment gates, both metadata
builder families and mixed contact counts. Damping is disabled and tensor-getter
TLS/static state is initialized by the private harness. This composes already
recovered local operations; complete group phases, pose constraints, secondary
correction, poststep and position/orientation integration remain separate.

### Contact secondary correction composition

`solve_pose_contact_secondary_correction` connects the recovered group's secondary
phase gate/transition to row refresh and special-phase solve. If context flags have
no bits in0x07ff0000 it returns false without mutation. Otherwise it clears bit27,
sets bit28, zeroes the retained state range from context+0x174 to+0x178, refreshes
both primary families, publishes their reset append counters, and runs the solver.
Refresh clears primary accumulator links and primary result slots while preserving
geometry. Special traversal skips shared and tangent rows. The corrected state is
left in the arena for an explicit subsequent body-update operation.

Body data/state arguments must be views into that arena. Layout and primary rows
must already correspond to the supplied links. The adapter does not apply correction
to transforms, repeat cache/body feedback, or run poststep. Zero contacts are valid;
malformed/out-of-range retained state spans are rejected by authored guards.

[256 composed native comparisons](../../native/snow_host/pose_contact_secondary_composition_validation.json)
cover body production, first build/solve/feedback, then secondary refresh/solve for
zero through three secondary iterations. Every arena, payload and raw-body byte
matches. Original numerical routines execute without interception. The harness
explicitly performs the previously recovered group flag transition and state clear;
the complete original group routine is not executed. Its earlier fixture placed
results before state, which is valid for first-pass-only tests but not this clear
range; the composition fixture now uses state-before-results layout. Damping and
secondary transform application remain outside this comparison.

### Contact correction through transform update

`correct_pose_contact_transforms` composes secondary contact refresh/solve with the
recovered temporary-state wrapper and constructor-selected body integrator. The
caller explicitly selects this supported body implementation; the API does not
claim general virtual dispatch for every body class. It supplies correction XYZ
as temporary motion, calls the transform update with scalar1, and restores the
original24 motion bytes on normal return. Corrected basis/translation persist.
Parsed builder body snapshots remain unchanged and must be refreshed before reuse.

General angular correction still requires `half_angle_trig`. Zero-angular cases
need no trigonometric service. Exception-safe restoration is not invented: the
existing wrapper's contract covers normal returns. Group poststep remains separate.

[256 composed transform comparisons](../../native/snow_host/pose_contact_transform_composition_validation.json)
execute native body production, contact building/solving/feedback, secondary
refresh/solve and actual constructor-selected virtual transform updates. All arena,
payload and raw-body bytes match. Observation hooks record317 original sine/cosine
pairs; the independent integration requests identical half-angles and replays those
responses. Native execution is not intercepted. This proves the composed arithmetic
and service boundary, not an independently recovered transcendental library.
Damping is disabled and group phase transitions/clears remain explicit harness work;
complete original group/poststep execution and live class coverage are not claimed.

### Scalar trig

`pose_scalar_trig.small_angle_sin_cos` independently reconstructs the dispatch-zero
finite small-angle branches of scalar sine0x1c808c0 and cosine0x1c803c0. Input is
rounded to float32, promoted to binary64 for polynomial evaluation, then rounded
back to float32. Domain is `abs(float32(x)) <= binary64(pi/4)`. The float32 value
nearest pi/4 lies slightly above that boundary and enters native range reduction;
the largest admitted positive encoding is0x3f490fda.

Sine returns x below2^-13, uses `x - (x*x*x)/6` with inspected multiplication order
below2^-7, then the inspected degree-nine polynomial. Cosine uses its degree-ten
polynomial. Exact binary64 coefficient encodings and evaluation order are in the
module; it does not call host sine/cosine or fuse operations. The tiny sine path's
floating-point status side effects are not modeled, but signed result zero is.

[8214 input pairs /16428 complete original calls](../../native/snow_host/pose_scalar_small_trig_validation.json)
match float32 output bits with no interception, including both signs, subnormals,
threshold neighbors and random encodings through the supported interval. This
helper can be explicitly supplied as `half_angle_trig` to body integration and
contact correction; bounded angular integration can now run without observed
responses. Larger-angle reduction, nonfinite handling, floating-point flags and
alternate CPU dispatch remain unresolved. Unsupported inputs raise an authored
error rather than silently selecting a different math library.

### Scalar trig range reduction and independent composition

`pose_scalar_trig.scalar_sin_cos` extends the independent dispatch-zero pair to
`abs(float32(x)) < 500000`. Above pi/4 it reduces the absolute input by the nearest
multiple of pi/2, using inspected binary64 split constants:

```text
n = truncate(abs(x) * inverse_pi_over_two + 0.5)
head = abs(x) - n * pi_over_two_high
reduced = head - n * pi_over_two_tail
if exponent(abs(x)) - exponent(reduced) > 15:
    next_head = head - n * tail_high
    error = (head - next_head) - n * tail_high
    reduced = next_head - (n * tail_low - error)
```

The initial reduced exponent selects tiny/cubic/full-polynomial branches even
when cancellation correction runs. Quadrant and input sign select sine versus
cosine polynomial and final sign. All split constants, binary64 operation order
and final float32 conversion are explicit in the module. No host trig is used.

[16508 input pairs /33016 original calls](../../native/snow_host/pose_scalar_reduced_trig_validation.json)
match output bits, including cancellation neighbors near multiples of pi/2 and the
largest float32 below500000. An initial wider-domain comparison failed in cosine;
inspection established its500000 large-reducer threshold versus sine's16000000.
The paired API therefore rejects the wider unsupported interval. The failure was
a domain assumption, not repaired by tuning polynomial coefficients.

[256 complete contact/transform compositions](../../native/snow_host/pose_contact_independent_trig_validation.json)
now match all arena, payload and body bytes with317 independently computed trig
pairs. Native observation hooks check requested arguments only; no observed result
is fed to the reconstruction. This supersedes the trig-replay limitation of the
previous composition receipt for these cases. Damping remains disabled, getter
initialization is supplied, and complete group/poststep/live lifetime remain open.
Large-argument reduction, alternate CPU dispatch, nonfinite handling and status
flags remain outside the scalar API contract.

### Contact inspector

Run the independent contact pipeline without an executable or private harness:

```sh
python3 -m engine.pose_contact_bench engine/examples/pose_contact_pass.json --output result.json
```

Schema `pose-contact-pass-v1` takes explicit provenance, ordered body/link tokens,
retained raw body/payload hex, symbolic resource/profile mappings, metadata fields,
context controls and body scalar/external vector. The authored adapter plans and
zero-initializes an arena using recovered count/layout helpers, produces body
buffers, builds and solves contacts, writes feedback and applies gated secondary
correction using independently recovered scalar trig. Input documents are copied,
not mutated. Raw body indices must match supplied order; damping is rejected rather
than approximated. Bounds on bodies, payload visits and iterations are authored
inspection limits, not native limits.

Output separates before, first-pass motion and post-correction transforms. It also
includes all six row pools, results, payloads and raw bodies as exact bytes. The
included two-point patch is authored synthetic data, not a native capture or a
calibrated rider model. It demonstrates shared-row construction and correction
without implying terrain generation, walking, skiing or a complete game tick.
Contacts and membership are supplied; pose constraints, damping and group poststep
remain outside the CLI. This adapter composes the individually and jointly validated
operations above; it is not itself an original engine entry point.
