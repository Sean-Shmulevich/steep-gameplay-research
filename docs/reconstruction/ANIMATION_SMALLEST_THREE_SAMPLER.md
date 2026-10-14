# Encoding-9 general quaternion sampler

Static evidence: encoding 9 registration selects `0x140d3cd00`, 872 bytes.
Single-value decode is `0x140d723f0`; paired decode is `0x140d71660`.
The callback uses the established byte-time key selector and quaternion blending
regimes. Runtime samples start at `(count+4) & 0xfffffffc`, stride four bytes.

The top two bits of each uint32 word select the omitted xyzw component. Remaining
fields at shifts 20, 10 and 0 supply the other components in ascending component
order. Each ten-bit value maps through float32 multiply and add:

```python
component = float32(float32(bits * float32(0.0013837706064805388))
                    + float32(-0.7071067690849304))
```

For decoded components a/b/c, the omitted positive component is reconstructed
from `n = float32(1 - float32(a*a + float32(b*b + c*c)))`, with every product also
rounded to float32. Native code computes an RSQRTPS estimate r, then:

```python
correction = float32(float32(3 - float32(float32(r*n)*r)) * float32(0.5*r))
missing = float32(n * correction)
```

This is a square-root approximation through reciprocal refinement, not a direct
SQRT instruction. The paired decoder repeats this for the next word. The missing
component is inserted at the selected position; it is not appended unconditionally.
Single-key output is not subsequently normalized.

`quaternion_smallest_three32` implements the value reconstruction, allowing an
explicit reciprocal estimate. Its default scalar reciprocal is a documented
substitute. The API rejects nonpositive radicands and invalid words; native
arithmetic has no equivalent rejection here. `sample_encoding_9` adds time/key
selection and interpolation. The shared serialized adapter and dispatch callback
now support encoding IDs 0, 9, 21 and 27. The sample function's optional seed
controls interpolation normalization only; its value decodes use scalar seeds.

## Original-byte comparison

Six previously extracted private clip bodies supplied 127 encoding-9 tracks.
Every parsed record length matched its recorded boundary. Seven times per track
produced 889 comparisons against the older decoded-key reference. Maximum
sign-invariant component difference was `1.25930273264796e-07`.
The [aggregate receipt](animation_smallest_three_validation.json) includes body
hashes, counts and scope without game data.

This validates this independent decoder against the prior reference on original
serialized records. It does not establish native hardware bit equality, fresh
archive extraction correctness or active player rig selection. Synthetic tests
cover all four omitted positions, field order, invalid radicands, explicit seeds
and serialized dispatch with nonzero X/Y rotation components.
