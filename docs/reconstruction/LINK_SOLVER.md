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
