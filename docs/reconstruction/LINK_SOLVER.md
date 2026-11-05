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

## Integrated group poststep

`engine/pose_group_poststep.py::poststep_integrated_pose_group` connects the recovered
poststep ordering to the constructor-selected inactive transition, body integration
and resource bounds refresh. It checks quiet state first when enabled. An inactive
group skips both integration and bounds. An active group integrates its captured
body span, then reloads the span for bounds refresh. Bounds therefore use the
updated transform. Zero-resource bodies publish point bounds at that translation.

The caller supplies retained body/metadata identity maps, resource entries and local
transforms, link release, resource-specific bounds and half-angle trig. The existing
box bounds and scalar trig implementations satisfy the latter two services for
their supported domains. Quiet metadata and bounds metadata must share storage
when their native identities coincide. This is in-place composition, without
invented rollback or concurrent lifetime protection.

[Integrated validation](../../native/snow_host/pose_group_integrated_validation.json)
runs384 uninterrupted original poststeps offline. It includes actual integration,
scalar trig and box virtual bounds calls, with no interception or response replay.
All group, body, metadata, entry-array, transform and resource bytes match for137
active and247 inactive outcomes. Fixtures use zero through five bodies and zero
through two box resources per body. Public tests check updated-transform bounds,
quiet suppression and zero-resource point bounds.

This supersedes the supplied integration/refresh boundary of the earlier poststep
orchestration comparison for these tested classes. Link rings are empty in this
composition receipt. Nonempty payload release, other body/resource classes, live
reactivation, broadphase publication and complete group solving remain separate
boundaries. Synthetic comparison is not evidence of an entire original game tick.

## Pose constraint feedback

`engine/pose_constraint_feedback.py` reconstructs routine0x1994080, the pose
feedback stage after body and contact feedback. Each endpoint's metadata byte52
bit0 suppresses the constraint; the second endpoint may be null. Eligible entries
receive a virtual kind query. Only kind2 proceeds, and the array slot is reloaded
after that query. Getter0x1942bf0 returns the constraint's inline configuration at70.

The result format depends on configuration. All three words at constraintf0/104/118
must be bitwise zero, and none of the floats atfc/110/124 may compare below the
float32 threshold999999995904. Then index190 selects one16-byte result and its
XYZ words copy to19c/1a0/1a4. Otherwise indices190/194/198 independently select
result records, copying each record's first word to the corresponding destination.
Each indexffffffff preserves the old destination. Negative zero is nonzero for
the configuration-word gate. Unordered float comparisons do not select the
below-threshold branch. Output copies preserve raw bits without float conversion.

Result records start at context plus the unsigned offset at178. The public API
uses retained byte storage, explicit body/metadata identities and a required
virtual type-query service. It does not infer constraint type from layout.

[Feedback validation](../../native/snow_host/pose_constraint_feedback_validation.json)
compares512 offline original calls. All retained bytes and ordered kind queries
match. Only the virtual kind response is supplied; the original feedback and
inline getter execute. Public tests cover packed bit preservation, signed-zero
configuration, scalar sentinel preservation, disabled endpoints and slot reload.
Floating-point exception flags, row generation, numerical constraint solving and
live object lifetime are outside this result.

The adjacent pose builder0x19948d0 uses the same endpoint gates, then invokes
0x19905f0. That helper dispatches virtual kinds1 through6 to six builders.
These are concrete leads for the remaining non-contact constraint producers;
feedback recovery alone does not implement those builders or their solvers.

## Command constraint rows

The jump table in0x19905f0 establishes the following kind-to-builder mapping.
These numeric kinds are observed dispatch values, not assigned physical names.

| Kind | Builder RVA |
| --- | --- |
| 1 | 0x19e7f20 |
| 2 | 0x19e5da0 |
| 3 | 0x19e7580 |
| 4 | 0x19e7290 |
| 5 | 0x19e8350 |
| 6 | 0x19e9510 |

`engine/pose_constraint_commands.py::build_pose_command_constraint` reconstructs
kind4 and expansion helper0x19e7360. It appends a912-byte category24 row, using
context104 as the append count, contexta0 as the base in16-byte units and
context16c as the arena offset. It increments that count and global result count180,
then writes the old result index into row4. The first body's ushort1c supplies
row0; the second supplies row2, or zero when absent. Constraint70 copies to row20,
and signed command count74 copies to row24.

Each inline64-byte command at constraint78 expands to128 bytes at row30 onward.
The first48 source bytes hold four XYZ triples. Each becomes an XYZ0 vector.
A nonzero constraint59 byte changes their order from0,1,2,3 to2,3,0,1. The final
four source words each broadcast to all four lanes of one vector. Copies preserve
raw bits. Nonpositive counts still reserve the row/result and publish the header,
but do not expand commands. Untouched row bytes and the reserved result remain
unchanged. The native return byte is1.

The independent API admits at most six commands to fit the retained row. This
is an authored bounds guard; the native helper does not clamp its signed count.
It does not establish which higher-level producer constrains that count.

[Builder validation](../../native/snow_host/pose_command_constraint_validation.json)
compares512 complete original builder calls, including getters and expansion,
without interception. Entire context arenas, source constraints, bodies and return
bytes match. Fixtures cover negative through six counts, both orders, arbitrary
source bits, null second bodies and nonzero existing counters. Category24 numerical
preparation/iteration and the physical meaning of the command fields remain open.

## Command constraint solving

`engine/pose_command_solver.py` implements category24 preparation0x19f2180,
impulse application0x19f2330 and iteration0x19f2430. The normal solver traversal
processes these912-byte rows first; the special phase skips them. The scalar
result index reserved by the builder is not read by these numerical routines.
Each command instead retains its own four-lane impulse at command-relative70,
which is rowa0 for command0.

For each enabled endpoint, let L and A be the command's linear and angular XYZ
coefficients, M the body's four-lane inverse-mass data and T its three tensor
columns. Preparation computes the denominator in this order:

```text
D = dotXYZ(T1*A1, A1) + dotXYZ(L1, M1*L1)
if row20 == 0:
    D = D + dotXYZ(L2, M2*L2)
    D = D + dotXYZ(T2*A2, A2)
inverse = [-1/D, -1/D, -1/D, 0]
apply(cached_impulse)
```

All products and additions round to float32, including the tensor multiply and
pairwise XYZ dot reductions. Row20 nonzero suppresses the second endpoint.
The inverse goes to row330 plus16 times command index. Impulse application updates
linear state by `L * (M * impulse)` and angular state by `T * (A * impulse)`.
It writes the first endpoint before reading/updating the second. Coincident body
indices therefore accumulate both effects. Fourth state lanes are retained and
updated by this helper, rather than universally masked away.

Iteration computes `speed = dotXYZ(A1,w1) + dotXYZ(L1,v1)`, then adds the second
linear and angular contributions in that order when enabled. Per lane:

```text
candidate = inverse * (speed - target) + cached_impulse
projected = max(min(upper, candidate), lower)
delta = projected - cached_impulse
apply(delta)
cached_impulse = cached_impulse + delta
```

The target, lower, upper and cached values are command-relative40/50/60/70.
The final addition is retained rather than replaced with assignment of projected,
because its rounding can differ. SSE min/max operand order is preserved for ties.
Finite, nonsingular inputs and at most six commands define the independent API's
supported domain; exceptional arithmetic is rejected rather than approximated.

[Command solver validation](../../native/snow_host/pose_command_solver_validation.json)
compares512 preparations and1536 iterations, without interception. All row,
body-data and body-state bytes match after every call. Cases include off-diagonal
tensor entries, nonzero fourth lanes, coincident indices and cached impulses.
These formulas identify a bounded impulse solve. They do not yet identify which
player/animation producers populate the commands or establish full group fidelity.

## Mixed command and contact traversal

`solve_pose_link_rows` now accepts `command_rows` alongside the six recovered
contact row families. Category24's traversal count is context168, independently
of builder append count104. Normal preparation and every normal iteration visit
commands first, followed by paired-primary, clear-primary, paired-shared,
clear-shared, paired-tangent and clear-tangent rows. The special phase omits
commands, shared rows and tangents, retaining the primary rows. Other populated
categories still raise an explicit unsupported-category error.

[Mixed traversal validation](../../native/snow_host/pose_seven_category_solve_validation.json)
compares256 uninterrupted original wrapper calls with all seven categories
populated. All context, row, body-state, body-data and result bytes match across
four phase masks and zero through three iterations. Command rows share body
indices with contact rows, so their effects feed into later contact processing.
Builders are outside this comparison; rows are synthetic retained inputs.

Public tests verify normal command effects without a result-array entry, special
phase preservation and traversal-count independence from append counts. The API
name is retained for existing callers. This extends the connected numerical
slice; it does not supply the other18 categories or complete group lifecycle.

## Paired angular increment solver

`engine/pose_paired_angular_solver.py` reconstructs category13 preparation0x19f0630
and iteration0x19f0930. Normal traversal visits its80-byte rows immediately after
command rows; the special phase skips it. Body indices occupy the first two
ushorts; result index is row4. Row10 stores XYZ response and one scalar increment
limit. Row20/30/40 become the inverse response matrix during preparation.

For each matrix column, preparation adds the first body's diagonal mass component
to its tensor column, adds the second body's diagonal component, then adds the
second tensor column. It inverts the resulting3x3 matrix through the recovered
cofactor helper0x19c9530. Every operation retains float32 rounding. In exact-real
notation only, this is `K = inverse(T1 + diag(M1) + diag(M2) + T2)`.
The mass contribution is observed arithmetic; its physical interpretation for this
angular-only update is not inferred here. Cached result XYZ then updates angular
state by `w1 += T1*cached` and `w2 -= T2*cached`. Linear states do not change.

Iteration performs:

```text
error = response.xyz + (w1 - w2)
increment = clamp(-(K * error), -response.w, response.w)
result = old_result + increment
w1 = w1 + T1 * increment
w2 = w2 - T2 * increment
```

The bound applies to the current increment, not the accumulated result. Multiple
iterations can therefore grow the total beyond that bound. First-body writes
precede second-body reads, including coincident indices. The result retains all
four lanes; tensor multiplication uses XYZ inputs and updates all four angular
state lanes. Inverse columns have a zero fourth lane. Finite nonsingular inputs
define the independent domain; exceptional arithmetic is not substituted.

[Paired angular validation](../../native/snow_host/pose_paired_angular_validation.json)
compares512 preparations and1536 iterations, including the original matrix inverse,
without interception. All row, data, state and result bytes match. Fixtures include
off-diagonal tensors, coincident indices and nonzero fourth lanes. Public tests
verify accumulation beyond the increment cap, opposite updates on the same body
and explicit singular rejection. The row builder, gameplay owner and connection
to the public mixed traversal remain unfinished.

## Single angular increment solver

`engine/pose_angular_solver.py` reconstructs category12 preparation0x19f07c0 and
iteration0x19f0a80. Row layout matches category13, but the second body index is
unused. Preparation first forms `A = T + diag(M)` in float32. It computes
`trace = (A00 + A11) + A22`, obtains `s = 1/trace`, scales the matrix XYZ lanes
by s and clears its fourth lanes, inverts that normalized matrix, then scales
the inverse XYZ lanes by s again. The inverse therefore corresponds to A's
inverse in real arithmetic, but replacing the normalization sequence with direct
inversion would change float32 results. The cofactor implementation is shared
with the paired solver; the paired receipt was rerun after that refactor.

Cached impulse updates only this body's angular state through its tensor.
Iteration uses `error = angular_state + response.xyz` followed by the same
negative matrix response and symmetric per-increment clamp as category13.
It adds the increment to the retained result and applies `T * increment` to
angular state. Linear state and the unused second body remain untouched.

[Single angular validation](../../native/snow_host/pose_angular_validation.json)
compares512 preparations and1536 iterations with all retained bytes matching,
including off-diagonal tensors and nonzero fourth lanes. Nonfinite inputs, zero
trace and singular normalized matrices are explicit unsupported arithmetic.
Gameplay ownership and row production are not established by this solver result.

## Nine-category numerical traversal

`solve_pose_link_rows` now accepts `angular_rows` and `paired_angular_rows` for
categories12 and13. Their traversal counts are context138 and13c. In normal
preparation and iteration, supported categories execute in this order:
24,13,12,1,0,5,4,7,6. The special phase skips both angular categories along with
commands, shared rows and tangents. Other populated categories remain rejected.

[Nine-category validation](../../native/snow_host/pose_nine_category_solve_validation.json)
compares256 uninterrupted native wrapper calls with all nine categories populated,
sharing body-state storage. Context, all rows, body data/state and results match
across four phase masks and zero through three iterations. Builders are outside
this comparison. Sixteen categories and the full group lifecycle remain open.

## Reused primary kernels in constraint categories

The original preparation traversal0x19e4710 calls the same paired primary kernel
0x19e5310 for categories9 and1, and the same clear primary kernel0x19e55d0 for
categories8 and0. Iteration traversal0x19e4d10 likewise reuses0x19e5840 and0x19e5710.
This establishes identical numerical kernels, not identical row producers or
physical meaning. Category9 rows are128 bytes; category8 rows are112 bytes.

`solve_pose_link_rows` now accepts `paired_constraint_primary_rows` and
`constraint_primary_rows` for categories9 and8. Their traversal counts are
context12c and128; their arena bases are context64 and60 in16-byte units.
Both run after angular rows and before the contact primary rows in normal phase.
Unlike categories1/0, categories9/8 are skipped during the special phase.
The recovered kernels retain nonnegative result projection and signed relative
accumulator links, including links to storage preceding the current row.

[Eleven-category comparison](../../native/snow_host/pose_eleven_category_solve_validation.json)
runs256 uninterrupted original wrappers with categories24,13,12,9,8,1,0,5,4,7,6
populated. Every retained buffer matches across all four phase masks and zero
through three iterations. Category8/9 fixtures link backward to shared accumulators
and share body state with other families. Public tests distinguish normal execution
from the special-phase skip and reject missing row storage. Fourteen numerical
categories, their unresolved producers and complete group composition remain open.

## Paired point solver

`engine/pose_paired_point_solver.py` reconstructs category11 preparation0x19efa40
and iteration0x19f0270 for176-byte rows. "Point" is our descriptive module name,
not a recovered class name. Row20/30/40 form the first angular coefficient matrix
A; row80/90/a0 form the second B. Preparation writes an inverse response into
row50/60/70. Row10 holds XYZ response and a scalar increment limit.

Preparation starts with diagonal first-body mass, adds the contribution from A
and the first tensor, then diagonal second-body mass, then the B/tensor
contribution. In exact-real notation:

```text
K = inverse(diag(M1) + A*T1*transpose(A)
            + diag(M2) + B*T2*transpose(B))
```

The implementation retains each float32 multiply/add and uses the recovered
cofactor inverse. This compact expression does not replace the required operation
order. Cached result is applied before iterations. Per iteration:

```text
error = ((A*w1 + v1) - v2) + B*w2 + response.xyz
increment = clamp(-(K*error), -response.w, response.w)
result = old_result + increment
v1 += M1*increment
w1 += T1*transpose(A)*increment
v2 -= M2*increment
w2 += T2*transpose(B)*increment
```

Angular application uses four-lane dot products against the stored coefficient
columns, then clears the torque's fourth lane before tensor multiplication.
Linear updates retain all four lanes. Endpoint writes occur sequentially, so
coincident body identities retain both reached updates. As with the angular
families, the limit caps each increment, not the accumulated result.

[Paired point comparison](../../native/snow_host/pose_paired_point_validation.json)
compares512 preparations and1536 iterations, including the original matrix inverse,
with no interception. Every row, body-data/state and result byte matches. Fixtures
include general coefficient matrices, off-diagonal tensors, nonzero fourth lanes
and coincident indices. Public tests check opposite linear updates, coefficient-led
angular signs, cached application and singular rejection. Finite nonsingular
inputs are supported. Row construction, gameplay ownership and mixed traversal
integration remain separate work.

## Single point solver

`engine/pose_point_solver.py` reconstructs category10 preparation0x19eff60 and
iteration0x19f04e0 for128-byte rows. The first body's linear and angular state
participate; the second index is unused. Coefficient matrix A occupies row20/30/40,
and the inverse response occupies row50/60/70. Its pre-inversion matrix is
`diag(M) + A*T*transpose(A)` in exact-real notation. Preparation retains the
float32 multiplication order, divides the matrix by its trace, uses the recovered
cofactor inverse and scales the inverse by the reciprocal trace again. Direct
inversion without that normalization is not an interchangeable float32 path.

Cached result applies `v += M*cached` and `w += T*transpose(A)*cached`.
Iteration uses the recovered formulas:

```text
error = response.xyz + (A*w + v)
increment = clamp(-(K*error), -response.w, response.w)
result = old_result + increment
v += M*increment
w += T*transpose(A)*increment
```

The same four-lane dot, XYZ torque mask and per-increment cap conventions as the
paired version apply. The second body need not exist in the retained map.
[Single point validation](../../native/snow_host/pose_point_validation.json) compares
512 preparations and1536 iterations with all bytes matching, including the
original inverse routine, general coefficients and off-diagonal tensors.
Nonfinite, zero-trace and singular arithmetic remain explicitly unsupported.

## Thirteen-category numerical traversal

`solve_pose_link_rows` accepts `point_rows` and `paired_point_rows` for categories10
and11, using context130 and134 traversal counts. The normal supported order is
24,13,12,9,8,11,10,1,0,5,4,7,6. Special phase skips both coupled families.

[Thirteen-category comparison](../../native/snow_host/pose_thirteen_category_solve_validation.json)
executes256 original wrappers without interception with all thirteen categories
populated and sharing body state. Context, all rows, body data/state and results
match across four phase masks and zero through three iterations. Builders are not
executed by this check. Twelve numerical categories, their unresolved producers
and full group lifecycle remain open; this count is not an engine coverage metric.

## Bounded scalar constraint solvers

`engine/pose_bounded_scalar_solver.py` reconstructs categories16 and17.
Single-body96-byte rows use preparation0x19ef900 and iteration0x19ef510;
paired112-byte rows use0x19ef650 and0x19ef2b0. They store direction at20,
first angular coefficient at30 and per-lane inverse response at40. Paired rows
store the second angular coefficient at50. Additive response terms occupy50
for single rows and60 for paired rows. Row10 supplies XYZ response and a symmetric
increment cap. These are observed arithmetic roles, not inferred gameplay names.

Preparation forms the scalar denominator from angular tensor and linear mass
contributions. Paired addition order is first angular, first linear, second linear,
second angular. Each lane adds its own stored response term before negative
reciprocal division; inverse W is masked to zero. Cached results apply to body
states. The second body's linear direction is negated, while its angular
coefficient comes from its own field.

Iteration measures first angular plus first linear projected speed. Paired rows
add a second term of second angular plus negatively directed second linear speed.
The scalar speed is broadcast. Response XYZ contributes to the first three lanes;
the fourth shuffle lane repeats response X. For each lane:

```text
proposal = inverse * (speed + shuffled_response)
if single_body:
    proposal = float32(float32(proposal + cached_result) - cached_result)
increment = clamp(proposal, -response.w, response.w)
result = cached_result + increment
apply_weighted_body_updates(increment)
```

The single-body add/subtract sequence is present in the instructions and must not
be cancelled algebraically. A sufficiently large cached value can round away a
small proposed increment. Paired endpoint state is snapshotted before writes;
coincident indices retain the second endpoint's update rather than accumulating
both. This differs from the sequential paired angular and point families.

[Bounded scalar validation](../../native/snow_host/pose_bounded_scalar_validation.json)
compares512 preparations and1536 iterations split evenly between the two families,
without interception. All row, data/state and result bytes match with off-diagonal
tensors, per-lane response terms and coincident indices. Public tests preserve the
rounding cancellation, second-snapshot behavior and signed result updates.
Finite nonsingular rows are supported. Row producers, gameplay ownership and mixed
traversal integration remain open.

## Fifteen-category numerical traversal

`solve_pose_link_rows` accepts `bounded_rows` and `paired_bounded_rows` for
categories16 and17. Context148/14c supplies their traversal counts, independently
of append counters. The normal supported order is now
24,13,12,9,8,11,10,17,16,1,0,5,4,7,6. Both bounded scalar families are skipped
in the special phase, before any preparation or cached application occurs.

[Fifteen-category comparison](../../native/snow_host/pose_fifteen_category_solve_validation.json)
executes256 uninterrupted original wrappers with all fifteen categories populated
and shared body states. Every context, row, body-data/state and result byte matches
across four phase masks and zero through three iterations. The retained rows are
synthetic supplied inputs; this does not validate their original builders.
Public tests exercise both new categories' phase gates and missing-storage errors.
Ten numerical categories and the remaining producer/lifecycle composition are
still unsupported. This supersedes the mixed-traversal boundary for categories16/17.

## Unbounded angular axis solvers

`engine/pose_axis_angular_solver.py` reconstructs category18 single64-byte rows
and category19 paired80-byte rows. Preparation uses0x19ee980/0x19ee7c0;
iteration uses0x19eeb80/0x19eea50. Axis A is row20, paired axis B is row40,
and inverse response is row30. There is no mass contribution or scalar clamp.

Preparation computes `D = dotXYZ(T1*A,A)`, adding `dotXYZ(T2*B,B)` for paired
rows, and stores `[-1/D,-1/D,-1/D,0]`. Cached impulses apply angular changes
`T*(axis*cached)` with componentwise axis multiplication before tensor transform.
Paired writes are sequential, so coincident indices accumulate both changes.
Linear states are untouched. Each iteration computes:

```text
speed = dotXYZ(w1,A) + optional dotXYZ(w2,B)
proposal = inverse * (broadcast(speed) + response)
increment = float32(float32(proposal + cached) - cached)
result = cached + increment
w1 += T1*(A*increment)
if paired: w2 += T2*(B*increment)
```

All four response lanes are used directly. There is no response-W cap in these
families. The cached add/subtract sequence preserves float32 rounding and cannot
be removed algebraically. Finite nonsingular inputs define the supported domain.
[Kernel validation](../../native/snow_host/pose_axis_angular_validation.json)
compares512 preparations and1536 iterations split between both families, with
all retained bytes matching and no interception.

## Seventeen-category numerical traversal

The mixed solver accepts `axis_angular_rows` and `paired_axis_angular_rows`, with
context150/154 counts. Normal order is
24,13,12,9,8,11,10,17,16,19,18,1,0,5,4,7,6. Special phase skips categories18/19.
[Mixed validation](../../native/snow_host/pose_seventeen_category_solve_validation.json)
compares256 original wrappers with all seventeen families populated and sharing
state. Context, row, body and result bytes match across four phase masks and zero
through three iterations. Public tests check uncapped results, linear preservation,
coincident endpoint accumulation and phase skips. Eight numerical categories,
remaining row producers and full group lifecycle are still unsupported.

## Angular axes with added response terms

Categories20/21 extend the category18/19 layouts by16 bytes. Their preparation
routines0x19eedf0 and0x19eec30 add a per-lane field to the angular denominator
before reciprocal division. The single row stores it at40 and is80 bytes; the
paired row stores it at50 and is96 bytes. The public axis-solver APIs select
these layouts explicitly with `softened=True`.

```text
D = dotXYZ(T1*A,A) + optional dotXYZ(T2*B,B)
inverse.xyz[lane] = -1 / float32(D + added_response[lane])
inverse.w = 0
```

"Softened" is an authored API label for the effect of positive added terms,
not proof of a physical compliance unit. Inputs are not restricted to positive
terms by the implementation; each resulting denominator must be finite and
nonzero. Original iteration dispatch calls exactly the same functions as for
categories18/19, preserving unbounded increments, cached add/subtract rounding
and sequential endpoint writes. The new preparation cannot be replaced with
iteration damping or an impulse cap.

[Added-response validation](../../native/snow_host/pose_softened_angular_validation.json)
compares512 preparations and1536 iterations split between both layouts, all bytes
matching. The unextended family comparison was also rerun. Public tests verify
per-lane inverse values, changed result magnitudes and both traversal phase gates.

## Nineteen-category numerical traversal

Mixed traversal accepts `softened_axis_rows` and `paired_softened_axis_rows` for
categories20/21 with context158/15c counts. Supported normal order is
24,13,12,9,8,11,10,17,16,19,18,21,20,1,0,5,4,7,6. Both added-response families
are skipped in special phase.
[Nineteen-category comparison](../../native/snow_host/pose_nineteen_category_solve_validation.json)
executes256 uninterrupted original wrappers. Every retained buffer matches across
four phase masks and zero through three iterations with all nineteen families
populated. Six numerical categories remain unsupported, alongside unresolved
builders and full group lifecycle. The category count is not overall fidelity.

## Bounded scalar rows without added response

Categories14/15 use80-byte single and96-byte paired rows. Their preparation calls
are0x19ef170 and0x19eeec0, the same numerical preparation used by the tangent
families. Iteration uses the bounded scalar calls0x19ef510 and0x19ef2b0, not the
tangent result-coupling routines. `added_response=False` selects these layouts in
the bounded-scalar API.

These preparations omit the extra denominator field present in categories16/17.
They also broadcast the negative reciprocal into all four lanes, whereas the
extended variants mask inverse W to zero. Thus supplying a zero extra field is
not a bitwise equivalent replacement. Direction, angular weights, cached-result
application, paired snapshot semantics and single-body add/subtract rounding
retain their previously recovered formulas. Iteration still clamps each increment
symmetrically and allows signed accumulated results.

[Plain bounded comparison](../../native/snow_host/pose_plain_bounded_scalar_validation.json)
compares512 preparations and1536 iterations across both layouts, with all bytes
matching. The extended variant comparison was rerun after the shared implementation
change. Public tests distinguish the fourth inverse lane and cover both phase gates.

## Twenty-one-category numerical traversal

Mixed traversal accepts `plain_bounded_rows` and `paired_plain_bounded_rows`,
with context140/144 counts for categories14/15. Normal supported order is
24,13,12,9,8,11,10,17,16,19,18,21,20,15,14,1,0,5,4,7,6. Special phase skips14/15.
[Mixed comparison](../../native/snow_host/pose_twenty_one_category_solve_validation.json)
executes256 original wrappers without interception, all twenty-one categories
populated and all retained buffers matching across four phase masks and zero
through three iterations. Four numerical categories remain unsupported, along
with unfinished row builders and group lifecycle. This is numerical traversal
coverage for supplied rows, not a full-engine fidelity measurement.

## Late primary categories and remaining numerical kernels

Original traversal calls the paired primary preparation/iteration routines
0x19e5310/0x19e5840 for category3 and the clear routines0x19e55d0/0x19e5710 for
category2. These are the same kernels used by categories1/0 and9/8. This is
observed call reuse, not an assumption based on similar row sizes. Categories3/2
execute late in the normal-only section, after categories23/22 and before1/0.
Their row strides are128/112 bytes. Context114/110 supplies counts, and context4c/48
supplies arena bases. Special phase skips both.

`solve_pose_link_rows` exposes `paired_late_primary_rows` and `late_primary_rows`
for these pools. "Late" describes observed execution order, not original class
names or physical semantics. Signed accumulator links use each pool's own base.
[Twenty-three-category comparison](../../native/snow_host/pose_twenty_three_category_solve_validation.json)
executes256 uninterrupted original wrappers with all supported categories
populated. All context, row, body-data/state and result bytes match across four
phase masks and zero through three iterations, including backward accumulator
links from the new pools. Public tests verify normal-only execution and required
row storage.

Remaining numerical categories are22 and23. Category22 uses256-byte rows,
preparation0x19edd10 and iteration0x19ee580. Category23 uses352-byte rows,
preparation0x19ed4d0 and iteration0x19ee190. Both occur before categories3/2 in
normal phase and remain explicitly rejected by the independent mixed solver.
Completing those kernels will not by itself supply row production, group lifecycle,
concurrency or original gameplay ownership.

## Two-stage single-body constraint

Category22 preparation0x19edd10 and iteration0x19ee580 operate on a256-byte row.
The independent API is `prepare_pose_two_stage_row` / `iterate_pose_two_stage_row`
in `engine.pose_two_stage_solver`. "Two-stage" describes the observed arithmetic;
it is not an original constraint class name or evidence of a player controller.

| Row field, hexadecimal | Meaning in these routines |
| --- | --- |
| 00,04 | ushort body index and uint external result index |
| 10 | coupled response, four lanes |
| 20,30,40 | three columns of coefficient matrix A |
| 50,60,70 | prepared coupled inverse K |
| 80,90,a0 | three columns of angular coefficient matrix C |
| b0,c0,d0 | prepared diagonal angular response H |
| e0 | angular response, four lanes |
| f0 | separate cached angular impulse |

Let T be the body's tensor, M its four-lane linear response, v its linear state,
and w its angular state. Matrix products use XYZ inputs and retain four output
lanes. Transpose application takes a four-lane dot product against each stored
column and masks the resulting torque W to zero. The source's float32 order is
preserved in the implementation.

Preparation computes the full inverse `K = inverse(diag(M) + A*T*transpose(A))`.
Unlike category10, it does not normalize by the trace before inversion. For the
second stage, let cy and cz be rows Y and Z of C, with W zero:

```text
hy = 1 / dotXYZ(cy, T*cy)
hz = 1 / dotXYZ(cz, T*cz)
H  = diag(0, hy, hz)

v += M * external_cached_impulse
w += T * transpose(A) * external_cached_impulse
w += T * transpose(C) * row.cached_angular_impulse
```

H is not the full inverse of C*T*transpose(C). The routine leaves its first
column zero and computes only the two diagonal reciprocals. Both caches are
applied without clearing them, including the cached first angular component.
The public implementation requires finite nonsingular coupled response and finite
nonzero angular denominators; it does not emulate exceptional division results.

Each iteration then performs these operations sequentially:

```text
coupled_speed = (A*w + v) + row.coupled_response
coupled_delta = -(K * coupled_speed)
external_updated = external_cached_impulse + coupled_delta
v += M * coupled_delta
w += T * transpose(A) * coupled_delta

angular_speed = C*w + row.angular_response  # reads the newly updated w
angular_delta = -(H * angular_speed)
w += T * transpose(C) * angular_delta
row.cached_angular_impulse = angular_delta + row.cached_angular_impulse
external_cached_impulse = external_updated
```

Neither increment is clamped. The response W fields are not interpreted as caps.
The external result is stored only after the second correction. With identity
A,C,T, unit M, zero states/caches and coupled responseXYZ=(2,4,6), the first stage
produces v=w=(-1,-2,-3). A zero angular response then produces angular delta
(0,2,3), leaving w=(-1,0,0) and v=(-1,-2,-3). Reading the initial w for stage two
would produce a different result.

[Kernel comparison](../../native/snow_host/pose_two_stage_validation.json)
checks512 uninterrupted native preparations and1536 iterations. All row, data,
state and result bytes match with general coefficient matrices, off-diagonal
body tensors, fourth lanes and both caches populated. These are synthetic retained
inputs, not observations of a gameplay owner or reconstruction of its producer.

Mixed traversal now accepts `two_stage_rows`, using context160 counts and context98
arena bases. Category22 runs after14 and before3 in normal phase; special phase
skips it. [Twenty-four-category comparison](../../native/snow_host/pose_twenty_four_category_solve_validation.json)
checks256 original wrappers with every supported category populated, all four
phase masks and zero through three iterations. All retained buffers match.
Category23 remains rejected. Remaining builders, full group lifecycle and live
scheduler behavior are separate unresolved boundaries.

## Two-stage paired constraint

Category23 uses352-byte rows, preparation0x19ed4d0 and iteration0x19ee190.
`engine.pose_paired_two_stage_solver` provides preparation and iteration APIs.
The first256 bytes have the same roles as category22, with a second ushort body
index at02. Additional columns at100/110/120 form the second coupled coefficient
matrix B; columns130/140/150 form its angular coefficient matrix D. The first
endpoint still uses A and C. Both endpoints use their own tensor T and linear
response M. No coefficient producer or original constraint-class name is inferred.

Preparation constructs, in order:

```text
Q = diag(M1)
Q += A*T1*transpose(A)
Q = diag(M2) + Q
Q += B*T2*transpose(B)
K = inverse(Q)

hy = 1 / (dotXYZ(cy,T1*cy) + dotXYZ(dy,T2*dy))
hz = 1 / (dotXYZ(cz,T1*cz) + dotXYZ(dz,T2*dz))
H  = diag(0,hy,hz)
```

Here cy,cz and dy,dz are the corresponding Y/Z matrix rows, with W zero.
The coupled inverse uses the full matrix. The angular stage retains only two
reciprocals, with no cross-axis inverse terms. Finite nonsingular inputs define
the independent implementation's domain.

Applying a coupled impulse p performs these writes sequentially:

```text
v1 += M1*p
w1 += T1*transpose(A)*p
v2 -= M2*p
w2 += T2*transpose(B)*p
```

Applying an angular impulse q updates w1 by T1*transpose(C)*q, then w2 by
T2*transpose(D)*q. Both angular contributions are added; any sign encoded in
B or D is supplied by the row. Transpose products use four-lane dot products,
then zero torque W. If endpoint indices coincide, writes accumulate on the same
state; they are not computed from two snapshots with the second replacing the
first. Preparation applies the external coupled cache, then the row's angular
cache, preserving both caches.

Iteration performs:

```text
speed = (((A*w1 + v1) - v2) + B*w2) + coupled_response
p = -(K*speed)
external_updated = external_cache + p
apply_coupled(p)

speed = (D*w2 + C*w1) + angular_response  # updated angular states
q = -(H*speed)
apply_angular(q)
angular_cache = angular_cache + q
external_cache = external_updated
```

Both increments are unbounded. The arithmetic retains float32 intermediate
rounding and the documented ordering. With identity coefficient matrices and
tensors, unit linear responses, zero states/caches and coupled responseXYZ
(4,8,12), p=(-1,-2,-3). The first stage gives opposite linear states and equal
angular states. With zero angular response, q=(0,2,3) leaves each angular state
(-1,0,0), while linear states stay opposite.

[Paired kernel validation](../../native/snow_host/pose_paired_two_stage_validation.json)
compares512 preparations and1536 iterations with every retained byte matching.
It includes general coefficient matrices, off-diagonal tensors, fourth lanes,
nonzero caches and coincident endpoints. No routine interception is used.

## Complete numerical category traversal

`solve_pose_link_rows` now accepts `paired_two_stage_rows` for category23,
with context164 counts and context9c arena bases. All25 numerical categories
are implemented and connected. Normal preparation and each iteration follow:

```text
24,13,12,9,8,11,10,17,16,19,18,21,20,15,14,23,22,3,2,1,0,5,4,7,6
```

Special phase still runs only1/0. Append counters do not drive traversal; the
caller must supply complete retained storage for each populated traversal count.
[Full-category comparison](../../native/snow_host/pose_twenty_five_category_solve_validation.json)
executes256 uninterrupted original wrapper calls with all25 categories populated.
All context, row, body-data/state and result bytes match across four phase masks
and zero through three iterations. The new paired row includes coincident indices
in selected cases and shares body states with the other families.

This closes numerical category dispatch for supplied rows within each kernel's
stated domain. It does not close the five remaining kind-dispatched non-contact
builders, damping response, complete group lifecycle, exceptional floating-point
behavior, concurrency or gameplay ownership. A runnable API that receives rows
is not yet an engine that produces every row from authored constraints.

## Point constraint producer

Kind1 dispatch reaches0x19e7f20. The independent entry point is
`engine.pose_constraint_point.build_pose_point_constraint`. This is a producer
for the recovered point solvers, rather than a row fixture invented for testing.
Its geometry uses two body frames and two local attachment points.

Inputs are retained context storage, constraint bytes through90, bodies keyed
by the tokens at constraint08/10, and metadata keyed by body30. Body1c supplies
the numerical index;40/50/60 hold basis columns,70 translation, and128 the local
center offset. Constraint70/80 hold attachment points. XYZ is used for geometry;
frame and center fourth lanes are masked. Both bodies are required even when only
one receives a numerical correction.

The second body's metadata ushort50 bit15 selects the row family. If clear, the
builder appends category10,128 bytes. If set, it appends category11,176 bytes.
This is an observed flag rule; assigning a universal dynamic/static class meaning
would need separate evidence. Row allocation uses the category's base in context
40+4*category, append counter a4+4*category, and common row offset16c. Arithmetic
wraps the base-plus-count product at32 bits before converting16-byte units.
The builder increments that append counter and context180, placing the previous
result count at row04. It writes both body indices even for category10.

For each endpoint with frame R, translation t, local anchor a and local center c:

```text
world_anchor = R.z*a.z + ((R.x*a.x + t) + R.y*a.y)
arm = R.z*(a.z-c.z) + (R.y*(a.y-c.y) + R.x*(a.x-c.x))
```

Each operation retains float32 rounding. The first expression's translation is
added before the Y and Z terms; it is not the same rounding sequence as adding
translation after a generic matrix transform. Center offsets affect the arm,
not the world anchor. Category10 needs only the first arm.

```text
phase_scale = 0.4 if (flags38 & 0x18000000) == 0x08000000 else 0
response.xyz = (world_anchor1 - world_anchor2) * (context_c * phase_scale)
response.w = largest finite float32
A = cross_matrix(-arm1)
B = cross_matrix(arm2)  # category11 only
```

For v=(x,y,z), `cross_matrix(v)` has columns(0,z,-y),(-z,0,x),(y,-x,0).
Thus A*w equals w cross arm1, and B*w equals arm2 cross w. The opposite signs
match the paired solver's relative linear velocity convention. The responseW
becomes the solver's per-increment cap, effectively unbounded for ordinary finite
motion. The positional response is disabled outside the exact normal pose-building
phase. This does not make the rest of row construction a no-op.

The routine leaves prepared inverse matrices and reserved result bytes untouched.
It does not publish the traversal counts at context108+4*category. The caller must
supply their producer and cached-result lifecycle; silently zeroing the result
would invent behavior absent from this routine.

[Builder validation](../../native/snow_host/pose_point_constraint_validation.json)
compares512 uninterrupted original calls, with all arena, constraint, body and
metadata bytes plus the return byte matching. Cases cover both families, all four
phase masks, general finite frames, center offsets, arbitrary unused bytes and
nonzero initial append/result counts.
[Builder-to-solver validation](../../native/snow_host/pose_point_constraint_solve_validation.json)
then runs512 original builders followed by their selected preparation and three
iterations. Every retained arena/state/result byte matches the independent
composition. Numerical body buffers and cached results are explicitly supplied;
this is not full group initialization or live gameplay validation.

Kind1 and kind4 builders are now reconstructed. Kinds2,3,5,6 remain open, as do
outer dispatch eligibility, count publication and full group lifecycle composition.

## Angular limit row producer

Kind3 builder0x19e7580 first emits category22 or23, then calls helper0x19f2560
twice for angular limits. Its later optional drive path calls0x19f3750. The
complete kind3 builder, its angle helper0x19a1760 and drive semantics remain
unfinished. The implemented limit helper supplies actual category8/9 rows from
explicit arguments; it does not manufacture missing angle data.

`engine.pose_constraint_limit.build_pose_angular_limit_row` receives a context,
`single` selector and six four-lane vectors. Their authored API names are axis,
coordinate, sign, offset, response_term and response_mix. The native calling
order is RCX context, DL selector, R8 axis, R9 coordinate, then pointers at entry
stack28/30/38/40 for sign, offset, response_term and response_mix. Their physical
units are not established. The helper returns the appended row; its caller
writes endpoint indices afterward.

A nonzero selector appends category8,112 bytes; zero selects category9,128 bytes.
It reserves a result index and increments the category append count. The body
index bytes and prepared inverse remain untouched. Common output fields are:

```text
row.direction20 = (0,0,0,0)
row.angular30 = axis * sign
row.accumulator_link50 = 0
row.angular70 = axis * (-sign)  # paired only
```

The zero direction makes these rows angular-only when fed to the existing
primary kernels. The primary kernels still project accumulated impulses to
nonnegative values. Define componentwise error `e = coordinate*sign + offset`,
context scalar s=context_c, and n=(flags38>>2)&0x3fff. Every operation below rounds
to float32 in source order. "All nonnegative" includes W, not just XYZ.

The helper takes its finite-response branch only if all three XYZ lanes of
response_term are strictly below float32(1e12), exactly999999995904. Equality
selects the other branch. The W lane does not participate in this decision.

For the branch selected when any XYZ term is at or above the threshold:

```text
added_response = 0
response = s*e
if not all_four_lanes(e >= 0):
    phase_gain = 0.4 if (flags38 & 0x18000000) == 0x08000000 else 0
    response = phase_gain * response
```

Thus a nonnegative error bypasses the phase multiplier. For the finite-response
branch, let k=response_term and d=response_mix:

```text
added_response = k
position_gain = 0.4
if abs(s) > float32(1e-6):
    divisor = float32(n*s)
    added_response = float32((1 / (float32(k/divisor) + d)) * s)
    position_gain = k / (k + float32(n * float32(s*d)))

if all_four_lanes(e >= 0):
    response = float32(1e12)
    added_response = 0
else:
    response = float32(s*e) * position_gain
```

Output response goes to row10 and added_response to row60. This branch's gain
does not use the phase mask. At or below the scalar epsilon, it retains k and
uses0.4, including zero-iteration cases. Outside that branch, zero iterations
reach division by zero in the original. The independent finite-input API rejects
zero/nonfinite reached divisors instead of emulating exceptional results. The
arithmetic is evaluated before the nonnegative-error override, as in the source.

For example, s=2,n=2,k=4,d=1,e=-1 gives added_response=1 and response=-1.
Changing n to4 changes these to approximately4/3 and-2/3. These are local response
formulas, not evidence that k and d have specific spring/damping units.

[Helper validation](../../native/snow_host/pose_angular_limit_builder_validation.json)
compares1024 uninterrupted original calls across both layouts and response
branches. All arena bytes, input vectors and returned row addresses match.
Cases include all four phase masks, zero and signed epsilon scalar boundaries,
strict threshold selection, a large W term, nonuniform errors and existing
append/result counts. Public tests isolate these boundaries and preserved fields.

The inspected outer pose-row loop0x19948d0 skips a constraint when either present
endpoint has metadata52 bit0 set. Eligible constraints reach0x19905f0's six-way
virtual-kind dispatch. Neither inspected routine publishes append counters into
traversal counts. That publication must be traced separately; it must not be
inferred by copying counters in this helper.

## Angular drive row producer

Kind3's optional drive path calls0x19f3750. The independent function
`engine.pose_constraint_drive.build_pose_angular_drive_row` now reconstructs
this helper. It produces category14/15, the bounded scalar rows without an added
response term. This identifies a producer for those kernels; it does not prove
that player controls directly invoke this drive.

Native arguments are RCX context, DL single-endpoint selector, R8D mode, R9 axis,
then pointers at entry stack28/30/38/40. Their authored names are sample,
reference, rate_bound and impulse_bound. Nonzero DL selects category14,80 bytes;
zero selects category15,96 bytes. The helper appends to the selected pool, reserves
a result index and returns the row address. Endpoint indices and the prepared
inverse remain untouched. Its caller writes the endpoint indices afterward.

```text
row.direction20 = 0
row.angular30 = axis
row.angular50 = -axis  # paired only

if mode == 2:
    value = sample
else:
    value = float32((sample-reference) * context_c)
    value = SSE_MIN(SSE_MAX(value, -rate_bound), rate_bound)

row.response.xyz = -value.xyz
row.response.w = float32(impulse_bound.x * context10)
```

Each subtraction and multiplication rounds to float32. Clamp equality selects
the second operand, including its zero sign. No assumption that bounds are
positive is added by the builder. The independent finite-input API does not
emulate NaN cases. Mode2 does not dereference reference or rate_bound; the API
allows those arguments to be absent in that mode. All other uint32 modes take
the same scaled-difference path.

The cap is separate from the sample clamp. For sample=(3,-3,1), reference=(1,1,0),
context_c=2 and rate_bound=(2,3,4), responseXYZ becomes(-2,3,-2). With mode2 it is
(-3,3,-1). In both cases impulse_bound.X=8 and context10=0.25 give responseW=2.
The bounded scalar solver consumes W as a symmetric per-iteration increment cap,
not a cap on the accumulated impulse. Zero direction keeps this drive angular-only.
A paired row uses opposite angular axes, while endpoint write semantics remain
those of the bounded scalar kernel.

[Native builder comparison](../../native/snow_host/pose_angular_drive_builder_validation.json)
checks1024 uninterrupted calls with all context bytes, input vectors and return
addresses matching. Coverage includes both layouts, modes0/1/2/3, signed-zero
clamp ties, signed bounds/scalars and nonzero append/result counts. Public tests
also connect an emitted row to the bounded solver and distinguish per-iteration
limits from accumulated limits.

This closes the drive-row helper dependency identified in kind3. Its upstream
sample getter, mode configuration, angle calculation, cleanup and optional body
notification still need composition into the complete builder. No new completed
top-level builder is claimed by this helper alone.

## Kind3 angle interval selection

Cross-checking earlier research resolves an apparent gap: signed angle helper
0x19a1760 is already implemented by `engine.snow_pose_angle.pose_row_angle`,
with an explicit atan2 service. See [Pose row angular helper](CENTRAL_IMPULSE.md#pose-row-angular-helper).
The earlier statement that this whole helper remained unrecovered was too broad.
Its float32 input arithmetic is recovered; the native transcendental implementation
and its integration into the complete kind3 builder remain separate boundaries.
The formula is:

```text
y = dotXYZ(reference, cross(axis,target))
x = dotXYZ(reference,target)
angle = float32(atan2(y,x))
```

No input normalization or degeneracy repair is added. Kind3 passes its transformed
axis/reference vectors, then sends the broadcast angle through0x19f3860 before
producing limit rows. That interval selector is now implemented as
`engine.pose_constraint_angle.select_pose_angle_interval`.

Let a,lo,hi be four-lane angle and bounds and tau=float32(2*pi), exactly
6.2831854820251465. If neither `allXYZ(hi<a)` nor `allXYZ(a<lo)` holds, the helper
returns a unchanged. Strict equality does not trigger the branch. Once the XYZ
gate triggers, every lane, including W, follows:

```text
plus  = float32(a+tau) if float32(a-hi)<0 else a
minus = float32(a-tau) if float32(lo-a)<0 else a
difference = float32(float32(lo-minus) - float32(plus-hi))
selected = minus if difference<0 else plus
```

This selects between representations near the supplied interval. It is not a
clamp, does not sort bounds and does not repeatedly wrap arbitrary angles into
one revolution. For bounds[-1,1], angle6 becomes approximately-0.28318548;
angle20 becomes approximately13.716815, not a value inside[-1,1]. A nonuniform
XYZ vector can suppress selection even when individual lanes are outside.

The source drive sample getter0x1942bb0 is also reconstructed as
`pose_constraint_drive_sample`. It reads lower=d0, upper=d4 and current=dc:

```text
selected = lower if float32(lower-current)>=0 else current
result = selected if float32(upper-selected)>=0 else upper
```

For ordinary finite ordered values this clamps current between lower and upper.
The implementation preserves subtraction/comparison ordering, reversed bounds
and signed-zero selection instead of replacing it with an abstract clamp.
Getter0x1942bf0 returns the inline configuration at constraint70. The cleanup
callee0x075e600 reached by kind3 is a bare return in the analyzed image.

[Input validation](../../native/snow_host/pose_constraint_angle_validation.json)
compares2048 interval selections and2048 scalar getter calls without interception.
All output bits and source bytes match. Coverage includes broadcast/nonuniform
vectors, reversed bounds, bound equality, signed zeros and angles beyond one
revolution. This does not prove the full kind3 builder or native atan2 equivalence.

Earlier research also already contains a detached drive-row implementation in
`engine.snow_pose_drive_row`. The newer arena-mutating drive API now delegates to
it, and its1024-case native comparison was rerun successfully. The newer limit
producer additionally covers the finite-response branch; the earlier detached
limit helper models the hard-response branch only. These APIs are not silently
interchangeable across that branch boundary.

## Kind3 constraint composition

`engine.pose_constraint_hinge.build_pose_hinge_constraint` reconstructs the full
row-emission sequence of0x19e7580. Hinge is an authored description, not a recovered
class name. The API uses retained context, constraint, body and metadata storage,
an explicit atan2 service and an optional notification service. It does not access
live memory or copy traversal counts from append counters.

Configuration is inline at constraint70, copied as90 bytes before angle evaluation:

| Constraint offset, hexadecimal | Use in the builder |
| --- | --- |
| 70,80 | local attachment points, first/second body |
| 90,a0 | local axis vectors, first/second body |
| b0,c0 | local reference vectors, first/second body |
| d0,d4 | angular interval bounds |
| d8 | optional drive mode, zero disables |
| dc | current scalar for the bounded drive getter |
| e0,e4 | drive difference bound and impulse-bound input |
| e8,ec | limit response term and response mix |
| f0 byte | suppresses optional body notification when nonzero |

The second body's metadata50 bit15 selects paired versus single numerical rows,
as in kind1. Both body frames are needed. World anchors and center-relative arms
use the previously recovered point-builder arithmetic. Let R1/R2 be frame bases:

```text
u = R1 * local_axis1
v = R2 * local_axis2
p = R1 * local_reference1
q = R2 * local_reference2
h = cross(u,p)
C = matrix whose rows are zero, p, h
D = matrix whose rows are zero, -p, -h  # paired only
phase_factor = context_c * (0.4 if normal_pose_build_phase else 0)
linear_response = (world_anchor1-world_anchor2) * phase_factor
angular_response = C * (cross(v,u) * phase_factor)
```

The first emitted row is category22 or23. Its coupled coefficient matrices are
cross_matrix(-arm1) and, for a paired row, cross_matrix(arm2). Its angular
coefficient matrices are C and D above. The angular cache at rowf0 is explicitly
zeroed; the external result is only reserved, not initialized. Prepared inverse
fields remain untouched. The builder writes both numerical body indices.

Next it obtains one signed angle using `pose_row_angle(v,p,q,atan2)`. The swap
byte at constraint59 changes the interval from[lower,upper] to[-upper,-lower];
it does not change these angle-helper arguments. The adjacent-revolution selector
processes that angle. Two limit rows then use axis v, first sign=-1 and bound=upper,
then sign=+1 and bound=-lower, with both response inputs broadcast from e8/ec.
Both rows receive endpoint indices after the limit helper returns.

If drive mode is nonzero, the source scalar comes from the d0/d4/dc getter and is
negated when swap is set. The drive helper receives axis v, this broadcast sample,
the selected angle as reference, and broadcast bounds from e0/e4. It appends one
category14/15 row and the caller completes the endpoint indices.

After drive emission, the builder requests `notify(first_body_token,2)` only if
configuration f0 is zero, the first body's pointer10 is nonzero and its metadata
pointer20 is nonzero. The independent API requires a callback when this path is
reached; it does not replace the notification with an implicit no-op. Callback
side effects are outside this reconstruction. The cleanup callee in the analyzed
image is a bare return, and the builder returns byte1.

[Whole-builder validation](../../native/snow_host/pose_kind3_builder_validation.json)
executes512 complete original calls covering both layouts, four phase masks,
swap selection, hard/finite-response limit paths, drive modes0–3 and notification
gates. Every arena, source, body and metadata byte matches, as do return values,
atan2 inputs and notification arguments. Native atan2 runs normally; its output is
observed and supplied to the independent service. Only the notification call is
intercepted. Thus this proves builder composition conditional on the explicit
math and notification services, not reconstruction of those service internals.

Kinds1,3,4 now have complete row-building paths within their stated domains.
Kinds2,5,6, outer eligibility integration, count publication, result-cache lifecycle
and complete group composition remain unfinished. Nothing here establishes that
this constraint is the player's active trick or ragdoll joint.

## Constraint builder eligibility and dispatch

`engine.pose_constraint_build.build_pose_constraints` connects the retained-list
loop0x19948d0 and type dispatcher0x19905f0 to the reconstructed kind1/3/4 builders.
The API takes explicit constraint/body/metadata maps, a slot list and a
`get_kind(token)` service for virtual slot10. Its sequence is:

```text
for each slot:
    constraint = slots[i]
    if first_body.metadata52 bit0: continue
    if second_body exists and second_body.metadata52 bit0: continue
    kind = get_kind(constraint)
    if kind in 1..6: invoke the selected builder
    otherwise: continue
```

The first body is required; a null second body bypasses its eligibility test.
That does not mean every kind supports a missing second body. The command builder
supports it, while point and kind3 geometry need both frames. The kind query is
not called for ineligible entries. The dispatcher retains the selected constraint
token across the query; it does not reload a replaced current slot. Later slots
are read when reached.

All six kinds now call their independent implementations. Kinds2/3/5 require
an explicit atan2 service, and reached notifications require a callback. The
earlier additional-builder callback API has been removed after composition.
Unknown uint32 kinds emit no row, matching the native default. The outer loop
does not use the builder's returned boolean to make a further decision.

[Dispatcher comparison](../../native/snow_host/pose_constraint_dispatch_validation.json)
runs512 original eligibility loops through the original dispatcher and selected
builders. Synthetic virtual methods return kinds1/3/4/7. Complete arenas and
source buffers match, along with angle-service inputs and notification arguments.
The comparison retains the previous explicit-service boundaries: native atan2
output is observed and supplied to the independent service; body notification
side effects are intercepted. One list entry is used per native case. Public
tests additionally cover multiple entries, slot replacement, missing dependencies,
unknown kinds and nullable second bodies for commands.

### Planned-count correction

Recent sections called count publication unresolved without distinguishing the
local initializer from full lifecycle composition. The earlier
[Solver category layout and count initialization](#solver-category-layout-and-count-initialization)
already establishes the local rule: planned prepass counts are copied into
context108..16b before construction; append counters at a4..107 start at zero.
`initialize_pose_solver_storage` implements it. `count_pose_categories` already
reconstructs the six-kind planned contributions from supplied type results.
There is no missing post-build copy from append counts to traversal counts.

The remaining integration question is how the complete caller maintains valid
planned storage and group membership while count and build passes have different
local gates. The inspected count loop invokes the kind query without the builder
loop's metadata52 skip checks. Do not repair this difference by inventing count
compaction or assuming ignored rows are zero. Recover the enclosing lifecycle
contract before composing arbitrary skipped entries into a full group solve.

## Motion-aware primary constraint producer

Kind6 dispatch reaches0x19e9510. The independent implementation is
`engine.pose_constraint_motion.build_pose_motion_constraint`. "Motion-aware"
describes its reads, not a recovered original type name or damping claim.
Constraint80/90 supply local attachment points and a0 supplies a four-lane normal.
Both body frames and indices are required. Metadata50 bit15 on the second body
selects category2,112 bytes when clear, or category3,128 bytes when set. These
are the late primary pools, already connected to numerical traversal.

For the first body and, when paired, the second body:

```text
center_world = translation + R*local_center128
arm = R*(local_anchor-local_center128)
point_velocity = linear1a0 + cross(angular1ac,arm)
```

The single-endpoint branch instead uses second translation as its center,
R2*anchor2 as its arm, and zero second velocity. It does not read second-body
center or motion for this calculation. XYZ body fields are masked before math;
normal W is retained in the written direction.

With first point=arm1+center1, second point=center2+arm2, define:

```text
delta = second_point-first_point
direction = -normal
half_delta = 0.5*delta
angular1 = cross(half_delta+arm1,direction)
angular2 = cross(direction,arm2-half_delta)  # paired only
positional = (dotXYZ(delta,direction)+context1c) * (-context_c)
```

The second angular coefficient has the reversed cross-product order. The resulting
row has direction at20, angular1 at30, angular2 at70 for paired rows, zero
accumulator link at50 and zero added response at60. It reserves a result index
and writes both body indices, preserving the inverse-response field and other
untouched bytes. The row's response at10 broadcasts the selected scalar.

The scalar selection retains a motion calculation even though its coefficient is
zero in this routine:

```text
speed = dotXYZ(normal,point_velocity2-point_velocity1)
motion_term = speed*0 if speed<0 else +0
response = motion_term if abs(positional)-abs(motion_term)<0 else positional
```

Finite ordinary inputs therefore do not receive a restitution or damping
response from this term. The implementation preserves the calculation and zero
sign behavior instead of inventing a configurable coefficient. No phase-mask
condition gates this builder's positional response. All arithmetic follows the
observed float32 ordering; no normal normalization is added.

[Kind6 comparison](../../native/snow_host/pose_motion_constraint_validation.json)
executes512 uninterrupted original calls. All context, constraint, body and
metadata bytes and return values match across both branches, general frames,
nonzero centers, anchors, normals and linear/angular motion. Public tests verify
midpoint coefficients, context bias, zero motion gain and the ignored second-body
fields in the single branch.

Kind6 is now connected to `build_pose_constraints`. The
[dispatcher comparison](../../native/snow_host/pose_constraint_dispatch_validation.json)
was expanded and rerun with kinds1/3/4/6 and unknown7. All512 cases pass. Kinds2/5
remain explicit external dependencies. Numerical solving already supports the
emitted categories; complete group lifecycle and active gameplay ownership remain
unresolved.

## Quaternion inputs to angular drive

The kind5 angular-drive helper at RVA19f32f0 calls matrix-to-quaternion
RVA18c0b60 and quaternion multiplication RVA18c09e0. Independent implementations
are in `engine/pose_quaternion.py`. These are local recovered kernels, not a
claim that the entire kind5 builder or its gameplay ownership is established.

`multiply_pose_quaternions` takes two XYZW operands. With first=(x,y,z,w) and
second=(a,b,c,d), its scalar operation order is:

```text
out.x = (((c*y)-(b*z))+(a*w))+(x*d)
out.y = (((a*z)-(c*x))+(b*w))+(y*d)
out.z = (((b*x)-(a*y))+(c*w))+(z*d)
out.w = (w*d)-(((b*y)+(a*x))+(c*z))
```

Each multiplication, addition and subtraction rounds to float32. This is the
Hamilton product in the stated operand order, with no normalization or sign
canonicalization. Changing operand order changes rotation composition.

`pose_matrix_to_quaternion` accepts three XYZ columns, with optional unused
fourth lanes. Use column names X=(xx,xy,xz), Y=(yx,yy,yz), Z=(zx,zy,zz).
The converter computes four candidates:

```text
W = (yy+xx)+zz
X = (xx-yy)-zz
Y = (yy-xx)-zz
Z = (zz-xx)-yy
```

Starting with W, it replaces the selected candidate only on a strict greater
comparison, in X/Y/Z order. Equal candidates preserve W/X/Y/Z priority. Set
`major = 0.5*sqrt(candidate+1)` and `scale = 0.25/major`, rounding each operation
to float32. The selected branch produces XYZW as follows:

| Selected | X output | Y output | Z output | W output |
| --- | --- | --- | --- | --- |
| W | (yz-zy)*scale | (zx-xz)*scale | (xy-yx)*scale | major |
| X | major | (yx+xy)*scale | (zx+xz)*scale | (yz-zy)*scale |
| Y | (yx+xy)*scale | major | (zy+yz)*scale | (zx-xz)*scale |
| Z | (zx+xz)*scale | (zy+yz)*scale | major | (xy-yx)*scale |

This routine does not repair nonorthogonal frames, normalize the result, or
force W positive. A zero matrix yields quaternion(0,0,0,0.5), not identity.
The drive caller performs separate normalization; it must not be silently moved
inside either helper. The public implementation supports finite, bounded
consumed inputs. Overflow and nondefault floating-point modes remain outside
its verified domain.

[Quaternion comparison](../../native/snow_host/pose_quaternion_validation.json)
records4096 uninterrupted original calls per helper. All output bits match.
Matrix branch counts are W1204, X955, Y960, Z977. Cases include rotations,
general matrices, half-turns, equal candidates, signed zeros, ignored fourth
lanes and destination aliasing. Source bytes outside the destination remain
unchanged. The product's returned address also matches. No native calls were
intercepted and no math service was substituted. The source image and comparison
script remain private; this receipt contains no game payload.

## Quaternion angular-drive response

`engine/pose_constraint_vector_drive.py` reconstructs RVA19f32f0, a kind5
producer dependency that appends an80-byte category12 single-body or category13
paired-body row. Inputs are two three-column frames A/B, an output frame,
four-lane gain/cap/strength/additive values, and context scalars c/10. Physical
units and active player ownership are not established. Body indices remain for
the caller to write; prepared matrix coefficients and cached results are untouched.

The relative orientation calculation is:

```text
b = normalize(matrix_to_quaternion(frame_b))
a = normalize(matrix_to_quaternion(frame_a))
if dot(a,b) < 0: a = -a
q = normalize(hamilton_product(conjugate(b),a))
v.xyz = asin(clamp(q.xyz,-1,1)) * (gain.xyz * (-2*context_c))
v.w = 0 * (gain.w * (-2*context_c))
magnitude = sqrt((v.x*v.x+v.y*v.y)+(v.z*v.z+0))
if cap.x < magnitude and cap.y < magnitude and cap.z < magnitude:
    v = (v/magnitude)*cap
response = output_frame*v.xyz + additive
response.w = strength.x*context_10
```

All operations round to float32. Matrix quaternion norms sum Y²+X², then Z²,
then W². The product norm sums X²+Y², then Z², then W². The quaternion dot sums
Ay*By+Ax*Bx, then Az*Bz, then Aw*Bw. Normalization multiplies each component by
one rounded reciprocal of the rounded square root. The helper calls arcsine in
Z/Y/X order. This is componentwise quaternion arcsine, not an axis-angle vector
conversion. The negative factor2 is an observed constant, not a guessed gain.

The magnitude gate uses all three XYZ comparisons and excludes W. It does not
clamp each axis independently. Mixed caps can disable limiting entirely. The
frame multiply evaluates columnZ*v.z + (columnY*v.y + columnX*v.x), then adds
the supplied additive vector. Strength replaces the final W lane. These choices
matter when composing with the category12/13 increment-clamped angular solver.
The helper reserves one result index and advances only its selected append count;
it does not publish traversal counts or initialize endpoint indices.

The called CRT routine identifies itself as `asinf`. Its finite[-1,1] arithmetic
is independently implemented in `engine/pose_scalar_asin.py`:

- Below magnitude2^-14, return the original input bits, including signed zero.
- At magnitude1, return signed float32 pi/2.
- Below magnitude0.5, evaluate the recovered rational polynomial in x², then
  return x+x*polynomial with the input sign.
- Otherwise, evaluate the same polynomial in(1-abs(x))/2, split its square root
  by clearing the low16 mantissa bits, and use the recovered compensated pi/2
  reconstruction. The implementation preserves constants and operation order.

The public function excludes CRT floating-point status and errno side effects,
NaNs, out-of-domain inputs and nondefault floating-point modes. It does not
claim a complete CRT replacement. The builder likewise excludes overflowing
arithmetic, zero quaternion norms and negative caps causing division by zero.

[Vector-drive validation](../../native/snow_host/pose_vector_drive_validation.json)
records16408 scalar arcsine comparisons and1024 complete original builder calls.
All output bits, context arena bytes, input preservation and returned row
addresses match. The native builder executes its original matrix, quaternion
and arcsine helpers without interception or supplied math outputs. Tests cover
both endpoint layouts, general/equal frames, cap-gate branches and nonzero
existing counters. Public regressions additionally cover shortest-sign selection,
frame-before-additive order, untouched endpoint/preparation fields and signed zero.
Complete kind5 composition, its angular-limit geometry and group lifecycle remain
unresolved; this closes one producer dependency, not the whole constraint type.

## Elliptical limit projection

Kind5's limit-geometry helper RVA19e9060 calls projection RVA19f3930 and normal
RVA19f4180 when both supplied extents exceed its small-value threshold.
`engine/pose_ellipse.py` reconstructs these two dependencies. It does not yet
compose the complete limit geometry or assign anatomical meanings to its axes.

`pose_ellipse_project(x,y,a,b)` projects onto the boundary of an axis-aligned
ellipse with positive radii a/b. It does not preserve interior points. Let
A=a², B=b² and epsilon=float32(1e-4). All arithmetic below rounds to float32
at each operation, including square roots and division.

For abs(x)<=epsilon, if a<b and abs(y)<b-A/b, select py=B*y/(B-A) and
px=sign(x)*a*sqrt(abs(1-(py/b)²)). Otherwise select(0,sign(y)*b).
The abs(y)<=epsilon branch is symmetric, tested second. Zero takes the positive
sign. Thus the origin maps to the positive shorter-radius endpoint, with the
positive Y endpoint winning when radii are equal. The implementation retains
reciprocal-first products in these tests and reconstruction expressions.

For other points, initialize t=0 inside the ellipse, otherwise
`t=max(a,b)*sqrt(y²+x²)`. Define AX=x²*A and BY=y²*B. Each iteration evaluates:

```text
u = t+B
v = t+A
residual = ((u*u)*(v*v) - (u*u)*AX) - (v*v)*BY
if abs(residual) < epsilon: stop
derivative = 2 * (((u*v)*(u+v) - u*AX) - v*BY)
t = t - residual/derivative
```

There are at most19 updates. The original code unrolls groups of8 before the
final scalar loop. If it exhausts the limit, final reconstruction uses the last
evaluated u/v, without recomputing them after the last t update. This behavior is
retained; the independent implementation does not add extra convergence steps.

If abs(v)>abs(u), compute px=A*x/v, then
py=sign(u*y)*b*sqrt(max(0,1-(px/a)²)). Otherwise compute py=B*y/u, then
px=sign(v*x)*a*sqrt(max(0,1-(py/b)²)). Negative-sign tests are strict. Input radii
and intermediate arithmetic must be finite and nondegenerate. Authored guards
reject unsupported degeneracy rather than claiming recovery of IEEE exceptions.

`pose_ellipse_normal(a,b,px,py)` forms n=(px,(a²*py)/b²), computes one rounded
reciprocal of sqrt(nx²+ny²), and multiplies both components by it. This has the
ellipse-gradient direction for positive radii, but algebraically substituting a
different gradient formula could change float32 results.

[Ellipse validation](../../native/snow_host/pose_ellipse_validation.json) records
8192 projection and8192 normal comparisons against uninterrupted original code.
Both output components match bit-for-bit in every case. The projection reached
its iteration cap in872 cases. Coverage includes unequal/equal radii, interior
and exterior points, both near-axis branches and signed coordinates. The public
regressions include one synthetic native-output fixture that reaches the cap.
No game payload is included. Full kind5 geometry, allocation and lifecycle remain
separate work.

## Composed angular-limit geometry

`engine/pose_constraint_limit_geometry.py` reconstructs RVA19e9060. Its inputs
are four-lane radius, angle, X/Y extents, initial correction axis and rotation
axis. It returns a correction axis and error vector. These names describe the
local geometry, not established units or anatomical axes. No solver row is
allocated here. The original local-static initializer supplies epsilon=1e-4;
the independent function uses that value directly and excludes initializer locks.

Branch ordering and lane semantics are significant:

1. If every lane of abs(extentX-extentY)<=epsilon, preserve the initial axis
   including W and return extentX-radius, lane by lane. This precedes radius checks.
2. If all XYZ radius lanes are strictly below epsilon, preserve the axis and
   return four positive zeros. This is not an absolute-magnitude comparison.
3. Otherwise use only radius.X, angle.X and the two extent.X values for geometry.
   Compute point=(cos(angle)*radius,sin(angle)*radius) with scalar float32 math.
4. If both absolute extents exceed epsilon, use the reconstructed ellipse
   projection and normal helpers. Otherwise clamp point coordinates to each
   signed extent pair, form point-projection, and normalize that difference.
   If its squared length is <=epsilon, preserve the initial axis and zero error.

For the continuing path, let point=(x,y), projection=(px,py), and normal=(nx,ny).
The remaining formulas are:

```text
inverse_radius = 1/radius
turn = ((inverse_radius*y)*nx) - ((inverse_radius*x)*ny)
correction = asin(clamp(turn,-1,1))
q.xyz = rotation_axis.xyz * sin(correction*0.5)
q.w = cos(correction*0.5)
rotated_axis = quaternion_basis(q) * initial_axis.xyz
error = ((py-y)*ny) + ((px-x)*nx)
return (rotated_axis.xyz,0), broadcast(error)
```

There is no normalization of the supplied rotation axis. The matrix transform
sums X contribution plus Y contribution, then Z contribution, with rounding
at each operation. This differs from some SIMD transform helpers' association.
The general result always clears axis.W, unlike early returns. The error's sign
is retained; no absolute value or extra penetration clamp is added.

The implementation reuses reconstructed dispatch-zero scalar sine/cosine,
finite-domain arcsine, quaternion-basis arithmetic, ellipse projection and
ellipse normal. All arithmetic functions execute independently; none receives
observed native results as a service. Supported inputs are finite, use positive
radii when the ellipse branch is reached, nonzero scalar radius when division is
reached, and remain within the scalar-trig implementation's supported range.

[Geometry comparison](../../native/snow_host/pose_limit_geometry_validation.json)
records2048 uninterrupted original calls including all nested math helpers.
All eight output lanes and unchanged source bytes match. Synthetic setup supplies
initialized TLS/static epsilon and trig dispatch zero. Cases cover all-lane
extent equality, W-only extent mismatch, small-radius skip, exact threshold,
elliptical projection, degenerate extents, negligible residual and general axes.
No interception or substituted math output is used. Static initialization
concurrency, CRT status effects, complete kind5 composition and gameplay ownership
remain outside this evidence.

## Bounded drive target frame

Before kind5 emits its quaternion drive, wrapper RVA19439d0 passes the inline
configuration at constraint+70 and swap byte59 to RVA19434c0.
`engine/pose_constraint_target.py::prepare_pose_target_frame` reconstructs that
second routine. It copies configuration XYZ columns80/90/a0 into the destination,
preserving each destination padding lane. A nonzero swap flag transposes only the
working frame used to measure angles; it does not transpose the initial output.

Let M be that working frame. The routine forms u=M*config20 and t=M*config40,
with v=config30 and reference=config50. The correction axis is normalize(cross(u,v)),
except that a length strictly below1e-4 selects config50 directly. It computes
angle=signed_angle(axis,v,u) using the existing explicit atan2 service. The
unmodified u/t/axis/angle remain the inputs for later measurements, even if an
intermediate correction changes the output matrix.

With a=config60 and b=config64, if angle>min(a,b), rotate v by pi/2 around the
correction axis, measure its signed azimuth around v against reference, then:

```text
bound = (b*a) / sqrt((sin(azimuth)*b)^2 + (cos(azimuth)*a)^2)
if angle > bound:
    output = rotation(axis,bound-angle) * output
```

If config68 is nonzero, rotate t around the correction axis by the original
angle. Measure twist=signed_angle(v,reference,rotated_t), with bound=config6c.
When twist>bound, correction=bound-twist. When twist<-bound,
correction=-twist-bound. Otherwise leave the output unchanged. A reached
correction left-multiplies output by rotation(u,correction). The correction axis
is not renormalized before axis-angle conversion. Scalar matrix composition
sums X+Y, then Z; the measurement transforms use the recovered SIMD association.
Both compositions preserve destination padding lanes.

[Target-frame comparison](../../native/snow_host/pose_target_frame_validation.json)
records1024 complete original calls. Every destination byte and unchanged
configuration byte matches, as do signed-angle arguments and call counts.
Native atan2 outputs are supplied to the explicit independent service; the
comparison does not establish independent atan2 arithmetic. The native path runs
without interception. Other trig and quaternion arithmetic is independently
reconstructed. Cases include146 fallback-axis paths,693 elliptical corrections
and373 secondary-angle corrections. Positive finite angular bounds and bounded
finite matrices define the tested domain. Complete kind5 row composition,
nonfinite behavior and active rig ownership remain open.

A synthetic native-checked sign regression starts with a1-radian Z rotation and
produces approximately1.25radians after correction with its supplied reference
axes. Thus these local signed-bound formulas are not a universal world-angle
clamp. Caller frame conventions and valid authored configuration still matter.

## Kind5 constraint composition

`engine/pose_constraint_cone.py::build_pose_cone_constraint` reconstructs the
complete RVA19e8350 builder. "Cone" is our descriptive name, not an established
original class or active player-joint identity. It emits one category10/11 point
row, one category8/9 angular-limit row, four additional category8/9 rows when
config68 is nonzero, and one category12/13 drive row when config70 is nonzero.
Configuration offsets below are relative to constraint+70.

The point-row construction is identical to the recovered kind1 producer and
reuses it. Endpoint layout follows second-body metadata50 bit15. Frames and
translations mask their W lanes. With body frames A/B and config axes20/30 and
references40/50, define u=A*axis20, v=B*axis30, p=A*reference40, q=B*reference50.
The swing axis starts as cross(u,v). If its length is strictly below1e-4, replace
it by cross(v,worldX); if still below threshold, use cross(v,worldY). Normalize
with a rounded reciprocal. There is no final zero-axis recovery.

Measure swing=signed_angle(axis,u,v). Its negation supplies the radius input to
`pose_angular_limit_geometry`. Azimuth is signed_angle(v,q,axis) normally, or
signed_angle(u,p,axis) when constraint59 is nonzero. Geometry uses config60/64
as extents, the normalized axis as its initial correction axis, and u normally
or v when swapped as its rotation axis. Emit the resulting limit with coordinate
=geometry error, sign=1, offset=0, response term=configc4 and mix=configc8.

When config68 is nonzero, rotate q around the swing axis by the original swing
angle, then measure twist=signed_angle(u,p,rotated_q). Emit four limit rows in
this order: axis u/sign+1, axis u/sign-1, axis v/sign+1, axis v/sign-1. All four
share twist, offset=config6c, response term=configcc and mix=configd0. Every row
receives the retained endpoint indices after helper allocation.

When config70 is nonzero, prepare the target using the live inline configuration
and current swap byte through `prepare_pose_target_frame`. The surrounding
builder keeps its earlier configuration snapshot for gains and flags. If the
retained swap byte was nonzero, apply the scalar target inverse RVA18c1480 to
the prepared frame. This is not simply a transpose. That inverse computes
cofactors with scalar operation ordering, evaluates its determinant along the
first row, and skips reciprocal scaling when abs(det-1)<=float32(1e-6).
The independent `_inverse_target` preserves this near-unit branch. The separate
SIMD inverse used for body frame B retains its own ordering and always divides.

Compute relative=inverse(B)*A. The vector-drive helper receives:

| Argument | Source |
| --- | --- |
| frame A | Prepared target, inverted when swapped |
| frame B | Relative body frame |
| output frame | Body frame A |
| cap | Broadcast config74 |
| strength | Broadcast config78 |
| gain | Broadcast configc0 |
| additive | Four lanes at configb0 |

The order of target and relative frames is consequential for quaternion error
sign. Finally, only inside the enabled-drive branch, config71==0 permits the
same body notification shape seen in kind3: first body's field10 must be nonzero,
as must its metadata field20, then notify(first_body,2). Reached notification
requires an explicit service. The original cleanup helper returns without work.
The builder returns1. It does not initialize result caches or publish traversal
counts.

[Complete kind5 comparison](../../native/snow_host/pose_kind5_builder_validation.json)
records512 original builder calls with all nested geometry and drive helpers.
All arena, constraint, body and metadata bytes match, together with angle-service
arguments/call counts, return byte and notification arguments. Native atan2
outputs are supplied to the explicit independent service. Only notification is
intercepted in native execution. Another2048 uninterrupted scalar target-inverse
calls match XYZ output and preserved padding, including determinants near1.
Inputs are finite synthetic retained records with nonsingular frames and positive
angular extents. Callback mutation, notification side effects, original atan2
arithmetic, active rig ownership and full group lifecycle remain unproven.

Kind5 is connected to `build_pose_constraints`. Reconstructed builders now cover
kinds1/3/4/5/6; kind2 remains an explicit supplied dependency. Public tests compare
kind5 dispatch to direct construction, exercise row-count combinations and
notification gates, and retain the target-inverse near-unit rule. This is a local
six-kind dispatch milestone, not an engine-wide coverage percentage.

## Translation spring row producers

Kind2 calls hard translation RVA19f2bd0 and soft translation RVA19f2d20.
`engine/pose_constraint_translation.py::build_pose_translation_row` reconstructs
both, emitting category14/15 or16/17 respectively. The caller supplies the branch,
axis, two points, two lever arms, and soft stiffness/damping when applicable.
Presence of stiffness selects the soft API path; classification thresholds remain
the caller's responsibility. This API does not assign physical units.

The response distance is dotXYZ(axis,pointB-pointA), rounded with the recovered
pairwise reduction. Both helpers write direction=axis, first angular coefficient
=cross(armA,axis), and paired second coefficient=cross(axis,armB). They reserve
one row and result index, preserve endpoint indices and inverse-response fields,
and set response.W to FLT_MAX. The caller completes endpoint indices later.

The hard response is distance*(context_c*(-0.4)), broadcast to XYZ. No phase mask
gates that gain. For soft rows, let s=context_c and n=(flags>>2)&0x3fff:

```text
if abs(s) <= float32(1e-6):
    added_response = stiffness
    gain = -0.4
else:
    ratio = stiffness / (n*s)
    denominator = ratio+damping
    added_response = s*(1/denominator)
    gain = (-ratio)/denominator
response.xyz = distance*(gain.xyz*s)
```

All stages round to float32. Soft parameters may differ across lanes; coefficient
W is preserved even though final response.W is replaced. Added response occupies
row50 for single rows and row60 for paired rows. The implementation reuses the
existing soft parameter arithmetic and reverses its gain sign. This is not the
angular soft-row producer, which measures an angle and has a different layout.

[Translation-row validation](../../native/snow_host/pose_translation_row_validation.json)
records2048 uninterrupted original calls without interception. Complete arena
bytes, source preservation and returned row addresses match. Cases cover hard and
soft rows, both endpoint layouts, all phase masks, signed/near-zero scalar values,
nonuniform coefficients and existing counts. Public tests distinguish cross-product
signs, phase independence, added-response placement and result reservation.
Complete kind2 classification, limit rows and top-level composition remain open.

## Paired translation limits

Kind2's RVA19f2fb0 emits two category8/9 rows in one call. The independent
`build_pose_translation_limit_pair` in `engine/pose_constraint_translation.py`
reconstructs its full writes, including endpoint indices. Category8 uses112-byte
rows and category9 uses128-byte rows. It reserves two consecutive result indices.
The public return tuple of row offsets is our inspection convenience; no meaning
is assigned to the original return register.

With delta=pointB-pointA, the first direction is the supplied axis and the second
is its sign-bit negation. Bounds remain supplied four-lane values, without sorting
or an assumed lower/upper convention:

```text
first_error = broadcast(dotXYZ(axis,delta)) + first_bound
second_error = broadcast(dotXYZ(-axis,delta)) - second_bound
phase_gain = 0.4 if (flags & 0x18000000) == 0x08000000 else 0
for each error:
    gain = phase_gain * (-context_c) if all XYZ error lanes > 0 else -context_c
    response = error * gain
```

The gate is strictly positive and only considers XYZ. An exact zero in any XYZ
lane selects full gain. W cannot change the gate but receives the same selected
gain. Response W is not replaced by an impulse cap. Both dot products are
computed with their own signed axis; the second is not implemented by negating
the first dot result. This preserves signed-zero and rounding behavior.

Each row writes direction at20, cross(armA,direction) at30, and paired
cross(direction,armB) at70. It zeros the qword at50 and the vector at60, preserving
58..5f and the prepared inverse response at40. Endpoint indices use the low16
bits of the supplied unsigned values. Allocation/count arithmetic follows the
existing arena convention. No solver result-cache initialization is added.

[Translation-limit validation](../../native/snow_host/pose_translation_limit_validation.json)
records2048 uninterrupted native calls without interception. Complete arena bytes
and unchanged source vectors match across both endpoint layouts, all phase masks,
nonzero counts, signed context scalars, nonuniform bounds and exact-zero/mixed-lane
gates. Public tests cover W exclusion, strict positivity, opposite axes, endpoint
truncation and preservation of untouched fields. Kind2's full caller composition
and classification remain unresolved; this closes its translation-limit helper.

## Kind2 translation assembly

`engine/pose_constraint_axes.py` reconstructs world-input preparation and the
translation portion of RVA19e5da0. `prepare_pose_axis_constraint` snapshots the
0x120-byte record at constraint70 and derives two world anchors, lever arms and
three world axes per endpoint. Config0 is the first anchor and40 the second;
config10/20/30 and50/60/70 are the respective local axes. Frames, translations
and centers use XYZ with W cleared. A single-endpoint row ignores the second
body's center when deriving its lever arm. Angular fields remain in the snapshot
for later composition but are not executed by this stage API.

`build_pose_axis_translations` reads three20-byte records at config80/94/a8,
containing state, two bounds, stiffness and damping. If all states are0 and all
stiffness values are at least float32(1e12), it emits a single category10/11 point
row using the recovered point arithmetic. Only constraint190 receives that row's
result index;194 and198 remain unchanged.

Otherwise compare constraint59 with config11c. On inequality, select the second
endpoint's world axes and adjust its lever arm by worldPointA-worldPointB. On
equality, select the first endpoint's axes and adjust its lever arm by
worldPointB-worldPointA. The other arm remains unchanged. This adjustment is
part of row geometry; it must not be replaced by an unmodified anchor arm.

Each selected axis then follows its own record:

| State | Emission |
| --- | --- |
| 0 | Hard14/15 when stiffness>=1e12, otherwise soft16/17 |
| 2, stiffness<1e12 | Soft16/17, then the ordered pair of category8/9 limits |
| 2, stiffness>=1e12 | Only the category8/9 limit pair |
| Other | No translation rows |

Hard/soft scalar rows receive endpoint indices and publish their result index to
constraint190+4*axisIndex. Limit pairs do not overwrite those feedback indices.
Their first/second bound inputs are the record's first/second stored bounds,
without sorting or sign conversion. Skipped states also preserve feedback fields.
All row and result allocation remains delegated to the verified producers.

[Translation-stage comparison](../../native/snow_host/pose_kind2_translation_validation.json)
executes512 complete original kind2 calls with angular states set to1 and drive
flags cleared. This isolates translation without replacing any reached helper.
Entire context arenas, constraints, bodies and metadata match, including native
success and feedback publication. Coverage includes states0..3, both endpoint
layouts, every phase mask, hard-triple collapse, soft-plus-limit emission,
axis-owner comparison, nonzero centers and general axes.

Public tests compare emitted category counts with the existing count prepass for
all216 combinations of states0/1/2 and hard/soft coefficients across three axes.
They also check feedback preservation and the second-center rule. The stage API
returns prepared inputs for later angular composition; it is not registered as
a complete kind2 dispatcher implementation. Angular-frame preparation, angular
row dispatch and drive composition remain open. No full group lifecycle or active
player ownership is established by these isolated translation runs.


## Kind2 angular frames and complete composition

`engine.pose_constraint_axes.build_pose_axis_constraint` now composes translation,
angular rows and optional direct drives for the complete kind2 builder at
RVA0x19e5da0. This supersedes the earlier kind2 composition gaps above. All six
known kinds now have independent implementations in `build_pose_constraints`.
These are local constraint producers, not the full scheduler or active rig.

Let A and B be the prepared endpoint world-axis triples. Without swap, choose
base=A2, other=B0, alternate=B1. With swap choose base=B2, other=A0,
alternate=A1. Cross products clear W and dot products use XYZ. Operations retain
float32 rounding, including square root and reciprocal before normalization.

```text
if abs(dot(base, other)) < float32(0.9999):
    middle = normalize(cross(base, other))
    secondary = normalize(cross(middle, base))
else:
    secondary = normalize(cross(alternate, base))
    middle = normalize(cross(base, secondary))

if swapped:
    triples = [(A0, A1, middle), (middle, A0, secondary), (B2, middle, B1)]
else:
    triples = [(B0, middle, B1), (middle, secondary, B0), (A2, A1, middle)]
```

Each triple contains axis, reference and target for signed-angle calculation.
Angular records at configbc/d0/e4 contain state, lower bound, upper bound,
stiffness and damping. If all states are1, frame preparation is skipped.
State1 emits nothing. State0 emits hard18/19 when stiffness>=float32(1e12),
otherwise soft20/21 with the existing spring arithmetic. Other states emit two
category8/9 angular limits: sign=-1 with offset=upper, then sign=+1 with
offset=-lower. They share one signed-angle evaluation. Endpoint indices are
completed after emission; angular rows do not publish translation feedback slots.

The builder emits limits for state3 too, but the count prepass only reserves
angular limit pairs for state2. This is an unresolved input-validity/lifecycle
boundary. Count agreement is established for states0/1/2, not arbitrary states.
Do not allocate using the prepass for state3 and assume enough capacity.

Drive records at configf8/104/110 pair with the three angular states. A drive
requires a nonzero state and enabled byte. It uses the corresponding original
world axis from A without swap or B with swap, direct mode2, and the stored
sample and strength. It does not use the constructed middle/secondary axes.
Unless the suppression byte is set, each reached drive checks the first body's
owner and metadata notification pointers and calls the supplied notification
service with that body token and2. Three drives can cause three notifications.

[Angular-stage comparison](../../native/snow_host/pose_kind2_angular_validation.json)
and [complete-builder comparison](../../native/snow_host/pose_kind2_builder_validation.json)
each passed512 native cases. Entire arenas and retained objects match. Complete
builder checks also compare notification arguments and signed-angle service
arguments/call counts. Native atan2 outputs remain supplied to the independent
implementation; notification effects and callback-driven mutation are excluded.
Public tests check all54 angular state/hardness combinations against counts,
near-parallel fallback, skipped-frame preparation, repeated notification and
complete dispatcher equivalence. Full group lifecycle, count/build eligibility
reconciliation and active player ownership remain open.


### Angular state-domain boundary through submission

The record submission converter copies the six state records unchanged from
source60..d7 to converted80..f7. Neither conversion, optional frame swap nor
field storage sanitizes angular state3 or UINT32_MAX. A composed public regression
passes those values through `prepare_pose_submission`, count planning and the
complete kind2 builder. In both frame orders the state survives, planning reserves
zero limit rows, and construction emits two. Thus the known submission conversion
cannot explain away the mismatch. This does not establish that game-authored
records use those values. The remaining lead is the source-state producer or its
valid-state contract before submission, together with enclosing allocation policy.

## Group preparation through solve entry

`engine.pose_group_prepare.prepare_pose_group` composes the retained-storage path
of wrapper RVA0x1994da0. It accepts explicit stable link/pose/body views, settings,
a scalar, a group token and caller-owned storage. It clears a local 25-counter
array, counts links using the full settings mode, adds pose counts, initializes
storage using the group body count, then applies settings to that same buffer.
The returned layout description is authored API output. The native wrapper
continues by calling the group-step routine once with the resulting buffer.

```text
counts = zeroes(25)
count_links(counts, links, full_uint32_settings_mode)
count_poses(counts, poses)
initialize_retained_storage(context, counts, body_count)
initialize_settings(context, settings, scalar, group)
# Native next call: group_step(context).
# Independent caller explicitly invokes run_pose_group_step with its services.
```

There is no eligibility filtering or planned-count adjustment between counting
and solve entry. Link counting uses the full mode word; settings retains only its
low two bits. Mode4 therefore counts nonzero-mode link rows while publishing mode0
for builders. This difference remains visible rather than being normalized away.
Body storage uses the low16 bits of body count, as in the layout helper.

[512 native wrapper comparisons](../../native/snow_host/pose_group_prepare_validation.json)
execute original link/pose counters, retained storage initialization and settings
initialization. Only byte-fill and the subsequent group-step call are supplied
services. Synthetic virtual methods provide type results. Complete allocations
and retained source objects match; each native case calls group-step exactly once
with the retained allocation. Cases combine contact links and all six pose kinds,
unknown kinds, both metadata banks, varied raw modes and nonzero retained bytes.

The API does not allocate or release native memory and does not run the group
step implicitly. Object mutation during virtual queries, count/build eligibility
mismatches, unsupported state domains and active player ownership remain open.
This validates preparation composition, not full numerical lifecycle equivalence.

## Complete arena numerical dispatch

`engine.pose_solver_arena.solve_pose_arena` connects all25 reconstructed numerical
categories directly to a retained context allocation. It creates writable views
using category starts at context40, planned counts at108 and row origin16c.
Each stride comes from the recovered25-entry layout table. Body data spans170
through174 in64-byte records; body state spans174 through178 in32-byte records;
results start at178 with one16-byte slot per planned row. These views alias the
original allocation, including references from primary rows to shared-row fields.

The adapter delegates preparation, phase selection and iteration to the existing
complete numerical dispatcher. It does not infer traversal from append counters
or silently replace planned counts when fewer rows were built. A caller must
establish valid populated rows. Bounds/alignment checks are authored API guards.
It does not build rows, allocate memory, publish body motion or run poststep.

[256 native full-arena comparisons](../../native/snow_host/pose_solver_arena_validation.json)
execute the uninterrupted original solver wrapper with all25 categories populated,
four phase masks and zero through three iterations. Every byte of the retained
allocation matches, including unused padding, context scalars, body data/state,
results and cross-row updates. Numerical inputs are synthetic and supplied;
these tests do not establish complete group lifecycle or live-player equivalence.

This adapter can consume a context prepared by `prepare_pose_group` once its body
buffers and rows have been populated. It removes the need to manually pass25
separate row lists, while preserving the same numerical and state-domain limits.

## Joined group numerical runtime

`engine.pose_group_runtime.run_pose_group_runtime` binds the existing native-order
`run_pose_group_step` to body-buffer production, six-kind constraint construction,
complete arena solving, body-motion feedback and kind2 result feedback. It accepts
retained raw groups, bodies, constraints and metadata plus explicit pointer-array
views. The callback argument tokens identify these views, not live process memory.

Body preparation reads basis40/50/60, tensor170/180/190, scalar124, motion1a0/1ac,
flagsaa and metadata52. It consumes scalar/vector addresses supplied by the group
orchestrator, preserving the context10 scalar and context0 vector relationship.
Reached damping pointers require an explicit record map and response service;
fixed-body and zero-scalar branches do not resolve damping records. Produced data
and state are copied into their retained arena regions. The normal-phase flag is
set by the orchestrator before constraint construction.

```text
produce_body_buffers_into_arena()
build_links_via_explicit_service()
select_normal_phase()
build_constraints_into_arena()
solve_pose_arena()
link_feedback_via_explicit_service()
copy_solved_body_motion()
copy_kind2_constraint_results()
if secondary_phase_enabled:
    clear_body_state()
    refresh_links_via_explicit_service()
    solve_pose_arena()
if secondary_phase_still_enabled:
    temporarily_apply_secondary_body_state_via_explicit_update_service()
poststep_via_explicit_service()
```

No empty callback defaults are provided. Link build/feedback/refresh and poststep
are mandatory services; secondary body update is required when reached. This
lets existing implementations connect without silently substituting behavior.
Array views must describe stable retained spans. Lifetime pinning and concurrent
mutation are outside the adapter. Count/build mismatch inputs remain unresolved.

[256 joined native comparisons](../../native/snow_host/pose_group_runtime_validation.json)
run the original group wrapper through counts, retained layout, settings, body
production, kind2 construction, numerical solve and both feedback paths. Entire
allocations, raw bodies, constraints and metadata match. Poststep arguments and
atan2 service arguments/call counts match. Cases cover single/paired endpoints,
translation/angular states0/1/2, hard/soft rows, optional drives, swaps and one
through three normal iterations. Native atan2 outputs are supplied; byte-fill and
poststep are services. Contact arrays are empty, damping is absent, and secondary
phase is disabled in this native composition check.

Public tests additionally exercise the secondary clear/update/restore sequence,
required damping resolution and the fixed-body damping bypass. Those tests are
independent implementation tests, not additional joined native comparisons.
Full mixed-contact group execution, poststep integration, allocation growth and
live player ownership remain distinct validation work.

## Mixed contact and constraint group runtime

`engine.pose_link_runtime.make_pose_link_services` binds contact construction,
contact-result feedback and secondary contact refresh to the same retained arena
used by `run_pose_group_runtime`. Construction appends only the six contact
categories0/1/4/5/6/7; it preserves all pose category counts. Result indices use
the shared arena counter, so later pose construction starts after contact results.
The callbacks do not run a separate solve. The group orchestrator performs one
shared normal solve, followed by contact and pose feedback in their native order.

Secondary refresh exposes only the two primary contact pools to the existing
refresh implementation and writes back their append counts. It does not change
pose category counts, switch phase, clear body state or solve independently; those
operations belong to the group orchestrator. Category views and results are rebuilt
from the retained header at each callback. Parsed body views must describe the
same state as the raw bodies supplied to the group runtime. Refresh those views
before reusing the adapter for a later tick; no automatic snapshot is implied.

[256 mixed native group comparisons](../../native/snow_host/pose_mixed_group_runtime_validation.json)
execute the original wrapper through contact/pose counting, retained layout,
settings, body production, both builders, shared numerical solve and all normal
feedback paths. Every context, body, constraint, metadata, link and payload byte
matches. One through four contact points are combined with every mode0..3 and
both endpoint layouts, covering multi-point shared rows as well as per-point
friction rows. Kind2 states0/1/2, hard/soft rows, drives, swap modes and one through
three iterations are included. Poststep and angle-service arguments also match.

Native atan2 outputs remain supplied; byte-fill and poststep are services. This
comparison excludes secondary phase, body integration, damping response, allocator
growth and concurrent ownership. Public composition tests cover all16 contact
count/mode combinations and secondary refresh preserving pose counts, but do not
upgrade the secondary path to a joined native validation claim.

## Joined secondary correction and poststep

`engine.pose_poststep_runtime.make_integrated_pose_poststep` binds the recovered
constructor-selected body poststep to raw group/body/metadata maps. The callback
reads group membership and inactive flag, resolves reached quiet override records,
then runs quiet aggregation, inactive transition, transform integration and resource
bounds refresh through the existing implementations. It publishes the group flag
back into retained storage. Resource bounds, link clearing and half-angle trig are
explicit services. Selecting this adapter selects the known body implementation;
it does not discover or implement arbitrary virtual classes.

The mixed runtime can pass `integrate_pose_body` as its secondary update service
with `scalar_sin_cos` for independent finite-range trig. Secondary application
exposes solved correction motion temporarily, integrates with scalar1, then
restores ordinary motion. Poststep subsequently integrates ordinary motion with
the context scalar if the group remains active. These are separate transform
updates with different state inputs, not duplicate ordinary integration.

[256 mixed secondary comparisons](../../native/snow_host/pose_mixed_group_secondary_validation.json)
extend the normal mixed test through original secondary refresh/solve and actual
body virtual integration. Whole retained arenas and bodies match; independent
sine/cosine arithmetic is used without replaying native trig values. Poststep is
still an explicit service in that receipt.

[256 joined poststep comparisons](../../native/snow_host/pose_mixed_group_poststep_validation.json)
continue through the actual native poststep, quiet aggregation, inactive method,
body transform integration and box-resource bounds. Complete retained context,
group, body, constraint, metadata, link, payload, resource, entry and local-transform
bytes match. There are58 inactive groups at return and479 changed body transforms
across the512 body instances. All four settings modes, one to four contact points,
both endpoint classes and one to three iterations in each phase are covered.
Native atan2 outputs remain supplied to the independent implementation; native
execution itself only substitutes byte-fill. Known body and box vtables execute
normally, including native scalar sine/cosine.

The fixtures have group contact links but empty per-body link rings. Therefore
inactive-link payload clearing and full membership consistency are not established
by this joined test. Damping, allocation growth, callback-driven membership
mutation, alternative resource/body classes, upstream invalid state exclusion and
live player ownership remain open. Public adapter tests check raw group-flag
publication, integration/bounds writes and quiet-override admission separately.

## Inactive body rings and contact retirement

`engine.pose_link_payloads.clear_pose_link_contacts` implements the raw no-transfer
wrapper RVA0x1958b90 and the corresponding branch of0x1958720. It captures the
link58 entry-array pointer and link60 count. Each16-byte entry contains a key and
payload token; nonnull payloads go to an explicit pool-return service. Later
entries are read when reached. After normal completion only link60 is cleared.
Capacity, pointer, keys and inactive entry bytes remain unchanged. A zero count
does not dereference the entry array. No exception rollback is invented.

Connected to `make_integrated_pose_poststep`, this completes the explicit clearing
route used by both endpoint body rings. A shared link can be visited twice during
a group inactive transition. The first visit clears its active payload count;
the second sees an empty span and does not request another release. The link
itself remains in the rings; payload clearing is not unlinking or link destruction.

[256 joined ring-retirement comparisons](../../native/snow_host/pose_mixed_group_retirement_validation.json)
repeat the complete mixed two-phase wrapper with one shared contact link present
in both body rings. All retained bytes and release order match.58 groups become
inactive, each requesting exactly one payload release despite visiting the shared
link from both endpoints. Active cases retain their payloads. Both next-pointer
branches are exercised. The protected payload pool-return block is supplied as a
recording service; its free-list mutation, synchronization and later reuse are not
validated. Native atan2 outputs also remain supplied to the reconstruction.

Parsed link views used by the build/count adapters must be refreshed from the
raw link before another tick. Retired array entries are still present but are
outside the cleared count. Reusing the old parsed count would incorrectly revive
released payloads. Public tests cover null skipping, shared-ring clearing, captured
span with later entry edits, empty-array admission and release failure behavior.

## Repeated retained group passes

`engine.pose_group_retained.read_retained_pose_group` rebuilds typed input views
from current raw group, body, metadata, constraint and link records. Group spans
supply current body/link/pose tokens. Link58/60 selects active16-byte contact entries;
bodyb8/c0 selects active72-byte resource entries. Zero counts skip array lookup.
Body transforms, motion, centers, indices and metadata class flags are reread.
Constraint kinds come from the supplied query and inline records are copied.
Inactive entries beyond a current count are not revived.

`run_retained_pose_group_pass` calls this reader, performs preparation and runs
the joined group runtime with shared contact services. All maps, retained storage,
profiles, resource resolution and reached services remain explicit caller inputs.
It returns the authored layout description. Each invocation uses new parsed views
so the previous pass's transform updates and payload-count clears are retained.
Within a pass records must be stable except for the modeled operations. Eager
parsing is authored adapter behavior and does not reproduce native read ordering
under callback mutation or imply an atomic live snapshot.

[256 four-pass native comparisons](../../native/snow_host/pose_repeated_group_validation.json)
execute1024 consecutive original wrapper calls, preserving native and independent
state separately between calls. Every retained byte matches after each call,
including layout changes following contact retirement. There are312 pass returns
with inactive group flags,89 total payload release requests and1507 changed body
transforms across2048 body-pass instances. Native angle inputs and release order
also match. No already-cleared contact is released again.

These are direct repeated group-wrapper calls. The test deliberately does not
infer whether an outer scheduler would admit an inactive group again. It also
does not regenerate terrain contacts, reactivate bodies or simulate native pool
reuse. Count/build invalid-state admission, damping, allocator growth, other body
classes and live ownership remain open. The supplied atan2 and pool-return service
boundaries remain unchanged. Public tests cover fresh frame/motion reads, cleared
contact spans,72-byte resource strides and four successive integrated passes.

## Group batch worker admission

`engine.pose_group_worker.run_pose_group_worker` reconstructs worker RVA0x18e31b0,
reached through thunk0x18e3340. It captures the job's source-context token at0,
scalar atc and settings token at10. Each work claim is an atomic fetch-add1 on the
caller's context448. The returned old uint32 index is compared to the captured
source context's current batch count440. These two context identities may differ.
The independent worker requires an explicit claim service;
`claim_pose_batch_serial` is only a serial equivalent, not a synchronization API.

Batch storage comes from source438, with16-byte descriptors: uint32 group count
at0 and pointer-array identity at8. The count is captured for each batch; its array
pointer is reread for each group. The actual dispatch is:

```text
while (index = fetch_add(owner.claim448, 1)) < source.batch_count440:
    batch = source.batch_array438[index]
    for group in batch's captured count:
        if settings.byte20 == 0 and uint32(group.link_count + group.pose_count) != 0:
            solve_group(group, reusable_request)
        else:
            if not (group.body_count == 1 and first_body.metadata52 bit3):
                advance_free_motion(group.body_span, request.scalar, settings.vector8)
            poststep(group, request.scalar, settings.byte14, thresholds34/38/3c)
if request.buffer:
    release(request.buffer)
```

The worker initializes one request with null buffer and zero capacity, reuses it
across solved groups, and releases its last buffer after exhausting claims. The
claim that discovers exhaustion still increments the counter. The free path
passes the complete settings14 byte to poststep, unlike the solver's bit0 flag
packing. A single fixed body skips free-motion advancement but still reaches
poststep. No group inactive-flag test occurs in this worker. Earlier selection
into the batch source must therefore be studied separately; this is not evidence
that the outer scheduler always processes sleeping groups.

[512 native worker comparisons](../../native/snow_host/pose_group_worker_validation.json)
execute the original lock-xadd loop with numerical solve, free-motion advancement,
poststep and final release as explicit recording services. All retained bytes,
service order/arguments, scratch reuse and release match. Coverage includes empty
and multiple batches, exhausted initial indices, differing context identities,
bypass bytes0/1/2, wrapped count sums, fixed-body shortcut and poststep bytes0/1/2/255.
These are worker-control comparisons, not a concurrent scheduler proof or an
uninterrupted worker-plus-numerical-solve receipt. The branch target0x1957590 is
free-motion update; its raw body arithmetic and batch formation remain next leads.

## Free-motion worker branch

`engine.pose_free_motion.advance_pose_free_motion` reconstructs RVA0x1957590.
Before traversing the retained body span it computes float32 delta=scalar*vectorXYZ.
A body with metadata52 bit3 is skipped. Otherwise its optional damping record
supplies four values. If the damping pointer is nonzero and scalar is nonzero,
the explicit library service receives base=1-damping and the scalar, producing
four multipliers. Without that call the multipliers are all1.

```text
applied = (0,0,0) if body.flagsaa bit3 else delta
linearXYZ = float32(float32(linearXYZ + applied) * multiplierXYZ)
angularXYZ = float32(angularXYZ * multiplierW)
```

The routine preserves transforms, metadata and other body fields. Duplicate body
tokens update repeatedly in array order. It does not integrate position itself;
that happens through the worker's subsequent poststep call. Scalar/vector inputs
are constant finite values in the independent contract. Damping-library arithmetic
remains explicit; no platform power function is silently substituted.

[512 native free-motion comparisons](../../native/snow_host/pose_free_motion_validation.json)
match all body/metadata bytes and damping service arguments.384 cases run without
a damping interception;128 allow the supplied response. Cases cover repeated
identities, empty spans, flags, zero/negative/positive scalars and pointer presence.

## Joined numerical batch worker

`engine.pose_worker_runtime.run_retained_pose_worker` binds the worker to fresh
retained parsing, group preparation, mixed numerical runtime and the free-motion
routine. It requires explicit claim, allocator, poststep and other reached
services. The allocator returns a token registered in the caller's buffer map.
For each solver group, required size comes from the recovered count/layout policy.
If it exceeds scratch capacity, the old buffer is released before allocation;
otherwise the existing buffer is reused. The worker releases its final buffer.
This adapter supports normal-return, sufficient nonwrapping storage and stable
class/resource views. It is not a concurrent mod host or native allocator.

[256 joined native worker comparisons](../../native/snow_host/pose_numerical_worker_validation.json)
run the original batch worker with two successive visits to a retained group.
Both solver and bypass routes execute their original numerical routines, including
poststep and box bounds. Complete retained numerical/group/body/link/resource
bytes, claim counters, allocation sizes, reuse, final release, contact retirement
and angle-service arguments match. Allocator storage, byte-fill and protected pool
return are supplied. Atan2 outputs remain explicit reconstruction inputs. Native
scalar sine/cosine is independently reproduced.

The repeated group is a synthetic fixture for worker scratch and state behavior,
not evidence that normal batch construction repeats groups. This receipt does
not validate allocator internals, live concurrency, damping inside the joined
worker, other body/resource classes or earlier active-list selection. Public tests
also cover a larger later group causing release-before-growth, but that growth
scenario is not part of the joined native receipt.

## Group batch formation

Binary-derived behavior: wrapper `0x18e2fb0`, ordering helper `0x18e2d00`,
comparator `0x18e19a0`. Independent implementation:
`engine/pose_group_batches.py`. Validation receipt:
[`pose_group_batches_validation.json`](../../native/snow_host/pose_group_batches_validation.json).

The source is the context's active group array, not a scan of every allocated
group. The wrapper captures its active count before reordering. The reorder helper
partitions groups whose uint32 contact-plus-pose sum is zero to the tail by swapping
with the last unpartitioned slot. It sorts only the nonzero prefix, then repairs
**every** active group's stored index. Zero-work groups remain active and receive
batch entries. The worker can therefore reach their free-motion branch.

For ordinary small counts, nonzero groups sort by descending work. The exact
comparator is signed32(uint32(work(second)-work(first))), where each work value is
itself a uint32 sum. Overflow is not equivalent to an unbounded integer comparison.
Equal-key order depends on the native CRT sorting implementation; our API requires
a sorting service instead of silently promising Python's stable order.

```python
original_count = context.active_count
partition_zero_work_to_tail()
sort_nonzero_prefix(descending_wrapped_work_comparator)
repair_all_active_group_indices()
context.batch_count = 0
index = 0
while index < original_count:
    if context.batch_count == context.batch_capacity:
        grow_batches(8 if capacity == 0 else uint32(2 * capacity))
    batch = append_batch(pointer_to_active_slot(index))
    accumulated = 0
    while index < original_count:
        group = active_groups[index]
        work = uint32(group.contact_count + group.pose_count)
        batch.count += 1
        accumulated = uint32(accumulated + max(1, work))
        index += 1
        if signed32(accumulated) >= 25:
            break
workers = min(dispatcher.worker_capacity, context.batch_count, 32)
for job in first_worker_jobs(workers):
    job.scalar = scalar
    job.settings = settings
context.claim_counter = 0
if workers:
    dispatch(workers, worker_thunk, context.job_table)
context.batch_count = 0
transfer_completed_groups(context)
```

For example, work values `[13,12,1,0,0]` produce batches of two and three groups.
The first reaches25; the second costs3 because zero-work groups still cost one.
A group of work40 occupies one batch by itself.26 zero-work groups produce batches
of25 and1. These values are scheduling weights, not simulation substeps or elapsed
milliseconds. Large wrapped values can make the signed accumulator negative;
public tests preserve this branch rather than imposing a new upper bound.

Batch records contain a count and a pointer into the active group array. They do
not copy group identities. Callers connecting these records to the retained worker
must provide views of that array at each batch's starting address. Storage must
remain valid through dispatch. This wrapper writes scalar/settings fields in
existing worker jobs; it does not initialize their owner pointers. It resets the
claim counter even if the dispatcher admits zero workers, clears the batch count
after dispatch returns, and then invokes completed-group transfer. These are
observed sequencing rules, not proof of the dispatcher's synchronization internals.

The512-case offline comparison executes the original partition, original CRT sort
and complete retained-capacity wrapper. Only dispatch and completed-group transfer
are recording services. Every context/group/array/batch byte matches, including
unused padding and unused job fields. The comparison also checks state at dispatch,
before the final batch-count reset. Cases use0–80 groups, distinct small nonzero
weights, zero-work tails, seven worker capacities and three scalar signs. No live
game was launched. Public tests cover growth requests, wrapped counts, signed
accumulation and worker limits. Native allocation growth, equal-key CRT ordering,
concurrent dispatch, job construction and completed-group transfer remain outside
this validation.

## Completed-group transfer

Binary-derived routines `0x18e3350` and `0x18e1740` supply the completion stage
called after the batch wrapper clears its batch count. Implementation:
`engine/pose_group_transfer.py`. Receipt:
[`pose_group_transfer_validation.json`](../../native/snow_host/pose_group_transfer_validation.json).

The context's transfer-enable byte gates the entire operation. When enabled, the
routine walks the original active indices backwards. Every group whose inactive
byte is nonzero is removed using its stored index. The last active pointer fills
that slot, and the moved group's index is repaired when the slot is still active.
The removed group's index becomes its insertion index in the inactive collection.
Its body tokens are then appended to the context's tracked-body collection.

```python
if context.transfer_enabled:
    for index in reversed(range(context.active_count)):
        group = context.active_groups[index]
        if not group.inactive:
            continue
        context.active_count -= 1
        context.active_groups[group.index] = context.active_groups[context.active_count]
        if group.index < context.active_count:
            context.active_groups[group.index].index = group.index
        group.index = context.inactive_count
        append_inactive_with_growth(group)
        append_tracked_bodies_with_growth(group)
```

The inactive flag stays set. Stale array tails are not erased, and body tokens are
not deduplicated. There is no special-group exemption at this boundary, unlike the
existing wake/finalize path. No body-reset callback, integration or contact-clear
callback occurs here. The index changes ownership from the active collection to
the inactive collection. The active-group list must have consistent indices on
entry; the routine does not validate or reconstruct them.

Inactive storage grows from zero capacity to8, otherwise doubles. Tracked storage
instead grows from zero directly to the needed body count; nonzero capacity doubles
until sufficient. The helper captures group body count and prior tracked count
before growth, then reloads both pointer arrays while copying. Growth callbacks
may therefore replace storage. The independent implementation rejects a doubling
sequence that wraps to zero and cannot terminate; this is an authored guard, not
a native exception path. Ordinary well-formed counts do not reach that guard.

512 native comparisons match all context, group and array bytes, including unused
tails and relocated arrays. They cover2262 group transfers and1160 growth requests.
The original transfer and body-append instructions execute unchanged; only the two
storage-growth helpers are supplied. Those services relocate storage, preserve
retained bytes and record requested capacities. Native allocator internals remain
outside this result. Public tests additionally connect transfer to batch completion
across two passes: a synthetic inactive outcome removes that group from the next
pass and does not append its bodies again. This composition test is not a live
sleep/wake observation or proof of dispatcher synchronization.

## Dispatcher claim and completion counters

The batch wrapper calls `0x18b7ca0`. Its independent control-flow implementation is
`engine/pose_dispatch.py`; receipt:
[`pose_dispatch_validation.json`](../../native/snow_host/pose_dispatch_validation.json).
The routine is synchronous at its completion-counter boundary. It does not return
merely because the queue has been emptied or every callback has been claimed.

The dispatcher admits the unsigned minimum of requested workers and its configured
capacity. With one worker, it directly invokes the callback with argument-table
entry0, or null if no table was supplied, and a true caller-thread flag. With more
workers, it searches32 completion slots. A successful compare-exchange reserves a
zero unfinished counter with worker_count-1 and initializes a separate unclaimed
counter to the same value. Both exclude the callback run directly by the caller.

Each remaining worker gets a24-byte queued record containing a tag, completion-slot
index, callback pointer and argument. The caller publishes these records and calls
an opaque notification path for each corresponding worker handle. It then invokes
its own callback. While its unclaimed counter is positive, it helps consume queued
records. For each record it decrements that record's unclaimed counter, invokes the
callback with the caller-thread flag true, then decrements the unfinished counter.
It may therefore help records belonging to another completion slot. This helper
path does not test the record tag. It exits queue-help if no complete record is
available, then polls its own unfinished counter and enters an opaque wait/yield
path until that counter is nonpositive.

```python
workers = min(requested, dispatcher.capacity)
if workers == 1:
    invoke(callback, argument(0), caller_thread=True)
    return
slot = reserve_zero_unfinished_slot(workers - 1)
unclaimed[slot] = workers - 1
for index in range(1, workers):
    publish(tag, slot, callback, argument(index))
    notify(worker_handle(index))
invoke(callback, argument(0), caller_thread=True)
while signed32(atomic_read(unclaimed[slot])) > 0:
    record = try_take_complete_record()
    if record is None:
        break
    atomic_decrement(unclaimed[record.slot])
    invoke(record.callback, record.argument, caller_thread=True)
    atomic_decrement(unfinished[record.slot])
while signed32(atomic_read(unfinished[slot])) > 0:
    wait_or_yield()
```

A separate inspection of worker-consumer block `0x18b80f9` confirms the same
before/after callback decrements, but passes a false caller-thread flag. Its broader
wait loop and other record types are not implemented here. The pose worker thunk
`0x18e3340` ignores that flag: it takes the argument as a job record, loads the owner
from that record and enters the existing group batch worker. Thus the argument
pointer table and initialized job owner fields remain necessary inputs.

The counters have distinct meanings. If two queued callbacks have been claimed
but are still executing, unclaimed is0 while unfinished remains2. The caller stops
helping its queue but still waits. Only callback return decrements unfinished.
Under valid counter ownership and successful normal-return callbacks, this gives
the batch wrapper the completion boundary needed before resetting batch count and
transferring inactive groups. It does not establish safe scheduler mutation or
live object ownership for arbitrary mods.

256 offline native comparisons execute the original dispatcher, queue publication,
queue reads and atomic instructions. Whole dispatcher bytes and event sequences
match. Counter snapshots at callbacks and simulated external completion match too.
Cases include single-worker dispatch, admission caps, occupied slots, null argument
tables, caller-help, ring split-copy and uint32 cursor wrap. Scripted external
workers claim jobs during notification but delay completion until the wait service;
334 wait-service calls occur across the comparison. No concurrent native threads
or live game are involved.

Opaque notification and wait blocks, callback execution and memcpy are supplied
services. The notification boundary includes a post-call marker byte; the wait
boundary includes its stack adjustment. Their platform/protected implementations
are not decoded by this experiment. The public dispatcher requires explicit
atomic and queue services. Its serial atomic adapter is only for tests, not a
thread-safe implementation. It rejects zero admitted workers and exhausted slots
with authored errors; native behavior for those invalid admissions is not asserted.
Callback exceptions, cancellation, nested dispatch, starvation, slot reuse races
and platform memory-order guarantees remain unresolved integration questions.

## Joined retained batch execution

`engine/pose_batch_runtime.py` joins group ordering and batch construction,
dispatcher publication/completion policy, the pose worker thunk, retained numerical
workers and completed-group transfer. It accepts the existing worker service map
and explicit dispatcher queue/atomic/notify/wait services. It does not allocate
threads, install a game hook or infer job ownership. Job records must alias the
context fields updated by batch construction. The argument table supplies those
job addresses, and each job's owner pointer must already be initialized.

The authored `RetainedPointerArrays` adapter resolves aligned interior pointers
into supplied arrays. This matters because each batch points to its first slot
inside the active-group array. A copied list would hide later slot changes. The
adapter returns a view of retained slots, resolves replacements on a new lookup,
and rejects ambiguous overlapping interior spans. Exact registered bases take
precedence. It supplies address resolution, not an original allocator or class.

Call `run_retained_pose_batch_pass` with a context token, dispatcher record, scalar,
settings token, callback identity, aliased job map, worker services and dispatcher
services. Sorting and both storage-growth policies remain explicit. The callback
adapter reads each job's owner pointer and invokes the numerical worker; unrelated
callbacks encountered during queue-help require an explicit alternate callback
service. Completion then transfers inactive groups using the same retained lists.

[`pose_joined_batch_validation.json`](../../native/snow_host/pose_joined_batch_validation.json)
records256 comparisons beginning at the original batch wrapper. Native execution
continues through the original dispatcher, thunk, batch worker, solver/free-motion
route, body/contact/kind2 construction, numerical solving and feedback, secondary
correction, poststep integration/box bounds, contact retirement and final group
transfer. The caller executes its direct callback and the remaining queued
callback. The complete solver allocation, retained records, world/job/batch state,
dispatcher ring/counters and active/inactive/tracked arrays match. Allocation and
release requests and angle arguments match too.

Each fixture contains one physical group and30 empty groups, enough to form two
batches. Empty groups are synthetic work-distribution fixtures, not a claim about
normal live topology. Across these cases439 body transforms change and56 physical
groups become inactive. Solver and bypass routes, quiet checking, all four contact
settings modes and both endpoint layouts are covered. Separate public tests run
two consecutive composed passes and verify that retired groups produce no further
body updates or scratch allocations on the next empty pass.

Native allocation, notification, standard byte-copy/fill and protected pool return
remain supplied services. Atan2 output is observed from the native routine and
supplied to the independent numerical path. Storage capacity is retained; only the
known constructor-selected body and box-resource implementations are exercised.
This is offline normal-return composition, not live ownership, concurrent replay,
all-body-class fidelity, native job construction or a complete engine frame.

Run the public composition tests with:

```sh
python3 -m unittest discover -s tests -p 'test_pose_batch_runtime.py'
```

## Context job construction

The pose context constructor begins at `0x18e0ca0`. Its job-initialization loop is
`0x18e0dda..0x18e0e17`, after special-group creation and collection initialization.
`engine/pose_context_init.py` reconstructs that loop and the visible constructor
tail beginning at `0x18e0d46`. This narrows the earlier job-construction gap: owner
pointers and argument-table relationships are now directly evidenced. Earlier
allocation, protected calls and vtable assignment remain outside the new API.

For every index from0 through31, the loop performs these writes:

```python
job_offset = 8 + 24 * index
context.job_at(job_offset).owner = context_token
context.job_at(job_offset).index = index
context.argument_table[index] = context_token + job_offset
```

Within each24-byte job, owner occupies bytes0–7 and index occupies bytes8–11.
Bytes12–15 hold scalar and bytes16–23 hold settings, but **this constructor loop
does not initialize them**. Batch submission fills those fields for admitted
workers. The argument table begins at context+0x308 and contains32 pointers to the
same records, not copies. Native pose dispatch ignores its caller-thread flag and
uses the job owner to enter the already reconstructed worker.

The preceding visible tail clears active/inactive/batch descriptors and other
observed collection fields, clears the batch claim counter, and sets transfer-enable
byte+0x44c to1. It then calls the inactive-marking helper for each of the two special
groups already stored at+0x408 and+0x410, before initializing jobs. Padding is not
blanket-zeroed. The independent tail accepts inactive marking as an explicit
service; it must only be applied during construction, not to an active context.

`bind_pose_jobs` is an authored convenience adapter. It returns a map of job tokens
to memoryviews and a pointer-table sequence that reads the retained bytes on every
access. Thus batch writes are visible to worker invocation, and later pointer-table
changes are visible without rebuilding a copied list. The storage must outlive
these views and cannot be resized while they exist. Example wiring:

```python
initialize_pose_jobs(context, context_token=context_token)
binding = bind_pose_jobs(context, context_token=context_token)
arrays[binding['table_token']] = binding['arguments']
# Supply binding['jobs'] as jobs to run_retained_pose_batch_pass.
```

[`pose_context_init_validation.json`](../../native/snow_host/pose_context_init_validation.json)
records512 comparisons of the original tail and original inactive-marking helper,
with no instruction interception. The two special groups use the previously
validated group constructor and have zero body entries. Every context and special
group byte matches, including randomized untouched job scalar/settings fields and
padding. This does not test inactive marking on populated special groups or the
constructor's earlier protected allocation paths.

The joined256-case batch comparison was rerun using the new initializer and aliased
pointer-table adapter; every prior comparison still passes. Public tests cover all32
job identities, final job scalar/settings aliasing, pointer-table rereads, callback
order, second special-pointer reload and untouched padding. The local construction
join is now covered; concurrent ownership and live lifetime are still unresolved.

A newly inspected upstream caller at `0x18b9710` places batch execution inside a
larger stage. It sets its own phase field to3, performs several preparation calls,
passes changed membership to the context, publishes pending links to another
interface, obtains settings and calls the batch wrapper. Afterward, if active groups
remain, it calls a downstream interface and finally resets its phase field to0.
This is a static lead for the next integration boundary, not yet an implemented or
native-compared outer stage.

## Outer pose update stage

`engine/pose_update_stage.py` reconstructs the normal-return service ordering of
`0x18b9710` and the two-collection preparation driver `0x18b9830`. The outer stage
sets its phase field to3, prepares constraints, obtains a body source, invokes the
body update with the observed callback identity, runs three contact-stage calls,
attaches the changed link span, publishes pending links, obtains settings and runs
the pose batches. It tests the **post-batch** active-group count before a downstream
notification, then resets phase to0. It is not an exception cleanup guarantee.

```python
owner.phase = 3
prepare_constraints(owner, scalar)
update_bodies(get_body_source(owner.provider), scalar, body_callback)
begin_contacts(owner.contact_stage)
update_contacts(owner.contact_stage, scalar)
finish_contacts(owner.contact_stage)
attach_links(owner.context, owner.changed_links.span)
pending = capture_pending_span(owner.context)
for slot in pending:
    publish_link(owner.interface, slot.link + 8 if slot.link else null)
settings = get_settings(owner.provider)
run_batches(owner.context, scalar, settings)
if owner.context.active_count != 0:
    notify_active(owner.interface, null)
owner.phase = 0
```

The implementation reloads the owner's provider/context/interface/contact pointers
at their observed uses. Pending span bounds are captured once; each slot and the
interface pointer are read when reached. Publishing null links passes null, not8.
Callbacks can change later slots, and a batch callback can replace the context
whose active count is checked. Public tests preserve these differences.

The preparation driver computes float32(1.0 / scalar) once. It captures the first
collection count, fetches and prepares each indexed constraint, then obtains the
second collection count and repeats. The provider pointer is reloaded before each
getter. The two loops are ordered; they are not one concatenated snapshot. Positive
and negative zero produce signed infinities under the tested native floating-point
mode. No local clamp or zero guard appears. This does not establish whether callers
can legitimately submit zero. NaN payloads, floating-point status flags and other
MXCSR modes remain outside the independent arithmetic contract.

The individual constraint preparation call at `0x19445c0` remains an explicit
service. Static inspection shows endpoint metadata-bit gates, endpoint swapping,
a callback stored in the constraint record, and a returned count capped by resetting
values above6 to0. Its callback/data semantics are the next numerical producer to
resolve; they are not implemented by the outer-stage ordering model. Changed-link
attachment at `0x18e2200` likewise includes wake, endpoint migration and group merge
services that still need binding to the existing retained group implementations.

[`pose_update_stage_validation.json`](../../native/snow_host/pose_update_stage_validation.json)
records512 original outer-stage comparisons with subsystem calls supplied as
recording services. All service arguments/order, phase observations and retained
bytes match. It covers empty and populated pending spans, null/wrapped link-pointer
conversion, scalar signs and post-solve active-count changes.
[`pose_collection_prepare_validation.json`](../../native/snow_host/pose_collection_prepare_validation.json)
records256 original preparation-driver comparisons. Reciprocal float32 bytes and
both collection loops match, including signed-zero division.

These receipts establish local orchestration and reciprocal preparation, not a
complete numerical outer-stage execution. The already validated retained batch
API can be supplied as run_batches; body/contact preparation, changed-link effects,
publication interfaces and provider lookups remain explicit. No live game session
or concurrent ownership proof is part of this pass.

## Command preparation producer boundary

The preparation service `0x19445c0` belongs to the kind4 command constraint. Its
output count at+0x74 and six64-byte records at+0x78 feed the existing
`build_pose_command_constraint` directly. `engine/pose_command_prepare.py` now
implements the visible wrapper and the six-record initializer `0x19440c0`.

The first endpoint's metadata byte+0x52 bit0 blocks preparation when set. A nonnull
second endpoint applies the same gate. These checks happen before endpoint swapping.
If blocked, the wrapper returns without clearing the old count or command bytes.
When admitted, any nonzero swap byte reverses the callback's two endpoint arguments,
including the case where the original second endpoint is null. Callback arguments
are the stored function, ordered endpoints, writable command span, writable count,
reciprocal scalar, mode1, and the stored user-data token. The count is not reset
before this update call.

```python
if first.metadata.flags52 & 1:
    return
if second is not null and second.metadata.flags52 & 1:
    return
callback_first, callback_second = (second, first) if swap else (first, second)
callback(callback_first, callback_second, commands, count,
         reciprocal_scalar, mode=1, userdata=userdata)
if uint32(count) > 6:
    count = 0
```

That unsigned check resets both7 and UINT32_MAX to0. It changes only the count,
leaving produced bytes intact. It is a post-call validity check, not buffer-overrun
prevention. A callback must respect the six-record allocation itself. The earlier
row builder's independent six-command storage guard is still needed for inputs
that have not passed through this preparation path; the builder itself does not
clamp. Gated updates and deserialized records are distinct paths.

Each64-byte command contains four XYZ vectors followed by four scalar words. The
initializer zeroes all vector components and sets the scalars to0, negative largest
finite float32, positive largest finite float32, and0. The row builder expands each
XYZ to XYZ0 and broadcasts each scalar into four lanes; it swaps endpoint vector
pairs when the constraint swap flag is set. Public composition tests pass callback
outputs through that existing expansion and check count/reset behavior. Callback
math and user-data meaning remain supplied, not inferred from the output layout.

Static constructor inspection adds a lead. `0x19441e0` stores its supplied callback
and user data, chooses endpoint ordering, clears the count, and invokes the callback
with scalar0 and mode0. Unlike the update wrapper, this inspected construction path
does not perform the same post-call six-count reset. The cloning path `0x1944340`
copies callback and user-data identities from an existing constraint before calling
that constructor. A default constructor instead stores a null callback. Concrete
gameplay callback assignment remains unresolved; the construction/cloning evidence
does not identify animation, tricks or player ownership.

[`pose_command_prepare_validation.json`](../../native/snow_host/pose_command_prepare_validation.json)
contains512 update comparisons, including171 admitted callback calls, and512
initializer comparisons. All retained bytes match. The update check supplies the
callback's output and verifies argument order, raw pointers, previous output bytes,
metadata gates and final count. The original initializer executes without
interception. Construction-time callbacks, deserialization validity, actual callback
production and live concurrency remain outside these checks.

## Command creation and callback modes

`construct_pose_command_constraint` now reconstructs specialized constructor
`0x19441e0` with the base constructor and callback supplied. It calls base
construction with the requested bodies, owner token and low request byte. Base
construction may reorder the stored endpoints. The specialized layer installs its
two tables, initializes six command records, stores callback/userdata, and sets its
swap byte according to whether the requested first body differs from the stored
first body.

The single-body flag is1 if the stored second endpoint is null or its metadata
word+0x50 bit15 is clear, otherwise0. This flag uses stored endpoint order. The
callback instead receives endpoints after the swap correction. The constructor
clears the count and calls the function with scalar0 and mode0. It does not apply
update-time metadata bit0 gates or the update-time unsigned six-count reset.

```python
construct_base(constraint, requested_first, requested_second, owner, request_byte)
initialize_six_command_records()
constraint.callback = callback
constraint.userdata = userdata
constraint.swap = requested_first != constraint.stored_first
constraint.single = stored_second is null or not stored_second.metadata.bit15
constraint.count = 0
callback(ordered_endpoints, commands, count, scalar=0, mode=0, userdata=userdata)
# No post-call count reset here.
```

This preserves the callback's two-mode contract. Mode0 supplies initial rows; mode1
refreshes them during the reciprocal-scalar preparation stage. These mode numbers
are observed arguments; their names do not establish what an arbitrary callback
computes. An invalid count from construction can still fail the independent row
builder's storage guard. The reset in the update wrapper is not a universal factory
invariant and must not be moved into the common callback adapter.

[`pose_command_construct_validation.json`](../../native/snow_host/pose_command_construct_validation.json)
records512 full specialized-constructor comparisons. The native initializer runs
unchanged. Supplied base construction varies endpoint order, and the callback
produces counts0/1/6/7/UINT32_MAX. Whole records and call arguments match, including
initial command defaults, cleared count, scalar/mode, userdata, null endpoints,
metadata single-mode selection and request bytes. Base construction's registration,
wake and ordering effects remain explicit services, not reconstructed by this test.

The cloning function `0x1944340` is referenced by the command constraint's table and
carries source callback/userdata into construction. The default constructor is
reachable through generic type allocation and initializes a null callback. A raw
search for direct writes to offset+0x1f8 produced many unrelated object fields;
no concrete gameplay producer was identified. Such offsets alone are not evidence
of a command callback assignment. Next evidence should come from indirect factory
callers, resource registration, or a guarded observation of actual registered
constraint objects. No animation/trick/player attribution is established here.

## Command registry to preparation

`prepare_retained_pose_commands` now binds the preparation driver to retained
provider records. The owner field+0x20 identifies the provider. Its first command
span is pointer+0x70/count+0x78; its second is pointer+0x80/count+0x88. The getters
at `0x18d02e0`, `0x66cd60`, `0x18d02c0` and `0x18d02d0` directly read these fields.
Each active slot identifies the command constraint passed to preparation.

```python
first_count = current_provider.first_count
for index in range(first_count):
    constraint = current_provider.first_array[index]
    prepare_command(constraint, reciprocal_scalar)
second_count = current_provider.second_count
for index in range(second_count):
    constraint = current_provider.second_array[index]
    prepare_command(constraint, reciprocal_scalar)
```

The implementation reuses the existing reciprocal driver and command wrapper.
It does not snapshot both lists together, remove duplicate identities or skip a
constraint merely because it was visited earlier. A changed later slot is read
when reached. This joins actual provider storage to the callback ABI and six-count
handling; it does not invent callback calculations.

Static registration inspection gives a stronger ownership lead than offset-store
searches. At `0x18cffe0`, a supplied constraint is appended to the general collection
at provider+0x60, passed to `0x195c170` with argument2, then queried through its kind
virtual method. Kind4 is additionally appended to provider+0x70. At `0x18d0080`, an
object is appended to provider+0x50; its child-pointer span+0x58/count+0x60 is scanned,
and children reporting kind4 are appended to provider+0x80. The inspected code
establishes individual versus child-derived registration, but does not establish
that the child-owning object is a player, animation rig or physics group.

Both paths grow collections when full. Deserialization also writes provider command
spans, so ordinary registration is not necessarily their sole producer. Those
registration/growth/deserialization paths remain static leads here, not implemented
by the retained preparation adapter. A future runtime observer can follow the
owner's provider and these active spans, then inspect each constraint's callback
and userdata fields. It must validate live object identity and lifetime rather than
reuse stored addresses. This pass launches no game and installs no observer.

[`pose_command_registry_validation.json`](../../native/snow_host/pose_command_registry_validation.json)
records512 original preparation-driver comparisons with original provider getters
and original per-constraint wrapper executing. Only the registered callback is
supplied.688 callbacks are admitted across the fixtures. Whole constraint/body/
metadata bytes and callback order/arguments match, including previous output bytes,
reciprocal scalars, gates, swapping, and count resets. Fixtures vary both collection
counts from0 through4 and include repeated identities across the lists. Those
repetitions are synthetic coverage, not a claim about normal live topology.
Public composition tests additionally mutate a later slot during callback execution.

This removes provider lookup and individual preparation as supplied services in the
joined adapter. Concrete gameplay callback production, registration effects,
deserialization validity and concurrent ownership remain unresolved.

## Command registry population

`engine/pose_command_registry.py` reconstructs individual registration
`0x18cffe0` and child-container registration `0x18d0080`. This supersedes the prior
static-only classification of these two paths; their allocation and notification
services remain supplied.

Individual registration appends the constraint to the provider's general collection
at+0x60, calls the observed notification helper with argument2, then asks the
constraint's virtual kind method. Only kind4 is appended to the first command list
at+0x70. Kind lookup happens after notification, not before it. Collection append
reloads pointer/count after growth. Neither path rejects duplicate identities.

```python
append(provider.general_constraints, constraint)
notify(constraint, 2)
if get_kind(constraint) == 4:
    append(provider.first_command_list, constraint)
```

Container registration captures the provider's object-list count before growth,
appends the supplied object at+0x50, then captures that object's child count+0x60.
For each child it reloads the child-array pointer+0x58, reads the slot, asks its kind
and appends kind4 to the second command list at provider+0x80. It returns the
original object-list insertion index. Changing the source child count during a
callback does not change the captured loop bound; changing the array pointer can
change later visited children. The object's semantic class remains unresolved.

```python
insertion_index = provider.objects.count
append(provider.objects, container)
child_count = container.child_count
for index in range(child_count):
    child = container.current_child_array[index]
    if get_kind(child) == 4:
        append(provider.second_command_list, child)
return insertion_index
```

All inspected append sites request capacity8 when empty, otherwise double the
uint32 capacity. Growth is invoked only when count equals capacity. The independent
API requires the service to preserve active slots and publish the new pointer and
capacity. It does not reinterpret corrupted count/capacity combinations or provide
native allocation semantics. Notification behavior remains supplied; argument2 is
an observed value, not an inferred wake/sleep label.

[`pose_command_registration_validation.json`](../../native/snow_host/pose_command_registration_validation.json)
contains256 individual and256 container comparisons. The original routines execute
with recording kind/notification services and relocating storage-growth services.
Every provider/object/constraint/array byte matches, including inactive tails and
relocated arrays. Service ordering, growth requests and the insertion-index return
match. Fixtures cover noncommand kinds, zero through eight child entries, existing
collection entries, repeated identities and growth/no-growth cases.

Public composition tests register an individual command and a container containing
that same command plus a noncommand child, then run the retained preparation API.
Both registered command entries reach preparation in list order; the noncommand
child does not. This is executable registration-to-preparation composition on
synthetic data. Removal, actual notification effects, deserialization, object
lifetime and concrete gameplay callback discovery remain outside the result.

## Endpoint ring registration and removal

The previously opaque registration service `0x195c170` is now decoded: it attaches
a record to circular lists on both endpoint bodies. It is not a generic wake/event
notification. `engine/pose_endpoint_rings.py` implements insertion and the matching
removal `0x195c270`, including body-head accessors `0x18baba0` and `0x18bb430`.
The existing registration API keeps its `notify` keyword for compatibility; callers
can bind it directly to `attach_pose_endpoint_rings`.

Selector2 reads/writes body+0x90, selector1 body+0x80, and selector0 body+0x88.
Individual command registration passes2, establishing its body+0x90 linkage.
A record's first endpoint uses next/previous fields+0x20/+0x28; its second uses
+0x30/+0x38. For a neighboring record, the routine chooses first-endpoint fields
only if that neighbor's endpoint+8 equals the body being processed. Otherwise it
uses second-endpoint fields. There is no general ring-node abstraction in the
observed representation: the same constraint carries links for two different bodies.

Insertion processes first endpoint then second. An empty body head becomes the
new record, whose endpoint links both point to itself. For a populated ring, the
record is inserted immediately after the head: it points forward to the head's
successor and backward to the head, then the two neighbors are repaired. The body
head remains unchanged.

```python
for endpoint_port in [first, second]:
    body = record.endpoint(endpoint_port)
    head = body.head(selector)
    if head is null:
        record.next(endpoint_port) = record
        record.previous(endpoint_port) = record
        body.head(selector) = record
    else:
        following = head.next_for(body)
        record.next(endpoint_port) = following
        record.previous(endpoint_port) = head
        head.next_for(body) = record
        following.previous_for(body) = record
```

Removal repairs the predecessor's next link and successor's previous link. If the
removed record was the body head, the head becomes its predecessor, not its
successor. A singleton clears the body head. After both endpoints are processed,
all four record linkage fields are zeroed. Endpoint identities and unrelated body
head fields remain unchanged. Provider list removal is a separate operation.

[`pose_endpoint_rings_validation.json`](../../native/snow_host/pose_endpoint_rings_validation.json)
compares512 fixtures containing one through eight records across four bodies.
The original insertion/removal and accessors execute without interception. Every
body/record byte matches after each operation:4608 operation comparisons total.
Random endpoint orientation and insertion/removal order cover singleton and larger
rings, both neighbor endpoint layouts, and head/non-head removal. All selected body
heads are empty after removing every record. A public composition test replaces
the individual-registration service with actual reconstructed ring insertion.

The valid tested domain has distinct, valid endpoint bodies and consistent rings.
The native helper does not special-case a null endpoint. How any nullable command
constraint is admitted to this registration path remains an upstream question.
Duplicate insertion and repeated removal are not made idempotent by this model.
Earlier mocked registration tests showing duplicate provider entries do not prove
that duplicate structural insertion is safe. No synchronization, live ownership,
reclamation or arbitrary concurrent mod mutation is established by these checks.

## Individual registration removal

`unregister_pose_constraint` reconstructs provider removal `0x18d0e30`. It first
searches the general collection at+0x60 for the first matching identity and retains
that index. It then queries the constraint kind. For kind4, it searches the first
command list at+0x70, decrements its active count and fills the matching slot with
the last active pointer. It calls selector2 endpoint-ring detachment before
performing the corresponding swap removal in the general collection.

```python
general_index = first_match(provider.general_constraints, constraint)
if get_kind(constraint) == 4:
    command_index = first_match(provider.first_command_list, constraint)
    swap_remove(provider.first_command_list, command_index)
detach_endpoint_rings(constraint, selector=2)
swap_remove(provider.general_constraints, general_index)
```

The general collection's pointer/count are reread after ring detachment, but the
search index is the value captured earlier. Neither list tail is cleared. Only the
first matching identity is removed. This does not make duplicate structural
registration safe; the separate ring membership invariants still apply.

The native search uses UINT32_MAX when an identity is absent, then continues into
count decrement and indexed writes. The independent API raises ValueError for a
missing required membership instead. This is an authored guard, not a recovered
native exception. The reconstruction is not transactional: callback failure or an
invalid concurrent mutation can leave earlier changes applied. Valid serial
membership is the tested contract.

[`pose_command_lifecycle_validation.json`](../../native/snow_host/pose_command_lifecycle_validation.json)
compares512 fixtures across4608 registration/removal operations. Original provider
registration, provider removal, endpoint-ring insertion/removal and body-head
accessors execute without instruction interception. A small authored fixture
virtual method returns each record's supplied kind; it does not stand in for a
claimed original class implementation. Every provider/body/constraint/array byte
matches after every operation, including stale tails and unrelated fields. Cases
cover one through eight records, all six supplied kinds, mixed endpoint orientation,
random registration/removal order, and first/middle/last list slots. Storage remains
within retained capacity8. Native growth was separately tested as a service, not
retested inside this joined lifecycle result.

Public composition tests now register and unregister using the real reconstructed
ring operations. Both active collection counts and selected body heads return to
zero, while endpoint links are cleared. No destructor or free call occurs in this
provider removal routine. Static base-destructor inspection at `0x19a1670` separately
checks whether the first ring-link field is nonzero before invoking detachment;
its remaining registration/notification/free behavior is not covered here.

Container removal is not interchangeable with individual removal. A separate
inspected path around `0x18d11a9` removes kind4 children from the second command list,
checks endpoint metadata bit0 and appends eligible children to another output
collection for later work, before removing the registered container. That broader
path includes body processing and remains a separate reconstruction task. Live
ownership, safe reclamation and concurrent mod mutation remain unresolved.

## Container removal and deferred children

`unregister_pose_constraint_container` reconstructs `0x18d1130..0x18d1369`.
The earlier container-removal gap is now narrowed to its supplied body/tree
services and allocation. This is a separate operation from individual removal.

```python
body_count, saved_index = container.body_count, container.index
for i in range(body_count):
    body = reload(container.bodies)[i]
    if body.metadata.flags52 & 8:
        remove_tree_body(provider.tree, body)
    process_body(provider, body, output)
child_count = container.child_count
for i in range(child_count):
    child = reload(container.children)[i]
    first, second = child.endpoints  # captured before virtual kind query
    if get_kind(child) == 4:
        swap_remove_first_match(provider.second_command_list, child)
    if first.metadata.flags52 & 1: continue
    if second and second.metadata.flags52 & 1: continue
    append(output, child)
swap_remove_at(provider.containers, saved_index)
old_owner = container.owner
container.owner, container.backlink, container.index = 0, 0, UINT32_MAX
if saved_index < provider.container_count:
    moved = provider.containers[saved_index]
    moved.owner, moved.backlink, moved.index = old_owner, provider + 8, saved_index
```

Body count and insertion index are captured before services. Child count is
captured after body processing. Both array pointers are reread on each iteration;
endpoint metadata pointers are read after the kind query even though endpoint
identities were captured before it. Kind4 removal occurs even when metadata later
blocks output queueing. The queue is deferred work, not proof of destruction.

Output storage grows from zero to8, otherwise doubles, with alignment16/tag0x19.
The wrapper supplies allocation, then writes capacity and clamps count before
appending. It rejects uint32 allocation-size overflow instead of reproducing
unsafe wrapped allocation. Missing child membership and invalid container indices
also have authored errors. Earlier changes remain applied if a service fails.
The removed-index constant at `0x29ca0f8` is UINT32_MAX in the inspected image.

[The native comparison receipt](../../native/snow_host/pose_container_removal_validation.json)
covers512 fixtures and767 queued children, matching all retained bytes and body/tree
service order. Cases include first/middle/last removal, zero through eight children,
metadata gates and nullable second endpoints. Tree removal and body processing are
recording-only services in this comparison. Output capacity is retained, so native
allocation is not validated here. Public tests separately exercise relocating
allocation and mutation-sensitive count, pointer and endpoint capture rules.

The body service at `0x18d0cf0` has a further inspected lead: it walks selector2
endpoint rings, removes cross-owner constraints through individual unregistration,
then queues or destroys them according to output availability and metadata gates.
It restarts from the body's current head after removal. This service has not yet
been reconstructed or included in this native comparison. Tree removal at
`0x19598d0`, live lifetime and concurrent mutation remain separate work.

## Cross-owner body ring processing

`process_pose_body_constraints` reconstructs `0x18d0cf0..0x18d0e24` and closes the
body-processing service described in container removal above. It uses the existing
individual unregistration and endpoint-ring detachment implementations.

```python
edge = anchor = body.head90
while edge:
    first, second = edge.endpoints
    first_owner = first.metadata.owner20
    second_owner = second.metadata.owner20 if second else 0
    if not second_owner or first_owner == second_owner:
        edge = edge.first_next if body == first else edge.second_next
        if edge == anchor: break
        continue
    unregister_individual(provider, edge)
    if output is not None and not (first.metadata.flags52 & 1) \
                          and not (second.metadata.flags52 & 1):
        append(output, edge)
    else:
        deleting_destructor(edge, 1)
    edge = anchor = body.head90
```

The owner comparison is asymmetric. A null or unowned second endpoint preserves
an edge. A zero first owner still differs from a nonzero second owner and triggers
removal. Internal edges remain registered. Endpoint identities are captured before
unregistration; metadata pointers and flags are reread afterward. Queueing requires
both bit0 flags clear. Without output storage, all removed edges go to the virtual
destructor, regardless of those flags. Destruction itself remains supplied.

Every successful removal restarts traversal from the current head. The routine
does not retain a potentially stale next-edge pointer across detachment/destruction.
This explains its repeated scan of internal edges. It still assumes valid serial
ring membership; there is no observed concurrency or lifetime protection here.
Output growth uses the descriptor helper at `0x18d8160`, with capacity8 initially
and doubling thereafter. The reconstruction supplies that helper and rejects
allocation-size overflow as an authored guard.

[Native comparison receipt](../../native/snow_host/pose_body_removal_validation.json):
512 synthetic fixtures,2048 body passes,223 queued constraints and935 destructor
calls. Original traversal, individual removal and ring detachment execute together.
All retained bytes match after every body pass, as do destructor identity/order/flag.
The fixture kind method and destructor are authored services; the destructor only
records a call. Output capacity is retained in native checks. Public tests cover
relocating growth, zero-owner asymmetry, preserved internal edges, restart behavior,
and a container removal composed with the real reconstructed body helper.

Native destructor/free effects, joined container-plus-body binary comparison,
tree membership removal and live/concurrent reclamation remain unresolved.
The helper's null-second skip does not establish that null-ended records can be
admitted through the separately recovered two-endpoint registration routine.

## Body metadata tree removal

`pose_body_tree.remove_pose_tree_body` reconstructs search/removal at `0x19598d0`,
node retirement at `0x1959c50`, structural deletion/rebalancing at `0x1959d90`,
and rotations at `0x1959bb0` and `0x18da970`. This closes the tree-removal service
used for container bodies with metadata52 bit3 set, apart from value destruction.

The key is the body's metadata uint32 at+0x54. Search compares unsigned keys.
A missing key or empty root returns without changes. Nodes occupy32 bytes:

| Offset | Meaning in this path |
| --- | --- |
| 0 / 4 / 8 | Signed left / right / parent indices; -1 is absent |
| 12 | Red byte:0 black,1 red |
| 13 | Free-slot marker |
| 16 | Value pointer |
| 24 | Unsigned key |

Descriptor fields are node pointer0, active count8, free count12, root index20,
and free-list head24. Capacity and unrelated bytes are preserved. This is an
indexed red-black tree, not a spatial traversal or a pointer-based tree.

```python
matched = lookup_unsigned(body.metadata.key54)
if matched is absent: return
saved_value = matched.value
physical = matched
if matched.left and matched.right:
    physical = rightmost(matched.left)
    matched.key, matched.value = physical.key, physical.value
unlink_and_rebalance(physical)
retire_slot(physical.index)
if saved_value:
    deleting_destructor(saved_value, 1)
```

Absent children use index -1, not index zero. Two-child removal copies only the
predecessor's key and value, leaving the target's structural fields in place.
The saved original value is destroyed after structural and free-list changes.
A null value still removes the node. Missing lookup is a no-op.

Structural removal links the sole child, if any, to the removed node's parent.
Removing red needs no repair. A nonnull replacement of a black node is painted
black. A black leaf propagates a black-height deficit through its parents:

- A red sibling is painted black, its parent red, and the parent rotated toward
  the deficit. The sibling is then reloaded.
- A black parent with two black sibling children paints the sibling red and
  propagates the deficit upward.
- A red parent with two black sibling children paints the sibling red and parent
  black, ending repair.
- A red near child with black far child first rotates the sibling away from the
  deficit, exchanging their colors.
- The final sibling takes the parent's color; parent and far child become black;
  rotation toward the deficit ends repair.

The executable implementation preserves the native branch order and both rotation
layouts. The public invariant test separately checks parent links, strict key
ordering, root color, no adjacent red nodes and equal black heights after removal.

Slot retirement has two cases. An interior removed slot becomes free: byte13=1,
left=-1, right=old free head, old head.left=removed index, free head=removed index,
free count increases and active count decreases. A removed last occupied slot
instead scans backward over existing free-marked slots, unlinking them from the
free list and decrementing free count. It finally decrements active count. No
allocation shrinks, payload clears or blanket node resets occur. Retired bytes
outside those writes remain stale. Active+free counts define the retained logical
prefix, which can become shorter than the allocated array.

[Native comparison receipt](../../native/snow_host/pose_body_tree_removal_validation.json)
covers256 synthetic trees and5834 lookup/removal operations, with4053 recorded
value destructor calls. Initial valid all-black trees contain1/3/7/15/31/63 nodes,
with permuted physical indices and unsigned keys across the uint32 range.
Random complete deletion produces changing tree shapes and colors. Instrumented
instruction coverage confirms every identified deletion repair branch, both
rotations, predecessor copying, interior retirement and trailing-free trimming.
Every descriptor/node/body/metadata/value byte matches after every operation.
Original search, tree mutation and slot retirement run without interception;
only the value destructor is an authored recording method.

Public tests additionally compose the tree helper with container removal and
verify that tree mutation/destruction precedes body processing. Native insertion,
value-destructor effects, concrete gameplay value classes and concurrent/live
ownership remain unresolved. These checks do not establish a general concurrent
container API or prove that arbitrary game objects can be deleted safely.

## Constraint destructor and release flags

`destroy_pose_constraint` reconstructs the base destructor `0x19a1670` and the
shared deleting policy in the base wrapper `0x19a1700` and kind4 wrapper
`0x19442e0`. The kind4 constructor installs table `0x29caa30`; inspection of its first slot
confirms wrapper `0x19442e0`. A runtime object still needs a matching type identity.
This implementation does not assume all tree values or derived constraints share it.

```python
linked = constraint.first_next20 != 0
constraint.table0, constraint.table40 = base_tables
if linked:
    detach_endpoint_rings(constraint, selector=2)
if constraint.callback_enabled5a:
    callback = callback_manager.callback28
    if callback:
        callback(constraint, 1, constraint.userdata50)
# observed cleanup target is return-only in the inspected image
constraint.table40 = final_secondary_table
constraint.table0 = final_primary_table
if deleting_flags & 1 and not deleting_flags & 4:
    allocator.free(constraint)
return constraint_identity
```

Base table identities are image-relative `0x29cb740` and `0x29cb760`; final table
identities are `0x29c9fd0` and `0x29c9800`. The reconstruction takes these as supplied
identities. The linked check occurs before table publication, and callback invocation
occurs after any endpoint detachment but before final table publication.

The callback manager comes from global `0x33365e0`. Forwarder `0x18b73f0` reads its
callback at+0x28 and calls it with object,1,userdata. An enabled object with a null
manager callback makes no call. The meaning and concrete producer of that callback
remain unresolved. Callback user data is captured before manager lookup.

Normal deleting flags1 call allocator virtual+0x18 through global `0x33365b8`.
With bit0 clear, base destruction still runs but storage release is skipped. With
bits0 and2 set, the base wrapper passes object,size0x70 to `0x75e600`; kind4 passes
object,size0x200. That target is `ret 0` in the inspected image, as is the earlier
base cleanup call to the same target. These are observed no-ops, not evidence of
an unimplemented free or notification. This claim is build/image-specific.

This destructor does not remove provider arrays. Body processing already performs
individual unregistration before calling it; cleared ring fields then prevent a
second detach. Direct destruction of an attached object only detaches its rings
and can leave stale provider membership. Callers must preserve the full lifecycle.
The wrapper returns the original identity even after allocator release; that return
does not imply a live object or safe access afterward.

[Native comparison receipt](../../native/snow_host/pose_constraint_destruction_validation.json)
covers512 fixtures,170 optional callbacks and128 allocator releases. Original base
and kind4 wrappers, ring detachment, callback forwarding and return-only stubs run.
Every retained constraint/body/manager byte matches, including full object snapshots
at callback/release boundaries, argument ordering and returned identity. Fixtures
cover flags0..7, linked/unlinked records with neighbors, callback enable and null
callback gates. Callback and allocator free are authored recording services.
Public tests additionally join body removal to the reconstructed destructor.

Remaining boundaries are allocator effects, callback effects, other derived
wrappers, actual tree-value classes, and live/concurrent/reentrant lifetime safety.

## Joined container cleanup

`remove_retained_pose_container` binds container removal to the reconstructed tree
and body helpers. It aliases the provider's tree descriptor at+d0, rather than
copying tree state into a disconnected object. Both body processing and container
child processing append to the same output descriptor. Kind and destruction remain
virtual services; known base/kind4 records can use `destroy_pose_constraint`.
This binding adds no new deletion or queueing policy.

[The joined native receipt](../../native/snow_host/pose_joined_cleanup_validation.json)
compares256 full container cleanup scenarios. Original container removal, tree
lookup/deletion/rebalancing, body traversal, provider unregistration, ring detach,
kind4 virtual methods, base destruction and callback forwarding execute together.
Only the external callback and allocator free are authored recording services.
The native kind4 method at `0xd4bb10` returns4. No kind-query interception is needed.

Every provider/container/body/metadata/constraint/tree/array/output/manager byte
matches, with306 queued constraints,1088 release calls and563 callbacks. Cases use
four bodies in randomized visit order, one through eight individual edges, zero
through three child constraints, a three-node tree, both metadata gates, and all
three container removal positions. This supersedes the earlier open joined-check
boundary while retaining its scope limits.

Tree values are synthetic known kind4 records. The test does not establish the
dynamic types stored in a live gameplay tree. Output storage retains capacity,
so native allocation growth is outside this receipt. Callback side effects and
actual allocator reclamation remain supplied. No live/concurrent safety follows.

### Runnable cleanup inspection

```sh
python3 -m engine.pose_cleanup_bench
```

The public example builds an authored synthetic fixture and runs the actual joined
reconstruction. Its JSON shows tree-value destruction first, cross-owner constraint
removal next, then child queueing and moved-container repair. One same-owner edge
remains registered and linked. It exposes final registries, body heads, deferred
queue, tree counts and ordered callback/release intents. Tokens are fixture IDs,
not game addresses. Releasing storage is recorded, not performed.

This is an inspection API for the independent reconstruction. It neither injects
into the game nor declares arbitrary native objects safe to delete. Public tests
check the complete retained state and event order, including preservation of the
internal edge and separation between destroyed and queued records.

## Base construction and endpoint canonicalization

`construct_pose_constraint_base` reconstructs `0x19a1530` and endpoint ordering
`0x19a1480`. It closes the base-construction service in the earlier specialized
kind4 constructor, apart from two conditional body virtual calls.

Endpoint priority is metadata50 bit15. A set bit sorts ahead of a clear bit.
Within the same priority class, unsigned metadata54 keys sort ascending; equal
keys preserve input order. A null second endpoint remains null with key0.

```python
swap = second is not None and (
    (not first.priority15 and second.priority15)
    or (first.priority15 == second.priority15 and second.key54 < first.key54)
)
stored_first, stored_second = (second, first) if swap else (first, second)
record.endpoints8_10 = stored_first, stored_second
record.keys18_1c = stored_first.key54, stored_second.key54_or_zero
record.ring_links20_38 = 0, 0, 0, 0
record.index48 = UINT32_MAX
record.userdata50 = 0
record.swap59 = 0
record.callback_enabled5a = 1
record.pointer60 = 0
record.index68 = UINT32_MAX
record.tables = base_tables
if low_byte(request) and first.priority15 and second and second.priority15:
    first.virtual28()
    second.virtual28()
```

The pseudocode groups assignments for readability. The implementation preserves
observed publication order: ring/index/userdata defaults, primary/secondary tables,
then flag/pointer/index defaults, before the body calls. Unrelated bytes including
+0x4c..0x4f,+0x58,+0x5b..0x5f and+0x6c..0x6f remain unchanged.
The apparent owner argument in R9 is not consumed by this base path; endpoint
initialization overwrites R9. No provider insertion or endpoint-ring attachment
occurs here. The final `0x75e600` call is the previously inspected return-only stub.

Body calls use the original argument order, regardless of canonicalized storage.
Both eligibility checks finish before the first virtual call; there is no second
eligibility check between calls. Concrete body virtual+0x28 effects remain a
service, not an inferred wake or activation operation. Construction supports a
nullable second endpoint, but this does not resolve admission to two-ended rings.

The specialized kind4 constructor then overwrites tables/userdata, derives swap59
from requested-first versus stored-first, and swaps callback arguments back. Thus
canonical storage and original callback ordering coexist. Its single flag still
uses the stored second endpoint's priority bit. Initial callback mode0/scalar0 and
count behavior remain as previously decoded.

[Base comparison](../../native/snow_host/pose_base_construction_validation.json):
1024 fixtures match all bytes and body-call snapshots, including396 endpoint swaps
and308 body virtual calls. Cases cover all priority combinations, equal/ordered
keys across the unsigned sign boundary, nullable second endpoints and request
bytes0/1/2/255. Original base construction/ordering execute; body calls record only.

[Joined specialized comparison](../../native/snow_host/pose_joined_command_construction_validation.json):
512 fixtures execute original base and kind4 constructors plus original command
default initialization. All bytes, body-call ordering and command callback arguments
match. This supersedes the earlier supplied-base limitation. Concrete command
production and body virtual effects remain supplied, as do live ownership and
allocation. Default construction at `0x19a1600` is inspected but not implemented
by this API; arbitrary other derived constructors are not covered.

## Construction-triggered body quiet reset

The constructor's body virtual+0x28 now joins an earlier decoded method. The known
physical-body table `0x29c99a8` resolves this slot to `0x18be770`, exactly the reset
used by ordinary-group reactivation. It clears metadata53's low nibble and stores
positive zero in body timer28. All motion, transforms, unrelated body fields and
the metadata high nibble remain unchanged.

`construct_retained_pose_command` binds the reconstructed base and specialized
kind4 constructors to `reset_pose_body_quiet_state`. It checks each reached body's
primary table against the supplied known-class identity before applying the reset.
The table identity is build-specific evidence, not an arbitrary-body reset license.
The separately known box-resource table `0x29c9ac8` has serialization code at this
slot; it must not be treated as the physical-body class.

A nonzero request low byte and two priority15 endpoints admit both resets, in
original caller order. The command callback subsequently sees reset timer/state
but still receives original endpoint ordering, even if storage was canonicalized.
Neither reset transfers a group to an active collection, repairs group indices,
queues group links or performs registration. Calling this a complete group wake
would overstate the constructor's effects.

[Native joined check](../../native/snow_host/pose_construction_body_reset_validation.json)
runs512 original base/kind4 constructions with actual physical-body virtual calls,
original endpoint canonicalization and command initialization. Only command
production is supplied. All constraint/body/metadata bytes and callback arguments
match across random prior timers, state nibbles and motion bytes, priority gates,
nullable second endpoints and request values. The previously supplied body-virtual
boundary is closed for this class in this construction path.

Public tests verify reset visibility at the initial command callback, preservation
of metadata high bits, and rejection of an unsupported reached body table. That
rejection is an authored guard after base writes, not rollback or a native error.
When the request gate is closed, no virtual reset is reached or type-checked.
Concrete gameplay command production, other body classes and live ownership remain
unresolved. This result does not establish all automatic reactivation triggers.

## Serialized kind4 command records

The callback search exposed a separate command-input path: specialized reader
`0x19443f0`. `deserialize_pose_command_constraint` reconstructs this consumer with
explicit base-decoder and block-reader services. It does not claim to decode the
full asset envelope or identify the callback producer.

```python
read_base(constraint, reader)
if select_block(reader, tag=0x2607, size=5, scan_limit=3, required=True):
    constraint.count74 = read_u32_bits(reader)
    constraint.single70 = read_byte(reader) != 0
index = 0
while index < signed_i32(constraint.count74):
    if select_block(reader, tag=0x2608, size=64, scan_limit=3, required=True):
        for word in range(16):
            constraint.commands[index].word[word] = read_u32_bits(reader)
    index += 1
```

Block2607 contains four count bytes and one normalized boolean. Each block2608
contains the exact64-byte command layout already consumed by the category24 row
builder: four XYZ vectors and four scalar words. The loader copies raw bits;
no float conversion, endian reinterpretation beyond the little-endian word copy,
angle conversion or normalization is introduced. Per-word cursor reads preserve
the native sequence. Reader framing remains the `0x18c0590` service. Inspection establishes that3
is a scan limit, not a format version, and the final true argument requests an
error flag when no matching block is found. Native headers have magic0xecd7 in
the high16 bits, the tag in the low16, followed by a total block byte size. The
reader can scan up to three candidate blocks. Malformed headers or missing required
blocks set reader20; the consumer itself continues according to the false result.

Absent2607 leaves count and single mode unchanged. Absent2608 leaves that command
slot unchanged, but its index is still consumed. The signed count is reloaded on
every loop comparison, so base/block services that change it affect iteration.
Negative counts skip all command blocks. The native path has no six-record clamp;
the independent loader rejects signed counts above6 to prevent writes outside
inline storage. Short reader responses also raise an authored error. Neither guard
is rollback; header/base writes may already have happened.

The loader does not assign callback1f8 or userdata50. The generic kind4 factory
uses default construction `0x1944190`, which initializes callback1f8 to zero.
Therefore loading inline command records does not prove that a valid per-step
producer callback exists. The original preparation path invokes callback1f8 when
its metadata gates admit it, with no inspected null check. Upstream registration,
callback installation or selection must still be established for any live object.
The clone at `0x1944340` copies callback and userdata from a source; it is not an
independent producer. No additional direct constructor caller was established in
this pass. These are boundaries, not proof that no indirect producer exists.

The supplied base reader at `0x19a17f0` has concrete further leads: it records an
object/type pair0x9fb9, reads endpoint references under tag2602/type0x9fb6, and
reads pointer60/index68/swap59 under tag2609/type0x9fba. Reference fixups and the
reader's error/registration behavior are not implemented in this specialized API.

[Native consumer comparison](../../native/snow_host/pose_command_decode_validation.json)
covers512 cases and844 loaded command blocks. All constraint and reader bytes,
service ordering, tags, sizes, scan limits and required flags match. Original native
per-word loads/stores/cursor updates execute; base decoding and block selection
are supplied. Fixtures cover missing headers/records, counts-1/0/1..6, nonzero
boolean normalization and raw random word patterns. No asset corpus or native
framing comparison is implied.

Public tests additionally feed decoded records into the existing command-row
builder and check XYZ expansion and scalar broadcasting. They cover count mutation,
missing-block preservation, callback-pointer preservation and authored malformed
input guards. The full resource reader, callback producer and live selection remain
open, with clear independent entry points for further reconstruction.

## Tagged block framing and cursor rules

`pose_block_reader.select_pose_block` reconstructs `0x18c0590`. This replaces the
framing service used by specialized command loading. The public
`deserialize_retained_pose_command` adapter joins the reader and command consumer;
base object/reference decoding remains supplied.

Reader state comprises buffer pointer0, uint32 byte length8, payload cursor10,
next-block cursor18 and error byte20. All offsets here are hexadecimal. Each header
has two little-endian uint32 words: `0xecd70000 | tag16` and total block size,
including the8-byte header. The requested payload size is a minimum, not an exact
size requirement. No header version field is consumed by this routine.

```python
candidate = reader.next_block
for attempt in range(uint32(scan_limit)):
    if candidate + 8 > buffer_end: break
    magic_tag, total = header(candidate)
    if magic_tag.high16 != 0xecd7 or total < 8 or candidate + total > buffer_end:
        reader.error = 1
        return False
    if magic_tag.low16 == uint32(requested_tag):
        if total < uint32(min_payload) + 8:
            reader.error = 1
            return False
        reader.payload_cursor = candidate + 8
        reader.next_block = candidate + total
        return True
    candidate += total
if low_byte(required): reader.error = 1
return False
```

The search cursor is local until a match succeeds. Exhaustion, invalid data and
short matching payloads preserve both stored cursors. This includes skipped valid
blocks: a failed later search does not commit their traversal. Ordinary absence
sets error only when required; malformed magic/size/bounds always sets it. A short
remaining header counts as absence. Success never clears a prior error byte and
does not refuse to proceed merely because that byte was already set.

The requested tag is uint32, while header tags are16 bits; a request above65535
cannot match by truncation. Payload-size addition uses the zero-extended uint32
size plus8. Valid retained buffers require nonwrapping ranges and an in-range
next-block cursor; the independent implementation rejects invalid external pointer
domains rather than reproducing unsafe native memory reads.

`read_pose_block_bytes` is an authored bounded adapter for the original consumer's
inline loads and cursor advances. It reads only through the selected block end.
It is not presented as a separately recovered native helper. Header selection may
permit extra payload bytes; the next search still begins at the stored block end,
not at a partially consumed payload cursor.

[Selector comparison](../../native/snow_host/pose_block_reader_validation.json):
1024 native calls without instruction interception match return booleans, every
reader byte and unchanged input bytes. Cases cover scan limits, matching/missing
and oversized requested tags, wrong magic, total-size failures, truncated headers,
minimum payload failures, required/optional absence and existing error state.

[Joined reader/command comparison](../../native/snow_host/pose_framed_command_loading_validation.json):
512 original command loads use the original selector and native inline reads,
with only base reference loading supplied. All object/reader/input bytes match.
Unknown-block skipping, exhausted search, missing headers, truncated streams,
malformed magic, counts0..6 and retained errors are included;363 outputs carry an
error flag. Those are intentional error-path comparisons, not successful assets.

Public tests cover cursor rollback on failure, error persistence after success,
bounded reads and complete tagged bytes reaching inline command storage. No real
asset corpus, base reference fixup or callback-production proof is claimed. The
next reader dependency is base object registration and typed reference resolution.

## Typed references and deferred writes

`pose_reference_reader.read_pose_reference` reconstructs ordinary pointer reader
`0x18c0410`, counted pointer reader `0x18c0340`, and retained-capacity fixup append
`0x18c0300`. These are the typed-reference services reached by base constraint
loading. Framing and payload cursors use the reader described above.

```python
marker = read_u32()
if marker.high16 != 0x73cb or marker.low16 != uint32(expected_type):
    return False
index = read_u32()
if ordinary_pointer and index == 0xffffeeee:
    destination = null
    return True
if index < reader.object_count:
    entry = reader.objects[index]
    if entry.type != expected_type: return False
    destination = entry.pointer
    if counted_pointer: atomic_increment_u32(entry.pointer + 8)
else:
    reader.fixups.append(destination_address, index, expected_type, counted_pointer)
return True
```

Object table entries are16 bytes: pointer0,type8, with remaining bytes untouched.
The table descriptor is reader28/count30/capacity34. Forward references append to
reader38/count40/capacity44. Fixup entries are24 bytes: destination pointer0,
uint32 index8,type12,retain byte16, and seven preserved padding bytes. These field
offsets within entries are decimal; reader offsets are hexadecimal.

The deferred destination is a pointer to the eventual output slot, not its current
value. Enqueueing leaves that output slot untouched and still returns success.
The counted variant records retain byte1 for later replay. It does not special-case
ordinary null sentinelffffeeee; that value is treated as a forward index when it
is outside the current object count. Do not apply nullable-pointer rules to it.

Malformed marker/type consumes only the first word. A table type mismatch consumes
both words. Both return false without changing the destination or setting reader20.
Callers such as base constraint loading set the error flag themselves. Immediate
success publishes the pointer before the counted variant's `lock xadd` increments
the uint32 count at object+8. The reconstruction requires an explicit retain service
for that operation; it does not pretend a Python write supplies cross-thread atomicity.

Fixup growth requests8 slots initially, then doubles. The existing capacity helper
uses24-byte elements, alignment16 and allocator tag0x18. Allocation remains a service;
counts/pointers are reread after growth. The independent API rejects byte-size
overflow and bounds payload reads as authored guards. Errors are not transactional.
Deferred fixup replay, object-table population and real allocation are separate work.

[Native comparison](../../native/snow_host/pose_reference_reader_validation.json)
covers1024 cases with no instruction interception, including the actual native
atomic increment. Every reader/destination/table/fixup/object/input byte and return
boolean matches:237 immediate successes,312 deferred successes,475 rejected reads,
and113 retains. Fixtures cover ordinary null versus counted deferred sentinel,
marker/type failures, expected types exceeding16 bits, forward indices, padding,
unchanged deferred destinations and count values including UINT32_MAX wraparound.
Retained fixup capacity suffices in all native cases. This is serial fixture proof,
not evidence that the public API is safe for concurrent live mutation.

Public tests add relocating fixup growth, pointer publication before retain,
failed-read cursor consumption, and composition with actual block framing.
Original object types, delayed replay and loader completion ordering remain open.

## Deferred reference replay

`replay_pose_references` reconstructs `0x18c0710`. It completes the deferred path
of ordinary and counted reference reads for retained serial storage. It returns
true only if every queued fixup resolves, without changing reader error20 itself.

```python
scratch = allocate(entry_fixup_count * 24) if entry_fixup_count else empty
object_count = reader.object_count
fixups = captured_span(reader.fixups, reader.fixup_count)
remaining = []
for fixup in fixups:
    if fixup.index >= object_count or objects[fixup.index].type != fixup.type:
        *fixup.destination = null
        remaining.append(copy_all_24_bytes(fixup))
    else:
        *fixup.destination = objects[fixup.index].pointer
        if fixup.retain:
            atomic_increment_u32((*fixup.destination) + 8)
reader.fixup_count = 0
ensure_fixup_capacity(len(remaining))
reader.fixup_count = len(remaining)
copy_remaining_to_front(remaining)
release(scratch)
return len(remaining) == 0
```

Object count and fixup pointer/end are captured after initial scratch allocation.
The object-table pointer is reloaded for each in-range row. Success writes the
pointer before the retain operation; the destination pointer/value are reread for
retention. Both out-of-range indices and type mismatches zero the destination and
preserve the entire24-byte row, including padding, in stable order for retry.
Successful rows disappear from the active queue. Inactive tail bytes are not cleared.
No null-sentinel special case exists in replay.

Scratch initially holds the entry fixup count, with24-byte elements, alignment16
and allocator tag0x18. The native routine also has scratch growth branches for
allocator-driven changes to the input span. The reconstruction requires stable
serial storage and rejects scratch overflow; that mutation domain is not claimed.
Final queue growth starts at the needed count when capacity is zero, otherwise
repeatedly doubles. Under ordinary valid capacity, failed rows cannot outnumber
the input, so retained capacity suffices. Allocation and retain remain services.

The reader reset entry at `0x18c02c0` clears buffer/cursor fields, invokes replay,
then zeros both object and fixup counts. Its handling of unsuccessful replay is a
separate lifecycle question; this API exposes the replay result rather than
silently treating unresolved destinations as complete.

[Native replay comparison](../../native/snow_host/pose_reference_replay_validation.json)
covers512 cases with zero through eight fixups. Original replay, native memcpy and
atomic increments execute together; only temporary allocation/free is supplied.
All reader/table/fixup/destination/object bytes, return flag and allocation arguments
match. There are1760 unresolved rows across the fixtures and141 retains. Cases
include mixed index/type failures, ordinary/counted references, stable compaction,
reference-count wrapping and preservation of existing reader error state.

Public tests run successive replay passes after table population/type correction,
verify that already-resolved objects are not retained again, and compose typed
reference enqueue with replay. They also check full failed-row preservation and
zero destinations. Original object-table population, allocator mutation, real
asset graphs and concurrent/live lifetime remain outside this result.

## Base object registration and complete command loading

`pose_constraint_decode.deserialize_pose_constraint_base` reconstructs `0x19a17f0`
and the constraint-specific use of link reader `0x1958d70` and userdata reader
`0x18c0d40`. `deserialize_pose_command_record` joins these with specialized kind4
loading, actual block framing and typed references. No base-decoder placeholder
remains in this entry point. Allocation growth is still supplied.

The reader first appends `(constraint_pointer, type0x9fb9)` to its16-byte object
table, growing from0 to8 or doubling capacity as needed. Count increases before
the pointer/type writes; entry padding remains untouched. Registration precedes
field loading, so references to this new table index can resolve immediately.
This is serialization identity registration, not physics provider/ring insertion.

All following base searches scan at most three blocks and do not require a match:

| Tag | Minimum payload | Effect when present |
| --- | --- | --- |
| 0301 | 8 | Copy raw userdata to object50; absent block explicitly zeros it |
| 2602 | 9 | First endpoint reference/type9fb6; presence byte; optional second endpoint reference, or clear second |
| 2c02 | 8 | Two endpoint references/type9fb6; recompute paired metadata54 keys at18/1c |
| 2c03 | 16 | Four type9fb9 references into20,30,28,38 in that order |
| 2609 | 13 | Type9fba reference into60, uint32 index68, normalized swap flag59 |

Tags and object offsets in this table are hexadecimal; payload lengths are decimal.
Minimum sizes are the native checks, not full guaranteed consumption lengths. For
example, two typed references normally need16 bytes, while2c02 requests only8.
The bounded reconstruction raises on an actual overread rather than following an
unsafe native load beyond a malformed payload. No silent padding is manufactured.

A false typed-reference result sets reader20 and loading continues. A forward
reference is considered successful and leaves the destination unchanged until
replay. Endpoint keys are recomputed from the pointers currently stored after2c02:
second null contributes key0; first must be a valid body. No canonical reordering
occurs here. A later2c02 can overwrite endpoints loaded by2602. Link fields are
loaded as serialized references, without calling ring insertion helpers.

This exposes an unresolved dependency for forward endpoint references. Key
recomputation occurs immediately, but replay only repairs pointers. It does not
refresh18/1c. Fixtures in the native comparison keep key-source pointers valid and
immediately resolved. Upstream load ordering or a later refresh must be established
before claiming arbitrary serialized graphs are ready for simulation.

[Complete native reader comparison](../../native/snow_host/pose_full_command_decoding_validation.json)
covers512 loads with no instruction interception. Original object-table append,
base/link/userdata loading, framing, typed references, deferred append and kind4
commands execute together. Every object/reader/table/fixup/body/metadata/input byte
matches, with645 deferred references.256 outputs retain a preexisting error flag.
Cases vary optional legacy/new endpoint blocks, overrides, null/forward references,
self-reference, ring-field ordering, userdata, relation/index/swap fields and0..6
commands. Object/fixup capacities are retained; no allocation calls are needed.

Public tests add relocating object-table growth, full load then forward-reference
replay, missing-field preservation, and continued loading after a type mismatch.
Callback1f8 remains untouched by these readers. This completes the inspected
base/kind4 field-loading chain, not callback assignment, safe physics registration,
actual asset-corpus coverage or arbitrary object graph reconstruction.

## Tagged factory entry and outer load ordering

`load_pose_constraint_object` reconstructs envelope entry `0x18d46e0`. It requests
required block2601 with minimum payload2 and scan limit3, consumes a uint16 kind,
creates that kind through the factory, invokes its virtual reader at+0x18, and
returns the object pointer. A missing envelope returns null. The native entry
assumes factory success and dereferences the result; the independent entry raises
an authored error on null instead. Creation/dynamic dispatch remain services for
kinds not reconstructed through this entry point.

The kind4 branch of factory `0x18d47f0` allocates512 bytes, alignment16, tag0x2e,
then invokes default constructor `0x1944190`. `initialize_pose_command_constraint`
reconstructs this and base default `0x19a1600`: endpoints/paired keys/ring links
are zero; base index48/index68 are UINT32_MAX; userdata50/pointer60 are zero;
swap59=0,callback-enabled5a=1; single70/count74=0; six command records get their
known defaults; callback1f8=0. Unrelated bytes remain unchanged. The kind4 tables
are published before virtual field loading. No initial command callback runs.

[Factory-to-reader native comparison](../../native/snow_host/pose_kind4_factory_loading_validation.json)
covers512 cases. Original tagged entry, kind4 factory, base/default constructors,
virtual dispatch, complete field loading, block reader and reference handling all
execute. Only the512-byte object allocation is supplied. Every object/reader/table/
fixup/body/metadata/input byte, allocation request and returned identity matches.
Object and fixup capacities are retained. Callback1f8 remains zero after the full
factory load, confirming that this path alone does not install a command producer.

### Outer ordering evidence

Static inspection of the outer reader around `0x18b6030..0x18b60e4` places its
container-body loop before its constraint loop. Each body uses `0x18d4650`, which
reads required kind block0c01, constructs the body, invokes virtual+0x80 loading,
then virtual+0x88 finalization. Afterward the outer loop assigns the returned body's
metadata owner20 to its container and its body index18. It then loads resource
objects through `0x18d4760`, followed by constraints through `0x18d46e0`.

After further object loops, it calls reference replay `0x18c0710` at `0x18b6165`
and proceeds to `0x18b6740` without branching on the replay result. Finalization
contains protected collection access and a later optional pass of body virtual+0x88.
The latter is resource backlink repair for the known body table, not an observed
constraint paired-key refresh. Full finalization is not reconstructed here.

This ordering supports the inference that endpoints belonging to already-loaded
container bodies can resolve immediately during later constraint loading. It does
not establish arbitrary cross-container/external forward endpoints, all object
classes or all asset layouts. The earlier endpoint-key dependency remains explicit
for graphs outside the inspected ordering. No universal key-refresh step has been
invented. A full native outer-loader comparison and real asset graph inspection
are still needed to strengthen that inference.

Public tests cover default construction followed by actual field loading, null
callback preservation, serialization registration, default command words, padding,
missing envelopes and null factory guards. They do not claim that a newly loaded
kind4 object is admitted to callback preparation or physics provider membership.

## Body load entry and resource backlinks

`pose_body_load.load_pose_body_object` reconstructs entry `0x18d4650`: select
required block0c01 with minimum4 bytes and scan limit3, consume its first uint16
kind, call the factory from provider608, then invoke body virtual80 deserialization
and virtual88 finalization. The remaining two minimum payload bytes are not consumed
by this entry. Both missing envelope and null factory result return null. This
null behavior differs from the constraint load entry's unchecked native result.
Factory and dynamic reader/finalizer selection are explicit services in this API.

For the known physical-body table `0x29c99a8`, virtual80 is `0x18a93e0` and virtual88
is `0x18bc6f0`. The reader calls `0x18bc1b0`, which calls base body reader
`0x18bade0`; the latter registers object/type0x9fb6. Full body field decoding remains
separate work. The finalizer is reconstructed as `finalize_pose_body_resources`:

```python
count = uint16(body.resource_count_c0)
for i in range(count):
    entry = reload(body.entries_b8)[i]  # stride72 bytes
    if entry.resource16:
        entry.resource16.owner30 = entry.owner0
        entry.resource16.index38 = entry.index8
```

Body/resource offsets are hexadecimal; entry field suffixes0/8/16 and stride72 are
decimal. Count is captured once and the entry-array pointer reloaded per iteration.
Null resources are skipped. Repeated identities are not deduplicated; the last
entry overwrites prior backlinks. No bounds, transforms, body timers, constraint
keys or registration arrays are changed. The leading base call reaches the
previously inspected return-only stub.

These are the same72-byte entries used by bounds refresh, which reads resource16
and transform24. Finalization fills resource ownership; bounds refresh later
composes transforms and asks each resource for bounds. They are separate operations.
The outer loader's optional second virtual88 pass can repair these backlinks after
reference replay, but is not evidence of a constraint paired-key refresh.

[Native finalizer comparison](../../native/snow_host/pose_body_resource_finalize_validation.json)
covers512 fixtures with zero through eight entries, null/duplicate resources and
arbitrary owner/index values. Original known-class finalizer and base stub execute
without interception. Every body, entry and resource byte matches. This receipt
does not include the outer body-load entry or full body deserialization.

Public tests cover body-load service order, null creation, the four-byte minimum
versus two-byte kind consumption, last-entry overwrite and finalization composed
with the existing bounds-refresh implementation. Dynamic body classes, the actual
resource corpus, allocator ownership and complete outer finalization remain open.

## Physical-body serialized state

The known physical-body reader at RVA18a93e0 calls the base resource/body reader
18bc1b0, then processes four blocks through the recovered selector. All scans use
limit3. This establishes a serialized-data connection to the motion fields used
by the existing integration/secondary-update kernels, without identifying a
player-specific caller or proving that a particular save uses these blocks.

| Block | Required/minimum | Effect |
| --- | --- | --- |
|1001|yes/92 bytes|Copy23 raw words: five at120..130, then XYZ triples at140,150,160,170,180,190. Preserve the fourth lanes and other padding. If another byte remains, copy it unchanged to1c8; otherwise set1c8 to0.|
|1002|yes/24 bytes|Copy six raw words into motion fields1a0..1b4.|
|1003|no/16 bytes|Capture scalar and XYZ triple, then call scalar setter18a98d0 followed by vector setter18a9e90.|
|1004|no/12 bytes|Capture three scalars before calling18a9c30,18a9b00,18a9d60 in that order.|

A failed selection does not copy that block's fields. Required failures set the
reader error but do not stop later block attempts. A missing1001 therefore leaves
1c8 untouched; a selected legacy92-byte1001 explicitly clears it. The flag byte
is not boolean-normalized. The reference implementation passes setter arguments
as raw little-endian bytes to preserve signed zero and NaN payloads. It does not
assign names or units to unproved parameters.

`pose_body_decode.deserialize_physical_pose_body` implements this reader with
base loading and the five setter effects supplied explicitly. It uses actual
block selection and bounded payload reads.512 synthetic native comparisons pass
for all body/reader bytes and setter arguments, order and cursor positions. The
original block selector ran unmodified; base and setter calls were recording
services. See `native/snow_host/pose_physical_body_decode_validation.json`.

Remaining work includes the base body's resource records and reference graph,
setter allocation/derived-state effects, real serialized-corpus validation and
joining loading to the scheduler's actual body registration. This evidence does
not provide a complete body factory or restore a running game from saved state.

## Sparse body parameter setters

The optional1003/1004 serialized blocks feed two sparse records. These are local
storage/lifetime rules, not established gameplay names or units.

- Body1b8 points to16 bytes: XYZ at0/4/8 and scalar at12. Scalar setter18a98d0
  checks the incoming scalar against zero, then existing XYZ. If all match the
  defaults, it returns the record to its pool and clears1b8. Otherwise it allocates
  when absent, initializes XYZ to positive zero and writes the raw scalar word.
  Vector setter18a9e90 mirrors this rule, checking incoming XYZ and existing scalar;
  a new vector record initializes only the scalar to positive zero.
- Body1c0 points to three raw float32 parameters, defaulting to minus one. Setters
  18a9c30/18a9b00/18a9d60 write lanes0/1/2 respectively. When absent, a default input
  does nothing; a nondefault input allocates, initializes all three lanes to-1 and
  writes its lane. When present, the lane is written first. If all three lanes then
  compare equal to-1, the record is returned and1c0 cleared. Bytes beyond the three
  lanes are not initialized by these setters.

These comparisons use UCOMISS with JE/JNE and no parity check. An unordered NaN
therefore takes the same branch as equality. Both signs of zero match zero. Raw
words are retained on writes, including NaN payloads and signed zero. This is
recovered behavior, not a recommended generic floating-point equality policy.

`pose_body_parameters` implements all five setters. Pool allocation and return
are explicit services. A return callback observes the old pointer still published;
clearing occurs after it returns. `deserialize_retained_physical_pose_body` joins
these setters to the physical reader, leaving only base loading and pool services
supplied. Native pool locks/free-list manipulation and null-allocation faults are
not reproduced; a null result raises an authored error.

1024 synthetic comparisons execute the original setter branches, initialization
and stores, with protected pool acquisition/return regions replaced by recording
services. All body/record bytes and allocation/release events match. The receipt
is `native/snow_host/pose_body_parameters_validation.json`. Public tests also join
serialized blocks, motion restoration and all five setters, and cover the shared
record's lifetime across sequential changes. No live game or asset corpus was used.

## Base body identity and metadata loading

Base reader18bade0 appends `(body_token, type9fb6)` to the reader's object table
before any block selection. It increments the count before writing the entry,
leaves entry padding intact, and grows capacity from0 to8 or doubles it through
18ab920. The following75e600 call is a return-only stub in the inspected image.

All selectors scan at most three blocks. Exact destination behavior follows:

| Block | Required/minimum | Meaning established by writes |
| --- | --- | --- |
|0c02|yes/2|Low16 bits of body1c; default0 when selection fails.|
|0c0d|no/2|High16 bits of body1c; default0 when absent.|
|0c03|no/4|Typed9fba owner reference into body10; absent explicitly clears it. The reference itself normally consumes8 bytes.|
|0c05|yes/58|Metadata reader18be5d0, detailed below.|
|0c06|yes/1|Raw flag byte into bodyaa; an optional following uint16 into bodya8, otherwise0. One trailing byte is ignored.|
|0c07|no/0|Typed9fbb reference into body80; absent leaves previous value.|
|0c0a|no/0|Typed9fb9 constraint-ring head into body90; absent leaves previous value.|
|0c04|no/8|Raw userdata into body20; absent explicitly clears it.|
|0c0b|no/48|Four XYZ triples into body40/50/60/70; fourth lanes remain untouched.|

The metadata target is the existing pointer at body30. Its reader copies six
raw bounds words to metadata4..18, then eight bytes to30 and24 bytes to38..4f.
The24-byte helper1941780 performs raw8/8/4/4-byte copies. The final two payload
bytes replace the low nibble of metadata53 and all of metadata52 respectively.
The high nibble of53 survives. This path does not write metadata owner20,
priority word50 or runtime tree key54. Consequently, deserialization alone does
not establish runtime identity/key assignment or physics-provider membership.

`pose_body_base_decode` implements this path using actual framing, typed
references and deferred fixups. Failed typed reads set reader20 but do not abort.
Missing required blocks likewise allow subsequent work; no rollback occurs.
Malformed reference payloads shorter than the actual reference read fail through
our bounded-read guard rather than reproducing native out-of-block reads.

512 native comparisons pass without instruction interception, including344
forward-reference fixups, required-block failures, legacy flag variants and
preservation of unrelated bytes. All body, metadata, reader, table, fixup and
input bytes match. The native fixtures retain capacity; public tests additionally
cover relocating table growth and body loading followed by constraint registration
and deferred ring-head replay. See `native/snow_host/pose_body_base_decode_validation.json`.
Resource entries and the middle body reader remain separate unresolved loading
work; real asset-corpus and live lifecycle validation have not been performed.

## Serialized body resource entries

Reader18bc4a0 selects required0e03/min95 with scan limit3. It reads a typed9fb7
resource reference into entry10, captures four XYZ triples as a local transform,
then writes eight bytes at entry20,24 bytes at28..3f and four bytes at40. Failed
reference resolution marks reader20 and continues; forward references retain the
old pointer and enqueue its exact destination slot for later replay.

The payload ends with three required bytes A/B/C and up to three optional bytes
D/E/F. Low bits are packed into entry44 as follows, preserving existing bits6..7:

```text
entry.flags = old_flags & 0xc0
            | (F & 1) | (A & 1)<<1 | (E & 1)<<2
            | (B & 1)<<3 | (C & 1)<<4 | (D & 1)<<5
```

Absent D defaults0. If the payload cursor's low32 bits equal the block end's
low32 bits after D, E defaults to the boolean expression:

```text
(metadata.priority_word & 0x8000) == 0
or (metadata.flags52 & 8) != 0
or A != 0
```

The A comparison uses the whole byte before final low-bit packing. Otherwise E
is read when one byte remains, defaulting0 on an out-of-range cursor. Absent F
defaults1. These are exact storage rules; semantic names for all six bits remain
unproved. The lower32 cursor comparison is preserved rather than silently widened.

After every field write, reader calls18a80f0 on the transform pointer at entry18.
`deserialize_pose_resource_entry` supplies this through `set_transform(entry,
packed_xyz48)`. The native stack's fourth lanes are uninitialized and not passed
as meaningful values. Transform allocation/shared-identity ownership remain open.

512 original-reader comparisons match all retained bytes, including111 forward
references, with only the transform setter supplied as a recording service.
Fixtures cover95..98-byte payloads, missing/short blocks and typed-reference
outcomes. Public tests check full-byte fallback versus low-bit packing, explicit
flag overrides, preserved fields and exact deferred destinations. See
`native/snow_host/pose_resource_entry_decode_validation.json`. No live or real
asset-corpus validation is claimed; the enclosing array lifecycle remains open.

## Shared identity transform storage

Constructor18bb6a0 and setter18a80f0 share identity comparison18a8050. The shared
identity token is image-relative3336780 in this build, but the reconstruction
requires it as an explicit identity token rather than treating that address as
portable storage. The comparison checks the nine basis components against the
identity matrix and translation XYZ against zero with tolerance float32(1e-6).
Diagonal subtraction is rounded to float32 before absolute value and comparison.
Only strict ordered greater-than rejects identity, so NaN does not reject it;
positive/negative infinity does. Fourth lanes are neither tested nor copied.

```text
construct(slot, frame):
    if near_identity(frame): slot = shared_identity
    else: slot = allocate(); copy_XYZ(slot, frame)

assign(slot, frame):
    if slot == shared_identity:
        if near_identity(frame): return
        slot = allocate()
    else if near_identity(frame):
        release(slot)
        slot = shared_identity
        return
    copy_XYZ(slot, frame)
```

Construction does not release any old slot value. Assignment reuses existing
private storage when the incoming transform remains nonidentity. Release happens
before the slot is replaced, and new slots are published before XYZ writes.
Allocation and release pool internals remain supplied. Native null-allocation
faults become explicit authored errors in the retained implementation.

`pose_transform_storage` implements these operations and
`deserialize_retained_pose_resource_entry` joins them to resource loading. Its
input is four packed XYZ triples; retained transforms use64 bytes and preserve
their fourth lanes. This removes the transform-setter placeholder from entry
loading without inventing stack padding or pool synchronization semantics.

1024 native comparisons pass with only pool allocation/free supplied, including
431 allocations and98 releases. Fixtures test exact tolerance neighbors,
float32 diagonal rounding, NaN, signed zero, infinity and preserved padding.
Public tests join resource decoding to actual transform allocation. See
`native/snow_host/pose_transform_storage_validation.json`. All fixtures are
synthetic and offline; real resource ownership/concurrency remain unvalidated.

## Resource-array loading lifecycle

Middle reader18bc1b0 calls base18bade0, optionally reads0e01/min48 as four XYZ
triples overriding body40/50/60/70, then selects optional0e02/min4. Without0e02,
array state and body110 remain unchanged. With it, the reader captures old uint16
countc0 and walks72-byte entries, reloading bodyb8 each iteration. Every nonnull
resource triggers virtualD0(body,index,identity_transform,0). Its concrete cleanup
semantics remain supplied here; neither removal nor release is assumed.

Only after those calls does it read the new uint32 count. If greater than uint16
capacityc2, capacity repeatedly doubles with16-bit wrap before18bcbb0 growth.
Certain starting capacities/counts never converge. The retained implementation
raises on a repeated capacity instead of reproducing a nonterminating loop.
It stores count's low16 bits in bodyc0 and uses the full count as the loop bound.

Each new entry initializes owner0, index8, null resource10 and identity transform18;
entry20..3f become all ones,40 becomes zero,44 becomes `(old & 0xdf) | 0x1f`.
Other padding survives. It then scans exactly one block for optional0e04/min0.
A match marks a placeholder. Otherwise it calls the resource-entry reader and
increments a local attempt count regardless of that reader's error. The final
attempt count is stored at body110. It is not a count of successfully resolved
resources. Array pointers reload for each entry after growth.

`pose_body_resource_array` implements this lifecycle with explicit base/reset/
growth/entry services and recovered identity construction.512 native comparisons
pass for body/array/reader bytes and service order, using an error-only entry
service to exercise failed attempts. Native framing and identity constructors run
unmodified. Public tests additionally compose actual entry decoding and transform
storage, and exercise array relocation during resets. See
`native/snow_host/pose_body_resource_array_validation.json`.

The complete known-body pipeline is now composable from the base reader, this
middle reader, the physical-state reader and finalizer. Whole-pipeline native
validation, virtualD0 effects, allocation/reallocation ownership and real resource
corpus remain open. No full body-load equivalence is claimed by the local tests.

## Joined physical-body loading

`pose_body_loading_runtime.deserialize_known_pose_body` composes the actual
base identity/metadata reader, middle resource-array reader, resource references
and transform storage, physical state/motion reader and sparse parameter setters.
It requires a constructed known-class body and explicit retained object maps.
Pool operations, array growth and virtualD0 reset remain external services.
It does not silently replay references, finalize backlinks or register physics.
Call the recovered resource finalizer separately at the caller's observed point.

512 comparisons run original18a93e0 and then18bc6f0 without instruction
interception. Every retained body/metadata/entry/reader/table/fixup/resource/
parameter/input byte matches. Cases include zero through six entries, placeholders,
305 deferred references, duplicate resource backlinks, legacy flags, motion/state
words and updates to existing optional parameter storage. This is joined native
validation within a bounded domain: arrays start empty with sufficient capacity,
entry transforms are identity and parameter records already exist. It does not
cover virtual reset, growth, allocation or release in the combined native run.
See `native/snow_host/pose_body_loading_runtime_validation.json`.

Run the independent synthetic example with:

```sh
python3 -m engine.pose_body_loading_bench
```

It uses supplied pools to decode a nonidentity resource transform, allocate both
parameter-record kinds, restore motion and finalize a resource backlink. Its
public test checks the resulting values and service sequence. These are authored
fixture bytes, not extracted assets; this example does not establish live-world
registration, complete asset compatibility or original-engine equivalence.

## Known-body resource transform reset

Known physical-body table29c99a8 virtualD0 resolves to18a99a0. This is a local
transform update, not resource removal. It calls18a80f0 on the entry's transform
slot with the supplied frame. The loader passes identity and update_now=0, which
can return private transform storage to its pool but does not clear resource10,
release the resource or change its backlinks.

After transform assignment, nonzero low-byte update_now invokes18bc750(body,0).
Bodyb0 is then set to the inverse of that byte's truth value. The entry-array pointer
is reloaded, and entry44 bit0 gates the remaining work. If that bit is clear,
bodyaa is preserved. If set, update_now=0 or metadata52 bit3 sets bodyaa bit4.
Otherwise calls18bf970 and18bfb70 occur in order, then bodyaa bit4 is cleared.
The immediate derived-refresh operations remain explicit services in
`update_pose_resource_transform`; their effects are not invented here.

`reset_known_pose_resource` binds the loader's deferred path to the recovered
transform setter and flags. `deserialize_known_pose_body` now uses this binding
by default, retaining an optional caller-supplied dispatch for other body classes.
Array initialization later overwrites entries, so this reset itself must not be
misreported as destruction of the previous resource.

512 additional joined native reader/finalizer comparisons pass without instruction
interception on occupied arrays, exercising the real known virtualD0 and dirty
flags. These fixtures use identity transforms, so no transform free occurs in that
joined comparison. Existing transform-storage comparisons cover private-to-identity
release separately. Public tests check that reset preserves the resource pointer,
releases private transform storage, and that immediate callbacks precede entry-array
reload and respect metadata/entry gates. See
`native/snow_host/pose_body_occupied_loading_validation.json`.

Open boundaries remain pool/growth ownership, immediate derived refresh effects,
resource lifetime outside this setter and live provider registration. No real
asset corpus or live game was used for this pass.

## Inline resource-array storage

Resize helper18bcbb0 receives the descriptor at bodyb8. Pointer is descriptor0,
count is uint16+8, capacity is uint16+a, and inline storage begins at+10, or bodyc8.
That inline area holds one72-byte entry. A request equal to current capacity returns
immediately, even if count would otherwise require clamping.

For requested capacity greater than1, inline storage switches to allocator
allocation of72*capacity bytes, alignment16, tag0x4c. It publishes the new pointer
then copies current count*72 bytes from inline storage. External storage uses
reallocation with the same size/alignment/tag and publishes the returned pointer.
Both paths store the requested low16 capacity. The retained API supports uint16
capacity rather than native oversized/wrapping allocation inputs.

For requests0/1, external storage moves back to inline. Request1 copies exactly
72 bytes before freeing old storage; request0 skips the copy, preserving stale
inline bytes. Free occurs while the old pointer is still published. The pointer
then switches to inline and stored capacity becomes1 for either request. An
already-inline array just gets capacity1. All non-no-op paths finally clamp count
to the requested value. No entry/resource/transform destruction occurs here.

`pose_resource_array_storage.resize_pose_resource_array` implements this policy
with allocator services. The inline map view aliases the body's own bytes. Released
external buffers can remain in evidence maps but are not live storage.512 native
comparisons match all bytes and allocator events:199 allocations,171 reallocations
and57 frees. Original memcpy runs unmodified. Public tests also connect inline
growth to the array reader and check copy-before-free, stale-byte preservation and
same-capacity no-op. See `native/snow_host/pose_resource_array_storage_validation.json`.

This identifies array-buffer ownership only. It does not establish resource or
transform destruction policy, allocator synchronization, or live-safe mutation.
Combined whole-reader allocation-path validation remains separate work.

## Resource-array destruction pass

Routine18bc790 captures bodyc0 and traverses entries in reverse order. Unlike the
loader's transform reset, this path invokes each nonnull resource's deleting
virtual method. For every nonnull resource:

1. Capture resource key10 and call registry dispatcher18b74b0 with descriptor
   `{body,index}`, event1 and that key. Descriptor padding is not semantic data.
2. Reload the resource vtable and invoke its first method with deletion flag1.
3. Reload bodyb8, clear the same entry's resource10, and decrement body110 as uint32.
4. Reload bodyb8 again and inspect transform18. If not shared identity, return it
   through18ba6a0 and replace the transform pointer in the captured entry storage
   with shared identity.

A null resource skips the entire sequence, including transform cleanup. The
original therefore leaves any private transform attached to such an entry alone.
The reason for that ownership arrangement remains unresolved; the reconstruction
does not silently add cleanup. Final bodyc0 becomes0, while array pointer/capacity
remain unchanged. Counter110 can underflow if initial state is inconsistent.

`pose_resource_array_clear.clear_pose_body_resources` implements traversal and
mutation with registry notification, resource deletion and transform return supplied.
Callbacks may relocate entry storage; the implementation preserves the observed
reload points. A transform-return callback does not cause the final identity write
to chase another relocation: that write uses the already captured array.

512 native comparisons pass with1363 notification/destruction pairs and680
transform returns, covering null entries, reverse order, shared/private transforms
and counter underflow. Public tests also exercise array relocation and callback
changes to the count. See `native/snow_host/pose_resource_array_clear_validation.json`.
Registry dispatch internals, concrete resource destructors and whole-body lifetime
remain open. These are synthetic offline fixtures, not proof of live-safe deletion.

## Resource notification and box destruction

Notification18b74b0 is one optional callback, not a registry-list traversal.
It captures manager20, returns if null, otherwise copies the caller's16-byte
body/index descriptor to a local stack object and calls the callback with
`(descriptor_copy,uint32_event,resource_key)`. Callback changes to the copy do
not alter the caller's descriptor. The last four descriptor bytes are copied
padding with no established meaning; synthetic examples may initialize them but
must not describe that initialization as native behavior.

The known box table29c9ac8 first virtual method is18aa740. It publishes teardown
table29c9a88, reads attached object20 and, if nonnull, invokes that object's
virtual+8. It then clears20 and publishes base table29c9800. Deleting flag1 with
flag4 clear returns the box to its pool. Flags1+4 call75e600(size0x50), the observed
return-only stub. Without flag1 no storage return occurs. The returned identity
is not a lifetime guarantee. Attached object release and pool synchronization
remain supplied; this is not proof of an atomic reference-count decrement.

`pose_resource_lifecycle` implements both operations.512 notification comparisons
and512 box-destructor comparisons pass with callback/child/pool effects supplied.
Checks include descriptor mutation isolation, uint32 event truncation, all low
three deleting flags and resource bytes at callback boundaries. Public tests join
notification forwarding and box destruction to the reverse resource cleanup pass.
See `native/snow_host/pose_resource_lifecycle_validation.json`.

The actual installed notification callback, attached-object class and other
resource subclasses remain open. No callback-list behavior, global registry cleanup
or live-safe deletion is inferred from this forwarding function. All validation
used synthetic offline objects.

## Known-body destructor layers

Physical destructor18be6b0 publishes table29c99a8, returns nonnull parameter1b8
to its scalar/vector pool, clears that pointer, then does the same for parameter1c0
and its separate triple pool. It tail-calls middle destructor18bb780, which
publishes29c98c8 and invokes the reverse resource cleanup18bc790. It then performs
the equivalent of resize-to-zero on the resource descriptor: nonzero capacity
permits external buffer release and temporary inline reset; zero capacity skips
that release. Finally it zeros bodyb8 andc2 regardless and calls base18a7bc0.

The base destructor publishes29c9808 and calls body-event broadcaster18a7f60 with
event10. Metadata30 is captured after that notification, returned to its pool and
left as a stale field value. The final table becomes29c9800. This is not the outer
deleting wrapper, which separately decides whether to return body storage.

`pose_body_destruction.destroy_known_pose_body` implements these layers, reusing
the resize policy and accepting the recovered reverse cleanup as a binding. Pool
operations and body-event listener dispatch remain explicit services. It does not
claim to unregister physics provider membership or detach all constraints.

512 native comparisons pass for body bytes, service order and identities, table
state at callbacks, optional parameters and inline/external/zero-capacity storage.
Notification fixtures replace metadata30, confirming the subsequent pool return
uses the new pointer. Resource cleanup is supplied in that native receipt, while
public tests compose the recovered cleanup and verify its ordering before array
release and event10. See `native/snow_host/pose_body_destruction_validation.json`.

The remaining body-event broadcaster has a distinct enabled-listener loop and
thread-local dispatch/deferred-update state; it must not be confused with the
single resource-event callback. Its full behavior and outer body-storage deletion
remain open, along with live-safe lifecycle coordination.

## Body-event listener dispatch

Broadcaster18a7f60 obtains a thread-local state block through the Windows TLS
index and GS table. It captures that TLS base, loads the global listener descriptor,
sets TLS27bd to1 and visits16-byte rows in increasing index order. Each row has a
callback pointer at0 and enabled byte at8. Enabled rows receive `(body,uint32_event)`.
The global registry pointer reloads after each callback, and count is rechecked
before the next index. Listener rows are not snapshotted: appends may receive the
same event, disabling a later row skips it, and registry replacement continues at
the current next index in the replacement array.

After dispatch it sets TLS27bd to0. If TLS27bc is nonzero, it walks the then-current
count backwards and removes disabled rows by decrementing count and shifting the
remaining suffix down16 bytes. Remaining listener order is stable; vacated tail
bytes are not cleared. Registry pointer reloads after each copy. TLS27bc is cleared
at completion. Disabled rows persist if no cleanup request is present.

`pose_body_events.dispatch_pose_body_event` implements this using retained registry,
rows and TLS bytes. It supplies callback code and global registry access explicitly.
It does not invent a recursion counter or restore the previous dispatch flag: nested
dispatch clears that same byte before returning to its outer callback. This is an
observed local consequence, not a claim that recursive notification is supported.
Exception unwinding, listener-registration writers and cross-thread synchronization
remain open.

512 native comparisons execute original GS/TLS reads, listener traversal and memcpy
compaction with1248 supplied callback calls. All registry/row/TLS bytes and callback
arguments match across append, disable and cleanup-request mutations. Public tests
also check registry replacement, absent cleanup requests and nested flag behavior.
See `native/snow_host/pose_body_events_validation.json`. These single-thread synthetic
fixtures do not establish live concurrency or safe arbitrary listener mutation.

## Body listener registration and removal

Append18bb2c0 captures the global listener descriptor once and constructs a16-byte
row containing callback0 and enabled byte8=1. The remaining seven bytes come from
uninitialized stack padding and have no established semantics. It grows capacity
from0 to8 or doubles it through18bb310, reloads count/array from the captured
descriptor, copies the entire row, then increments count. There is no duplicate
check and no dispatch gate. Registry replacement during allocator activity does
not redirect this append to the replacement descriptor.

Removal18bb610 searches callback pointers in order and accepts the first match,
including a disabled row. During dispatch, identified by TLS27bd, it clears that
row's enabled byte and sets TLS27bc for later compaction. Otherwise it decrements
count and shifts the suffix down16 bytes immediately, preserving order and stale
tail bytes. Repeated removal of a duplicated callback during dispatch keeps finding
the already-disabled first row, so another duplicate can remain enabled.

The native routine does not guard a failed search before using index-1; callers
must establish membership. `remove_pose_body_listener` raises an authored KeyError
before writes instead. `register_pose_body_listener` requires explicit seven-byte
padding rather than inventing recovered padding values. Growth remains supplied.
No locks occur in these local routines, but that does not prove all callers are
unsynchronized or that arbitrary cross-thread calls are safe.

512 native append and512 native removal comparisons pass without instruction
interception, using retained capacity and deterministic native stack padding.
All registry/listener/TLS bytes match. Public tests join registration, self-removal,
append during notification and deferred compaction; they also cover duplicate
behavior, missing-membership guard and relocating growth. See
`native/snow_host/pose_body_event_registry_validation.json`.

This supplies the local listener lifecycle needed to study mod hooks. Installed
listener identities, their scheduling/thread ownership, registry startup/shutdown
and allocator integration remain open. These are offline synthetic comparisons,
not authorization or evidence for safe injection into a running game.

## Registered body listener identities

Direct call-site inspection identifies two concrete listener registrations. These
are static installation paths, not a claim that both are active in every session.

- Manager insertion18da8d0 registers18da5e0 when its collection count18 is zero,
  before inserting through18da700. Surrounding protected calls use manager30 as
  a synchronization object; their exact locking semantics remain unvalidated.
- Controller initialization19a4370 calls each child virtual+8, installs two other
  callbacks through18ba3d0/18ba3e0, then registers18b8670. Its teardown19a4320
  unregisters18b8670 before visiting child virtual+20 in reverse order.

Listener18da5e0 captures manager global33368f0 and routes uint32 events as follows:

| Event | Argument | Target operation |
| --- | --- | --- |
|10|body pointer|18dad60|
|11|raw qword bodyb0|18dac90|
|12|body pointer|18daf80|
|other|none|return|

`pose_body_owner_events.dispatch_pose_body_owner_event` implements this exact
routing with manager operations supplied.512 native comparisons pass for targets,
arguments and unchanged body bytes. Public tests connect it to the actual
broadcaster. See `native/snow_host/pose_body_owner_events_validation.json`.
The bodyb0 argument is class-sensitive: it must not be equated with the known
physical body's byteb0 dirty flag without establishing which body classes emit11.

The second listener18b8670 has a larger controller-facing switch. It immediately
ignores10..12. For other events it resolves `body30 -> metadata20 -> owner20` as
its controller; a null controller returns. Its protected enter/leave calls use
controller50. Events outside0..9 perform no switch action after that resolution.
The following table records static branch behavior, not yet a reconstructed or
native-compared implementation of these callees:

| Event | Gate and action |
| --- | --- |
|0|If priority50 bit15 is clear, compare metadata1c to controller4c; on mismatch copy the latter and call18b8860(body). If priority is set and quiet nibble53 is2, call18b8380(controller,body), then18b8860(body). Finally call controller28 virtual+a8 with boolean `priority bit15 is clear`.|
|1|For priority bodies, quiet nibble2 calls18b8380; other quiet values call body virtual+28. Then invoke controller28 virtual+a8 with the same priority boolean.|
|2|Call18b8380(controller,body).|
|3|Only if metadata52 bit3 is set: obtain tree from controller20 through11fd350, then call known tree-removal19598d0(tree,body).|
|4|Only if metadata52 bit0 is clear: call18d0a90(controller20,body).|
|5|Same bit0 gate, then18d16c0(controller20,body).|
|6|Call18b8b60(controller,body).|
|7|Call18b8a40(controller,body).|
|8|Call18b9530(controller,body).|
|9|Call18b9610(controller,body).|

This establishes a direct link from body notifications to known tree removal and
quiet-state virtual dispatch, and supplies concrete leads for provider-membership
and group updates. It does not establish thread ownership, meanings of every event,
callee equivalence or safe asynchronous hooks. Next validation should cover this
switch with explicit callback effects, then bind already reconstructed callees.

## Controller body-event routing

`pose_body_controller_events.dispatch_pose_body_controller_event` now implements
the previously static18b8670 switch documented under "Registered body listener
identities". It preserves the early10..12 return, metadata/owner/controller chain,
null-controller return, protected enter/leave positions and all0..9 branch gates.
Unknown event values still traverse that chain and enter/leave when a controller
exists. The protected calls remain synchronization services; their implementation
is not inferred from placement alone.

Event0's metadata1c stamp assignment occurs before18b8860. Events0/1 reload body
metadata and controller28 after preceding callbacks to compute the final virtual+a8
priority boolean. The retained implementation therefore does not cache a priority
value across a state-changing callback. Event1 body virtual+28 can be bound to the
known physical-body quiet reset only when that class identity is established.

1024 native switch comparisons match all body/metadata/owner/controller bytes and
2181 service calls, with protected enter/leave and callees supplied. Fixtures cover
priority/quiet/flag gates, stamp mismatches, null controller and callback changes
to priority. Public tests join event1 to the recovered known-body quiet reset,
confirming timer/state clearing while motion survives, and check event0 ordering,
event3 tree selection and event4 gating. See
`native/snow_host/pose_body_controller_events_validation.json`.

This supersedes the earlier statement that the larger switch is static-only;
its routing and direct writes are now locally native-compared. Group-transition,
refresh, provider and remaining controller-event effects still require bindings
or reconstruction. No active listener identity, runtime scheduling, lock ownership
or general live mod-hook safety follows from these offline fixtures.

### Body-event group transition

The controller's group-transition helper reaches `18e14f0`. Its local selection
flow is reconstructed in `engine/pose_body_group_transition.py`. Tokens below
identify objects; they are not portable addresses or claims about player identity.

```text
group = body.group
if metadata.flags52 & 8:
    was_special = byte(group == context.special410)
    if predicate(context, body).low_byte != was_special:
        remove_body(context, body)
        if body.virtual8(1).low_byte != 0:
            metadata = reload(body.metadata)
            if !(metadata.priority50 & 0x8000):
                target = context.special408
            elif metadata.flags52 & 8 and predicate(context, body).low_byte != 0:
                target = context.special410
            else:
                target = obtain_group(context)
                if reload(body.metadata).state53 & 15 == 2:
                    body.virtual28()
            append_body(target, body)
        group = reload(body.group)
finalize_group(context, group)
```

The first predicate comparison uses the raw byte, not boolean normalization:
return2 differs from membership1. The second predicate uses a nonzero test.
If reassignment is skipped, finalization uses the initially captured group even
if the predicate changes the body's group field. Once reassignment is entered,
that field is reloaded even if virtual8 rejects admission. Group acquisition can
change metadata before the state2 test. Only ordinary selection takes that local
virtual28 reset path; special targets do not.

Evidence anchors: predicate `18e1dd0`, remove `18e23c0`, obtain `18e19c0`, append
`19573c0`, finalizer `18e11b0`. Append and finalizer have separate reconstructions;
the known physical body's virtual28 is the quiet reset described above. Dynamic
class identity must still be established before binding that implementation live.

Validation: `native/snow_host/pose_body_group_transition_validation.json` records
1024 offline native comparisons, matching2584 ordered calls plus body, metadata
and context bytes. Predicate, group operations and virtual methods are supplied
recording/mutating services. Public tests compose the known quiet reset, checking
that motion survives. This validates local selection and ordering, not callee
internals, live thread ownership, or a general player-wake API. The surrounding
controller synchronization wrapper and connectivity refresh remain separate work.

### Controller group-transition wrapper

The controller listener's transition service is `18b8380`, now reconstructed as
`engine/pose_body_controller_transition.py`. It supplies the missing outer ordering
around the preceding group-selection routine:

```text
if body.metadata.flags52 & 1 or body.group == null:
    return
enter(controller + 0x50)
context = reload(controller.context30)
transition_body_group(context, body)
body.virtual28()
leave(controller + 0x50)
```

The gates are evaluated before enter and are not rechecked. The context is loaded
only after enter. Virtual28 runs after every normally returning inner transition,
including when that inner routine skips reassignment. For the known physical-body
implementation this resets quiet state and its accumulator, preserving motion;
other dynamic body classes require their own implementation. This outer reset is
separate from the inner ordinary-target/state2 reset and from finalizer resets.
The parent controller listener already brackets its switch in synchronization on
the same controller+50 token. Thus the static call chain contains nested entry on
the same token; the reconstruction does not substitute a non-reentrant lock or
claim to establish the protected implementation's actual locking semantics.

Protected call sites `18b83b2` and `18b83d1` resume at decoded continuations
`18b83b8` and `18b83d7` respectively. Linear disassembly through intervening bytes
misidentifies instruction boundaries. These sites are treated as explicit supplied
synchronization services, not executed protected-code equivalents. No exception
cleanup guarantee is added.

Validation: `native/snow_host/pose_body_controller_transition_validation.json`
records512 offline native comparisons of wrapper gates, calls and fixture bytes,
with synchronization, inner transition and virtual28 supplied. Tests mutate context
and gates during enter to establish the reload boundary. A public composition test
runs the reconstructed inner selection and known quiet reset, showing the outer
reset still occurs when selection is skipped. This is local control-flow evidence,
not live-safe scheduling or proof of lock ownership.

### Body connectivity refresh

Controller event0 reaches `18b8860`, reconstructed logically by
`engine/pose_body_connectivity_refresh.py`. This is a connectivity operation, not
merely a transform refresh. It captures controller through body30→metadata20→owner20,
then reads the body's circular link head at80 through getter `12f2f20`.

```text
controller = body.metadata.owner.controller
seed = body.link_head80
if seed == null: return
rows = []
current = seed
repeat:
    rows.append(copy24(current + 8))
    current = current.next20 if current.endpoint8 == body else current.next30
until current == seed
output = collect(controller.provider38, rows)
rebuild(controller.context30, output)
retire(controller.provider38, output, 1)
```

Names collect/rebuild/retire are authored service labels. The three callees are
`18dedf0`, `18e28d0`, `18de440`. Controller identity stays captured; its context30
and provider38 fields are reloaded at their respective call sites. The same mutable
output descriptor passes through all three. An empty head skips all calls; a
nonempty ring still calls the latter stages if collection returns no entries.

Native scratch storage starts with64 inline24-byte rows and doubles at capacity
through `18b9450`; the output starts with512 inline pointer slots. External output
storage is freed before external input storage, with nonzero-capacity and noninline
pointer checks. The public logical API abstracts this scratch ownership rather
than claiming allocation-level equivalence. Its malformed-ring ValueError is an
authored guard; native traversal assumes a valid circular ring.

Validation: `native/snow_host/pose_body_connectivity_refresh_validation.json`
records512 offline comparisons spanning17500 copied rows,1512 downstream calls
and42 supplied scratch growth/free pairs. Both endpoint orientations, empty rings,
capacity crossing and callback changes to controller fields are covered. Native
getter and traversal run; stack probing, allocation and downstream effects are
supplied. Public tests verify snapshot copies and shared mutable output identity.
No live concurrent traversal guarantee follows from this test.

Further static leads, not yet implemented by this module:

- `18dedf0` is now reconstructed; see "Provider link-tree selection" below.
- `18e28d0` is now reconstructed; see "Body connectivity rebuild". Original lead:
  `18e28d0` zeroes context464..46b, skips selected objects with flags84 bit1, and
  follows endpoint8→body.group10. Groups with a0 and a1 both zero are marked a1=1
  and queued once; `19581c0(group,object)` runs for each eligible selected object.
  Correction: `19581c0` removes the object from the group's link array; see
  "Group link-array removal".
  The subsequent group loop clears a1 before calling `18e2de0` and increments
  context464. Those callee effects and full group rebuild remain unresolved.
- `18de440` is now reconstructed; see "Body connectivity retire" below. It
  does not destroy links; it unlinks, resets and queues them.

### Provider link-tree selection

The connectivity refresh's collect stage `18dedf0` is reconstructed by
`engine/pose_provider_link_selection.py`. It is a destructive selection: each
matched node is removed from the provider's tree as its value is reported.

```text
output.count = 0
for row in rows:                       # 24-byte snapshots from the link ring
    meta = row.endpoint0.metadata30
    if not meta.priority50 & 0x8000: continue
    if meta.state53 & 0xF == 2: continue
    node = search(provider.tree8, key=row.qword10)   # unsigned 64-bit compare
    if node is absent: continue
    output.append(node.value10)        # read before removal
    remove(provider.tree8, node.index) # 19a40b0
```

The tree descriptor at provider+8 has the layout already documented in "Body
metadata tree removal": node pointer+0, active count+8, free count+0xC, an
untouched dword+0x10, root index+0x14 and free-list head+0x18. Nodes are 32
bytes with the same left/right/parent, red byte and free byte. This
instantiation's key is the unsigned **64-bit** qword at node+0x18. Retirement
`19a40b0` therefore copies an 8-byte predecessor key, where `1959c50` copies 4
bytes. The two retirement routines are otherwise the same. They share the
red-black unlink `1959d90` and the rotations `1959bb0` (left) and `18da970`
(right). The reconstruction reuses `pose_body_tree._Tree` with `key_size=8`.

Behavior worth preserving:

- Eligibility reads live endpoint metadata through the copied endpoint pointer;
  only the row bytes are snapshots.
- A key repeated across rows is selected at most once, because the first hit
  removes the node. A later equal key can still match a duplicate-key node.
- For a two-child match, the predecessor's key and value move into the matched
  slot and the predecessor slot is retired. The reported value is the original one.
- Retiring a non-final slot pushes it onto the doubly linked free list (free byte
  set, left=-1, right=previous head). Retiring the final slot instead trims
  preceding free slots from the free list and leaves the slot bytes untouched.
- Output growth doubles capacity through `18df270`. The public API abstracts it
  as a Python list.

Validation: `native/snow_host/pose_provider_link_selection_validation.json`
records 512 offline comparisons covering 10,363 rows and 3,595 selections. The
native selector, retirement, unlink and both rotations ran unmodified. Only output
growth was supplied (811 growths). Provider descriptor bytes, every node byte
(including retired slots), selected-value order and all other fixture bytes
matched. Fixtures are valid red-black trees with 0..47 live nodes and 0..7
pre-existing free slots, built by an authored insertion routine. Native insertion
was not compared. A post-condition check confirms each reconstructed tree remains
a valid red-black tree. A deliberate 4-byte-key mutation fails the comparison.
Public tests compose this selector as the refresh's collect stage. The selected
values are not yet joined to concrete object types. The rebuild and retire stages
remain supplied, and no live concurrency guarantee follows.

### Group link-array removal

`engine/pose_group_link_remove.py` reconstructs RVA `0x19581c0`, a 15-instruction
leaf (0x19581c0..0x141958201, no unwind entry) called by `18e28d0` at `0x1418e29b4`
as `(group, object)` for each eligible selected link object. It is not an append:
it removes the object from the group's link/constraint array. The group layout
(+0x40 slot array, +0x48 uint32 count, link index at +0x80, 0xffffffff detached) is
the one already documented for `remove_body_constraints` in CENTRAL_IMPULSE.md
(Body removal and attached constraint pruning), whose inline copy of this exact
sequence is reused; no new layout was introduced.

```text
index = object.index80                 # trusted, membership not searched
group.count48 -= 1
slots = group.slots40
slots[index] = slots[group.count48]    # last active pointer (may be itself)
object.index80 = 0xffffffff
if index < group.count48:              # a different member moved into the slot
    slots[index].index80 = index
```

Quirks: the removed pointer is overwritten, not zeroed, and the old last slot keeps
its pointer (inactive tail retained). When the removed object is last (index ==
new count) the copy is a self-write and no index repair happens. Native does no
bounds check: index >= old count, the 0xffffffff detached value (zero-extended into
a 0x7fffffff8-byte offset) or count 0 (wraps to 0xffffffff) read/write out of the
array. The Python raises ValueError for those cases rather than inventing behavior.
In `18e28d0` this runs after the group a1 queue marking, so the queued group's link
array is shrunk before `18e2de0` runs on it; that downstream effect is unresolved.

Validation: `native/snow_host/pose_group_link_remove_validation.json` records 512
native Unicorn comparisons (11999 members total, groups of 1..199, 170 swap-with-
repair, 136 last-member, 206 single-member cases) of the original run as a leaf with
no callees or supplied services. Group header (0x100 bytes), the whole slot array
including inactive tail, and every member object (0x100 bytes each, random
garbage elsewhere) are compared byte for byte. A deliberate `index < count - 1`
bug failed the harness at trial 4; it was restored and the receipt regenerated.
Only valid active indices are exercised; layouts come from caller context, not a
native constructor; no live or concurrent guarantee.

### Link state reset before provider queue handling

`engine/pose_link_state_reset.py` reconstructs RVA `0x1958ba0`, called by the connectivity retire stage `18de440` immediately after `195c270(object,1)` (endpoint ring removal). It is a single contiguous routine (unwind entry `0x1958ba0..0x1958c13`, no external chunks).

```
reset_pose_link_state(link):
    link[+8]  = 0                      # endpoint body 1
    link[+0x10] = 0                    # endpoint body 2
    0x1958720(link+0x48, null)         # contact span: array +0x58, count +0x60
        # = clear_pose_link_contacts: release each nonnull entry payload (+8 of 16-byte entry)
        #   then count(+0x60) = 0
    held = link[+0x78]
    if held:
        pool_return(held)              # protected block 0x1958bd1..0x1958bff
        link[+0x78] = 0
```

Quirks: endpoints are cleared first, so the rings (+0x20..+0x3f) are left exactly as `195c270` left them and the record can no longer be traced to its bodies. The contact span is the same one cleared by `clear_pose_link_contacts` (wrapper `0x1958b90` is equivalent but not called here); only the count is reset, entry bytes and capacity persist. The held payload at +0x78 is returned to a different pool global than the contact payloads (`[rip+0x19dded8]` versus `[rip+0x19de3c8]`); the visible publication writes the old free-list head into the payload, decrements the pool count at +0x28 and installs the payload as head at +0x30, bracketed by obfuscated protected calls. +0x78 is cleared only after the return, and a null +0x78 is skipped. Routine does not free the link itself; its role as retirement of link state (not destruction) is an authored label.

Validation. `analysis/command-executor-audit/check_pose_link_state_reset.py` runs the original routine in Unicorn for 512 randomized cases (341 with a held payload, 171 null; 0..16 contact entries, 1624 contact releases, 681 null contact payloads, 129 empty spans), supplying both protected pool-return blocks (`0x19587e9`, `0x1958bd1`) as recording services. It compares service order and arguments, the full 0x90-byte link snapshot at every service call, final link bytes, the contact entry array including slack past the active extent, and return address/stack pointer. All 512 pass; a deliberately injected bug (skipping the +0x78 clear) fails at trial 1 and was reverted. Limits: pool locks and free-list publication are not run or validated, payloads are opaque tokens, malformed counts and live concurrency are excluded. Receipt: `native/snow_host/pose_link_state_reset_validation.json`.

### Body connectivity rebuild

The connectivity refresh's rebuild stage `18e28d0` (RVA0x18e28d0..0x18e2a53) is
reconstructed by `engine/pose_body_connectivity_rebuild.py`. It receives
controller.context30 and the selected-object output descriptor (pointer+0,
count u32+8, capacity u32+0xC). It deduplicates the groups of selected objects
through group byte a1, then processes each queued group once.

```text
context.dword464 = 0; context.dword468 = 0     # one qword store
queue = local array, 512 inline slots
n = output.count                                # captured once
for i in 0 .. n-1:
    obj = output.ptr[i]                         # pointer and slot reread each pass
    if obj.flags84 & 2: continue
    group = obj.endpoint8.group10
    if group.a0 == 0 and group.a1 == 0:
        group.a1 = 1
        queue.append(group)                     # grows by doubling through 18df270
    link(group, obj)                            # 19581c0, every eligible object
for group in queue:                             # local queue, callbacks cannot reach it
    group.a1 = 0
    process(context, group)                     # 18e2de0, return ignored
    context.dword464 += 1                       # reloaded after process, u32 wrap
if queue.capacity != 0 and queue.ptr != inline: allocator.vtable18(queue.ptr)
```

Names link/process are authored labels. Behavior worth preserving:

- The flags84 test is a byte test of bit1 only. Skipped objects get neither the
  group gate nor `19581c0`.
- Group gate bytes are read live, after earlier `19581c0` calls. A group already
  marked a1 (or with a0 set) is not queued but is still linked for each object.
  If a callback clears a1, a later object can queue the same group again, and that
  group is then processed twice. If a callback sets a0, later objects of that
  group are not queued.
- a1 is set before `19581c0` and stays set until that group's turn in the second
  loop. Groups found with a nonzero a1 on entry are never cleared by this routine.
- 0x468 is cleared but not otherwise touched. 0x464 is reread from memory after
  every `18e2de0`, so a callback's store is incremented rather than overwritten.
- Output count is captured at entry. The pointer and slot are reread per
  iteration, so in-place slot changes are observed but an appended entry is not.
  No null checks exist on endpoint8 or group10.
- The queue holds 512 pointers inline in a 0x1048-byte frame (stack probe
  `1c45120`). At count==capacity, `18df270(queue, 2*capacity)` grows it. External
  storage is released at exit through the global allocator at image+0x33365b8,
  vtable slot+0x18. The public API models the queue as a Python list.

Validation: `native/snow_host/pose_body_connectivity_rebuild_validation.json`
records512 offline comparisons spanning13998 selected slots (2219 initially
flag-skipped), 11735 `19581c0` calls and7167 `18e2de0` calls, of which30 are
callback-induced re-queues. Applying3625 scripted callback mutations of output
slots, flags84, endpoint/group links, a0/a1 and the 464/468 pair, the native
routine and the reconstruction emit the same call order and arguments. At each
link they also see the same a0/a1, and at each process the same a1 and 464.
Context, descriptor, output-array, object, body and group bytes also match. Eight
cases with513..1099 distinct groups cross inline capacity (10 growths, 8 frees).
The native routine runs unmodified. `19581c0`, `18e2de0`, `18df270`, the allocator
free and the stack probe are supplied. Moving the a1 clear after `18e2de0` fails
the comparison at case1. Public tests also compose this stage under the
refresh. No live or concurrent-mutation guarantee follows.

Static leads for the supplied callees:

- `19581c0(group, object)` is reconstructed as group link-array removal (see
  "Group link-array removal"). A public composition test binds it as this stage's
  link service.
- `18e2de0` now has a byte-model adapter, `engine/pose_group_process_bytes.py`
  (CENTRAL_IMPULSE.md, "Ordinary-group processing on raw bytes"). Original lead:
  `18e2de0` is ordinary-group processing, already reconstructed as
  `engine.pose_group_process.process_pose_group` (CENTRAL_IMPULSE.md, "Ordinary-group
  processing and retirement"). That module uses a dict representation, so the
  two are not yet composed through a shared byte model.
- `18df270` is a generic pointer-array grow. It keeps inline storage up to
  0x200 slots and switches to allocator slots+8/+0x10 above that. It is not
  reconstructed here.

### Body connectivity retire

The refresh's third stage `18de440` is reconstructed by
`engine/pose_body_connectivity_retire.py`. The authored label "retire" overstates
it. Nothing is destroyed or freed. Each selected link leaves its selector1
endpoint rings, has its endpoint, contact and held state reset, and has its
pointer appended to a vector held by a queue owner chosen round-robin from the
provider's slot table. Correction: that vector is a per-worker free list of
recycled link objects, consumed by the pair link worker (see "Recycled link
acquire"), not pending work.

```text
count = output.count                    # captured once
slot = 0
for i in 0 .. count-1:
    link = output.pointer[i]            # pointer reread each iteration
    detach_endpoint_rings(link, 1)      # 195c270, body+0x80 heads
    owner = provider.slots70[slot]      # read before reset
    reset_link_state(link)              # 1958ba0
    v = owner + 0x28                    # pointer+0, count u32+8, capacity u32+0xC
    if v.count == v.capacity:
        reserve(v, v.capacity ? 2*v.capacity : 8)   # 18def10, 32-bit doubling
    v.pointer[v.count] = link           # pointer and count reread after reserve
    v.count += 1
    slot = (slot + 1) % divisor         # 32-bit unsigned div
```

Pointer-vector reserve `18def10` is reconstructed in the same module as
`reserve_pose_pointer_vector`. An equal capacity returns immediately. Otherwise
the routine calls one of three allocator methods through the global
`0x1433365b8` allocator:

- a null pointer is allocated with `vt+8(size, 0x10, 0x28)`;
- a nonnull pointer with nonzero capacity is reallocated with
  `vt+0x10(pointer, size, 0x10, 0x28)`, the tag passed on the stack;
- a nonnull pointer with zero capacity is released with `vt+0x18(pointer)` and
  then nulled.

The byte size is the 32-bit `capacity*8`. The new capacity is then stored, and a
larger count is clamped to it. The retire loop only ever grows, but the release
and clamp paths belong to the shared helper. Five other call sites use the same
helper: 18ddf22, 18de029, 18de3c0, 18de62d and 1958783.

Behavior worth preserving:

- Order per link is ring removal, slot read, state reset, then the capacity
  check. Ring removal must come first, because reset zeroes endpoints +8/+0x10
  and removal needs them. The queue owner is captured before reset. Count and
  capacity are read after it.
- The divisor is a 32-bit unsigned divide applied after each push. A zero
  divisor with nonempty output takes a divide fault after the first link has
  been fully queued. An empty output never divides. The refresh always passes 1,
  so every link lands in slot0's vector.
- Doubling uses 32-bit `lea edx,[rax+rax]`. A capacity of 0x80000000 would wrap
  to 0, and reserve would then release the storage before the store. Count above
  capacity is never grown or checked. Neither case is reachable from valid
  state; both are recorded rather than guarded.
- Output count is captured once. Output elements are reread every iteration.

Validation: `native/snow_host/pose_body_connectivity_retire_validation.json`
records 512 offline comparisons covering 2,901 queued links, 88 vector
allocations and 936 reallocations. The comparisons also cover 2,804 contact and
2,003 held pool-return calls and 15 divisor-0 faults. All of the following run
natively: the retire loop, endpoint-ring removal `195c270` with its accessors
`18baba0`/`18bb430`, link reset `1958ba0`, contact clearing `1958720`, and
reserve `18def10`. Only the two protected pool-return blocks (0x19587e9,
0x1958bd1) and the allocator vtable entries are supplied. The Python side
composes `retire_pose_body_connectivity` with `detach_pose_endpoint_rings`,
`reset_pose_link_state` and `reserve_pose_pointer_vector`. It matches every
supplied call and its arguments, a 0x90-byte link snapshot at each pool-return,
and every fixture byte. The fixture bytes cover provider, owners, old and new
queue arrays, bodies, links, contact arrays and output.

Fixtures attach 0..24 links to selector1 rings over four bodies, using the
validated reconstructed attach rather than native attach. They select a random
subset in random order. Divisors are 0..5 with aliased slot owners (216 cases).
Owner vectors are null or nonnull with capacities 0..8. In 128 mutation trials,
the pool-return services redirect the current provider slot and fill an owner
vector during reset. A separate 256-case leaf comparison of `18def10` covers its
no-op, allocate, reallocate, release and count-clamp paths, plus 32-bit size
truncation. The harness was shown to fail twice. Reading the provider slot after
reset fails at retire case 81. A shifted count clamp fails at reserve case 46.
Public tests compose retire as the refresh's third stage, with real ring removal
and link reset. Pool internals, locks and the allocator remain supplied. The
queue's consumer is unreconstructed, and no live or concurrency guarantee
follows.

Static leads, not implemented:

- The other caller is `18ddc40`. It calls retire with a divisor of
  `min(32, min(dword [[0x143336610]+0x10], n/10+1))`, then `18de510` with the same
  divisor. It then gathers `&provider.slots70[i]+0x28` for each slot and
  dispatches the slot table at provider+0x70 through `18b7ca0`, with callback
  `0x1418df760`, followed by `18df4e0` and `18df630`. The slots therefore look
  like per-worker job contexts. Superseded: `18ddc40`, the worker `18df760` and
  `18de510` are now reconstructed (see "Pair link job orchestration", "Pair link
  worker", "Recycled link acquire" and "Neighbor record retire"). The +0x28
  vectors are free lists of recycled links, not pending work.
- `18de510`, the neighbor routine, walks provider+0x38's indexed tree in order.
  For values whose dword+0x58 == 4, it removes the node through `19a40b0`, then
  calls `195c270(value,0)` (selector0, body+0x88) and `195c360(value)`. It
  appends the value to the slot owner's vector at +0x48, using the same
  round-robin and reserve.
- The pool-return blocks in `1958720`/`1958ba0` push onto free lists at globals
  0x143336bb0/0x143336bb8 and 0x143336aa8/0x143336ab0, under obfuscated thunks.
  They remain supplied.

### Pair link job orchestration

`18ddc40(provider, pairs, count, output)` is reconstructed by
`engine/pose_pair_link_jobs.py`. It drives the retire stages, the per-worker pair
jobs and the merges. It reconstructs control flow only. Every callee is a service.

```text
d = [0x143336610]                               # global dispatcher
workers = min(32, min(d.capacity10, count/10 + 1))   # u32; mul 0xcccccccd >> 35
retire(provider, output, workers)               # 18de440
retire_neighbors(provider, workers)             # 18de510
ctx[i] = provider.slots70[i] + 0x28  for i < workers   # read after both retires
rebalance(ctx, workers)                         # 1989e60
provider.pairs170 = pairs; provider.count178 = count; provider.cursor17c = 0
dispatch([0x143336610], workers, 0x1418df760, &provider.slots70)   # 18b7ca0; global reread
merge_links(provider, workers)                  # 18df4e0
merge_neighbors(provider, workers)              # 18df630 (tail jump)
```

Behavior worth preserving:

- The global dispatcher pointer is read twice: once for capacity and again for the
  dispatch call.
- Contexts are gathered after `18de510`. The pair array, count and zero cursor are
  stored after the rebalance and before dispatch. Garbage in those fields is never read.
- A dispatcher capacity of 0 gives zero workers, but every stage is still called with 0.
  The supplied 1989e60 would divide by that count, so its zero-worker behavior is not
  asserted.
- The argument table passed to the dispatcher is the provider's slot table itself.
  Each dispatched callback therefore receives one slot-owner pointer.

Validation: `native/snow_host/pose_pair_link_jobs_validation.json` covers 512 offline
comparisons. Native 18ddc40 runs, and its six callees are intercepted at entry.
Compared: call order and arguments, the gathered context array contents, slot-table
and +0x170..0x17f snapshots at each call, final provider bytes and the global pointer.
Pair counts range over 0..0xffffffff, including n/10 boundaries. Capacities range over
0..0xffffffff. Resulting worker counts: 0 in 46 cases, 32 in 115, capacity-limited in
211, count-limited in 168. In 128 mutation trials, services rewrite slots, swap the
global dispatcher (42 dispatches went to the switched dispatcher), scribble
+0x170/+0x17c, and advance the cursor during dispatch.

The harness was shown to fail twice. Gathering contexts before 18de510 fails at
case 39. Reading the dispatcher only once fails at case 19. A public composition test
binds retire to `retire_pose_body_connectivity`, dispatch to `dispatch_pose_workers`
with its serial atomics, and the callback to `run_pose_pair_worker`. In it, the
serial caller worker claims all 25 pairs, and the helped workers claim none.

### Pair link worker

Callback `0x1418df760` is a 5-byte `jmp 18ddd30`. It is reconstructed by
`engine/pose_pair_link_worker.py` together with its three pair handlers and the
recycled-link acquire. The worker context is the slot owner. Owner+0 is the provider.

Owner layout, from field use:

- +8: new-link vector (pointer, count +0x10, capacity +0x14).
- +0x18: neighbor vector (count +0x20).
- +0x28: link free list. 18de440 fills it; 18ddf60 pops from it.
- +0x38: vector.
- +0x48: neighbor free list, filled by 18de510.
- +0x58/+0x60: frame scratch pointer and size.

```text
owner.count10 = 0; owner.count20 = 0
owner.scratch58 = scratch_alloc([0x1433368d0], 0x5dc0); owner.size60 = 0x5dc0   # 18c9140
i = lock xadd(owner.provider.cursor17c, 1)
while i < owner.provider.count178:              # provider and count reread every pass
    pair = owner.provider.pairs170 + 24*i       # (first body, second body, key)
    ka, kb = first.kind30, second.kind30
    if ka.kind50 in (1,0x8002) and kb.kind50 in (1,0x8002):
        if first.wc0 and second.wc0:
            if (ka.b52 | kb.b52) & 4: flagged(owner, pair)       # 18e0a60
            else:                     dynamic(owner, pair)       # 18df770
        # else: skipped
    else: static(owner, pair)                                    # 18df910
    i = lock xadd(owner.provider.cursor17c, 1)
scratch_free([0x1433368d0], owner.scratch58); owner.scratch58 = 0; owner.size60 = 0   # 18c8f50
```

dynamic `18df770`:

```text
same = first.kind30.q20 == second.kind30.q20
(index, link) = search(provider.tree8, pair.key)       # unsigned 64-bit, root +0x1c
if index == -1:
    link = acquire(owner+0x28); link.8/10/18 = pair (reread); link.f84 &= ~2; link.50 = link
generate_contacts(owner, first, second, link, same)    # 18dd400
refresh_contact_flag(link)                             # 18dde70
if first.baa >= 0x80 or second.baa >= 0x80: external(owner, first, second, link)   # 18e0ad0
elif link.held78: release_held(link)                   # 18de3e0
ok = filter(owner.provider, link)                      # 18deb70
if not ok: if index == -1: link.f84 |= 2  else: link.f84 &= ~1; return
elif index != -1: return
push(owner+8, link)                                    # reserve 18df030 (tag 0x25)
```

static `18df910`: if first.kind50 == 0x8002 and second.kind50 == 4, return. If the key is
in provider.tree8, return. Otherwise acquire a link, copy the pair, set f84 |= 2,
set link.50 = link, and push it to owner+8.

flagged `18e0a60`: search the provider+0x38 tree (root +0x4c) for the key. If found,
tail-call `18dfa10(owner, pair)`; otherwise tail-call `18e01e0(owner, pair)`.
Correction: both tail calls leave r8d live. On a hit it holds the found node index,
so the real call is `18dfa10(owner, pair, index)` (see "Flagged neighbor update").
`route_pose_flagged_pair` drops that index; use `route_pose_flagged_pair_indexed`.

### Recycled link acquire

`18ddf60(vector)`:

```text
if v.count:
    v.count -= 1; link = v.ptr[v.count]
    link.vtable[0] (link, 0)                    # destructor, no free
    link.8,10,18 = 0; link.0 = 0x1429c9fd0; link.20..38 = 0
    link.40 = lock xadd([0x14333683c], 1)      # global serial, prior value
    link.0 = 0x1429c9fd8; link.50 = 0; link.58 = &link.68; link.60 = 0; link.64 = 1
    f = link.f84 (read after the destructor); link.78 = 0; link.80 = -1; link.f84 = (f & ~2) | 1
    return link
need = count + 5
if need > cap: reserve(v, max(need, 2*cap))    # 18def10, tag 0x28
v.count += 5; refill(v.ptr + old_count*8, 5)   # 18de1e0, protected pool allocation
v.count -= 1; return v.ptr[v.count]            # refilled object: no destructor, no constructor
```

Behavior worth preserving:

- Retire does not free links. The next pair job that needs a new link reuses one in
  LIFO order: the destructor runs, then the object is reinitialized in place. The
  inline contact storage at +0x68 has capacity 1.
- In a refill, the last of the 5 pushed objects is returned without destructor or
  reinitialization. The refill itself constructs all 5 (see "Pair link worker callees").
  The other 4 are destroyed and reinitialized when they are popped later.
- Flags +0x84 are read after the destructor.
- The worker never reads the dispatcher's caller-thread flag.
- The handlers recompute A/B from the pair, but the link triple is reread after acquire.
- Static and dynamic handlers search provider+8 (keys of existing links). The flagged
  handler searches provider+0x38 (the neighbor tree).
- A new link rejected by the filter is still pushed, with bit1 set. An existing link is
  never pushed; on rejection it loses bit0.
- `18df030` is byte-for-byte `18def10` with tag 0x25.

Validation: `native/snow_host/pose_pair_link_worker_validation.json` covers 512 worker
cases plus 256 direct acquire cases and 128 direct 18df030 cases. The following run
natively: thunk, worker, all three handlers, acquire, both reserves, the lock-xadd
cursor and the global serial. Supplied: contact generation, flag refresh, held release,
external contacts, filter, the two flagged handlers, the pool refill, the link
destructor, scratch alloc/free and the allocator vtable.

Totals: 5,164 pairs, 770 dynamic, 67/285 flagged found/new, 1,611 recycled links,
503 refills, 2,114 new links pushed, 345 held releases, 211 external calls, 564
tag-0x25 growths, 6 serial wraps. 128 mutation trials bump the shared cursor or change
the count between claims. Acquire leaf paths: 84 recycle, 62 refill without reserve,
110 refill with reserve (15 from a null pointer). Reserve leaf: 37 no-op, 25 allocate,
52 reallocate, 14 release, 34 clamp.

Compared: service call order and arguments, the 0x90-byte link at contact generation
and destruction, flags at filter, every fixture byte including refilled and allocated
storage, and the serial counter. The harness was shown to fail twice. Reading the
flags before the destructor fails at case 0. Pushing a found link after rejection
fails at case 2.

A public composition test runs the real retire (with ring removal and reset) into
owner+0x28, then the worker. The retired links come back in LIFO order with
increasing serials.

### Neighbor record retire

`18de510(provider, divisor)` is reconstructed by `engine/pose_neighbor_retire.py`.
It reuses `pose_body_tree._Tree.remove(key_size=8)` (19a40b0) and
`detach_pose_endpoint_rings`. It adds `clear_pose_neighbor_record` (195c360).

```text
i = leftmost(provider.tree38)              # root +0x4c
slot = 0
while i != -1:
    value = node[i].value10
    next = successor(i)                    # right-subtree leftmost, else parent climb; BEFORE removal
    if value.state58 == 4:
        remove(tree38, i)                  # 19a40b0
        detach_endpoint_rings(value, 0)    # 195c270, body+0x88 heads
        owner = provider.slots70[slot]
        value.count50 = 0 (decrement loop); value.10 = 0; value.8 = 0   # 195c360
        push(owner+0x48, value)            # 18def10, 2*cap or 8
        slot = (slot + 1) % divisor        # u32 div after push
    i = next
```

Behavior worth preserving:

- The successor is computed from live links before removal. A two-child removal moves
  the already-visited predecessor's key and value into the current slot. The
  precomputed successor stays valid.
- 195c360 decrements +0x50 one step at a time down to 0. The result is the same as a
  store of 0, but the cost grows with the count.
- An empty tree never divides. Divisor 0 faults after the first queued record.

Validation: `native/snow_host/pose_neighbor_retire_validation.json` covers 512 offline
comparisons. Fixtures are valid red-black trees with 0..39 live and 0..5 free slots
(10,126 live nodes in total). Totals: 4,888 retired, 1,686 two-child removals, 281
trailing-slot retirements, 15 divisor-0 faults, 126/1,105 allocations/reallocations,
286 aliased-owner cases. Selector0 rings include records that are not in the tree.
Only the allocator vtable is supplied. The sweep, 19a40b0, 1959d90, 1959bb0, 18da970,
195c270 with its accessors, 195c360 and 18def10 all run natively.

Compared: every fixture byte (descriptor, nodes including retired slots, bodies,
records, owners, arrays) and the allocator calls. The harness was shown to fail three
ways. Starting at the root fails at case 1. Advancing the slot before the owner read
fails at case 5. Computing the successor after removal makes the Python side not
finish within 60 s. The owner read between ring removal and clear cannot be
distinguished by this harness.

Static leads, not implemented:

- `1989e60(ctx[], n)` rebalances the worker free lists. It sums the counts of the
  owner+0x28, +0x38 and +0x48 vectors and computes avg+1 for each. It then moves
  surplus entries from over-full workers to the next worker, round-robin over 2n
  steps, growing with tag 0x28.
- `18df4e0` concatenates every owner+8 new-link vector into provider+0x28 (memcpy
  1c6afb0), sorts it with 1c8fd50 (8-byte elements, comparator just before 18df4e0),
  then calls `195c170(link,1)` for each link (selector1 ring attach) and continues.
- `18df630` concatenates the owner+0x18 vectors into provider+0x58, then inserts each
  entry's key into provider+0x38 through 18de830.
- `18dd400` (contact generation), `18deb70` (filter chain: provider+0x188, kind+0x20→+0x70,
  body+0xa0 callbacks), `18e0ad0`, `18dfa10`, `18e01e0` and `18de1e0` (pool refill)
  remain supplied.

---

### Connectivity refresh end-to-end composition

`tests/test_pose_connectivity_full_chain.py` composes the whole refresh chain over one
shared token-to-bytearray memory model: `refresh_pose_body_connectivity` with collect
`select_pose_provider_links` (destructive red-black selection), rebuild
`rebuild_pose_body_connectivity` with link `remove_pose_group_link`, and retire
`retire_pose_body_connectivity` with detach `detach_pose_endpoint_rings`, reset
`reset_pose_link_state` and reserve `reserve_pose_pointer_vector` (fake allocator). The
same link records serve as ring records, tree node values (key = link+0x18, equal to the
third qword of the copied row), group members and queued pointers. No representation
mismatch was found. Only the per-group process callee (`18e2de0`) is a recording stub, and
the allocator is an authored stand-in. The fixture (including the red-black tree builder)
is authored synthetic data: this is composition coverage of recovered modules, not live
evidence. Observations: refresh passes divisor 1 to retire, so every link queues to the
provider's slot-0 owner; tree, group arrays and rings are all checked for post-state
invariants; with all links ineligible, rebuild and retire still run with an empty output.

### Live snapshot check (spawn state)

A read-only live check ([receipt](../../native/snow_host/pose_connectivity_live_snapshot_validation.json))
captured the player's main and rider bodies while the world Step job was held
through the snow host. It took 12 snapshots across three bounded sessions, with
navigation input only and no plugins or writes. Both bodies carry the
physical-body table `0x29c99a8` and share one metadata owner. In every snapshot
the controller (owner+0x20) and the group (body+0x10) were null, and the +0x80
and +0x88 heads were empty. Only +0x90 command-constraint rings were present,
all closed and symmetric. The body-event listener (`18b868c..18b86a0`) skips
bodies whose controller is null, so in this state event 0 cannot reach
`18b8860`.

A bounded scan of the live-verified world physics object and state found one
controller. It was accepted only when this loop closed: controller →
context+0x418/+0x428 groups (table `0x29caba0`) → body (table `0x29c99a8`) →
metadata → owner → controller. Its provider tree was empty, and none of its 973
group bodies had a ring head. Run in Unicorn over the captured bytes, native
`18b8860` took the empty-ring return in 20 of 20 runs, with no service calls,
no writes and no uncaptured reads.

This input exposed a strictness mismatch. `refresh_pose_body_connectivity`
resolved the controller before testing the seed and raised `KeyError` on the
null controller. Native only loads that pointer before the test. The module now
defers the lookup until after a nonempty seed. A public test covers that case,
and the synthetic native comparison still passes.

Selection, rebuild and retire were not exercised on live bytes, because the
reachable state had no selector-1 links. Their validation remains synthetic.
Reads were sequential under a held Step job, not an atomic snapshot. The run
evaluated the captured state; it did not observe an invocation. Controllers
other than the one found, such as one used while riding, were not examined.
The riding-state follow-up is below.

### Live snapshot check (riding state)

A second read-only live check captured the player while it was riding
([receipt](../../native/snow_host/pose_connectivity_live_ride_validation.json)).
Both sessions used native director startup, and both reached gameplay without
navigation keys. The rider was then moved with bounded SendInput holds of scan 17
(forward), 1.5 s each. A private coordinator read the player chain at about 4 Hz.
A snapshot was taken whenever a player body had a non-null controller and a
nonzero +0x80 head, or when the operator asked for one. For each snapshot, the
coordinator held the world Step job through the snow host, read every region
twice and then resumed.

Seven snapshots came from riding, across two sessions. Once the board moved, both
player bodies joined the simulation. Each had a non-null controller, a non-null
group and a nonempty +0x80 ring with one or two links. Main also had a +0x88
head. The player's controller was the same one the closed-loop world scan finds.
Its provider tree held 2 to 11 live nodes.

Four more snapshots were taken during a crash tumble in the second session. In
those, both player bodies were detached again: controller null, +0x80 empty. The
world bodies under the same controller carried rings of up to 27 links, and the
provider tree held 25 to 41 live nodes. In every snapshot, every ring was closed
and symmetric, every provider tree passed the red-black and free-list checks,
and the second read changed no region. The engine step counter did not move
during any read.

`analyze.py` compared native `18b8860` in Unicorn with the Python chain 63
times. Each player body was compared in every snapshot, along with up to six
extra roots per snapshot drawn from the bodies that carry rings. All 63
comparisons matched exactly:

- **Inputs:** 55 comparisons had selection rows; 8 took the empty-ring return
  (the detached player bodies). Row counts ranged from 1 to 20. Three
  comparisons had rows but selected nothing.
- **Service calls:** in total, native made 60 group-processing calls, 41
  pool-return calls and 2 allocator calls, with 2 heap allocations. The Python
  chain produced the same arguments in the same order.
- **Bytes:** native changed 5,709 bytes in total, with 0 mismatched bytes.
- **Errors:** there were no uncaptured reads, no Python errors and no native
  errors.

The deferred controller lookup removed the earlier `KeyError`.

Limits:

- **Offline evaluation:** the captured state was evaluated offline. No in-game
  call of `18b8860` by controller event 0 was observed.
- **Atomicity:** reads were sequential under a held Step job, so the snapshots
  are not atomic.
- **Stubbed services:** group processing (`18e2de0`), pool return and the
  allocator are recording stubs. Their argument sequences were compared, not
  their effects.
- **Coverage:** most inputs had one or two links. The largest live selections
  had 10 and 20 rows. Retire divisors above 1 and repeated reallocation growth
  were not exercised.
- **No landing moment:** a combined forward-and-jump hold was rejected by the
  input helper. No landing-contact moment was isolated, and the crash snapshots
  came from riding into terrain.

### Pair link free-list rebalance

`1989e60(contexts, n)` is reconstructed by `engine/pose_link_free_list_rebalance.py`. It is the
`rebalance` service of the pair link job orchestration. It has no native callees; the pointer-vector
growth (`18def10`, tag 0x28, alignment 0x10) is inlined three times.

`contexts` is an array of n pointers, each to slot owner + 0x28. Each context holds three pointer
vectors at +0x00, +0x10 and +0x20 (owner +0x28 recycled link free list, +0x38 vector, +0x48 neighbor
free list), each {pointer, count u32 at +8, capacity u32 at +0xC}.

```text
for v in 0..2:  limit[v] = (sum of ctx[i].vec[v].count) / n + 1     # u32, computed once up front
for p in 0 .. 2n-1:                                                  # u32
    src = ctx[p % n];  dst = ctx[(p + 1) % n]
    for v in 0..2:
        while src.vec[v].count > limit[v]:
            pop last pointer from src.vec[v]
            if dst.vec[v].count == capacity: reserve(dst.vec[v], 2*capacity or 8)
            push it on dst.vec[v]
```

Behavior worth preserving:

- Limits are fixed before any move. A surplus only travels one ring hop per pass, so with 2n
  passes a large surplus on one context ends as limit, limit, ..., remainder (for example 9 on
  one of three contexts becomes 4, 4, 1, not 3, 3, 3).
- Elements move from the tail of the source and are appended in that order, so order reverses.
- Vector 0, 1 and 2 are independent, each with its own limit; the per-vector loop is do-while
  guarded by a count test.
- A single context never moves (limit exceeds its own count). Zero contexts divides by zero; not
  asserted, the leaf raises ZeroDivisionError.
- The contexts array is read as pointers, so the orchestration's gathered list (owner + 0x28) is
  passed straight through.

Validation: `native/snow_host/pose_link_free_list_rebalance_validation.json`, 512 randomized
Unicorn cases (harness `analysis/command-executor-audit/check_pose_link_free_list_rebalance.py`).
Native 1989e60 runs in full, including inlined growth; only the three allocator vtable entries are
stubs. Compared: ordered allocator calls with arguments, and every fixture byte (context array,
vector headers, element arrays, newly allocated arrays). 1..8 contexts; 313 cases moved elements
(13203 elements), 191 were already balanced, 8 were zero-context faults; 88 allocations from empty
storage and 4222 reallocations. Moves occurred in vector 0, 1 and 2 in 280, 276 and 287 cases. The
harness failed when the limit's +1 was dropped. Unit tests: `tests/test_pose_link_free_list_rebalance.py`
(9 tests), including a composition that binds the leaf as the `rebalance` service of
`run_pose_pair_link_jobs` and checks that the gathered contexts are levelled 12,0,0 to 5,5,2 with
conservation.

Not covered: aliased context pointers (would not terminate natively), counts above capacity, 32-bit
sum wrap, live behavior. The allocator stays supplied.

Static leads: the only 32-bit hazards are the sum wrap and `2n` pass count wrap; both need
implausible counts.

### Pair link merges

`18df4e0(provider, workers)` and `18df630(provider, workers)` are the two merges that
`18ddc40` calls after dispatch. Both are reconstructed in `engine/pose_pair_link_merge.py`,
together with the sort comparator `18df4a0`. Every other callee is a supplied service.

```text
# 18df4e0: new links
total = sum(slot[i].count10 for i < workers)             # u32 wrap; unrolled by 2, plain sum
provider.count30 = 0
if total > provider.cap34:
    provider.reserve(+0x28, total if cap == 0 else cap doubled until >= total)   # 18defa0, tag 0x22
provider.count30 = total
dst = provider.ptr28
for each slot: copy(dst, slot.ptr8, slot.count10 * 8) (1c6afb0); dst += bytes    # count re-read here
sort(provider.ptr28, provider.count30, 8, 0x1418df4a0)                           # 1c8fd50
i = 0
while i < provider.count30:                    # count and pointer re-read every pass
    link = provider.ptr28[i]
    attach(link, 1)                            # 195c170
    insert(provider+8, key = qword[link+0x18], link)     # 18de6a0
    i += 1

# 18df630: neighbor records (owner +0x18/+0x20 -> provider +0x58/+0x60/+0x64), no sort
reserve is 18df0c0 (tag 0x24); attach(record, 0); insert(provider+0x38, key, record)  # 18de830
tail jump: 18dea90(provider)

# 18df4a0 comparator (receives pointers to the 8-byte elements)
for off in (8, 0x10): d = a.off.body30.kind54 - b.off.body30.kind54  (u32 wrap, signed result); return first nonzero
```

Behavior worth preserving:

- The provider count is cleared before the reserve and set to the total afterward. A
  reserve is only requested when the total exceeds the old capacity. Existing contents
  are not copied; the old data is dead.
- The requested capacity is the total when the capacity is 0, else the old capacity
  doubled (u32) until it reaches the total. A wrapping double (capacity at or over
  0x80000000) never terminates natively; the Python module raises OverflowError.
- `18defa0` and `18df0c0` are `18def10`'s body with tags 0x22 and 0x24 (byte-identical
  apart from the allocator-global address, the tag and the branch targets).
- The comparator subtracts as u32 and returns a wrapped result: kinds 3 and 0xffffffff
  give +4, so the 0xffffffff body sorts as if it were -1. It is not a true ordering of
  unsigned kinds.
- Key read: `[(link or -8) + 0x18]`. A null entry would be read from address 0x10.
- Attach selector is 1 for new links and 0 for neighbor records. The neighbor merge does
  not sort.

Validation: `native/snow_host/pose_pair_link_merge_validation.json` covers 1,280 offline
comparisons: 512 native 18df4e0 runs, 512 native 18df630 runs and 256 native 18df4a0
runs. Native routines run over the memory image; reserve, copy, sort, attach, both
inserts and 18dea90 are intercepted at entry. Compared: ordered service calls and
arguments, provider vector descriptor at reserve, sort and finish, provider
count/pointer at each attach, all 0xb0000 fixture bytes, and the signed comparator result.
Worker counts range 0..32 (108 zero-worker, 510 odd). 518 reserve calls and 506 runs
without one; 26,118 entries total, at most 146 per run. 256 mutation trials shrink the
provider count or swap its array pointer during attach/insert (158 changed the walk).
The harness was shown to fail twice. Not clearing the count before the reserve fails at
case 6. Hoisting the count out of the walk loop fails at case 3.

Composition test: `tests/test_pose_pair_link_merge.py` runs the real retire, the real
dispatcher and the real pair worker inside `run_pose_pair_link_jobs`, then binds
`merge_links` and `merge_neighbors` to the two new functions. Worker 0 creates 25
links; two foreign links and two neighbor records stand in for other workers. All 27
links are sorted, attached and inserted in key order, the neighbor records are
inserted at provider+0x38, and `18dea90` is called last.

Static leads, not implemented:

- `18dea90(provider)` walks the provider+0x38 tree (root +0x4c, 32-byte nodes) from the
  leftmost node by successor and, for each node's value, sets value+0x58 = 4 when
  value+0x5c is 0, then clears value+0x5c.
- `18de6a0(tree, &key, &value)` and `18de830` are the tree inserts (red-black; 18de6a0
  starts with a vector grow at +0x10 when full). The sort `1c8fd50` is the shared 8-byte
  element sort whose stability is unknown.

### Pair link filter

`18deb70(provider, link)` returns true when every present predicate accepts. It is
reconstructed by `engine/pose_pair_link_filter.py` (`filter_pose_pair_link`). It is
a leaf apart from up to five indirect calls, each made with the link as the only
argument. Only the low byte of each result counts.

```text
p = provider.q188;                       if p and not p(link): return 0
A = pred70(link.first.kind30.q20)        # null when the kind extension is null
                                         if A and not A(link): return 0
B = pred70(link.second.kind30.q20)       if B and B != A and not B(link): return 0
C = link.first.qA0;                      if C and not C(link): return 0
D = link.second.qA0;                     if D and D != C and not D(link): return 0
return 1
```

pred70(ext) is `ext.q70 if ext else 0`.

Behavior worth preserving:

- `link+8` and `link+0x10` are reread before each step, so a predicate that edits
  the link changes which body supplies the next pointer.
- The A/B and C/D dedup compares pointer values only. B is compared with A even
  when A is null; a nonzero B then still runs.
- Rejection returns at the first false predicate. The dynamic handler turns that
  into bit1 on a new link (still pushed) or a cleared bit0 on an existing one.
- Nothing in the link or provider is written by the filter itself.

Validation: `native/snow_host/pose_pair_link_filter_validation.json` runs 512
randomized cases of the native routine in Unicorn. 344 accepted and 168 rejected;
1,078 predicate calls; rejections at call 1/2/3/4/5 are 85/50/28/4/1; 173 cases
have a predicate rewrite a link body pointer mid-filter. Supplied: the predicate
bodies (hooked at five authored stub addresses; random rax with garbage in the
upper 56 bits). Compared: boolean result, ordered (address, link) calls, all
fixture bytes. The harness was shown to fail once: dropping the `B != A` dedup
fails at case 0.

Composition tests bind the real filter as the worker's filter service: a rejected
new link is pushed with bit1 (and the filter saw bit1 clear and the copied pair),
an accepted one is pushed clean, a rejected existing link loses bit0 and is not
pushed.

Static leads: the predicate targets (provider+0x188, kind extension +0x70, body
+0xA0) are not yet identified; they are the natural next routines to reconstruct.

### Pair link external contacts

`18e0ad0(owner, first, second, link)` (rcx, rdx, r8, r9) is reconstructed by
`engine/pose_pair_external_contacts.py` (`external_pose_contacts`). The dynamic
handler calls it instead of the held release when either body's byte at +0xAA is
at least 0x80. The owner argument is never read.

```text
rec = link.q78
if rec == 0:
    guard_enter()            # 143f4633d, arg [143336ab0]
    rec = pool_take()        # 18dd100, arg [143336aa8]
    guard_leave()            # 14357414d, arg [143336ab0]
    link.q78 = rec
for body, blocks, extra in ((first, ((20,40),(30,50),(40,60),(50,70)), 0x00),
                            (second, ((80,40),(90,50),(A0,60),(B0,70)), 0x60)):
    for dest, src in blocks: rec[dest..dest+12] = body[src..src+12]     # 3 dwords
    if query_slot1(body, 0x8002) & 0xff: rec[extra..+0x18] = body[0x1a0..0x1b8]  # 6 dwords
    else:                                   rec[extra..+0x18] = 0                    # 3 qwords
```

Behavior worth preserving:

- link+0x78 is the same slot the dynamic handler tests before the held release. The
  record is created lazily and then refilled in place on every external call.
- The first body's virtual query runs after the first body's blocks and before the
  second body's blocks; a query that edits body bytes shows up in the second body only.
- Record bytes 0x18..0x20, 0x3c..0x40, 0x5c..0x60, 0x78..0x80 and 0xbc.. are never
  touched.
- The record is stored to the link only after the guard is released and before any copy.

Validation: `native/snow_host/pose_pair_external_contacts_validation.json` runs 512
randomized cases of the native routine in Unicorn (259 new record, 253 reused; first
query true 318, second 302, both false 87; 395 cases where the query changed body
bytes mid-routine). Supplied: both obfuscated stubs, the pool take, and the body
virtual query. Compared: ordered service calls with arguments (the lock object
[143336ab0] and pool object [143336aa8] are confirmed as the stub and take
arguments) and every fixture byte. The harness was shown to fail once: reading
second.0x74 instead of 0x70 for the last block fails at case 0.

Limits: the two obfuscated stubs are modelled as an enter/leave pair. Their lock
semantics are inferred from placement around the pool take, not proven. They must
return with `ret 8` (each is called after `push reg`), which the native epilogue
requires; they preserve rdi and rbx. The pool record size (at least 0xbc) and the
meaning of query mask 0x8002 are not recovered.

Composition tests bind the real routine as the worker's external service: a new
link gets a record taken under the guard, an existing link with a record is refilled
in place without guard or take, and the held release is not called.

Static leads: 18dd100 (pool take, sizing 0x2b-tagged block growth), the two
obfuscated stubs, and the body vtable slot 1.

### Flagged neighbor update

`18dfa10(owner, pair, index)` is reconstructed by `engine/pose_flagged_neighbor_update.py`.
The router `18e0a60` reaches it when the pair key is found in the provider+0x38 tree.
`index` is the node slot it found. The record is that node's value (+0x10). The routine
refreshes the record's list of colliding shape pairs.

Record fields:

- +0x48: entries. Each is a u32 whose low u16 is the first body's shape index and
  whose high u16 is the second body's shape index.
- +0x50: count. +0x54: capacity.
- +0x58: state. +0x5c: touched byte.

Body fields:

- +0x40: 3x4 transform. Rows are at +0x40, +0x50 and +0x60; translation is at +0x70.
- +0xb8: shape-entry array, 0x48 bytes per entry.
- +0xc0: u16 shape count.

Shape-entry fields:

- +0x10: shape. +0x18: local transform.
- +0x28 and +0x30: q masks. +0x38 and +0x3c: d masks.
- +0x44: flags. "Solid" means bits 2 and 3 are both set: `((f>>1)&f)&4`.

Shape field: +0x20 points to a block whose +0x48 holds a 16-byte mask pair.

```text
A, B = pair.first, pair.second
nA, nB = A.wc0, B.wc0                         # captured once
gA, gB = A.kind30.q20, B.kind30.q20           # captured once
MA, MB = copy of A/B transforms at +0x40      # captured once
active(X) = (X.kind30.w50 & 0x8000) ? (X.kind30.b53 & 0xf) != 2
                                    : X.kind30.d1c == owner.provider.d180
rec = owner.provider.q38[index].value10
rec.b5c = 1
if not active(A) and not active(B):
    if rec.state58 == 1: rec.state58 = 2
    return                                    # no empty check on this path
for i in 0..nA-1:
    eA = A.qb8 + 0x48*i
    if eA.shape10 == 0: continue              # entries for row i untouched
    WA = compose(eA.local18, MA)              # 18c16e0 + inline translation
    if not solid(eA.b44):
        for j in 0..nB-1: swap_remove(rec, (i,j)) if present
        continue
    maskA = eA.shape10.q20 + 0x48
    for j in 0..nB-1:
        eB = B.qb8 + 0x48*j
        k = find(rec, (i,j))                  # linear, first match, u16 count
        if eB.shape10 == 0: continue          # stale entry kept
        maskB = eB.shape10.q20 + 0x48
        hit = false
        if solid(eB.b44) and groups_ok and (maskA.hi & maskB.lo | maskB.hi & maskA.lo):
            WB = compose(eB.local18, MB)
            tester = provider.q68->vt[1] (shapeA, shapeB)
            hit = tester->vt[1] ({WA, WB, shapeA, shapeB}) & 0xff
        if hit:
            if k == -1: append(rec, i, j)     # 18dccb0, reserve 18df1e0 tag 0x2a, 2*cap or 8
            rec.state58 = 2
        elif k != -1: swap_remove(rec, k)     # count -= 1; e[k] = e[count]
if rec.count50 == 0: rec.state58 = 4
groups_ok:
    q = (eB.q30 & eA.q28) | (eA.q30 & eB.q28)
    d = (eB.d38 & eA.d3c) | (eB.d3c & eA.d38)
    gA != gB         -> q != 0
    A.kind30.b52&0x10 -> d != 0               # first body's kind only
    otherwise        -> q != 0 and d != 0
```

compose: `basis[i][j] = ((L[i].x*P[0][j] + L[i].y*P[1][j]) + L[i].z*P[2][j])`. The
translation is the same dot product of the local translation, plus `P.t[j]` added last.
Every operation is float32. This matches the 18c16e0 description earlier in this file.

Quirks preserved:

- A null second shape keeps any existing (i,j) entry. A non-solid second shape, a
  rejected mask or a tester miss removes it.
- A null first shape skips row i entirely. A non-solid first shape removes row i for
  j < nB without calling any tester.
- WA is composed before the solidity check, so it is wasted on non-solid rows. This is
  invisible because the result stays on the stack.
- Only the first body's kind+0x52 bit 0x10 selects the d-mask-only same-group test.
- The dormant path promotes state 1 to 2 and never sets state 4. The active path sets
  state 2 on any hit, including a hit on an existing entry, and sets 4 only when the
  list ends empty.
- The search compares the count as a u16. Swap-remove leaves stale bytes past the count.
- The tester's query block leaves the fourth lane of each row unwritten.

Validation: `native/snow_host/pose_flagged_neighbor_update_validation.json`. The harness
runs 512 cases entering at `18e0a60`, with the router, 18dfa10, 18c16e0, 18dccb0 and
18df1e0 all native.

- Routing: 467 found and 45 not found (the not-found pairs go to the supplied 18e01e0).
- Dormant: 117 pairs, 38 of them promoted from state 1.
- Shape skips and removals: 102 null first shapes, 293 non-solid first shapes, 143 null
  second shapes kept, 506 non-solid second shapes.
- Mask rejects: 352 by group masks, 164 by shape masks. 197 same-group d-only evaluations.
- Tester: 287 calls and 140 hits.
- Entry list: 134 appends, 100 removals, 23 vector allocations, 33 growths.
- Final states: 92 records emptied to state 4, 102 records ending in state 2.
- Leaves: 256 direct cases for 18dccb0 and 18df1e0 (79 append growths, 14 releases,
  28 count clamps).

The harness compares the ordered service calls and all fixture bytes, including stale
entry slots and new allocations. The 24 world-transform floats that reach the tester are
compared bit-exactly. Inputs include signed zeros and subnormals.

Four injected bugs each made the harness fail:

- Removing the entry when the second shape is null: case 10.
- Ignoring the 0x10 branch: case 31.
- Adding the translation before the z term: case 14.
- Treating either-inactive as dormant: case 10.

Limits:

- The tester factory and the tester are random stand-ins.
- Services do not mutate memory, so the reread order around tester calls is not checked.
- Trees are unbalanced BSTs.
- No NaN or overflow-to-infinity inputs are used, because the default-NaN sign may differ
  between the host and x86.
- No live run.

Static leads, not implemented:

- The tester factory at provider+0x68 may be the dispatch object that LINK_SOLVER.md
  places at owner+0x68 near `0x1927590` (vtable `0x29ca780`). That identity is not
  verified. Its vtable slot 1 picks a narrow-phase tester by shape pair.
- The sibling `18e01e0` (key not found) belongs to another lane.

### Flagged neighbor create

The flagged route `18e0a60` tail-calls `18e01e0(owner, pair)` when the pair key is not in
the provider+0x38 neighbor tree. It is reconstructed by
`engine/pose_flagged_neighbor_create.py`. The routine tests every enabled shape pair of
the two bodies and collects the overlapping ones in one neighbor record, which it creates
lazily.

Body fields: +0x30 kind (+0x20 group word, +0x52 flags), +0x40..+0x7c a 3x4 frame (basis
rows at +0x40/+0x50/+0x60, translation at +0x70), +0xb8 shape array, +0xc0 u16 shape
count. Shape entries are 72 bytes: +0x10 shape, +0x18 local frame, +0x28/+0x30 qword
masks, +0x38/+0x3c dword masks, +0x44 flags. Shape+0x20 is a filter record with qword
masks at +0x48/+0x50.

```text
A, B = pair.first, pair.second
countA = A.c0; groupA = A.kind30.q20; groupB = B.kind30.q20   # cached
frameA, frameB = A.frame40, B.frame40; countB = B.c0           # cached (stack copies)
record = 0
if countA == 0: return
for i in 0..countA-1 (u16):
    ea = A.shapes_b8 + 72*i                     # array reread per i
    if !ea.shape10 or ((ea.f44 >> 1) & ea.f44 & 4) == 0: continue    # bits 2 and 3
    worldA = compose(frameA, ea.local18)        # 18c16e0 basis + inline translation
    fa = ea.shape10.filter20                    # cached for the inner loop
    for j in 0..countB-1 (u16):
        eb = B.shapes_b8 + 72*j                 # array reread per j
        if !eb.shape10 or bits 2/3 of eb.f44 not both set: continue
        wide   = (eb.q30 & ea.q28) | (ea.q30 & eb.q28)
        narrow = (eb.d38 & ea.d3c) | (eb.d3c & ea.d38)
        if groupA != groupB:        ok = wide
        elif A.kind30.b52 & 0x10:   ok = narrow        # kind reread per pair
        else:                       ok = wide and narrow
        if !ok: continue
        if ((fa.q50 & fb.q48) | (fb.q50 & fa.q48)) == 0: continue
        worldB = compose(frameB, eb.local18)
        obj = owner.provider.q68                       # reread per pair
        collider = obj.vtable[1] (obj, ea.shape10, eb.shape10)
        query = {worldA basis/translation, worldB basis/translation, shapeA, shapeB}   # 0x90 bytes, 4th lanes unwritten
        if !collider.vtable[1] (collider, &query): continue
        if !record:
            record = 18de2e0(owner+0x28)               # pop owner+0x48 or allocate 0x60 (align 0x10, tag 0x29)
            195c3e0(record, pair)                      # record+8/+0x10/+0x18 = pair triple (reread)
            record.b5c = 1; record.d58 = 1
        18dccb0(record, i, j)                          # u32 (i | j<<16) onto record+0x48; 18df1e0 growth (4-byte, tag 0x2a)
if record: push(owner+0x18, record)                    # 18df150 growth (2*cap or 8, tag 0x27)
```

`18de2e0` pops from the owner+0x48 free list without a destructor or reinitialization.
On an empty list it allocates 0x60 bytes and constructs in place: +8/+0x10/+0x18 = 0,
vtable `0x1429c9fd0`, +0x20..+0x38 = 0, +0x40 = prior value of the global serial
`[0x14333683c]` (shared with links), vtable `0x1429ca778`, +0x48 and +0x50 qwords = 0,
+0x58 = -1, byte +0x5c = 0. `18c16e0` uses the float32 order of the transform helper
section: `basis[i][j] = ((L[i].x*P[0][j] + L[i].y*P[1][j]) + L[i].z*P[2][j])`. The
translation is computed inline in the same order and then adds `p[j]`.

Behavior worth preserving:

- A recycled record keeps its serial and its old +0x48 shape-pair storage and capacity.
  `195c360` cleared only the count and the endpoints at retire.
- The record is created on the first accepted shape pair and pushed to owner+0x18 once.
  If nothing overlaps, there is no record and no push. The state is set to 1 (retire
  takes state 4).
- The group words, shape counts and body frames are cached at entry. The shape arrays,
  entry masks and flags, A's kind+0x52, the provider dispatcher and the pair triple
  are reread.
- Cross-group pairs ignore the dword masks. Same-group pairs whose A kind has bit 0x10
  ignore the qword masks. Only A's kind is consulted for bit 0x10.
- A null allocation makes the following copy fault natively.
- The signature is two arguments. 18e01e0 never reads r8 before it writes it; the first use
  is `mov r8d, edx` at 0x1418e0369. On the router's miss path, r8d is -1 (the search ran
  off the tree). Only the found path hands a live index to 18dfa10.
- The fourth lanes of the 0x90-byte query frame are uninitialized stack bytes.

Validation: `native/snow_host/pose_flagged_neighbor_create_validation.json` covers 512
cases plus 256 leaf cases. Of the 512, 256 enter at 18e01e0 and 256 enter through router
18e0a60, of which 77 took the found branch to supplied 18dfa10. The 18dfa10 hook logs its r8d node index, so the router hand-off is compared too. Direct cases enter with a random r8. The following run
natively: 18e01e0, 18e0a60, 18c16e0, 18de2e0, 195c3e0, 18dccb0, 18df150, 18df1e0 and the
lock xadd on the global serial. Supplied: the two virtual calls, 18dfa10 and the
allocator vtable.

Totals: 960 overlap tests, 564 shape pairs pushed, 243 records (85 recycled, 158
allocated), 226 shape-pair vector growths, 149 owner+0x18 growths, 19 zero-count-A
cases, 289 same-group cases, 20 serial wraps. In 128 mutation trials, services swap
shape arrays, toggle kind+0x52 bit 0x10, rewrite group words, frames, the dispatcher,
the pair key, and entry flags and masks. Leaf paths: 29 pop, 35 allocate, 64 pushes (31
grew), 64 reserves for each tag (11 releases, 28 clamps).

Compared: ordered service calls with every argument, all 24 float32 lanes of the query
bit for bit, every fixture byte including allocations, the serial, and leaf return
values. The harness was shown to fail three times. Reading B's shape array once per
outer step fails at case 131. Omitting the +0x5c store fails at case 0. Caching A
kind+0x52 at entry fails at case 187.

Three public composition tests bind `create_pose_flagged_neighbor` into
`run_pose_pair_worker` through `route_pose_flagged_pair`. In the first, the worker builds
a record with all four shape pairs, and a key present in the tree goes to update
instead. In the second, laneB's `route_pose_flagged_pair_indexed` sends a miss to create.
In the third, `retire_pose_neighbor_records` queues a state-4 record on
owner+0x48. The worker's flagged route then pops it with its serial (555) and old
storage intact, recopies the pair, sets state 1 and pushes it to owner+0x18. No 0x29
allocation happens.

Limits: collider selection and overlap results are authored stand-ins. Frames are finite
synthetic float32 values, so NaN payloads and overflow were not exercised. A null
allocation is not exercised; Python raises MemoryError. There is no live validation.

Static leads, not implemented:

- The provider+0x68 object's vtable slot 1 selects a pair collider from two shapes. The
  collider's slot 1 is the overlap predicate over the two world frames. Neither the
  classes nor their implementations are identified.
- `18df630` (merge owner+0x18 into provider+0x58 and insert keys into provider+0x38)
  consumes these records. It is not reconstructed.
- The u32 entries `(i | j<<16)` at record+0x48 are the shape-index pairs that
  `195c400` (the routine after 195c3e0) appears to search and remove by u16 value. It is
  unread beyond its first instructions.

### Pair contact generation

`18dd400(owner, first, second, link, same)` is the dynamic pair handler's contact
stage. It is reconstructed by `engine/pose_pair_contact_generation.py`
(`generate_pose_pair_contacts`). The module also restates its leaf helpers over flat
memory:

- lookup `1958d60` -> `1958a40`
- insert `1958b70` -> append `19586b0` -> entry reserve `1958a90`
- removal `1959000`
- pair clear `19904e0`, using `1958fa0` and reset `1986020`
- payload pool pop `18ddee0` and return `18de390`, both growing through `18def10`

The entries, link and owner keep the layouts given in "Pair link worker". The payload
free list is the owner+0x28 descriptor's vector at owner+0x38 (pointer), +0x40
(count), +0x44 (capacity).

```text
na, nb = first.wc0, second.wc0;  multi = na > 1 or nb > 1
for i in 0..na-1:
    ea = first.entries_b8 + 0x48*i                  # entries pointer reread per i only
    if !ea.shape10 or !(ea.b44 bits 2 and 3): continue        # no clear
    geom.tail = (1, first.baa&0x40 || second.baa&0x40, 1)
    geom.frameA = compose(first.rows40, ea.local18)  # XYZ mask 0x3336890, float32
    kindA = shapeA.w28 & 0x7fff;  masksA = shapeA.q20 + 0x48
    if multi:
        boxA = shapeA.vt[0x10] (frameA)
        kb = second.kind30 bounds (+4 min xyz, +0x10 max xyz)
        if !(boxA.max >= kb.min, ordered) or boxA.min > kb.max (ordered):
            for j in 0..nb-1: clear(link, i, j, owner+0x28); continue
    for j in 0..nb-1:
        eb = second.entries_b8 + 0x48*j
        if !eb.shape10 or !(eb.b44 bits 2 and 3): continue    # no clear
        wide   = (eb.q30 & ea.q28) | (ea.q30 & eb.q28)
        narrow = (eb.d38 & ea.d3c) | (eb.d3c & ea.d38)
        hit = !same ? wide : first.kind30.b52 & 0x10 ? narrow : (wide && narrow)
        if !hit or !((shapeB.q20.q50 & masksA.q0) | (masksA.q8 & shapeB.q20.q48)):
            clear(link, i, j, owner+0x28); continue
        if kindA in (6,7) and kindB in (6,7): continue        # no clear, no call
        geom.frameB = compose(second.rows40, eb.local18)
        if nb > 1:
            boxB = shapeB.vt[0x10] (frameB)
            if !(boxA.max >= boxB.min and boxB.max >= boxA.min, all ordered): clear; continue
        pair = (first, second, u16 i, u16 j)
        if kindA in (6,7) or kindB in (6,7):
            (kindA == 6 or kindB == 6 ? 18e0980 : 18e08a0)(owner, geom, pair, link); continue
        p = lookup(link, i, j, 0)                                         # 1958d60
        h = provider.dispatcher68.vt[8] (shapeA, shapeB)
        n = h.vt[0x18] (geom, owner.scratch58, 500)
        if n:
            if !p: p = pool_pop(owner+0x28); insert(link, i, j, 0, p)      # 18ddee0, 1958b70
            update(p, pair, owner.scratch58, n)                           # 198fdc0
        elif p: p.count110 = 0                                            # 1986020
        if p:
            if p.count110 == 0: remove(link, i, j, 0); pool_push(owner+0x28, p)   # 1959000, 18de390
            else: p.b114 bit0 = ea.b44 bits 2&4 and eb.b44 bits 2&4   # entries reread from bodies
```

`compose` computes rows 0..2 as `(A0*Lk.x + A1*Lk.y) + A2*Lk.z`. Row 3 is
`((A0*L3.x + A3) + A1*L3.y) + A2*L3.z`. Every product and sum rounds to float32, and
the w lanes are signed zeros. `geom` is the 0x93-byte stack block that the handler and
the terrain wrappers receive: frameA, frameB, shapeA, shapeB and three flag bytes.

Leaves:

- `19904e0` repeatedly removes the last entry whose u16 fields equal the u32 arguments
  (detail is ignored). It zeroes the payload's +0x110 and pushes it with the 18def10
  growth rule. It stops at the first null payload removed. This matches
  `pose_contact_cache.clear_contact_pair`.
- `18ddee0` pops. When the pool is empty it reserves max(count+10, 2*cap), adds 10 to
  the count, refills 10 through `18de060` (supplied), then pops.
- `18de390` resets the payload, then pushes it (capacity 8, or doubled).
- `1958b70` stores the link into payload+0, then appends the key. When the vector is
  full, `1958a90` doubles its capacity. Leaving the inline one-entry storage at link+0x68
  allocates (tag 0x2d) and copies. Capacity at or below 1 copies one entry back, releases
  the heap buffer and returns to inline storage.

Behavior worth preserving:

- Inactive entries and null shapes are skipped without clearing their pairs. A failed
  mask or bounds gate does clear the pair, moving every keyed payload to the pool.
- The first-entry bounds test uses the second body's kind-record box, not a second
  entry. A failure clears the whole row j = 0..nb-1, even for inactive second entries.
- Bounds are queried only when either body has more than one entry. The second entry's
  box is queried only when the second body has more than one entry.
- NaN handling: an unordered `max >= min` rejects, but an unordered `min > max` passes.
- Two terrain kinds (6/7 after masking 0x7fff) skip the pair silently. With one terrain
  kind, the 16-bit wrapper `18e0980` is used when either kind is 6, otherwise `18e08a0`.
  Terrain paths never touch the payload cache here.
- The lookup is done before handler selection and production. A zero count resets an
  existing payload, which is then removed and released.
- After an update, the removal of a zero-count payload is decided by the payload's
  +0x110. The supplied updater writes that field.
- Payload bit0 needs bits 2 and 4 of both entries' +0x44 flags. Bits 2 and 3 gate
  activity.

Validation: `native/snow_host/pose_pair_contact_generation_validation.json` covers 512
randomized Unicorn cases. Bounds, handler lookup, production, update `198fdc0`, the two
terrain wrappers, the payload refill `18de060` and the allocator are supplied. These
run natively: 18dd400, 1958d60/1958a40, 1958b70/19586b0/1958a90 with memcpy 1c6afb0,
1959000, 19904e0/1958fa0, 1986020, 18ddee0, 18de390 and 18def10. The runtime XYZ mask
0x3336890 (zero in the memory image) is initialized to {-1,-1,-1,0}.

Totals: 912 first and 842 second entries; 200 productions (63 zero), 137 updates, 120
pool acquisitions, 46 refills, 58 releases, 74 narrow and 99 wide terrain calls, and
365 clear calls (50 payloads cleared, 8 null-payload stops). Growth: 64 pool-vector
growths and 34 entry-vector growths, 12 of them inline-to-heap. Lookups hit 25 times.

Compared: the ordered service calls with every argument (composed frames, 0x93-byte
descriptors, 0x14-byte pair descriptors, payload snapshots at update), and every fixture
byte, including allocations and refilled payloads. The harness was shown to fail three
ways:

- Clearing on the both-terrain skip fails at case 69.
- Adding the translation row last fails at case 1.
- Using bits 2 and 3 for payload bit0 fails at case 22.

Limits: frames are finite values within ±3, so NaN/inf frame propagation is not
exercised. The fixtures are synthetic and the runs are single-threaded.

Public tests: `tests/test_pose_pair_contact_generation.py` (18 tests). They cover the
gates, routing, NaN bounds, pool and entry growth, and the float32 order. They check
flat remove/clear against `pose_link_record.remove_link_key` and
`pose_contact_cache.clear_contact_pair`. A composition test binds the routine as
`generate_contacts` in `process_pose_dynamic_pair`.

Static leads:

- The handler vtable+0x18 bodies (e.g. 19dde20 / 198a780 for terrain-box) feed the
  same 48-byte record buffer as owner+0x58.
- `198fdc0` has a dict-model reconstruction (`pose_link_update`) but not a flat-memory
  binding.
- `18de060` (payload batch refill) and the shape-bounds vtables are unreconstructed.

### Pair link worker callees: contact flag, held release and pool refill

Three small callees of the pair link worker, reconstructed as separate modules. Each one is an
injected unit in `engine/pose_pair_link_worker.py`, which still takes them as services. The
worker is unchanged.

Contact-flag refresh, `refresh_contact_flag(link)` at 0x18dde70 (`engine/pose_link_contact_flag.py`):

```text
container = link + 0x48
n = contact_count(container)              # accessor 0x14144b420: u32 at container+0x18
found = False
for i in 0 .. n-1:                        # stops at the first flagged payload
    payload = contact_payload(container, i)   # accessor 0x141958840: qword at [container+0x10] + 16*i + 8
    if payload.+0x114 & 1: found = True; break
if found: link.+0x84 |= 1
else:     link.+0x84 &= ~1                # other bits of +0x84 untouched
```

Held-token release, `release_held(link)` at 0x18de3e0 (`engine/pose_link_held_release.py`):

```text
token = link.+0x78                        # read before any service call
enter_guard(guard)                        # protected thunk 0x143d0ad5d; guard = global 0x143336ab0
if token == 0: fault                      # native store to token+0 faults
token.+0 = pool.+0x30                     # pool = pointer at global 0x143336aa8, read after enter
pool.+0x28 -= 1                           # 32-bit, wraps at 0
pool.+0x30 = token                        # LIFO free-list push
leave_guard(guard, pool)                  # protected thunk 0x143d1de3a, rdx = pool
link.+0x78 = 0
```

Pool refill, `refill(elements, count)` at 0x18de1e0 (`engine/pose_link_pool_refill.py`), the
empty-vector branch of recycled-link acquire:

```text
prepare(guard, count)                     # protected thunk 0x143f3608c; guard = global 0x143336ac0
for i in 0 .. count-1:
    obj = take(pool)                      # 0x1418b5d10; pool = global 0x143336ab8
    if obj:
        construct(obj, next_serial())     # same field writes as the worker's in-place constructor
    elements[i] = obj or 0
leave_guard(guard)                        # epilogue 0x143f76da2, reached on both count-0 and loop-exit paths
```

Preserved quirks:

- The guard global 0x143336ab0 is the same one held release enters and leaves. Refill prepares and
  leaves guard 0x143336ac0, which is a different global.
- Held release faults on a zero token only after `enter`, and the pool and link are unchanged. The
  dynamic handler's `link.held78` check is the only guard against it.
- Refill constructs all `count` objects, not only the last one. Acquire then pops the last pointer
  without a destructor or reinitialization. The earlier LINK_SOLVER phrase "returned unconstructed"
  describes that pop, not the refill. It should read "returned without destructor and reinit."
- A contact entry is 16 bytes: key at +0, payload at +8. The count and base of the span are
  container+0x18 and container+0x10, which are link+0x60 and link+0x58.
- The return site of the prepare thunk, 0x18de1fb, holds one junk byte 0x62 before `test edi,edi`.
  The thunk resumes after it, so the native body is not directly executable from its start.

Validation. `native/snow_host/pose_link_contact_flag_validation.json` (512 cases): 279 set, 213 cleared,
138 already set, 61 empty spans, 1,066 payload reads, 214 early exits, 20 null-payload faults (the
scan reached a zero pointer), and 7 trials where a null entry was skipped after an earlier flagged
payload. `native/snow_host/pose_link_held_release_validation.json` (512 cases): 448 releases, 64
null-token faults, 84 count wraps, 143 null heads, 305 linked heads. `native/snow_host/pose_link_pool_refill_validation.json`
(512 cases): 1,287 constructed objects, 571 null takes, 48 zero counts, 1,858 slots checked, 1,287
serial draws. Each native run compares service call order and arguments, final bytes, and the
serial or pool globals. Contact flag also compares rbx, rbp and rsi. Unit tests:
`tests/test_pose_link_contact_flag.py` (7), `tests/test_pose_link_held_release.py` (4),
`tests/test_pose_link_pool_refill.py` (5, including composition with `acquire_pose_link`).
Fault injection, each followed by restore and a regenerated receipt: refill flag write dropped
(fails at trial 0), held release count direction flipped (fails at trial 1), contact-flag clear path
made a no-op (fails at trial 0). The full pose suite passes: 907 tests.

Supplied, not reconstructed: the protected guard thunks 0x143d0ad5d and 0x143d1de3a, the protected
prepare thunk 0x143f3608c, the epilogue thunk 0x143f76da2 (modeled as pop rsi plus ret), the pool take
0x1418b5d10 including its slow path at 0x18b5d35, and the contact count and element accessors. The
serial lock xadd on 0x14333683c is native code, mirrored by a Python counter.

Static leads, not implemented:

- The pool take slow path 0x18b5d35 (empty free list) is the main unreconstructed pool
  behavior, and it determines whether a null take is possible in practice.
- The guard thunks (0x143d0ad5d, 0x143d1de3a, 0x143f76da2, 0x143f3608c) are obfuscated. The
  lock they implement is unknown, so the enter and leave pairing is evidence of ordering only.
- LINK_SOLVER's state-reset section lists the pool-return free lists of 0x1958720 and 0x1958ba0 at
  globals 0x143336bb0/0x143336bb8 and 0x143336aa8/0x143336ab0. The held pool here is 0x143336aa8 and
  the guard is 0x143336ab0, so the two paths may share one pool. Confirm before merging.

### Live invocation capture

The two snapshot checks evaluated captured state offline. This check records
real in-game calls of `18b8860` instead. The receipt is
`native/snow_host/pose_connectivity_live_invocation_validation.json`.

**Capture point.** `18b8860` has exactly two static call sites, `18b8757` and
`18b8776`. Both are inside controller listener `18b8670`, in event 0. Nothing
calls `18b8670` directly, and no image pointer to it is stored. It is reached
only through a row of the global body-listener registry (descriptor pointer at
image `0x33367c0`), which broadcaster `18a7f60` calls as
`row.callback(body, event)`.

A private plugin swapped that one row's callback to a detour, using an aligned
8-byte compare-exchange on heap data. No code bytes or page protections were
changed. The detour always forwards to `18b8670`. Before installing, the plugin
checked:

- the image base;
- fingerprints of `18b8670`, `18b8860` and `18a7f60`;
- that both call sites decode as `call rel32` to `18b8860`;
- that exactly one enabled registry row holds `18b8670`.

On restore, the plugin scanned the current registry for rows holding the detour,
compared and swapped them back, waited for in-flight calls to drain, and kept
the module pinned.

The detour classifies each event-0 call by the listener's own gate:

- **Path A:** priority bit 15 clear and metadata+0x1c != controller+0x4c. The
  listener stamps the metadata and calls `18b8860`.
- **Path B:** priority bit 15 set and quiet nibble 2. The listener calls
  `18b8380`, then `18b8860`.
- **Neither:** any other event-0 call.

For path A calls, the plugin copies the walked refresh regions just before
the listener runs and again just after it returns, using self
`ReadProcessMemory`. The regions are: body, metadata, owner, controller,
context, provider with its node array, slot owners and their +0x28 vectors,
+0x80 ring links, endpoint bodies with their metadata and rings, tree values,
contact spans, and groups with their slot arrays and members. Session 1
captured the first 32 path A calls. Sessions 2 and 3 captured only calls whose
+0x80 head was nonempty, at most 4 per body.

Offline, the expected post-state is the pre-state plus the listener stamp,
with `analyze.run_python` (same stubs) applied. That is compared with the
post-state the game produced at every captured address. Differences are
attributed to the services that really ran in game (`18e2de0`, allocator,
pool return, listener enter/leave). Any other difference is unattributed and
fails the pair. Native `18b8860` also runs in Unicorn on the stamped pre-state
as a coverage cross-check.

**Results.** Three sessions used director startup and forward holds (scan 17,
1500 ms). The plugin armed when a player body first had a controller and a
+0x80 head. Install windows were 150, 150 and 300 s. In every session the row
was restored (no conflicts, the detour absent afterwards, one `18b8670` row) and
in-flight calls drained. Cleanup was fully verified.

While installed, the listener received 149,689 calls, 90,549 of them event 0.
Of those:

- **Path A:** 10,552 calls.
- **Path B:** 0 calls.
- **Neither:** 55,535 calls.
- **No controller:** 24,462 event-0 calls had a null or unreadable controller
  chain.

Every path A call whose ring state was recorded had an empty +0x80 ring: the 32
captured, plus 6,775 and 3,694 counted in sessions 2 and 3. The other 51
session-1 calls were not split. Session 3 counted 3,694 path A calls on 1,276
distinct bodies, all with class table `0x29c98c8` and none of them player
bodies.

Session 3 also counted event-0 calls on bodies with a nonempty ring: 19,078,
all with priority bit 15 set and quiet nibble 0, so the listener calls neither
`18b8380` nor `18b8860`. Of these, 18,516 were on the player's main and rider
bodies, which carry priority `0x8002`.

The 32 captured invocations, all on world bodies, each matched the Python
chain:

- **Path taken:** empty-ring early return, with no rows, selection or service
  calls.
- **Bytes:** 405,296 bytes compared. Of these, 64 changed in game: exactly the
  four stamp bytes per call, all predicted.
- **Differences:** 0 unattributed differing bytes. Nothing else in the captured
  regions changed, including the controller enter/leave bytes and any effects
  of `controller28` virtual+a8.
- **Cross-check:** Unicorn agreed with Python in 32 of 32 runs, with 0
  coverage gaps.

Pre and post reads ran on the same thread around each call. Sampled walks took
0.05–0.9 ms.

**Interpretation.** The empty-ring early return is now confirmed on real
invocations. The selection, rebuild and retire paths were not reached by any
observed in-game call. The bodies that carry selector-1 links (player and
ragdoll/world bodies) receive event 0 only with priority set and quiet 0. Session 2's
window included two crash detaches and one respawn. Those paths
therefore remain validated only on synthetic data and live snapshots.

Limits:

- **Atomicity:** pre and post reads are sequential self-reads, not atomic.
- **Bracket:** the capture brackets the whole listener call, not `18b8860`
  alone.
- **Untested branch:** path B never occurred, so it was never tested.
- **Removal hazard:** native removal `18bb610` does not guard a failed search.
  Short install windows bound this hazard but do not exclude it.

**Leads.** Nonempty-ring refreshes probably come from somewhere other than this
listener branch. Candidates are a quiet-2 wake (path B), or link creation
paths that call the selection, rebuild and retire services directly. Next
steps:

- Find other callers of `18dedf0`, `18e28d0` and `18de440`.
- Capture around priority-set bodies whose quiet nibble becomes 2.

### Broadphase pair lists

The object at controller+0x28 is the "Dynamic tree multi-threaded broad phase"
instance (string at image 0x29c9ce0), built by `193f450` (vtable `0x29ca8a0`,
allocation size 0xb10, base constructor `199a760`).

**Why this vtable is the installed one.** The controller constructor `18b8150`
stores its second argument at controller+0x28 (`18b8172`). It has two callers,
the factories `18ae130` and `18b64f4`. Both allocate 0xb10 bytes and construct
the object with `193f450` before passing it in. `193f450` has exactly these two
callers, so there is no sibling or derived broadphase class. Slots 0x40, 0x48,
0x60 and 0x68 of `0x29ca8a0` hold the four getters below (checked in the
harness).

**Accessors (all leaf, no side effects).**

    slot 0x40  1940410  count = u32 [ [obj+0xf8] + 8 ]
    slot 0x48  1940400  data  = ptr  [ [obj+0xf8] + 0 ]
    slot 0x60  19403f0  count = u32 [obj+0x120]
    slot 0x68  19403e0  data  = ptr [obj+0x118]

Siblings not used by the controller: slot 0x50 (`140e5df50`) returns u32
[obj+0x110] and slot 0x58 (`1419403d0`) returns ptr [obj+0x108], a third list
with the same inline layout (capacity u32 at +0x114).

**Storage.** `[obj+0xf8]` points at one of two vector headers `{data, count u32,
cap u32}` stored at obj+0xd8 and obj+0xe8 (base constructor `199a760`, stores
at `199a930` and `199a93e`). The per-step routine `199c880` swaps `[obj+0xf8]`
and `[obj+0x100]` (and copies the result to +0xd0), so the "current" header
alternates between steps. The append helper `199b590` pushes onto the current
header's vector, growing through `1940990`. The list at +0x118 is not a header:
data at +0x118, count at +0x120, capacity at +0x124 (initial capacity 0x20
rows, allocation 0x300 bytes).

**Pair row, 24 bytes (0x18).** Evidence from consumers and the append helper:

    +0x00  first body pointer   (consumers read body+0x30 -> shared state)
    +0x08  second body pointer
    +0x10  64-bit pair key      (0x18dedf0 reads it; 0x18ddd30 passes rows on)

`18ddd30` indexes rows as index*3*8 and reads +0/+8; `18dedf0` steps by 0x18 and
reads +0 and +0x10; `199b590` writes 16 bytes then 8 bytes per row.

**Controller use (`18b8fa0`, for orientation only).** Slots 0x60/0x68 (list at
+0x118) feed `18dedf0(provider, rows, count, buffer)` and then `18e28d0`. Slots
0x40/0x48 (current header) feed pair-link jobs `18ddc40(provider, rows, count,
buffer)`. The role names "removed" and "added" are inferred from that order
and from `18dedf0` locating existing links by key; they are not proven by a
producer trace. Live correction (see "Live pair update capture"): the +0x40/+0x48
list is every currently overlapping pair, not only new pairs; most of its keys
already have links.

Validation. `engine/pose_broadphase_pair_lists.py` has the four accessors plus
an authored row decoder. `check_pose_broadphase_pair_lists.py` ran 512
randomized cases in Unicorn over the memory image (2048 native getter runs).
Each compares rax to the Python accessor and requires object, header, row and
removed-array bytes to be unchanged, with return address and stack pointer
checked. Half the cases use an inline header (obj+0xd8/+0xe8), half a heap
header. 325 cases have added rows and 334 removed rows; 8 use a count with the
high bit set. The vtable slots were statically compared to the getter
addresses. Injecting the wrong count offset (+0x124 for +0x120) failed the
harness on case 0; restored and regenerated. Pose tests green (910).
Receipt: `native/snow_host/pose_broadphase_pair_lists_validation.json`.

Limits: only leaf getters run natively. The producers that fill the lists
(`199b590` callers, the broadphase update virtuals 0xc8/0xd0/0xa0) are not
reconstructed, and the row field meaning is from consumer reads.

Static leads: reconstruct slot 0x98 (`199b590`, append) and slot 0xa0
(`14199ed90`), the step `199c880`, and the dynamic-tree update behind virtuals
0xc8/0xd0; find which one writes the +0x118 list.

### Pair update step

`18b8fa0(controller)` (unwind `0x18b8fa0..0x18b90b2`) is the per-substep driver of the
select / rebuild / retire chain. The live capture showed that the body-event refresh
`18b8860` never runs with a nonempty ring, so this routine is the real driver. Module:
`engine/pose_pair_update_step.py`.

The controller is the 0x78-byte object built by `18b8150`. Its fields:

- `+0x28`: the broadphase.
- `+0x30`: the island context (the "Multi threaded island manager", 0x4a0 bytes, built by `18e0ca0`).
- `+0x38`: the provider (the "Narrow Phase", 0x190 bytes, built by `18dc300`).
- `+0x48`: the phase word. The constructor sets it to 0.
- `+0x4c`: the frame counter. The constructor sets it to 1.

The factory `18ae130` builds all four objects.

```
controller+0x48 = 1
19598b0(controller+0x28)            ; = bp->vfunc[0x90] () (update); returns 1, ignored
output = {ptr = inline[0x200], count 0, cap 0x200}   ; 0x1000-byte stack buffer
bp = controller+0x28
n = (u32) bp->vfunc[0x60] ()         ; removed-pair count, called before the array
a = bp->vfunc[0x68] ()               ; removed-pair array
18dedf0(controller+0x38, a, n, &output)    ; select (resets output count itself)
18e28d0(controller+0x30, &output)          ; rebuild
bp = controller+0x28
n = (u32) bp->vfunc[0x40] ()         ; overlapping-pair count (live-corrected)
a = bp->vfunc[0x48] ()               ; overlapping-pair array (live-corrected)
18ddc40(controller+0x38, a, n, &output)    ; pair jobs; their retire 18de440 consumes output
if output.cap != 0 and output.ptr != inline: allocator[0x1433365b8]->vfunc[0x18] (ptr)
(controller+0x28)->vfunc[0x88] ()    ; `ret 0` stub 0x75e600 in the observed class
controller+0x4c += 1
u32 (controller+0x28)+8 = controller+0x4c
18df490(controller+0x38, controller+0x4c)  ; provider u32 +0x180 = frame
controller+0x48 = 2
return 1
```

`19598b0` is `bp->vfunc[0x90] (); return 1`. `18df490` is `mov [rcx+0x180], edx; ret`. Both are reconstructed inline.

Preserved quirks:

- **One shared output vector.** The same output vector feeds select, rebuild and the
  pair jobs. The links selected from removed pairs are retired inside `18ddc40` (its
  `18de440` call), using the worker-count divisor rather than the refresh's divisor of 1.
  The vector is never cleared between stages.
- **Field reloads.** Every controller field is reloaded at each use. The broadphase
  pointer is read 5 times: the update, the removed lists, the new lists, `+0x88` and the
  `+8` store. The provider is read 3 times, and `+0x4c` is reloaded after the increment.
- **Count truncation.** Only `eax` is used from the count getters (u32).
- **Release check.** The output buffer is released only when its capacity is nonzero
  and its pointer is not the inline buffer. An external pointer with zero capacity is
  kept.
- **Return value.** The routine always returns `al = 1`. The thunk `18ae2b0` discards it.

Pair row format: both broadphase arrays hold 24-byte rows {bodyA, bodyB, u64 key}, the
same rows that the refresh `18b8860` builds. Two pieces of evidence confirm this: the
`add r14, 0x18` stride in `18dedf0`, and `index*24` in the pair worker `18ddd30`. The
broadphase lane's `engine/pose_broadphase_pair_lists.py` decodes them. The getters of the
observed class (vtable RVA `0x29ca8a0`) are:

- `+0x40`: `[[obj+0xf8]+8]`
- `+0x48`: `[[obj+0xf8]]`
- `+0x60`: `[obj+0x120]`
- `+0x68`: `[obj+0x118]`

These getters are also exposed as `pose_dynamic_tree_broadphase_vcall`. Its update
`199c880` swaps `+0xf8`/`+0x100` and stays supplied.

**Validation.** `check_pose_pair_update_step.py` ran 512 Unicorn cases of native `18b8fa0`
over the memory image (receipt `native/snow_host/pose_pair_update_step_validation.json`).
`19598b0` and `18df490` ran natively.

- **Vtable modes.** 256 cases used the real vtable `0x1429ca8a0`, so the four getters
  and the `+0x88` stub ran natively and only `199c880` was supplied. The other 256 used
  a fixture vtable that routes all six slots to supplied stubs, with garbage in the
  upper 32 bits of the counts.
- **Mutation.** 256 cases mutated controller `+0x28/+0x30/+0x38/+0x4c` and the broadphase
  lists from inside the services.
- **Comparisons.** The harness compared:
  - 3,398 service calls, with their arguments;
  - 16,452 24-byte rows;
  - the output descriptor state (count, capacity, inline or external, items) at each stage;
  - all fixture bytes.
- **Output storage.** 101 outputs grew past 0x200 entries. 70 were released and 31 were
  kept, being external with zero capacity.
- **Injected bug.** Releasing without the capacity check was caught, and the receipt was
  regenerated after the restore.

Composition test (`tests/test_pose_pair_update_step.py`): the full-chain scenario,
driven through the broadphase lane's getters, select, rebuild, the pair jobs and the retire
stage, reaches the same end state as the refresh chain: 3 tree keys removed, queue (10,
60, 30), groups GA and GB processed. It also shows the added row published at provider
`+0x170` for dispatch. Limits:

- Select, rebuild, the jobs, the broadphase update and the allocator are supplied (each
  has its own receipt).
- The select hook emulates output growth; `18df270` does not run.
- The harness is single-threaded, and this routine has no live validation.

Static leads:

- **Caller.** `18ae2b0` (`call 18b8fa0; ret`) is entered only by a tail jump from
  `0x140b1a0` (`mov rcx,[rcx+8]; jmp 18ae2b0`). That stub's only caller is `0x1389afd`,
  inside `1389a50`.
- **`1389a50`.** This is the broadphase job body. When profiling global `0x143075a88`
  equals 2, it opens a profiler scope named `"Physic::UpdateBroadphase"` (string RVA
  `0x2913250`). It then loops over substeps (count at `this+0x1390`, dt at `+0x1394`):
  `13c30c0`, then `140b1a0` (this step), then `140efa0(dt)`, `140b3d0` and `13c08f0(dt)`.
  So the pair update runs once per physics substep, with the controller at `[[this]]+8`.
- **Scheduling.** Nothing calls `1389a50` directly. Setup `136a550` stores it as a delegate
  at record `+0x2c0` (lea at `0x136aacf`), just before it names the job
  `"PhysicsWorldStep"` in batch `"Physic::PhysicsUpdate"` (`0x136ab7e`/`0x136ab8e`). That
  is probably the PhysicsWorldStep job's broadphase delegate, but the delegate-to-job
  binding has not been verified.
- **Controller factory.** `18ae130` (called from `13d1c8e`) allocates 0xb10 bytes for
  the broadphase (`193f450`, string "Dynamic tree multi-threaded broad phase"), 0x190 for
  the narrow phase, 0x4a0 for the island manager, and 0x78 for the controller (`18b8150`).
  The controller's vtable is at `0x1429ca0e0`.
- **Other callers.** The live gap is closed by capturing this routine rather than
  `18b8860`. A rel32 scan finds that `18dedf0` and `18e28d0` are called only from the
  refresh (chunk `18b88e1`) and from this step. `18de440` is called only from the
  refresh and from `18ddc40`, and `18ddc40` only from this step. So in gameplay, every
  select, rebuild and retire runs inside `18b8fa0`.

### Live pair update capture

This check records real in-game executions of the per-step pair update
`18b8fa0(controller)`, which runs the selection, rebuild and pair-job services
that the listener capture never reached. The receipt is
`native/snow_host/pose_pair_update_live_validation.json`.

**Routine.** In native order:

```
controller+0x48 = 1
19598b0(B)                         ; B = controller+0x28, calls B.vt+0x90 (update)
n = B.vt+0x60(); rows = B.vt+0x68()  ; removed rows: inline list at B+0x118, count B+0x120
18dedf0(provider38, rows, n, &vec)   ; selection into a local vector, 512 inline slots
18e28d0(context30, &vec)             ; rebuild
m = B.vt+0x40(); pairs = B.vt+0x48() ; pair rows: header at B+0xf8, {data, count}
18ddc40(provider38, pairs, m, &vec)  ; pair jobs: retire, neighbor retire, rebalance, workers, merges
free vec if external
B.vt+0x88()                          ; shared no-op 75e600
controller+0x4c += 1; B+8 = controller+0x4c
18df490(provider38, controller+0x4c)
controller+0x48 = 2; return 1
```

B is the broad-phase object, built by `193f450`. Its vtable is at image RVA
`0x29ca8a0` and has 34 slots. Only its constructor and destructor reference that
table, and no code compares an object against it. Both row lists use 24-byte
rows: body A, body B, u64 key.

**Capture point.** The path into `18b8fa0` has no stored pointer:

- `1389a50` (the world step) calls `140b1a0` directly.
- `140b1a0` loads `[rcx+8]` and jumps to `18ae2b0`.
- `18ae2b0` calls `18b8fa0`.

The hook is therefore a heap data write on B itself. A private plugin used an
aligned compare-exchange to point B's vtable at a private copy of the 34-slot
table. In the copy, slots +0x60, +0x40 and +0x88 were replaced by detours, and
each detour always forwards to the original slot. No code bytes, page
protections or shared `.rdata` table were changed.

A detour acts only when two conditions hold:

- self is the target object;
- the return address is the matching `18b8fa0` call site: `18b8ff2`, `18b902c`
  or `18b907b`.

That gives three snapshots per step, all taken on the stepping thread:

- **S0** (at +0x60): before select, rebuild and the pair jobs.
- **S1** (at +0x40): after select and rebuild, before the pair jobs. S1 also
  reads the caller's local selection vector at caller rsp+0x20. The caller
  frame is located through the detour's frame pointer, and the return address
  stored there is checked first.
- **S2** (at +0x88): after the pair jobs. This is before the counter bump, the
  B+8 write and `18df490`.

Before installing, the plugin checked:

- the image base;
- a 274-byte fingerprint of `18b8fa0` and a 64-byte fingerprint of the four
  getters;
- all 34 table slots against the image;
- the controller vtable `0x29ca0e0`, reached from the player body chain;
- that B's vtable pointer equals the image table.

On restore, the plugin re-checked controller+0x28 and the private table,
compare-exchanged the original table back and waited for in-flight detours to
drain. The module stays pinned.

Each snapshot walked these regions:

- B and its list header;
- both row arrays;
- controller, context and provider;
- both provider trees with all node values;
- provider vectors +0x28 and +0x58, and the publish rows at +0x170;
- the 32 slot owners and their vectors at +8, +0x18, +0x28 and +0x48;
- the row bodies, with their metadata and their +0x80, +0x88 and +0x90 rings;
- endpoint bodies, link contact spans, and groups with their slot arrays and
  members.

**Stage A (S0 to S1), byte level.** `select_pose_provider_links` runs on the S0
removed rows, then `rebuild_pose_body_connectivity`. Its link service is
`remove_pose_group_link` and `18e2de0` is a recording stub. The selection list
is compared with the game's vector. Predicted bytes are compared with S1 at
every S0 address.

Group and group-slot differences, and context bytes outside +0x464..+0x46b, are
attributed to `18e2de0` only when Python queued a group. Rebuild owns the
context counter, so those bytes are always compared. Any other difference
fails the step.

**Stage B (S1 to S2), structural.** These checks run:

- Publish fields: provider+0x170 and +0x178.
- Worker count: the claim cursor +0x17c minus the pair count, bounded by the
  `18ddc40` formula.
- New-link merge (`merge_pose_new_links` semantics): provider+0x28 is checked
  against the S2 worker vectors at owner+8 for count, multiset and
  `compare_pose_link_order` order. The worker vectors are the pair workers'
  supplied output.
- Each merged link's key is in the link tree, and the link is in both endpoint
  +0x80 rings.
- The fate of every selected link.
- Red-black invariants of both provider trees at S0, S1 and S2.

**Results.** Two sessions used director startup and forward holds (scan 17,
1500 ms). Session 1 captured any step with a nonempty list, spaced 400 ms
apart, in a 150 s window. Session 2 captured only steps with a removed row,
spaced 150 ms apart, in a 240 s window.

In both sessions:

- the vtable pointer was restored (the private table was gone afterwards) and
  in-flight calls drained;
- no foreign calls reached the detours;
- S1 and S2 were never missed;
- the walks had no overflow and no unreadable regions;
- cleanup was fully verified (bottle stopped, saves and settings restored,
  original DLL verified).

While installed, the hook saw 3,021 steps (7–9 per second). Every step had
a nonempty pair list, with at most 16 rows per step (3–16 in captured steps). 304 steps (10%) had removed
rows, at most 8 in one step.

All 64 captured steps (37 with removed rows) passed both stages:

- **Selection:** 43 removed rows passed the priority/quiet gate. Python
  selected 35 links, and the game's vector was identical in all 64 steps. Eight
  eligible rows had no tree node.
- **Bytes:** 1,164,424 bytes compared. 802 predicted changed bytes matched
  (link removal from groups, context clear and counter, tree removal). 28
  differing bytes were attributed to `18e2de0`, across 35 processed groups.
  There were 0 unattributed bytes.
- **Pair jobs:** one worker in all 64 steps. Publish fields were equal in all
  64.
- **Merges:** 28 links were merged. All 64 steps matched by count and multiset,
  with 0 comparator order violations. All 28 merged keys were in the tree, and
  all 56 endpoint ring memberships held.
- **Selected links:** 27 of the 35 were reused in the same step as the merged
  link object for a pair, and 8 went to the slot owner's +0x28 free list.
- **Trees:** both trees were valid red-black trees at every snapshot.

Negative controls injected one deliberate bug at a time into the Python side,
then restored it:

- Rebuild skipping the context counter: 34 steps failed, which is every step that processed a group.
- Rebuild skipping group link removal: the same 34 steps failed.
- Selection truncated to its first match on reversed rows: the one step with
  two selected links failed.
- Inverted merge comparator: 2 steps failed.

With the chain restored, all 64 steps passed.

**Interpretation.**

- Selection and rebuild are now confirmed byte for byte on real in-game
  executions.
- The pair list at B.vt+0x40/+0x48 holds every currently overlapping pair, not
  only new ones. In steady state the pair jobs write only the provider claim
  cursor and publish fields. At S1, 425 of the 517 captured pair-row keys
  already had a tree link, and 453 did at S2.
- A removed pair usually reappears in the same step's pair list. Its retired
  link goes onto the slot owner's free list and is reused for that pair through
  the recycled-link path.

Limits:

- **Atomicity:** the snapshots are sequential self-reads, not atomic.
- **Stage B is structural:** retire `18de440`, neighbor retire `18de510`,
  rebalance `1989e60`, the pair workers and the tree inserts `18de6a0` and
  `18de830` ran in game and are not reproduced byte for byte.
- **Worker count:** pair lists never exceeded 16 rows, so only one-worker
  dispatch was observed.
- **Outside S2:** `18df490` and the counter bump run after S2 and are not
  compared.
- **Coverage:** only the player's world controller was captured.

**Leads.**

- Byte-level stage B needs the tree inserts `18de6a0` and `18de830`
  reconstructed, so that S1 plus the worker vectors gives a predicted S2 tree.
- The eight eligible removed rows with no tree node are probably pairs the
  pair filter never linked. Check this against `18deb70`.
- A multi-worker dispatch needs a scene with more than 20 overlapping pairs.

### Job ring queue (0x18b7710 push, pop in 0x18b7f80, exit-record push in 0x18b797e)

`engine.pose_job_ring_queue` reconstructs the record queue that `0x18b7ca0` (see
Dispatcher claim and completion counters) fills through its enqueue service and that
ordinary workers drain. 0x18b7d03 is a chunk of the dispatcher (slot reservation, then a
call to 0x18b7710 per extra worker); 0x18b797e is a chunk of the shutdown routine
0x18b7940 with the push inlined; the pop is inlined in the worker loop 0x18b7f80.
Receipt: native/snow_host/pose_job_ring_queue_validation.json.

Layout (relative to the queue at dispatcher+0x218): 0x400 ring bytes, then u32 counters
+0x400 read claim, +0x404 read published, +0x408 write claim, +0x40c write published.
Counters run freely with wrapping 32-bit arithmetic; a record at counter c starts at
ring offset c and 0x3ff and splits across the ring end (two memcpy calls). Records are
24 bytes: tag, slot, callback, argument (the existing dispatcher enqueue tuple).

```python
push(record):                               # spins until it succeeds
    loop:
        A = read(read_published); B = read(write_claim)     # this order matters
        if (B - A) > 0x400 or (A - B + 0x400) < 24: continue   # full or inconsistent
        if cas(write_claim, B, B + 24) != B: continue
        copy record to ring[B & 0x3ff] (two pieces at the end)
        while cas(write_published, B, B + 24) != B: pass       # publish in claim order
        return
pop():                                      # one attempt, never spins on emptiness
    R = read(read_claim); W = read(write_published)
    if (W - R) > 0x400 or (W - R) < 24: return None
    if cas(read_claim, R, R + 24) != R: retry from the top
    copy ring[R & 0x3ff] out
    while cas(read_published, R, R + 24) != R: pass           # release in claim order
```

Worker loop 0x18b7f80(dispatcher, i): wait(handle[i]); pop. Empty: scan unclaimed[0..31];
the first nonzero entry calls the opaque non-returning routine 0x143e20621, otherwise wait
again. TAG_CALL 0x1de3f0c7: unclaimed[slot] -= 1, callback(token, 0), unfinished[slot] -= 1.
TAG_EXIT 0x1de3f0c9: unclaimed[slot] -= 1, unfinished[slot] -= 1, return. Any other tag only
re-reads. After a record, a nonzero unclaimed[slot] skips the next wait.

Preserved quirks: exit records carry slot 0, and the shutdown routine seeds
unclaimed[0] = unfinished[0] = workers - 1, so exit records are accounted on slot 0. Push
never reports failure (blocks on a full ring or an unpublished earlier writer); pop
reports empty on any inconsistent or short snapshot. Capacity 0x400 is not a multiple of
24, so at most 42 records fit and free space after 42 is 16.

Validation: 512 native Unicorn cases (192 push including 8 full-ring and 8 unpublished-writer
spin states and 95 with a consumer in flight, 256 worker-loop runs with 244 callbacks, 65 exit
returns, 94 opaque-routine faults and 67 unknown-tag records, 64 shutdown runs with 207 exit
records); all 0x728 dispatcher bytes, wait/callback/notify/fault service calls and counter
snapshots at every callback match. memcpy runs natively. Supplied: event wait stub
0x143f45b93 (modeled as callee cleaning the pushed queue pointer), callback, 0x143e20621,
notify stub 0x143f93753. Single-threaded: no native concurrency evidence.

Authored interleaving exploration (NOT native evidence): `engine.pose_job_ring_model_check`
explores every interleaving of the atomic-step machines under sequentially consistent
memory on a 0x40-byte ring (two records, wraps and splits). Example scenarios, all clean:
2 producers x 2 pushes + 1 consumer x 3 pops (19541 states); 2x2 pushes + 2 consumers x 2
pops across the 2^32 counter wrap (447557 states). Checked: no lost, duplicated, torn or
phantom records, counter order invariant, push counter equals pop counter for each record,
per-producer and per-consumer FIFO. Full ring: a producer finishes only when a consumer
pops; with no consumer it never finishes (no failure return). Mutants (unordered
publication, no space check) are detected. Liveness caveat: published records are visible
only as a prefix, so one stalled writer blocks every later publication and all consumers
(head-of-line blocking); this is structural, not a violation.

Static leads: the opaque routine 0x143e20621 reached from an empty pop while any
unclaimed counter is nonzero; the stub 0x143f45b93 calling convention; the remainder of
0x18b7940 after 0x18b7a6a.

### Live thread and lock observation

This is a live observation, not a reconstruction check. It records which threads run
the per-step pair update `18b8fa0` and the pair-link worker path, the job dispatcher's
capacity, and the in-memory state of the objects named by the 12 guard globals. The
receipt is `native/snow_host/physics_thread_lock_live_observation.json`.

**Capture.** A private bounded plugin installed two hooks. Both are data writes only:
no code bytes, page protections or shared `.rdata` were changed.

- **A.** The same broad-phase vtable-pointer swap as "Live pair update capture"
  (slots +0x60, +0x40 and +0x88; S0, S1 and S2 inside `18b8fa0`). Every step was
  recorded until the buffer filled, not only spaced captures.
- **B.** The pair-collider factory at provider+0x68 (provider = controller+0x38). Its
  vtable is image `0x29ca780`, with 4 slots: deleting destructor `18dc780`, selector
  `18de680`, `198f8b0` and `18e1150`. Its vtable pointer was compare-exchanged to a
  private copy in which slot +8 (`18de680`) is a forwarding detour. That detour records
  the calling thread and return site.
  - Slot +8 is a pure table lookup, `[this + 8*(kindA*8 + kindB) + 8]`, keyed by the
    two shapes' +0x28 kinds masked with 0x7fff.
  - It is reached from inside the worker path: `18dd400` (return `18dda2c`), the two
    terrain wrappers `18e0980` / `18e08a0` (returns `18e09de` / `18e08fe`), and the
    flagged-neighbor bodies (returns `18dffd4` in the `18dfa10` chunk and `18e064b` in
    the `18e01e0` chunk).

Identity checks before installing hook B:

- the factory's vtable pointer, its 4 slots and the word before them;
- a 32-byte fingerprint of `18de680`;
- the three call-site encodings.

On restore, the plugin compare-exchanged the factory first and then B, re-checking each
owner field first, and drained in-flight detours.

Lock reads used ReadProcessMemory and wrote nothing. For each guard global, the plugin
read the qword stored there and 0x40 bytes at that pointer. Reads were taken at S0, S1
and S2 of 48 steps spaced 300 ms apart, at the first worker-path factory call in those
steps, and every 5 s from the plugin thread.

A Wine fixture in the same prefix gives the reference layouts:

- **CRITICAL_SECTION, free:** DebugInfo all-ones, LockCount -1, RecursionCount 0,
  OwningThread 0.
- **CRITICAL_SECTION, held:** LockCount 0, RecursionCount 1, OwningThread = the thread
  id.
- **SRWLOCK:** 0 when free, 0x10001 exclusive, 0x10000 shared.

**Results.** Session census-01 used director startup and forward holds. The hook saw
25,382 steps in 240 s and fully recorded the first 12,000 (115 s, about 104 steps/s).
All 12,000 reached both S1 and S2.

Pair update thread:

- **`18b8fa0` does not run on a fixed thread.** It ran on 10 different threads,
  switching 4,542 times between consecutive steps. The most-used thread ran 15.8% of
  steps.
- All 10 are job-pool threads with one shared start address, game image RVA
  `0x1c94b94`. The process has 24 threads with that start address.
- It never ran on the snow host plugin thread or the plugin's own thread.

Worker path:

- 11,999 steps had factory calls.
- In every one, the calls came from exactly one thread: the thread running that step.
- The calls split by return site as follows (the first three are inside the
  steps; the last two include later steps after the buffer filled):

  | Return site | Caller | Calls |
  |---|---|---|
  | `18dda2c` | `18dd400` | 1,921 |
  | `18e09de` | `18e0980` | 26,035 |
  | `18e08fe` | `18e08a0` | 153,127 |
  | `18dffd4` | flagged-neighbor update | 45,946 |
  | `18e064b` | flagged-neighbor create | 22 |

Dispatcher:

- **The dispatcher capacity `[[0x143336610]+0x10]` was 1 in every step.** So
  `min(32, capacity, n/10+1)` was always 1, and the claim cursor confirmed
  `+0x17c - +0x178 = 1` in all 12,000 steps, with 0 mismatches.
- 2,009 steps had at least 10 new pairs, up to 83 in one step.
- **No multi-worker step occurred.** With capacity 1, `18b7ca0` takes its
  single-worker branch and calls the callback on the caller's thread. That matches the
  observed thread identity.

Lock objects:

- **11 of the 12 globals point to Wine CRITICAL_SECTION-shaped objects:** 0x143336ab0,
  ac0, aa0, bb8, 800, 7f0, 7d0, 810, 868, 878 and 888.
- The 11 pointees are distinct and lie within one 560-byte span. Each pointer was
  stable across all samples.
- The first 0x28 bytes were byte-identical in all 2,288 samples: DebugInfo all-ones,
  LockCount -1, RecursionCount 0, OwningThread 0, LockSemaphore 0, SpinCount 0. **So
  none was ever held at S0, S1, S2, in the worker path or asynchronously.** That
  includes never by the sampling thread.
- The SRW shape is rejected, because the first qword is all ones.
- **`0x14333c5e8` holds an all-ones value, not a pointer.** That fits its role as the
  magic-static guard/epoch word noted in the census.
- Live shapes for the offline thunk-emulation lane to cross-check against:
  CRITICAL_SECTION objects, uncontended at every sample point.

Cleanup in census-01 was fully verified:

- both vtable pointers were restored and drained;
- no foreign detour calls occurred;
- the bottle stopped, saves and settings were restored, and the original DLL was
  verified.

Session census-02 stalled at the title screen before arming, and cleanup was verified.
Session census-03 used steering holds and installed both hooks. The launcher watchdog
then stopped the bottle for host memory pressure (system free memory 19%; game RSS
about 1.1 GiB), so the in-memory step records were lost. Its cleanup was also verified.

Limits:

- This is Wine on macOS. Pool placement and dispatcher capacity may differ on Windows
  or with another CPU count.
- Locks were sampled at discrete points.
- Thread labels are per session.
- Step records are held in memory until restore.

Static leads:

- Where dispatcher+0x10 (capacity) is initialized, and whether it derives from the CPU
  count.
- `0x1c94b94` (the job-pool thread entry).
- The CS block around the 11 guard objects, and the code that initializes it.

Correction: thread start RVA `0x1c94b94` is the CRT `_beginthreadex` trampoline, so
every CRT-created thread shares it. "Job-pool threads" above means engine threads
that ran the physics step, not a specific pool (see PHYSICS_ATOMICS_AND_THREADS.md).

### Body velocity and pose setters (host set_velocity / set_pose entry path)

Evidence anchors: RVA `0x18aa520` (linear velocity), `0x18aa360` (angular velocity), `0x18a8c20` (pose). Module `engine/pose_body_state_setters.py`. These are the outer layers of the path set_velocity / set_pose -> setter -> `0x18b8380` (controller group-transition wrapper, `engine/pose_body_controller_transition.py`) -> `0x18e14f0` (`engine/pose_body_group_transition.py`).

Body layout used: `body+0x30` metadata, `metadata+0x20` holder, `holder+0x20` controller token (all three are plain loads, no locks); metadata `+0x53` low nibble is the body kind; `body+0x1a0..0x1a8` linear velocity; `body+0x1ac..0x1b4` angular velocity.

```text
set_linear_velocity(body, vec, force_r8b):      # 0x18aa520
    if kind(body) != 2 or force_r8b != 0:        # low byte of r8 only
        body[0x1a0..0x1ac] = vec[0..12]          # raw 3 x dword copy
    ctrl = body.meta.holder.controller
    if ctrl != 0 and force_r8b != 0:
        0x18b8380(ctrl, body)

set_angular_velocity(body, vec, force_r8b):     # 0x18aa360, identical, store at +0x1ac

set_pose(body, matrix12):                        # 0x18a8c20
    repack 12 floats into a 16-byte-stride stack buffer (padding words not written)
    body.vtable[+0xa0] (body, buffer)             # dynamic virtual, supplied
    ctrl = body.meta.holder.controller           # reloaded after the virtual
    if ctrl != 0:
        0x18b8380(ctrl, body)                    # no force flag
```

Preserved quirks: a kind-2 body with force 0 skips the store AND the notify; a kind-2 body with force nonzero stores and notifies; a non-kind-2 body with force 0 stores but never notifies (so a host velocity set with notify flag 0 mutates velocity with no group transition, and therefore no pool guard). The pose setter has no force flag: it notifies whenever the controller is non-null. Only the low byte of r8 is tested. Pose-buffer padding words are uninitialised stack. Not reconstructed: sibling entries `0x18aa580` (calls `0x18bf4f0` then notify unconditionally on non-null controller), `0x18aa3c0` (vector at `+0x128`, `0x18bf450`, then notify) and `0x18a8cf0` (notify with no null check); all use the same `0x18b8380` tail.

#### Pool guards reached beneath the setters (static, direct calls only; feeds the safe-point contract)

Gate chain, all of which must pass for any pool guard to be reachable:

1. setter gate above (`force != 0` for velocity setters; non-null controller for pose; `0x18b8380` rcx = controller, rdx = body);
2. `0x18b8380` returns early if metadata `+0x52` bit 0 is set or `body+0x10` (group) is null. Otherwise it enters the protected controller synchronization at `controller+0x50` (a protected stub call, NOT one of the 11 pool guards; supplied), then calls `0x18e14f0(controller+0x30, body)`, then dynamic virtual `+0x28` of the body (quiet-state reset), then the paired leave;
3. `0x18e14f0` does nothing but the final `0x18e11b0(context, body.group)` unless metadata `+0x52` bit 3 is set AND `predicate(0x18e1dd0)` result differs from `(group == context+0x410)`.

When the selection changes (gate 3 passes):

| Guard | Reached via | Extra conditions |
|---|---|---|
| `0x143336bb8` contact payload pool (return) | `0x18e23c0` (always called on selection change) -> `0x1957fc0` -> `0x1958030` -> `0x1958b90` -> `0x1958720` (also `0x18e23c0` -> pruning in the groups at `context+0x418/+0x428` when old group == `context+0x408`) | `0x1958720` takes the guard only for contact entries with a non-null payload in a link that has the body as an endpoint; no matching link or an empty/null contact span reaches no guard from this branch |
| `0x143336aa0` pose group storage pool | `0x18e19c0` (obtain group) | only on the third arm: body virtual `+8(1)` returns nonzero AND metadata `+0x50` bit 15 set AND NOT (`+0x52` bit 3 and predicate true). Bit 15 clear selects `context+0x408` and bit 15 set with predicate true selects `context+0x410`; neither obtains a group. Also reachable from `0x18e23c0` -> `0x18e2de0` (ordinary-group processing, when the old group is neither `context+0x408` nor `+0x410`), which calls `0x18e19c0` itself in one branch |

Not reached directly by this path (no guard-taking chunk in `0x18e14f0`, `0x18e11b0`, `0x19573c0`, `0x1957fc0`, `0x1958030`, `0x1958b90`): `0x143336ab0` (`0x1958ba0` is not a callee of `0x1958b90`, which jumps to `0x1958720` with a null second argument), and the body-record pools `0x143336800/7f0/810`. Open leads, NOT traced: callees of `0x18e11b0` (`0x18e2b80`, `0x1957340`, `0x18e2a60`, `0x18e17e0`), of `0x18e2de0` (`0x18e2660`, `0x1957720`, `0x18e1b10`, `0x18e2d00`) and of `0x19573c0`; virtual `+0x28` and `+0xa0` targets; `0x19572c0` (guard `0x143336aa0` return) has no direct callers. In particular, with no selection change (the usual steady case: body flags without bit 3, or predicate unchanged) no pool guard is reached at all; only the protected controller-sync enter/leave and `0x18e11b0` run.

Validation: 512 randomized native cases in Unicorn over the memory image (171 linear, 171 angular, 170 pose) execute the original setter entry routines with the call to `0x18b8380` and the pose virtual replaced by recording services; service calls and register arguments plus every byte of the body (0x200), metadata (0x60) and holder (0x40) fixtures and the return/stack match (287 velocity stores, 303 notifies, 55 kind-2 no-force skips, 48 cases where the virtual rewrites the controller slot to test the reload). A deliberately injected bug (notify without force) failed at case 10 and was restored. Composition unit tests chain velocity set -> controller wrapper -> body group transition using the existing modules (force 0, metadata bit 0, no-flag, bit-15-clear, special-group and obtain-group arms). Receipt: `native/snow_host/pose_body_state_setters_validation.json`. Limits: the wrapper and everything beneath it are not executed in this harness; no lock behaviour, no live validation, no claim of original-engine equivalence.

### Physics pool mutators outside the step

Static, read-only pass over the analysed image. It asks which systems reach the guard-taking physics routines that the step's own call closure does not. It makes no claim about what the protected stubs do, and it does not establish that any path runs in a given game state. Offsets are evidence anchors for this build, not portable API fields. Nothing here claims original-engine equivalence.

Method: the reverse direct-call graph (rel32 call and jump, cold chunks folded into their primary function) was walked upward from each routine to its roots. Roots were then named from two sources: an 8-byte data-pointer scan of the non-code sections, and the reflected-class vtable map (`vtable_map.json`) for slot ownership. Physics-region vtables carry no reflected names, so those were identified only by the constructors that store them. Indirect calls are not edges. "Reachable" therefore means a direct-call path exists, not that the path executes.

Classes used below: (a) runs inside the simulation half that the Step hold freezes, (b) runs on a loading, idle, async or world-construction path that the hold does not freeze, (c) unknown.

**Reference points.**

- The physics-state constructor `0x136a550` stores these job delegates: `0x1389a50` (PhysicsWorldStep, batch `Physic::PhysicsUpdate`), `0x13c8bc0` (PhysicsTerrainUpdate), `0x13c9950` (PhysicsPropsUpdate), `0x1371bd8` (AfterPhysicSimulationUpdate), `0x13c0b40` (AfterPhysicSimulationUpdateCharacterWrapup). The direct-call closure of each contains none of the routines below. That agrees with the earlier probe, which found only the pair-worker and refresh routines under the step.
- Physic::BeforeSimulation receivers run before PhysicsWorldStep inside the Step frame (701 of 701 live requests). Membership is verified for two classes: PlayerSnowboardComponent slot `0x270` (`0x564ee0`) and BipedComponent slot `0x270` (`0x13c1e80`, same table slot shared by QuadrupedComponent and PhysicsActivityZone). For other classes the slot number alone is the evidence.
- Held mode freezes Step and the world chain; BeginFrame, the graphics chain, UpdateWhileEngineIsPaused and EndFrame keep running; the loading thread, idle task workers and async services are off-graph and keep running. The closures of the frame-graph delegates `0x6a3790`, `0x6569e0`, `0x656c20` and `0x675c70` contain none of the routines below by direct calls.

**Classification.**

| Entry (guard) | Roots found | Class |
|---|---|---|
| Body record setters `0x18a98d0`, `0x18a9e90` (guard `0x1433367f0`) through `0x18aa340`, `0x18aa4f0` | `0x564ee0` > `0x5654c0` > `0x565100` > `0x556330` > `0x13806f0` > `0x13885b0` > `0x18aa340` or `0x18aa4f0`; Biped/Quadruped slot `0x270` > `0x13c9b10` > `0x1385470` > `0x1401190`; Bending, Inert and PlayerRagdoll slot `0x270` chains; component lifecycle slots; vtable slot `0x18a93e0` | a, with c secondary |
| Body record setters `0x18a9b00`, `0x18a9c30`, `0x18a9d60` (guard `0x143336800`) through `0x18aa5b0`..`0x18aa5d0`, `0x140d520`/`0x140d560`/`0x140d5a0`, `0x1383f20`, `0x13af9b0` | PlayerRagdollComponent slot `0x270` (`0x13c2d00`, inferred) and lifecycle slots; not reached from the player snowboard receiver | c, with a secondary |
| `0x1401190` body create (guards `0x143336728`, `0x1433367f0`, `0x1433367d0`, `0x143336810`, and `0x143336858` via `0x13e1690`) | 12 direct callers; roots are `0x270` receivers (a), lifecycle slots such as the `0x218` enable body `0x1372e00` and `0x1d0` activate slots, SpaceComponent, AmbianceZone, TriggerComponent, ShadowRigidBody, RagdollBoneInstance, game-logic virtuals | c, with a secondary |
| `0x18a7910` (guard `0x143336728`) | the `0x1401190` roots, plus MotionClothBody constructor `0x986700`, Cloth and SoftBody LOD instance slots, cloth body build `0x99f4d0`..`0x9a0040`, world create `0x13d1bd0` | c, with a and b secondary |
| Destructors `0x18be6b0` (via `0x18a8fd0`), `0x18a7bc0` | data pointers only: body vtable `0x1429c99a8` slot 0, base vtable `0x1429c9800` slot 1, vtables `0x1429ca1d0` and `0x1429ca6b0` slot 0; the body class is built by `0x18a8e70` from `0x18aa5e0` (called by `0x1401190` and cloth `0x9a0040`) | c |
| Pool init `0x18e0ca0` (guard `0x143336aa0`) | `0x18ae130` controller factory < `0x13d1bd0` < PhysicsWorldComponent slot `0x90` (`0x13a1460`) and SpaceWorldComponent slot `0x98` (`0x8ecfc0`) | b (world construction) |
| Pool init `0x18b5e70` (guard `0x143336aa0`) | slot 7 of vtable `0x1429c9f80`; its constructors are `0x18b5480` (< `0x18a7510` < `0x98c390` < `0x6489d0`) and `0x18b5850` (< `0x18b5ba0`); slot caller not found | c |
| `0x18aae40` (guard `0x143336858`) | `0x1401190` > `0x13e1690` > `0x18ac050` (a-reachable); physics-region vtable slots; cloth `0x9a0040` > `0x18abcb0` | c, with a secondary |
| `0x18d9040`, `0x18d9150` (guard `0x143336bc8`) | solver vtable slots (`0x1429ca1d0`, `0x1429cafb0`, `0x1429cb000`, `0x1429ca2e0`); cloth and softbody LOD slot `+0x88` > `0x9db0f0` > `0x9c0a10` > `0x18ad8f0`/`0x18ad910` > `0x18cb8e0`/`0x18cb980` | c |

**What the hold covers.** Paths rooted at BeforeSimulation receivers are inside the frozen half. The four routines that the player snowboard receiver reaches by direct calls (`0x18aa340`, `0x18aa4f0` and the two setters under them) are the verified case. Everything else stays class c, because the component lifecycle slots (`0x1d0`, `0x1d8`, `0x218`, `0x220`) are entity add, remove and enable transitions whose drivers were not traced. A transition driven by streaming, a loading publication callback, or the host adapter would not be frozen. No static link was found from the loading thread's destruction batch to a body destructor. That batch virtually destroys queued objects, so it stays a candidate and is not claimed.

**Preserved quirks and limits.**

- Class a is reachability, not execution. The chains cross branches (for example the `0x13885b0` per-component update) whose conditions were not examined.
- The cloth and softbody user of the `0x143336bc8` group and of the body allocator has no identified scheduler job. The LOD instance slot callers are indirect.
- World construction (class b) happens at session or map setup. Whether a map or sport change during a hold re-enters it is untested, per the stop-mode boundaries.

**Guards at risk while Step is held.**

- Static evidence of an unfrozen path: `0x143336aa0` (pose group pool, via `0x18e19c0`) and `0x143336bb8` (contact payload pool, via `0x1958720`). Both sit beneath the host adapter's velocity and pose setters through the `0x18b8380` group-transition notification, and the adapter thread is a host executor, not a frozen job. `0x143336aa0` is also taken by world-construction pool init.
- Conditional on a lifecycle, spawn or streaming transition while held: `0x1433367f0`, `0x143336800`, `0x143336728`, `0x1433367d0`, `0x143336810`, `0x1433367e0`, `0x143336858`, `0x143336868`, `0x143336878`, `0x143336888`.
- Unattributable statically: `0x143336bc8` (solver and cloth side).
- Live observation remains the way to settle any of these; this pass says only where to look.

Evidence file: `analysis/thread-census/t2mutators.json` (private workspace, not published).

Append after "### Body velocity and pose setters (host set_velocity / set_pose entry path)".

### Step-hold safe point live check

This is a live observation, not a reconstruction check. It asks whether holding the host's native Step pause leaves the physics pair and body state alone, and what the host's own setters touch while the pause is held. The receipt is `native/snow_host/physics_step_hold_safe_point_live.json`.

**Capture.** A private, bounded snow-host plugin was used. Its only writes were the two vtable-pointer swaps from "Live thread and lock observation", each compare-exchanged in and back:

- broad-phase slot `+0x60` (S0 inside `18b8fa0`);
- the provider+0x68 pair-collider factory slot `+8` (`18de680`).

Each detour records the calling thread and the world Step job's last-run counter (engine owner `+0x3b08`).

The plugin also read, never wrote, the PhysicsWorldStep job at `state+0x1b0`. It found the job through `world+0xff0 -> physics+0x18`. Before use it checked four things: the back-link, `state+0x10`, the delegate `0x8ab390` and the job vtable `0x1e89618`.

A read-only sampler thread swept the 11 guard globals. For each guard it read:

- the CRITICAL_SECTION's LockCount, RecursionCount and OwningThread;
- the count and head (`+0x28`/`+0x30`) of the sibling free-list pool at guard-8.

It swept continuously while held, and in 20 ms bursts every 200 ms otherwise.

`on_pause` and `on_resume` snapshotted the counters. A **frozen window** runs from `on_pause` (the host has verified the hold) to the first sweep that sees the Step last-run counter change after the resume clear. Every entry, factory call and sweep is tagged with the Step last-run value it saw. Activity counts as "in a frozen window" only when it carries the value that was frozen at `on_pause`.

The coordinator drove the session:

- host `simulation.pause` with an 8 s lease, held for about 1.2 s, then `simulation.resume`;
- early holds right after the drop-in;
- main holds between 1.5 s forward key holds (optionally steered);
- every third main hold (the first, second and fourth in session 3) was a setter hold: `player.set_velocity` at the held velocity x1.0 and x0.9, then `player.set_position` at the current position;
- marks timestamped each call window;
- sessions 2–3 also read both bodies' `+0x10` group word before and after each call, read-only and from outside the process.

**Results.**

Sessions:

- **t2-01:** 25 holds, 21 with the hooks installed.
- **t2-02:** 31 holds, 27 with the hooks installed.
- **t2-03:** the launcher watchdog stopped the bottle for host memory pressure during its 23rd hold, so its plugin records were lost. Coordinator-side data for its 22 completed holds is kept.

**Freeze.** Frozen windows lasted 1.24–4.84 s (median about 1.27 s). Across all 56 plugin-recorded holds:

- 0 `18b8fa0` entries;
- 0 worker-path factory calls;
- 0 changes of the PhysicsWorldStep job's `+0x58` counter;
- the host's own step counter never changed while held (all 78 holds, including t2-03);
- position read back identically at the start and end of every plain hold (59 of 59).

The physics job counter advanced normally between holds. At every one of 99,680 `18b8fa0` entries, PhysicsWorldStep `+0x58` minus Step last-run was the same constant, so there was exactly one PhysicsWorldStep execution per Step request. That makes `+0x58` a usable per-job progress counter, not just a proxy.

**Guards while held.** The sampler took about 1.34 billion sweeps between `on_pause` and `on_resume`. Inside frozen windows it recorded:

- 0 guard-owned observations;
- 0 changes to any pool's count or head.

The sampler is sensitive enough to catch real use. Outside holds the same sampler recorded 7,963 owned observations and 1,537 pool changes, owned only by game job-pool workers (start RVA `0x1c94b94`). In the short tail after the resume clear and before `on_resume`, job-pool workers again took ab0/ac0/bb8/7d0/878. That is ordinary stepping, and no other thread label ever owned a guard.

**Host setters while held.** 48 calls were recorded by the plugin (32 `set_velocity`, 16 `set_position`), all accepted. In every call window:

- Step stayed frozen;
- 0 guard-owned observations;
- 0 pool changes;
- 0 `18b8fa0` entries.

Group reads: 36 call windows across t2-02 and t2-03 (27 accepted and recorded by the plugin in t2-02, plus 9 coordinator-only in t2-03). In t2-03, 6 calls were accepted and 3 refused:

- **Accepted (6):** made at held speeds of 45 and 24 units/s. Body group words were identical before and after every call. Main and rider shared one group.
- **Refused (3):** all in one hold where the body was out of the world (flags without IN_WORLD, group null). That is the documented setter refusal.

**P2b answered for these states:** a host setter never changed group selection, so gate 3 of the setter chain did not open and neither `0x143336aa0` nor `0x143336bb8` was reached. After release, the body moved plausibly. The two moving accepted setter holds in t2-03 covered 23.8 and 12.9 units in 0.5 s at reported 46.7 and 25.9 units/s, and every post-release read was finite. No fallback restore was needed.

Cleanup was verified in all three sessions:

- both vtable pointers were restored and drained, with 0 foreign detour calls (t2-01 and t2-02);
- the bottle stopped, saves and settings were restored, and the original DLL was verified;
- t2-03 ended via the watchdog but restored the same way.

**Verdict.** Holding the Step pause is a valid safe point for physics pair/body state in the observed states:

- no pair update, worker-path call, physics job execution, pool-guard ownership or pool mutation was seen while held;
- the host setters made inside the hold took no pool guard and did not change group selection.

**Anomalies:**

- The rider often stopped within about 10 s of riding (terrain), so most later holds were near standstill.
- Setter holds in t2-02 lasted 3.4–4.8 s, because the external group reads are slow.
- The pre-existing `director.dll` startup-budget fault appeared in the host log, as in the census sessions.

**Limits:**

- Wine on macOS, dispatcher capacity 1.
- The sampler can miss very short critical sections. The pool count/head check is a second, state-based signal, but it covers only pool-taking paths.
- The protected controller sync at `controller+0x50`, which every host setter enters, was not sampled.
- Loading stress is partial. There were early post-drop-in holds and holds while riding, but the planned map-key attempt was not reached and no fast-travel load was observed.
- Off-graph services were not separately instrumented. They would have appeared as owned observations or pool changes, and none did.

**Static leads:**

- what the `controller+0x50` protected sync excludes against;
- whether any loading or idle-task path takes the 11 guards (exercise with a hold during a fast-travel load);
- confirming PhysicsWorldStep `+0x58`/`+0x5c` as last-run/current-request from the job class.

### Provider tree inserts (0x18de6a0, 0x18de830)

Two byte-identical bodies for the narrow-phase provider trees at provider+8 (new links, key = qword link+0x18) and provider+0x38 (neighbor records). They differ only in the grow helper they call: `18df350` (allocator tag 0x21) and `18df3f0` (tag 0x23). Nodes are the 32-byte indexed red-black nodes of Body metadata tree removal, with an 8-byte unsigned key at +0x18 and an 8-byte value at +0x10. The descriptor is node pointer q@0, active u32@8, free u32@0xC, capacity u32@0x10, root i32@0x14, free-list head i32@0x18.

```
insert(tree, &key, &value):
    parent = -1
    for node from root: parent = node
        key < node.key  -> left (went_left = true);  node.key < key -> right
        equal           -> return false         # nothing written, no growth
    if active == capacity:
        grow(tree, capacity ? 2*capacity : 4)   # 18df350 / 18df3f0
    if free_head != -1:  slot = free_head; free--; free_head = node[slot].right
                         if free_head != -1: node[free_head].left = -1
    else:                slot = active
    node[slot] = { left=-1, right=-1, key, value, red=1, free=0 }   # bytes 0xE/0xF and old parent word not cleared
    active++
    parent == -1 ? root = slot, node.parent = -1 : node.parent = parent, parent.(left|right) = slot
    fixup(tree, slot)                           # 19a3d40
    return true

grow(tree, n): n = max(n, active); if n == capacity return
    ptr ? (n ? realloc(ptr, n*32, 0x10, tag) : free(ptr), ptr = 0) : alloc(n*32, 0x10, tag)
    store ptr, capacity = n      # allocator vtable +8 alloc, +0x10 realloc, +0x18 free

fixup(tree, i):  # 19a3d40
    parent == -1 -> paint i black, return
    loop: parent black (byte == 0) -> return
          uncle = other child of grandparent; if uncle red (byte == 1):
              parent, uncle black; grandparent red; i = grandparent; parent = its parent;
              root reached -> paint black, return; else continue
          inner case: i right of parent and parent left of grandparent -> rotate left at parent (1959bb0), i = i.left;
                      mirror -> rotate right at parent (18da970), i = i.right
          parent black, grandparent red, rotate grandparent away from i's side
          (i left of parent -> right rotation 18da970, else left rotation 1959bb0); return
```

Preserved quirks: the duplicate test happens before growth and before the free-list pop, so a duplicate on a full tree allocates nothing and writes nothing. The parent test treats any nonzero red byte as red, the uncle test needs exactly 1. A reused slot keeps its stale bytes 0xE/0xF. Growth is by doubling from a minimum of four; the realloc contents carry only the old node bytes and the new tail is whatever the allocator returns.

Reconstruction: `engine/pose_provider_tree_insert.py` (`insert_pose_link_tree`, `insert_pose_neighbor_tree`, `fixup_pose_tree_insert`), reusing `_Tree.rotate`/`paint` from `engine/pose_body_tree.py` unchanged. They plug straight into the `insert` service of `merge_pose_new_links` and `merge_pose_neighbor_records` by closing over memory and an allocator.

Validation: `analysis/command-executor-audit/check_pose_provider_tree_insert.py` runs the original 18de6a0/18de830, the grow helpers, 19a3d40 and both rotations in Unicorn without interception (only the allocator vtable alloc/realloc/free is an authored deterministic stub). 512 trials, 35,640 insert calls (30,211 inserted, 5,429 duplicates rejected, 1,884 allocator calls), with 11,738 interleaved removals (pose_body_tree `_Tree.remove` with key_size 8, mirrored into native memory) to create real free lists. Trial starts: null pointer and capacity 0 to 6; keys ascending, descending, random 64-bit, high-bit boundary values and small domains; routines alternate. After every call the harness compares the return value, the allocator call sequence, and all 0x9f000 fixture bytes (descriptor, node arrays, junk-filled uninitialized slots), and checks red-black validity (unsigned order, parent links, black root, no red-red, equal black height, live count, free-list partition of used slots). All 17 targeted native branches were hit. A deliberate bug in the uncle test failed trial 0, and the restore regenerated the receipt `native/snow_host/pose_provider_tree_insert_validation.json`. Unit and composition tests: `tests/test_pose_provider_tree_insert.py` (7 tests, including both pair link merges feeding real trees and checking validity and key order).

Limits: the allocator is an authored stub, fixtures are synthetic, no live or concurrency evidence. Byte-level stage B in the safe-point contract (O7) is now reproducible offline up to the supplied allocator and the already-supplied attach, sort and neighbor-walk services.
