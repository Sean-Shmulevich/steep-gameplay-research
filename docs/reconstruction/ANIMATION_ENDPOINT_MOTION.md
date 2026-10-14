# Animation endpoint motion

Static evidence: `0x140d91df0`, 2,058 bytes, in the same image identified by
[Evaluator preparation](ANIMATION_EVALUATOR_PREPARATION.md). The inspected
initializer calls this routine after playback-range setup. This is endpoint
preparation, not a recovered frame-by-frame playback update.

## Channel selection and sampling

For each distinguished channel, a nonnull auxiliary binding supplies its source
index from the low twelve bits of the record at +0x18 or +0x1c. Sentinel 4095
skips that channel. With no binding, the routine instead calls `0x140d49c10`
with selector zero and type 5 or 6. That lookup remains to be decoded. Its
65535 return sentinel also skips sampling. Skipped channels retain prior output.

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
endpoint outputs and initial-pose table to evaluation, and decode the fallback
channel lookup before assigning root-bone identities.
