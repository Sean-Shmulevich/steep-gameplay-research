# Encoding-zero quaternion interpolation

Evidence: sampling callback `0x140d3dac0`, registered for encoding zero in the
[descriptor catalog](animation_descriptor_catalog.json). The two-key block starts
at `0x140d3db30`; the single-key branch copies its selected float4 directly.
[Key selection](ANIMATION_KEY_SELECTION.md) supplies the selected sample index
and packed current/next ticks. No gameplay clip identity is established here.

## Branches and arithmetic

The sampler converts two selected tick values to float32 and multiplies by a
runtime-initialized scale vector. It clamps float sample time to those endpoints,
then divides elapsed time by their difference to obtain t. The scale vector is
zero in the frozen image, but its initializer is now traced: `0x140081e60`
divides constant 1.0 by constant 60.0 using DIVSS and stores the scalar;
`0x140081e80` broadcasts it into the vector. Thus the intended initialized scale
is float32(1/60). This is separate from event timestamps at 120 units. Static
initialization code does not prove execution order in a live process.

For supplied quaternion samples a/b and weight t, the inspected blend is:

```python
d = dot_float32(a, b)
if abs(abs(d) - 1) <= float32(2**-23):
    return a
if d < float32(0.9893559813499451):
    if d < 0:
        b = -b
    aligned_dot = dot_float32(a, b)
    k = (1 - float32(0.8227968811988831) * aligned_dot)**2
    k *= float32(0.5854921936988831)
    def low(u):
        return ((2*u - 3) * (u*k) + (k+1)) * u
    corrected = low(t) if t <= 0.5 else 1-low(1-t)
    if aligned_dot < 0:
        b = -b
    result = a + corrected*(b-a)
else:
    result = (1-t)*a + t*b
return normalize_with_reciprocal_estimate(result)
```

Every native multiply/add/subtract rounds to float32. Dot reduction groups x/z
and y/w products before the final addition. The polynomial expression above is
shown with its observed multiplication order; algebraic rearrangement can change
rounding. The near-aligned branch uses separate weighted products, unlike the
difference-form linear blend used elsewhere in the reconstruction.

Normalization computes squared norm n, obtains an RSQRTPS estimate r, and uses
`(3 - ((r*n)*r)) * (r*0.5)` before scaling all lanes. There is no zero-norm guard
in this block. The absolute-unit-dot branch returns the source unnormalized,
even at t=1 and even for opposite-sign endpoint representations.

## Executable scope

`engine.animation_interpolation.quaternion_sample_blend` implements these branches
for finite caller-supplied float4 samples and t in [0,1]. Its default reciprocal
seed uses scalar square root, a declared substitute for the hardware estimate.
A caller can supply `rsqrt_estimate`. Nonfinite inputs and zero interpolated norms
are rejected as public API safeguards.

This is a sampler-specific helper. The existing general blend helper is unchanged.
Tests cover source-copy behavior without normalization, negative-hemisphere
correction, polynomial symmetry, the aligned branch, reciprocal seed injection
and invalid inputs. No native playback comparison was performed.

The subsequent decoder adapter below connects time scale, payload layout, key
selection and interpolation. Container/rig/graph integration and live validation
remain incomplete.


## Connected encoding-zero channel decoder

`engine.animation_decoder.sample_encoding_zero` accepts a private or synthetic
channel byte sequence, float time, unsigned hint and cached key index. Byte zero
must be encoding zero. Byte one is key count; count-1 byte timestamps follow.
Float4 samples begin at `(count+16) & 0xfffffff0`, relative to channel base.
Each sample occupies sixteen bytes. The adapter checks bounds and count before
selection and rejects nonfinite selected samples. Native aligned load addresses
assume suitable allocation alignment; Python decoding does not require it.

When the packed tick result is at most 65535, it copies the selected float4
without normalization. Otherwise it converts the two ticks with float32(1/60),
clamps float time to that interval, computes a rounded interpolation fraction
and invokes the recovered quaternion helper. Float time and integer hint remain
independent: the caller owns their consistency. No hidden hint recomputation or
looping is introduced.

`encoding_zero_decoder` plugs this implementation into the recovered recursive
sampling adapter. It accepts descriptor ID 0 and width 16, preserving output
identity and updating SampleState.cursor while leaving the hint unchanged.
The ID is our explicit mapping of the recovered encoding registration. Failed
validation leaves output/cursor unchanged, an API safeguard rather than native
fault behavior. The default normalization seed remains a scalar substitute for
hardware RSQRTPS; direct callers can supply an observed seed.

Synthetic integration tests now run encoded bytes through resource-chain dispatch,
key selection and quaternion output. They cover single-key nonunit copy, the
60-tick one-second midpoint, rewind, independent time clamping, malformed payloads
and failure atomicity. No private-clip comparison has been performed for this
new decoder. Other encodings remain unsupported here.
