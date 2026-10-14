# Scalar animation channel sampling

Two recovered descriptor callbacks produce four-byte outputs, unlike the
sixteen-byte vector/quaternion channels. Encoding 39 (`0x140d3c5f0`) produces a
float; encoding 54 (`0x140d3e570`) produces a uint32 word. Descriptor registration
and output widths are recorded in [the catalog](animation_descriptor_catalog.json).
No gameplay parameter or authored graph binding is established by these formats.

## Shared timing and layout

Both call byte-time selection at `0x140d57ff0` and use the initialized float32
1/60 tick scale documented in [quaternion sampling](ANIMATION_QUATERNION_SAMPLER.md).
They retain separate integer hint and floating sample time. For an interval:

```text
start = F(start_tick * F(1/60))
end = F(end_tick * F(1/60))
t = F(F(clamp(time, start, end) - start) / F(end - start))
```

`F` rounds to float32. A final-key selection copies/decodes that key directly.
Runtime encoding 39 starts samples at `count+1`, stride one. Encoding 54 uses
`(count+4)&~3`, stride four. Serialized channels have the existing nine-byte
header, count-minus-one time bytes and packed samples. Allocation metadata
remains opaque; adapter validation and bounds checks are independent safeguards.

## Encoding 39

Each byte is sign-extended. Its value is `F(signed_byte * F(0.008))`.
The observed constant is 0.00800000037997961. Interpolation preserves difference
form: `F(a + F(t * F(b-a)))`. This permits the full signed-byte range; the decoder
does not clamp it to [-1,1]. Values -128 and 127 decode to approximately -1.024
and 1.016. Units and consumers remain unknown.

## Encoding 54

Native arithmetic subtracts the next and current words in EAX, then converts
RAX to float. Writing EAX zero-extends, so the subtraction result is unsigned
modulo 2^32 even when the next numeric value is smaller.

```text
difference = (next_word - current_word) & 0xffffffff
increment = truncate_to_int64(F(F(t * F(difference)) + F(0.5)))
output = (current_word + increment) & 0xffffffff
```

For keys 0 and 3, the midpoint yields 2. For keys 10 and 9, it yields 2147483658;
the final key selected directly still yields 9. This discontinuity is retained.
It does not establish that decreasing word tracks are authored or that the
channel should represent a smoothly varying gameplay quantity. Treating this
as signed interpolation or float-bit interpolation would change inspected code.

## APIs and validation

`sample_encoding_39` and `sample_encoding_54` return one-element value lists,
with float and integer elements respectively. Registered dispatch requires width
4 for these formats. The corpus inspector now supplies descriptor-specific widths.

All 28 corresponding tracks in the six-body corpus pass seven sampling positions
and fresh-versus-retained cursor checks. Synthetic cases test signed extremes,
rounding, uint32 wrap, rewinds, width rejection and failure atomicity. These are
internal consistency and static-contract tests, not native runtime comparisons.
