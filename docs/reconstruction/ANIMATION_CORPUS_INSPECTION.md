# Repeatable serialized animation corpus inspection

Run from repository root with caller-owned files:

```sh
python3 -m engine.animation_corpus --body /path/to/clip-body.bin --records /path/to/track-records.json
```

The record file is a list, or an object containing a `tracks` list. Each ordinary
record supplies integer `codec`, `serialized_start` and `serialized_end` fields.
Records with `shared_track_reference` are counted as unresolved. When supplied, these offsets are external evidence. Without `--records`, the
[structural clip reader](ANIMATION_CONTAINER.md) derives them from supported bodies.
The CLI reads files and prints aggregate JSON. It does not save samples or assets.

Supported IDs are 0, 9, 10, 11, 12, 13, 14, 21, 22, 23, 24, 25, 26, 27, 28, 29, 39 and 54. Each supported record must match its stated
encoding and exact serialized boundary. Seven sample positions include forward
and rewind transitions. Every output and cursor is compared with a fresh-cursor
execution through the same decoder. This checks internal repeatability and
bounds, not an independent numerical reference or native execution.

Unsupported records and shared references are explicit incompleteness. Exit code
one reports validation failures; exit code zero does not mean every track is
supported. Consumers must read `all_tracks_supported_and_validated`. Error
reports contain indices and fixed reason labels, never arbitrary payload text.

## Current private-corpus checkpoint

The [aggregate report](animation_corpus_coverage.json) covers six existing private
clip bodies and 1,052 track records. Of these, 1,052 pass supported decoding and
cached/reset consistency, with 7,364 sample checks and no failures. This is
100% of tracks in this particular sample corpus, not engine, animation-system or
whole-game coverage. None of these six bodies has a shared-reference record.

No tracks in these six bodies remain unsupported. Encoding 26 and 29 are now
covered by the [mask-time float samplers](ANIMATION_MASK_FLOAT_SAMPLERS.md).

Full format coverage here does not establish active graph selection, rig binding,
procedural layers, arbitrary clip support or native playback equivalence. The
inspector can now derive boundaries through the structural reader; its supported
versions, unresolved shared references and other limits are documented separately.
Bodies and metadata remain private; this report publishes hashes and counts only.
Earlier independent-reference comparisons remain separate from these checks.

The structural reader can frame more channel formats than the sampler supports.
It can therefore report unsupported value codecs in whole bodies rather than
stopping at their first occurrence. See the [broader inventory](ANIMATION_CONTAINER.md#broader-indexed-inventory)
for a separate 3,760-body framing check; its counts are not sampling coverage.
