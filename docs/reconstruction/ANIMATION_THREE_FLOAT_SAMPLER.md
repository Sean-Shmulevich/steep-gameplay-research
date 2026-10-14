# Three-float quaternion channels

Encoding 24 reconstructs a four-lane quaternion from three float32 words.
The descriptor callback is `0x140d3d750`; it uses byte-time selection at
`0x140d57ff0`, paired value decoding at `0x140d71da0`, and single value decoding
at `0x140d727b0`. These are static evidence anchors for the studied build.

## Contract and arithmetic

Runtime samples start at `(count + 4) & ~3`, with a twelve-byte stride. Serialized
records use the ordinary nine-byte header, `count - 1` byte timestamps and tightly
packed samples. The allocation field remains opaque. Output is an xyzw quaternion;
this contract does not identify a bone, graph, coordinate frame or physical owner.

For three raw uint32 words, interpret each entire word as float32. Do not clear
selector bits before arithmetic. With `F` denoting float32 rounding:

```text
selector = (word[0] & 1) | ((word[1] & 1) << 1)
a, b, c = reinterpret_float32(word)
n = F(1 - F(F(a*a) + F(F(b*b) + F(c*c))))
r = reciprocal_square_root_estimate(n)
correction = F(F(3 - F(F(n*r)*r)) * F(0.5*r))
missing = F(n * correction)
output = insert([a, b, c], selector, missing)
```

The omitted component has positive sign. The third word's low bit remains numeric
but does not select a lane. Both paired outputs use this same reconstruction.
Inspected lane masks select w, z, y and x for selector 3, 2, 1 and 0 respectively.
The native routines load sixteen bytes per sample; the unused fourth lane does
not survive their lane permutation and masking. Our adapter reads twelve bytes.

The sampler retains separate integer key hints and float time, uses float32
`1/60` tick scaling, clamps the interpolation weight, then applies the established
[quaternion interpolation](ANIMATION_QUATERNION_SAMPLER.md). A final key returns
the decoded value without an additional interpolation normalization.

## Implementation and limits

`engine.animation_decoder.quaternion_three_floats` exposes value decoding;
`sample_encoding_24` and registered dispatch support full channel sampling.
Default reciprocal seed uses scalar `1/sqrt(n)`, a substitute for hardware
RSQRTPS. Optional value-decoder seeds permit controlled numerical experiments.
Sampler seed overrides affect interpolation normalization only.

Finite-value, positive-radicand, length and count checks are adapter safeguards.
They are not claims about malformed-input handling in the original game.

All fifteen encoding-24 tracks in the six-body private corpus pass seven sample
positions each, including rewind and fresh-versus-retained cursor checks.
Synthetic tests cover all selector lanes, retained low bits, explicit seeds,
serialization, dispatch, truncation and invalid values. These checks establish
internal consistency; no new native-output comparison is claimed.
