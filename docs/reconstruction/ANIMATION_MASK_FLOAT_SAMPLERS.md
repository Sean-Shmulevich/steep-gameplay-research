# Mask-time float quaternion and vector sampling

Encoding 26 callback `0x140d405f0` and encoding 29 callback `0x140d41de0`
complete format support for the six existing private clip bodies. Both call
mask selection at `0x140d580f0`. Both use twelve-byte samples beginning at
`((mode & 63) + 5) & ~3`. Output width is sixteen bytes.

The mode's high two bits shift timestamp positions and the low six bits give
mask length. Sample index is the population count before the selected bit, as
specified by [mask selection](ANIMATION_MASK_KEY_SELECTION.md). The incoming
cursor does not affect selection. Serialized adaptation validates the mask's
population count against the record sample count and preserves packed samples.

## Quaternion path

Encoding 26 calls paired decoder `0x140d71da0` or single decoder `0x140d727b0`.
These are the same three-float value decoders used by encoding 24, including the
embedded low-bit selector. See [the value formula](ANIMATION_THREE_FLOAT_SAMPLER.md).
The callback preserves the established quaternion interpolation branches: source
copy within epsilon 2^-23, the 0.9893559813499451 threshold, polynomial constants
0.8227968811988831 and 0.5854921936988831, and reciprocal-square-root refinement.

```text
selection = select_mask_key(mode, mask, hint)
a = decode_three_float_quaternion(samples[selection.index])
if selection.has_next:
    b = decode_three_float_quaternion(samples[selection.index + 1])
    a = quaternion_sample_blend(a, b, clamped_float32_time_weight)
return a
```

## Vector path

Encoding 29 reads three unmodified float32 components. It does not reconstruct
or normalize a quaternion. The fourth output lane is explicitly zeroed by a
verified w-lane mask, for both final-key and interpolation branches.

```text
selection = select_mask_key(mode, mask, hint)
a = read_float3(samples[selection.index])
if selection.has_next:
    b = read_float3(samples[selection.index + 1])
    a = [F(x + F(weight * F(y-x))) for x,y in zip(a,b)]
return [a.x, a.y, a.z, 0]
```

Weight uses separate hint and float time with the established float32 1/60 tick
scale. Units, coordinate frame and binding ownership remain caller evidence.

## Validation and next boundary

Three encoding-26 and six encoding-29 original tracks pass seven sample positions
with fresh-versus-retained cursor agreement. Synthetic tests compare byte-time
and shifted mask-time encodings, include rewinds and invalid lengths, and ensure
vectors remain unnormalized. Scalar reciprocal seeds remain substitutes for
hardware RSQRTPS; no native playback comparison is claimed.

All 1,052 tracks in the six-body corpus are now supported. This does not cover
all 72 registered formats, arbitrary clips, shared references or rig selection.

The existing private extraction script still finds the first binding-type marker
`0x653caa76`, reads a preceding count, then advances past fixed-size binding
records and opaque fields to reach channels. That marker search is an extraction
heuristic, not a verified general container parser. A production adapter needs:

1. A structurally verified path through the typed clip prefix to the binding table.
2. Bounds and counts for binding records, opaque metadata and channel records.
3. Defined resolution and ownership for shared-track tag 254, absent in this corpus.
4. Binding metadata preserved without guessing bone or gameplay identities.
5. Full-body consumption checks and malformed-container tests, followed by
   independent comparison against the existing private track boundaries.

The existing reader can continue accepting explicit boundaries while that
container contract is recovered. Completing format coverage does not remove
this dependency or establish authored graph and rig integration.
