# Packed 64-bit quaternion sampling

Encodings 15, 16 and 17 use eight-byte samples with four-byte alignment, producing
sixteen-byte xyzw quaternion outputs. Their callbacks are `0x140d3d3e0`,
`0x140d431d0` and `0x140d40280` respectively. They use byte, wide and mask time
selection, with the runtime headers already documented for those modes.

All call paired value decoder `0x140d71ae0` and final-key decoder `0x140d72650`.
Both helpers were inspected, including component extraction, masks, omitted-lane
branches and reciprocal-square-root refinement. The callback interpolation
sections each match the 166-instruction encoding-10 section after resolving
RIP-relative constants and expressing branches relative to their instructions.
This is static code comparison, not native execution or proof of live registration.

## Value equations

Read two little-endian uint32 words. The first stored word is the logical high
half, so do not read the sample as a normal little-endian uint64.

```text
packed = (word0 << 32) | word1
selector = word0 >> 30
fields = [(packed >> shift) & 0xfffff for shift in [40, 20, 0]]
values = [F(F(field * F(1.3487017440638738e-6)) + F(-0.7071067690849304))
          for field in fields]
squares = [F(value * value) for value in values]
n = F(1 - F(squares[0] + F(squares[1] + squares[2])))
r = reciprocal_square_root_estimate(n)
missing = F(n * F(F(3 - F(F(r*n)*r)) * F(0.5*r)))
return insert(values, selector, missing)
```

`F` denotes float32 rounding. Logical bits 60 and 61 are ignored. The native
extraction can also be expressed directly as fields `word0>>8`,
`((word0&255)<<12)|(word1>>20)`, and `word1`, each masked to twenty bits.
The SIMD masks were checked as integer words, including the middle-field mask
`[255, 0xfff00000, 0, 0]` and the all-lane twenty-bit mask.

The omitted component is positive. Native sixteen-byte loads include additional
bytes, but those do not contribute to the three retained fields or final result.
The independent adapter reads exactly eight bytes. Its default reciprocal seed
is scalar `1/sqrt(n)`, not hardware RSQRTPS; invalid/nonpositive radicands and
invalid seeds are rejected as explicit adapter safeguards.

## Sampling and APIs

`quaternion_smallest_three64` accepts the two raw words. `sample_encoding_15`,
`sample_encoding_16` and `sample_encoding_17` combine it with their respective key
selectors. Serialized adaptation, registered dispatch and corpus inspection
support all three formats. Final-key decoding returns the reconstructed value;
interval sampling applies the [established quaternion interpolation](ANIMATION_QUATERNION_SAMPLER.md).
Optional sampler seed overrides affect interpolation normalization only.

Synthetic tests cover all four selectors, spare bits, input validation, component
order and equivalent byte/wide/mask timelines including rewind and truncation.
The [original-track receipt](animation_64bit_validation.json) records seven-position
fresh-versus-retained cursor checks. Neither those checks nor the static callback
comparison establishes original runtime bit parity, bone identity or pose binding.
