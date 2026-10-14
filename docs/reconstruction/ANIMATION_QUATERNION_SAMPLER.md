# Encoding-zero quaternion interpolation

Evidence: sampling callback `0x140d3dac0`, registered for encoding zero in the
[descriptor catalog](animation_descriptor_catalog.json). The two-key block starts
at `0x140d3db30`; the single-key branch copies its selected float4 directly.
[Key selection](ANIMATION_KEY_SELECTION.md) supplies the selected sample index
and packed current/next ticks. No gameplay clip identity is established here.

## Branches and arithmetic

The sampler converts two selected tick values to float32 and multiplies by a
runtime-initialized scale vector. It clamps float sample time to those endpoints,
then divides elapsed time by their difference to obtain t. That scale vector is
zero in the frozen image. Its initialization copies a scalar through
`0x140081e80`; tracing that scalar's producer remains open. Do not infer this
conversion from the event system's separate 120-unit timestamps.

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

A complete encoding-zero decoder still needs verified time-scale initialization,
payload bounds/alignment handling, and integration with key selection and the
resource dispatcher. The interpolation helper does not silently invent those
missing producer contracts.
