# Structural animation clip-body reader

`engine.animation_container.parse_clip_body` walks a supplied typed Animation
body from its record identifier through events, bindings and channel records.
It does not search for type markers or require pre-extracted track offsets.
The corpus inspector now accepts `--body` alone:

```sh
python3 -m engine.animation_corpus --body /caller/owned/clip-body.bin
```

An optional `--records` file retains the earlier boundary-driven inspection path.
Neither path exports sample values. The Python parser returns caller-owned
identifiers and event offsets in memory; those metadata are not included in the
public corpus report.

## Evidence and layout

The container contract comes from Studio's saved `docs/specs/formats/animation.md`,
sections 2 through 6, recorded by [Studio provenance](../../STUDIO_SOURCES.json).
It is asset-format research, not an independently recovered native serializer.
The earlier [asset pipeline guide](ASSET_PIPELINE.md) summarizes this source.
Studio's full census has not been rerun here.

The body begins with u64 identifier, u32 type `0x0fa3067f`, byte 1, float32 duration
and hash A. A nonzero u32 at offset 0x15 selects version 2; zero selects version 1.
Version 2 preserves that value as hash B and then has eight zero bytes; version 1
has already consumed its four-byte zero field. Both then have three zero bytes,
a byte flag and a u32 event-track count. Hash meanings remain unassigned.

Each event track has a zero byte, zero u64, type `0x41682213`, marker 0xffff and
u32 event count. Event objects begin with zero byte, nonzero u64 and class:

| Class | Total bytes v1 | Total bytes v2 | Marker offset |
| --- | ---: | ---: | --- |
| `0x561e06fc` | 117 | 119 | last two bytes |
| `0x2350a2e0` | 109 | 109 | 94 |

The marker is bytes 01 03. Event bodies remain opaque. A zero u32, u16 count and
sorted u16 timestamps follow each event array. Count equality is checked. The
source reports 120 ticks per second for these events; the reader preserves ticks
and does not dispatch actions or assume their pairing proves gameplay timing.

The track-set header has zero byte, zero u64, type `0x0181efe8`, hash C and u32
binding count. Each binding is zero u64, type `0x653caa76` and u32 identifier.
Bindings must be sorted. They are called binding hashes rather than bones because
some identify auxiliary channels. A zero u16 follows. Version 2 then stores u32
opaque-blob length and that many bytes. Both versions finish with an opaque u32
channel-mask field, a matching u32 channel count and the serialized channels.

```text
parse fixed header and version
for each event track:
    validate typed header
    skip bounded known-class event bodies
    read and validate event timestamp count and ordering
parse typed track set and sorted binding identifiers
skip bounded optional version-2 blob
validate channel count equals binding count
for each binding:
    if tag is 254: preserve unresolved u32 shared reference
    else: use supported serialized-channel adapter to obtain exact record length
require exact body consumption
```

## Scope and safeguards

Unknown event classes, unsupported channel encodings, invalid tags, reserved
fields, counts, nonfinite duration, unsorted lists, truncation and trailing bytes
are rejected. Counts are bounded by remaining bytes before allocation/iteration.
These rejection policies are ours, not claims about original malformed-input
handling. The version-detection rule is source-reported and limited to these
serialization versions.

Channel decoding support remains the explicitly registered subset. This reader
is not yet an arbitrary-clip importer: wide-time and other value formats remain
unsupported. It preserves tag-254 references but does not resolve them, establish
their target domain or silently treat them as local indices. No such reference
appears in our six original bodies. Blob bytes and event bodies are not decoded.
It does not infer rig identity, root-motion ownership or graph selection.

## Validation

[The aggregate receipt](animation_container_validation.json) records exact
consumption of six private version-2 bodies and agreement with all 1,052 track
boundaries and binding identifiers from the older independent marker-based
extractor. Two bodies have event tracks. This verifies the new structural walk
against existing extraction, not native playback or Studio's entire census.

Synthetic fixtures exercise both versions, event framing, an opaque blob with a
decoy type marker, all truncation positions, invalid counts/types, trailing bytes
and unresolved shared references. Version 1 and tag-254 handling have synthetic
coverage only. Broader original-body testing and remaining channel formats are
the next acceptance gates before general asset import.
