# Wide animation timestamps and vector sampling

The native selector `0x140d581f0` reads uint16 timestamps. The encoding-28 callback
`0x140d44e30` uses it for twelve-byte float3 samples and sixteen-byte outputs.
Encoding 10 and 13 also call this selector; their value-sampler integration is
still pending. This guide describes inspected code, with adapter checks separated.

## Count and key layout

Byte zero is the encoding. If byte one is nonzero, it is the key count and stored
timestamps begin at byte two. Otherwise a uint16 count is at byte two and stored
timestamps begin at byte four. The first key's time is implicitly zero in both
forms. Exactly `count - 1` stored uint16 ticks follow.

```text
header = 2 if count_byte != 0 else 4
count = count_byte if count_byte != 0 else uint16_at(2)
times = [0] + uint16_array_at(header, count - 1)
if count < 2: return cursor=0, packed_ticks=0
if cursor < count and hint >= times[cursor]:
    after = cursor + 1
    while after < count and times[after] <= hint: after += 1
else:
    after = upper_bound(times[1:], hint) + 1
cursor = after - 1
packed_ticks = times[cursor]
if after < count: packed_ticks |= times[after] << 16
```

Hints and cursors are unsigned 32-bit. Equality advances past duplicate ticks;
rewind uses upper-bound binary search. A last tick of 65535 fits in low16 and
has no successor. The adapter rejects unsorted/out-of-range inputs and truncated
headers. The standalone selector retains the native count-below-two behavior,
but a sample decoder rejects zero count because no payload exists.

## Encoding 28

Sample offset is `align_up(header + 2*(count-1), 4)`, stride twelve. Each selected
sample supplies x, y and z float32 components; the fourth output lane is explicitly
zeroed. Interpolation is `F(a + F(weight * F(b-a)))` per component. No normalization
is applied. Weight uses the established float32 1/60 tick scale and clamped float
time, independently of the integer hint. See [vector sampling](ANIMATION_VECTOR_SAMPLER.md).

Serialized records keep u32 count and tightly packed times/samples. The adapter
uses the short runtime header below 256 keys and extended header otherwise,
rejecting counts above 65535 instead of truncating. The allocation field remains
opaque. `wide_channel_layout` reads either runtime header; `select_wide_key`
performs selection and `sample_encoding_28` samples vectors. Registered dispatch
and the corpus inspector now accept encoding 28.

## Validation scope

Synthetic tests compare selector results against an independent upper-bound
oracle, including duplicate and 65535 timestamps, stale cursors and rewinds.
Serialization/sampling tests cross counts 255/256 and include 300 keys, final-key
copy, long-duration interpolation, invalid count/time and truncation.

The [original-track receipt](animation_wide_vector_validation.json) records
seven-position fresh-versus-retained cursor consistency on encoding-28 tracks
from the larger indexed inventory. This is internal sampling consistency, not
an independent numerical reference or native output comparison. Header support
does not prove original clip selection, bone identity or root-motion ownership.
