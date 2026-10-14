# Animation endpoint motion

Static evidence: `0x140d91df0`, 2,058 bytes, in the same image identified by
[Evaluator preparation](ANIMATION_EVALUATOR_PREPARATION.md). The inspected
initializer calls this routine after playback-range setup. This is endpoint
preparation, not a recovered frame-by-frame playback update.

## Channel selection and sampling

For each distinguished channel, a nonnull auxiliary binding supplies its source
index from the low twelve bits of the record at +0x18 or +0x1c. Sentinel 4095
skips that channel. With no binding, the routine instead calls `0x140d49c10`
with hash zero and converted type 5 or 6. The decoded lookup is described
below. Its 65535 return sentinel also skips sampling. Skipped channels retain prior output.

Both selected channels are sampled at the effective range start and end. The
routine computes signed-conversion sampling hints from float32 time multiplied
by **60**, without adding 0.5. The hints are stored as low 32 bits of a truncating
64-bit conversion. This is separate from the 120-unit event timestamps.

Sampling uses the alternate resource callback when flag bit 3, the channel
predicate and a nonnull alternate resource permit it. Otherwise descriptor
slot +0x10 receives the channel, output, argument 16, time pointer, hint pointer
and a scratch cursor initialized to -1. The callback may modify scratch fields;
these arguments are not a fully decoded sampler API.

## Displacement and rotation formulas

Let p0/p1 be the first channel's four-lane samples at start/end, and q0/q1 the
second channel's xyzw samples. The inspected arithmetic is:

```python
displacement = p1 - p0
rotation = conjugate(q0) * q1
if evaluator_variant_bit_0:
    displacement.x = -displacement.x
    rotation.y = -rotation.y
    rotation.z = -rotation.z
rotation = normalize_with_rsqrt_refinement(rotation)
```

Quaternion multiplication order was recovered from the SSE shuffles. The native
sum accumulates the conjugate-start w contribution, then x, y and z contributions,
with float32 rounding after each multiplication and addition. It does not divide
by the squared start norm before multiplication. Displacement includes all four
lanes. Outputs are evaluator +0 and +0x10. No position integration is done here.

For squared norm n and hardware reciprocal-square-root estimate r, normalization
uses `scale = (r * 0.5) * (3 - r * (r * n))`, rounding each operation to float32,
then multiplies each rotation lane by scale. The inspected block has no zero-norm
guard. The public helper rejects invalid/zero norms as an API safeguard.

The sign changes match a reflection-style convention, but the variant's complete
meaning and its gameplay uses remain open. This is evidence for endpoint motion
arithmetic, not proof that the engine applies it to the player's physical body.

## Runnable helper

`engine.animation_endpoints.endpoint_delta` implements this arithmetic over
caller-supplied samples. Its default scalar reciprocal seed is a documented
substitute for RSQRTPS. Supply `rsqrt_estimate` to reproduce a known native seed.
Tests cover noncommuting rotations, four-lane displacement, variant signs,
explicit seed and rejected invalid inputs. No game samples are shipped.

## Separate initial-pose table

The same routine allocates a table of 32-byte pairs with reported count
`resource.field_2e >> 1`. It walks the source index array in increments of two
while the index is below field_2e. Each pair begins as zero vector plus quaternion
identity, then any nonmissing member is sampled at the effective start time.
This establishes a different use of field_2e from the earlier preparation's
nonzero gate followed by ten fixed pairs. An even count is an apparent data
contract; this routine does not validate it before the last paired read.

The table lives at evaluator +0x390 and does not consume the compact caches at
+0x70/+0x90. Their later consumers remain open. Next work should connect the
endpoint outputs and initial-pose table to evaluation. Hash zero selection is
now established, but assigning root-bone identities still requires the producer.


## Fallback channel lookup

The wrapper at `0x140d49c10` loads resource +0x40 and tail-calls `0x140da83a0`.
The latter has 258 bytes of instructions through its final return, followed by
alignment and an eight-entry switch table. Its metadata contains a hash-array
pointer at +6 and a uint16 count at +0x10. The channel array is passed separately.

```python
index = unsigned_lower_bound(channel_hashes, requested_hash)
while index < count and channel_hashes[index] == requested_hash:
    descriptor = descriptor_table[channels[index].encoding_byte]
    raw_type = descriptor.type_byte
    converted_type = (6, 5, 5, 5, 0, 2, 3, 1)[raw_type] if raw_type < 8 else 8
    if converted_type == requested_type:
        return index
    index += 1
return 65535
```

It returns the first matching type among duplicate hashes. A different hash ends
the search immediately; it does not continue scanning for type alone. Hash
comparison is unsigned. Sorted hashes and valid metadata/channel alignment are
native data contracts, not validations performed by this routine.

The two endpoint fallback searches therefore select the first hash-zero channel
with converted type 5 and the first with converted type 6. Hash zero is not the
CRC32 named Reference channel identified elsewhere. The absence of an auxiliary
binding triggers fallback; a present binding containing source sentinel 4095
skips the endpoint without fallback.

Public helpers in `engine.animation_binding` implement `find_typed_channel` and
`select_endpoint_channels`. Callers supply descriptor type bytes, not channel
encoding bytes. Synthetic tests cover unsigned high hashes, duplicate type
ordering, hash-group termination and present-but-missing bindings. Invalid
sortedness, widths and array lengths are rejected by the public adapter.

## Alternate-resource routing

The predicate at `0x14075b680` is a 114-byte leaf routine with both return paths
inspected. It compares the unsigned channel index against resource +0x7a. An
out-of-range index returns true. Missing metadata at resource +0x40 also returns
true. Otherwise it reads that channel's hash through metadata +6 and returns
false for these identifiers:

```text
00000000 898e99d5 1087c86f 6780f8f9 f9e46d5a 8ee35dcc
17ea0c76 60ed3ce0 f0522171 875511e7 e7929802
```

It also returns false for the inclusive unsigned range `ffffffda..ffffffe3`.
The native expression is unsigned32 `hash + 0x26 <= 9`, including wraparound.
Every other hash returns true. The ten nonzero isolated hashes remain unnamed.

The caller dispatches to the alternate resource only when all three conditions
hold: resource flag bit 3, predicate true, alternate-resource pointer nonnull.
Otherwise it uses the ordinary descriptor decoder. Thus a valid hash-zero
fallback channel stays on the ordinary decoder even when the alternate resource
is installed. This is a source-backed narrowing of the endpoint sampling path.

The identical exclusion sequence is inlined in the initial-pose table branches.
The earlier single-sample eligibility helper rejects alternate-routed channels
before checking field_22 and the descriptor's result of one. Missing metadata
and out-of-range results are not evidence of a safe or valid channel access.

`engine.animation_binding.alternate_channel_candidate` implements the predicate;
`channel_sample_route` composes the flag and pointer-presence gates. These helpers
do not access resources, execute the alternate callback or validate channel
payloads. Tests cover every isolated identifier, wrapping-range boundaries,
missing metadata, invalid indices and the hash-zero dispatch consequence.
