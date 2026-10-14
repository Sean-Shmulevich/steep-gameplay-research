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
