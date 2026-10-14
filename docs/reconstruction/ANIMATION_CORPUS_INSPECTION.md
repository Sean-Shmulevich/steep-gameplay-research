# Repeatable serialized animation corpus inspection

Run from repository root with caller-owned files:

```sh
python3 -m engine.animation_corpus --body /path/to/clip-body.bin --records /path/to/track-records.json
```

The record file is a list, or an object containing a `tracks` list. Each ordinary
record supplies integer `codec`, `serialized_start` and `serialized_end` fields.
Records with `shared_track_reference` are counted as unresolved. These offsets
must come from separate container research; the tool does not discover them.
The CLI reads files and prints aggregate JSON. It does not save samples or assets.

Supported IDs are 0, 9, 21 and 27. Each supported record must match its stated
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
clip bodies and 1,052 track records. Of these, 803 pass supported decoding and
cached/reset consistency, with 5,621 sample checks and no failures. This is about
76.3% of tracks in this particular sample corpus, not engine, animation-system or
whole-game coverage. None of these six bodies has a shared-reference record.

The remaining 249 tracks are unsupported:

| Encoding | Tracks |
| --- | ---: |
| 12 | 141 |
| 14 | 24 |
| 23 | 17 |
| 11 | 15 |
| 24 | 15 |
| 39 | 14 |
| 54 | 14 |
| 29 | 6 |
| 26 | 3 |

Encoding 12 is the next largest blocker. Complete decoding of these clips still
would not establish active graph selection, rig binding, procedural layers or
native playback equivalence. Bodies and metadata remain private; the report
publishes body hashes and counts only. Earlier independent-reference comparison
receipts remain separate from this consistency check.
