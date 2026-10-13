# Asset decoding and import strategy

These are curated findings from Studio's format documentation, not a new asset census. [Studio provenance](../../STUDIO_SOURCES.json) records document hashes and the observed checkout revision; files may include uncommitted changes. No assets, decoded tracks, complete resource inventories, or remote project code were copied into this repository. Counts and format claims below are reported by those documents and were not independently rerun here.

## Studio evidence categories

Studio also authored replacement animations and estimated behaviors from gameplay videos. Those are not decoded original clips or binary-derived formulas. Keep four categories in every import report: asset-decoded, binary-derived, video-estimated, and Studio-authored substitute. A label such as "verified" only describes its stated test; it does not move an authored clip into the asset-decoded category. No Studio-authored animation tracks or video-fitted timing constants are included here. The pipeline proposals are design guidance, not claims about original animation behavior.

## Separate storage, records, and runtime meaning

Use four stages: archive index → decompressed record → typed resource → runtime binding. Give each stage a bounded reader and an exact consumed-byte result. Preserve unknown fields in a local diagnostic report. A successful parser does not prove that gameplay selects that resource.

For the documented version-27 `scimitar` archive, little-endian index entries contain a 64-bit offset, 64-bit resource ID and 32-bit payload size (20 bytes). Names are labels; duplicates exist. Resolve patch precedence by resource ID, retaining the chosen archive and overridden records as provenance. Do not sort by name or assume index order matches physical offsets. Validate table counts, file bounds and chain termination; reject cycles. Reserved slot capacity can exceed meaningful payload length.

Keep compressed framing separate from record parsing. The common case is two adjacent type-5 Zstandard frames in the documented layout, but raw and LZO exceptions exist. Detect the supported framing explicitly, cap decompressed output, and require complete consumption. Do not send every record through a guessed codec.

## Animation clocks and codecs

The Studio census reports 33,525 physical animation records and 5,838 active IDs after patch resolution. Those are different populations. Serialization versions 1 and 2 require separate parsing; ambiguous successful parses should fail review, not silently select one.

Channel tags split as `kind = tag // 3`, `time_format = tag % 3`. Key ticks are reported as 1/60 second and event ticks as 1/120 second. A 30 Hz authoring-duration grid is a third concept. None establishes the physics timestep or weather clock.

For multiple keys, time format 0 stores the first tick implicitly as zero followed by unsigned bytes; format 1 uses little-endian unsigned 16-bit ticks. Format 2 stores a mode byte: `shift = mode >> 6`, `byte_count = mode & 63`. Following mask bits are least-significant-bit first; bit i yields tick `i << shift`. Check population count against the key count and require bit zero. Preserve duplicate explicit ticks. Nonminimal mask lengths occur; do not derive their byte count from duration.

The channel size field describes an aligned representation, not necessarily serialized bytes. The reported relationship is `align_up(header + time_bytes, alignment) + key_count * element_size`, with header 2 or 4 depending on whether count is below 256. Mask mode bytes are excluded from that time-byte term. Use the actual serialized layout to advance the cursor.

The included [codec example](../../reference/animation_codec.py) implements only the documented 32-bit smallest-three quaternion and time-key primitives. For kind 3, the top two bits select the omitted XYZW component; the remaining three ten-bit fields use `(value - 511) / (511 * sqrt(2))`. Insert them in ascending component order and reconstruct the omitted positive square root. Synthetic tests exercise all four omitted positions. This is not a complete animation decoder.

Other reported leads: kind 4 uses three 16-bit words with omitted-index bits in the first two high bits; kind 5 stores a packed 64-bit value with the first little-endian word as its high half; kind 7 is local-Z rotation. Kind 8 float-bit flag clearing has an unresolved native one-ULP detail. Keep those separate decoder variants until individually tested.

## Skeleton, graph and mesh joins

Join track IDs to skeleton channels through recorded identifiers, not track position. Auxiliary channels need not be bones. Report unbound channels and missing bones separately. Retain hierarchy order, parent indices and LOD subtree metadata. Compare model binds against propagated local binds with sign-insensitive quaternion error; preserve disagreements rather than overwriting one representation.

Local binary-derived [skinning findings](../systems/animations/skinning/CLIENT_GUIDE.txt) supersede the older Studio uncertainty about final palette production. They establish the palette formula and remap fallback. Active addon-rig selection and packed vertex/resource-view conversions still require evidence. Establish mesh palette → skeleton index → inverse bind for each imported mesh. Graph nodes also do not prove runtime clip selection: resource UID, runtime handle key, selected output and active instance are separate joins. Preserve source transition ordering, optional/inline/reference pointer tags and output indices. Treat speculative lookahead rules as parser limitations.

For mesh and texture work, start with descriptor bounds and byte budgets before rendering. Keep vertex stream layout, index width, material assignment, texture format, mip extents and color space explicit. Validate a tiny locally owned sample at each boundary. Do not infer collision geometry from a visible mesh or physical snow properties from texture color. Full decoder coverage tables and payloads are intentionally not bundled.

## Terrain and snow material registration

Studio distinguishes the terrain texture grid (extent 16,000, origin -8,000 on each axis) from FloorHeightData (extent 16,384, origin -8,192). For terrain level L, tile extent is `16000 / 2**L`, interior width 128, raw width 132 including a two-pixel border. Pixel size is `125 / 2**L`; stitched pixel coordinate is `(world - origin) / pixel_size - 0.5`. Raw tile pixel j maps to `origin + (128 * tile_index + j - 1.5) * pixel_size`. Height scale is not horizontal extent. Row direction alone does not establish geographic north.

Validate registration against independent heights and placements, including flip/transpose alternatives and regional residuals. Studio reports regional disagreement in Japan; a globally plausible fit must not hide that exception. Avoid inventing a per-region transform solely to make one reference agree.

The snow-depth importer follows terrain group → PhysicsMaterial → fluid script → depth field. A shared surface class can merge different powder depths, so retain group and material identity. Binary depth and script thickness disagree in some cases; their gameplay consumers remain unresolved. Studio's centimeter raster and snow-depth debug view are reconstruction choices, not recovered original simulation inputs. Quantization loses distinctions; retain original scalar metadata locally.

## Import acceptance gate

Require supported version, bounded sizes, exact consumption, patch identity, referential integrity, clock/frame metadata, and a report of unknowns. Validate animation norm continuity and bind composition before showing a moving character. Keep original files in a user-supplied local asset directory outside this public repository. A future importer should output a versioned intermediate format, with source hashes and warnings, rather than make the simulation depend directly on archive internals.
