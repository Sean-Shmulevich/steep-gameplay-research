# Animation evaluator preparation

## Evidence and scope

Static inspection of the recorded executable image identifies a preparation
routine called immediately after auxiliary binding acquisition. This explains
local evaluator flags and cached samples. It does not establish gameplay clip
selection, automatic clock advancement, root-motion ownership or update cadence.
Names below are reconstruction labels. No original animation payload is included.

Evidence anchors: preparation `0x140d8a2c0`, 1,034 bytes; eligibility helper
`0x140db2d80`; initializer `0x140db3070`. Image SHA-256:
`32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`.

## Single-sample eligibility

Both the helper and the inlined pair branches apply this predicate:

```python
def eligible(resource, channel_index):
    if resource.flags & 8:
        if opaque_channel_predicate(resource, channel_index):
            if resource.auxiliary_pointer is not None:
                return False
    if resource.field_22 != 0:
        return False
    channel = resource.channels[channel_index]
    return descriptor_for(channel).virtual_40(channel) == 1
```

The channel predicate, field_22 and descriptor result need further semantic
identification. Result 1 permits a single sample here; calling it a proven
constant-track classification would overstate this evidence.

Sampling dispatches through descriptor slot +0x10, with output storage, argument
16, two zero-initialized scalar scratch fields and a further output pointer.
The time interpretation of those arguments remains unproven.

## Distinguished channels and identity tests

Two embedded four-byte records in the binding are examined. Their packed source
indices use low twelve bits; index 4095 means absent. The first record is at
binding +0x18, the second at +0x1c. Flags live in evaluator +0x60.

```python
for record, present_bit, identity_bit, reference in (
    (first_record,  0, 2, (0, 0, 0, 0)),
    (second_record, 1, 3, (0, 0, 0, 1)),
):
    source = record.source_word & 0xfff
    if source == 0xfff:
        continue
    flags |= 1 << present_bit
    if eligible(resource, source):
        value = sample_channel(source)
        matches = all_four_lanes_within_tolerance(value, reference)
        flags = replace_bit(flags, identity_bit, matches)
```

The native comparison performs float32 subtraction in both directions, MAXPS,
CMPLEPS against `0.0005000000237487257`, and requires all four comparison bits.
For ordinary finite values this is component-wise absolute difference at most
that tolerance. It is not a vector-length test. The second reference matches
quaternion identity in xyzw order, but this alone does not prove channel names.
NaN differences fail the ordered comparison. Quaternion sign equivalence is not
applied: negative identity fails this component comparison.

Presence bits are ORed. The corresponding identity bit is replaced only after
eligibility succeeds. This routine does not clear stale flags on skipped paths;
the inspected initializer clears the flag word before calling it.

## Ten paired resource channels

If resource +0x2e is zero, the pair loop is skipped. Otherwise the routine reads
exactly ten pairs of uint16 channel indices from resource +0x24. The nonzero
field is a gate here, not the loop's numerical bound. Each index uses 65535 as
its missing sentinel. These are distinct from the twelve-bit indices above.

```python
if resource.pair_gate != 0:
    for pair_index in range(10):
        for side, presence_base, cached_base, cache in (
            (0, 4, 24, first_cache),
            (1, 14, 34, second_cache),
        ):
            source = resource.pairs[pair_index][side]
            if source == 0xffff:
                continue
            flags |= 1 << (presence_base + pair_index)
            if eligible(resource, source):
                destination = append_one(cache)
                sample_channel_into(source, destination)
                flags |= 1 << (cached_base + pair_index)
```

The native order handles side zero then side one for each pair. Cache headers
are evaluator +0x70 and +0x90; append helper is `0x140dacd20`. Samples are compacted:
missing or ineligible channels do not append placeholders. Presence and cached
masks therefore carry different information. The mask layout is:

| Bits | Meaning established locally |
| --- | --- |
| 0, 1 | Distinguished source records present |
| 2, 3 | Eligible distinguished samples match their reference |
| 4–13 | First member present in each of ten pairs |
| 14–23 | Second member present in each of ten pairs |
| 24–33 | First member sampled into first cache |
| 34–43 | Second member sampled into second cache |

The caller initializes cache counts before this routine. Repeated direct calls
would append samples and retain ORed flags; this is not an idempotent refresh API.

## Next consumer checks

Trace reads of these masks alongside the two compact sample arrays to establish
how skipped pairs map to cache positions. Identify the producer of the ten-pair
table and of the two distinguished binding records before assigning bones or
root-motion semantics. This pass has no live-game validation.

A subsequent initializer stage computes
[endpoint motion and an initial-pose table](ANIMATION_ENDPOINT_MOTION.md).
It does not consume the two compact caches described here.
