# Encoding-27 vector sampler

Static evidence: descriptor registration maps encoding 27 to callback
`0x140d3ef30`, 454 bytes, output width 16. See the
[descriptor catalog](animation_descriptor_catalog.json) for image identity.

The callback uses the same byte-time key selector as encoding zero. Sample data
begins at `(key_count+4) & 0xfffffffc`, relative to channel base, with a twelve-byte
stride per float3. Selected xyz components are loaded directly. For a two-key
result, tick endpoints are multiplied by the initialized float32 1/60 scale,
float time is clamped to the interval, and weight is the float32 ratio of elapsed
time to interval length. Each component is computed as:

```python
result = float32(a + float32(weight * float32(b-a)))
```

The final ANDNOT mask is `(0,0,0,0xffffffff)`. It clears the fourth lane on both
single-key and two-key paths. No quaternion normalization is performed.

`engine.animation_decoder.sample_encoding_27` implements this layout and
arithmetic with bounds, finite-value and nonzero-count checks as API safeguards.
`registered_channel_decoder` connects encoding IDs 0 and 27 to the recursive
resource dispatcher, rejecting other IDs and widths other than sixteen.
Successful decoding updates output and cursor; failed validation leaves them
unchanged. No rig or root-motion semantics are inferred from encoding alone.

## Private corpus comparison

The local representative corpus contains 1,744 tracks across ten clips. None use
encoding zero; 835 use encoding 27. We therefore cannot claim private-corpus
validation of the encoding-zero decoder from this dataset.

For encoding 27, decoded keys were reserialized in memory using the recovered
layout and sampled at seven positions per track, including rewinds. Across 835
tracks and 5,845 samples, maximum absolute component difference against the prior
host-double pose-assembly reference was `9.5367431640625e-07` authored units. Every
fourth lane was zero. The [aggregate receipt](animation_vector_validation.json)
records the source hash and comparison scope without payloads.

This checks float32 sampling against an existing decoded-key reference. It does
not verify that original raw channel bytes are extracted correctly, establish
native decoder parity, or confirm live rig/clip selection. No private keys,
poses or original channel bytes are included. Next validation should use original
channel slices and independently verify their container offsets.
