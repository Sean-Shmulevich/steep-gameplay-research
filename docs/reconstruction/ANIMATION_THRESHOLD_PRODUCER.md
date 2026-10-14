# Animation update threshold producer

The deferral threshold in the [update policy](ANIMATION_UPDATE_POLICY.md) is refreshed by a named `GetUpdateThresholds` callback at the start of the outer update. The constructor default is therefore not a reliable description of active behavior.

## Installation and consumption

The callback-table constructor publishes its table globally, clears its slots, and registers an installer under the exact name `GetUpdateThresholds`. The installer writes its incoming function pointer into slot `0x50`. A separate initialization routine supplies the concrete callback under that same name through the named dispatcher. The dispatcher invokes the registered installer when the name lookup succeeds.

The outer animation update calls that slot with its actor/context object and a destination at interface offset `0x104`. The callback writes seven bytes; the last lands at interface offset `0x10a`, exactly the threshold byte consumed by the deferral counter comparison. This closes the local producer-to-policy join. Startup ordering and the callback installed in a particular live session have not been observed.

## Packet construction

The callback first writes defaults, then attempts two component resolutions. Names below describe their roles in this callback rather than recovered class names.

```text
packet.raw_word = 0
packet.byte4 = 1
packet.byte5 = 2
packet.deferral_threshold = 0

first = resolve_first_component(actor)
second = resolve_second_component(actor)
if first is absent or second is absent:
    return packet

if second.kind == 40:
    packet.byte4 = 3
    packet.byte5 = 10
else:
    selector = (first.selector_word >> 3) & 7
    packet.raw_word = global_table[selector]

packet.deferral_threshold = second.threshold_byte
return packet
```

The first component's selector is a uint16 field; only bits 3 through 5 select the table entry. The selected table entry is copied as a raw uint32. Its semantic type is not established here, so the implementation preserves its bits instead of treating it as a float. Kind 40 bypasses the selector/table entirely and leaves the first word zero. The special kind is not identified with a particular sport, actor type or quality setting.

The last byte is copied unchanged from the second component. There is no local clamp. A source value of 255 stays 255; the separate policy increments its own counter with byte wrapping before comparing against this threshold. Missing either component leaves threshold zero, which prevents the counter gate from selecting deferral.

## Executable interface

`engine.animation_thresholds.update_threshold_packet` accepts caller-supplied resolved component fields and raw table words. `None` represents a missing component. `deferral_threshold` extracts the byte with the proved consumer relationship.

```python
from engine.animation_thresholds import update_threshold_packet, deferral_threshold
from engine.animation_update_policy import plan_animation_update

packet = update_threshold_packet(
    first_component={'selector_word': 24},
    second_component={'kind': 1, 'threshold': 3},
    table_words=[0, 1, 2, 3, 4, 5, 6, 7])
plan = plan_animation_update(
    pending_count_word=1, graph_state_word=0, mode_flags=1,
    counter=0, accumulated=0, interval=0.125,
    threshold=deferral_threshold(packet))
assert plan['deferred']
```

All example values are invented. The adapter does not resolve native components, install callbacks in the original game, or choose runtime thresholds. Bounds and integer-width checks are designed guards.

## Validation and remaining leads

Four repository tests cover defaults, every selector index with ignored bits set, raw table-bit preservation, the special branch, invalid snapshots and composition with the deferral policy. Original callback instructions matched 400 synthetic cases with component lookup and type lookup stubbed. Seven written bytes matched exactly and nine following sentinel bytes remained unchanged. The [validation receipt](animation_thresholds_validation.json) states that scope; this does not validate live component identity or table contents.

Next follow the second component's threshold-field writer and the global table producer. The first component lookup uses a type getter; the second uses a global type reference. Their concrete classes and relation to distance, visibility, quality settings or sport remain unresolved. The outer update's scheduler caller is also still open. An indirect call sharing slot `0x50` is insufficient to identify it.

Static anchors: callback-table constructor `14125bec0`; installer `141250510`; named supplier `140ddd050`; dispatcher `141297690`; concrete callback `140dda710`; outer update `14131bf90`. The callback reads first-component selector offset `0xe8`, second-component kind offset `0xa0`, and second-component threshold offset `0x358`. No original object snapshots, game data or instruction bytes are published.
