# Encoding-12 48-bit quaternion sampler

Static evidence: callback `0x140d3d070` through `0x140d3d3dd`; single decoder
`0x140d72540` through `0x140d7264d`, including all return branches. The paired
helper entry is `0x140d718e0`; this pass's value formula is established from the
single decoder. The sampler uses the existing byte-time selector and quaternion
interpolation regimes.

Samples begin at `(count+2) & 0xfffffffe`, with six-byte stride. Three little-endian
uint16 words hold fifteen-bit component fields. The omitted xyzw index is
`(word0 >> 15) | ((word1 >> 15) << 1)`. Word2's high bit is masked out and does
not contribute to that selector. Components remain in ascending order after
omitting the selected lane.

Each component uses float32 multiply/add with scale `4.316100603318773e-05` and
bias `-0.7071067690849304`. The omitted component uses the same grouped sum and
reciprocal-square-root refinement as the
[32-bit decoder](ANIMATION_SMALLEST_THREE_SAMPLER.md). It is inserted positively;
there is no separate final normalization in the single-key path.

`quaternion_smallest_three48` and `sample_encoding_12` implement the value and
channel behavior. The public serialized adapter inserts the required runtime
alignment and copies six-byte sample records unchanged. The resource dispatcher
and corpus checker now accept encoding 12. Scalar reciprocal seeds and validation
safeguards remain explicitly independent implementation choices.

The original six-body corpus now validates 944 of 1,052 tracks, with 6,608
cached-versus-reset sample checks and no failures. All 141 encoding-12 tracks pass.
This is internal consistency on original serialized slices, not an independent
numerical-reference or native-execution comparison for this new encoding.
Synthetic tests cover all four selector values, ignored third high bit, output
norm and serialized-to-dispatch integration.

## Expanded independent-reference comparison

A subsequent original-byte comparison tested every stored key time and every
nonempty interval midpoint for all 141 encoding-12 tracks. The 9,689 samples used
the older decoded-key/host-double pose-assembly reference as comparator. Record
lengths all matched. Maximum key-time component difference was
`1.0459658117412118e-07`; maximum midpoint difference was
`0.0002589571241477101`, with four samples above `1e-5`.

The [expanded receipt](animation_48bit_validation.json) retains the outliers'
dot products, interpolation weights and copy decisions without sample values.
All four lie at the absolute-unit-dot copy threshold. One reconstructed float32
dot is exactly `0.9999998807907104`, so the recovered inclusive epsilon branch
copies the source while the older reference interpolates. In the other three,
the reference copies while our float32 calculation interpolates. Both component
reconstruction rounding and dot reduction affect this branch.

This is a documented numerical disagreement, not a clean native-equivalence
result. No tolerance was widened to hide it. A synthetic regression now tests
the exact epsilon boundary and the next representable value outside it. Resolving
native hardware parity requires observed reciprocal estimates or direct native
sample outputs; the scalar reciprocal seed remains a declared substitute.
