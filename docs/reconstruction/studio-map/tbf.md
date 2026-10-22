<!-- Imported authored research, not game payloads. -->
> Source: Studio `steep-wasm`, commit `1344bca03985eb1540236fb2ecd3cbbe8ecdcf14`, `docs/specs/formats/tbf.md`.
> Evidence labels and validation counts below are the source agents' reports;
> the asset-level checks were not rerun for this import. Local source links were
> converted to plain references; their files may not be included here. Historical
> superseded sections remain labeled. Studio-authored runtime policies are not
> evidence of original game behavior.

# `.tbf` terrain container ("FBT" quadtree) — P2-06

Clean-room spec written from the data files only (no executable code was examined).
Kaitai description: `tbf.ksy` (Studio source: `tbf.ksy`). Parser: `crates/summit-formats/src/tbf.rs`.
Lab scripts: `tools/lab/P2-06/` (and `tools/lab/P0-05/tbf/` from P0-05).

Six files, all in `$STEEP_INSTALL`:

| Region | lin0 | lin1 | sections/node |
|---|---|---|---|
| `PCAlpes` | 7,364,564 B, 315 nodes | 1,203,120,344 B, 87,381 nodes | 4 (F = 0x0C); 5 at L8 with the class map |
| `PCAlaskaTUX` | 7,191,780 B, 315 nodes | 1,099,869,884 B, 87,381 nodes | 5 (F = 0x10); 6 at L8 with the class map |
| `PCJapan` | 8,680,990 B, 315 nodes | 1,690,646,257 B, 87,381 nodes | 5 (F = 0x10); 6 at L8 with the class map |

VERIFIED: `tools/.venv/bin/python tools/lab/P2-06/tbf_audit.py $STEEP_INSTALL/*terrainlin*.tbf`
(sizes, node counts and flags as above; `misfits 0`, `gaps/overlaps 0` on every file).

All integers are little-endian.

## 1. Header (0x1C bytes) and offset table

| Off | Type | Value (all 6 files) | Meaning |
|---|---|---|---|
| 0x00 | char[4] | `FBT\0` | magic |
| 0x04 | u32 | 1 | version (UNVERIFIED) |
| 0x08 | u32 | 16 | UNVERIFIED. Equals the tiles per side of level 4, the one deep level lin0 holds in full (§5) |
| 0x0C | u32 | 2048 | UNVERIFIED. Equals 16 × 128 texels (level 4 across) |
| 0x10 | u32 | 1024 | UNVERIFIED. Equals 8 × 128 (level 3 across) |
| 0x14 | f32 | 6800.0 | height scale: trailer `height_min/max` × 6800 = metres (VERIFIED, §4, world-coords.md (Studio source: `world-coords.md`) §5) |
| 0x18 | u32 | 87381 | node count = (4^9 − 1)/3, a full 9-level quadtree (levels 0..8) |
| 0x1C | u64[87381] | | absolute offset of each node block; 0 = node absent |

- The first block starts right after the table (0x1C + 8·87381 = 0xAAAC4). Offsets are unique. The blocks
  tile the rest of the file with no gaps, so header + table + blocks = 100% of the bytes in all 6
  files (VERIFIED, `tbf_audit.py`, `bytes explained … (100%)`).
- A block's size is the distance to the next larger offset, or to the end of the file. Blocks carry no
  size field of their own.
- **Storage order:** on disk, blocks are written level by level, then in Morton (Z) order of the
  node's (x, y) within each level. Example: level 2 is stored as local indices 0, 1, 4, 5, 2, 3, 6, ….
  This order is not the table order. VERIFIED: `tbf_audit.py` prints
  `file order == level-major, then Morton(x,y) of row-major local index … True` for all 6 files.
  Readers must follow the offsets and must not assume any order.

## 2. Quadtree indexing

```
start(L) = (4^L − 1) / 3            L = 0..8, level L has 4^L = 2^L × 2^L nodes
i        = start(L) + y·2^L + x     row-major within a level, x fastest
L        = largest L with start(L) <= i;  k = i − start(L);  x = k mod 2^L;  y = k div 2^L
children of (L, x, y) = (L+1, 2x+dx, 2y+dy), dx, dy ∈ {0, 1}
```

- **Row-major, not Morton.** VERIFIED by exact byte equality. With B = node k+1 for the x
  neighbour and node k+2^L for the y neighbour, the BC1 block column 32 of tile A equals block
  column 0 of tile B, and likewise for rows. Result at level 5 in all three regions:
  `A.blockcol32==B.blockcol0 992/992`, `A.blockrow32==B.blockrow0 992/992`
  (`tools/lab/P2-06/seams.py $STEEP_INSTALL/PC*_terrainlin1.tbf 5`).
- **Seam metric.** The seam ratio is the mean |ΔRGB| across tile seams divided by the mean
  |ΔRGB| between interior neighbours. Alpes level 5 (`seams.py`, VERIFIED):
  - row-major: 1.16 / 1.18
  - Morton: 2.95 / 4.65
  - column-major: 4.64 / 4.62
- **Child rule.** The rule (2x+dx, 2y+dy) gives mean |downsampled children − parent| = 4.08 at
  Alpes L5→6, against 8.51 with x and y swapped and 12.2 / 13.0 with one axis flipped. VERIFIED:
  `tools/lab/P2-06/parentchild.py $STEEP_INSTALL/PCAlpes_terrainlin1.tbf 5`.
- **Two independent cross-checks** (both VERIFIED, `tools/lab/P2-06/tbf_trailer.py`):
  - The trailer min/max field (§3.2) is smoothest under row-major. Roughness of L8 `height_min`
    for Alpes: row-major 0.0102, Morton 0.0633, shuffled 0.4407.
  - Under row-major the lin0 node set is a solid 3×3 block at the map centre (§5).

### Texel grid and stitching

A colour tile is 132 × 132 texels: a 2-texel border, the tile's own 128 × 128 area, and another
2-texel border.

- Texels 128..131 of a tile are byte-identical to texels 0..3 of its right/bottom neighbour.
  That is one duplicated BC1 block column/row, so the tile stride is 128 texels. VERIFIED: an
  offset scan of mean |A[:, s+j] − B[:, j]| at Alpes L5 gives 5.14 / 3.36 / **0.00** / 3.09 / 4.74
  for s = 126..130 (`seams.py`), with the same exact zero in all regions.
- Texel j covers [(j − 2), (j − 1)) × s_L from the tile origin, where s_L = tile size / 128, so
  texel centres sit at (j − 1.5)·s_L. VERIFIED: a sub-texel fit of parent against downsampled
  children has its minimum at offset −1.5 in all three regions (`parentchild.py` plus a scan).
- Stitch rule:
  ```
  image[128·y + r][128·x + c] = tile(L, x, y)[2 + r][2 + c]      r, c ∈ 0..127
  ```
  This gives a 128·2^L-square seamless level image. Texel row r increases with tile y, and
  texel column c with tile x.
- Seam ratio with this rule (VERIFIED, `tools/lab/P2-06/stitch.py`):
  - Alpes L5: 0.96 / 0.99
  - Alpes L6: 0.97 / 0.97
  - Alaska L5: 1.12 / 0.99
  - Japan L5: 1.07 / 1.04
  - Contrast: Morton with the same crop gives 2.84 / 4.55.
- Rust stitcher, same rule, one combined x+y ratio. VERIFIED:
  `target/release/summit-import tbf stitch $STEEP_INSTALL/PCAlpes_terrainlin1.tbf --level 6 --out $STEEP_DATA/captures/lab/P2-06_Alpes_L6_rust.png`
  → `raw_overlap_blocks_equal=266112/266112 (100.000%)`, `seam_ratio=0.970`
  (`--order morton` gives `seam_ratio=4.344`). Its BC1 565 expansion uses bit replication,
  while `tools/lab/P2-06/bc1.py` uses rounding, so pixels can differ by at most 1 LSB between the two
  (UNVERIFIED here: review subagent's comparison).
- Whether +y points north or south is UNVERIFIED. The images look plausible with y down, but that
  is an image-only judgement.

## 3. Node block

```
u8[3]  ED FE 0C
u8     F                     bits 0..6: n = (F & 0x7F)/4 + 1 sections; bit 7: leaf
n × { u32 len; u8 data[len] }
u8     trailer[40]
if F & 0x80: { u32 len; u8 data[len] }      "extra" section
```

- F is 0x0C or 0x8C in Alpes (4 sections) and 0x10 or 0x90 in AlaskaTUX/Japan (5 sections).
- Bit 0x80 is set on exactly the level-8 nodes: 65,536 per lin1 file, 9 per lin0 file.
- Every block ends exactly at the next block start.
- All of the above is VERIFIED by `tbf_audit.py` and by the Kaitai spec parsing every present block
  in all 6 files: `tools/.venv/bin/python tools/lab/P2-06/tbf_ksy_check.py docs/specs/formats/tbf.ksy $STEEP_INSTALL/*terrainlin*.tbf`
  → `ksy blocks parsed 87381 {'0xc': 21845, '0x8c': 65536}` (Alpes lin1); the other files are analogous.

**T-11 reading of the same bytes** (`tbf-heights.md` (Studio source: `tbf-heights.md`) §0.1). `ED FE` is the u16
magic 0xFEED, and the next two bytes are a u16 descriptor word W = `0x0C | F << 8`: version =
W & 0x3FF (12 everywhere), layout flags = W & 0x7C00 (0x0C00 Alpes, 0x1000 AlaskaTUX/Japan), and
bit 15 (F bit 7) = a class map follows the trailer. Flags above 0x0C00 add the second colour section.
The formula n = (F & 0x7F)/4 + 1 gives the same section count for these two flag values only.
VERIFIED: `cd tools/lab/T-11 && $STEEP_DATA/shared/lab-venv/bin/python -I layout.py` →
`W (hex, is L8): {('0xc0c', False): 21845, ('0x8c0c', True): 65536}` (Alpes),
`{('0x100c', False): 21845, ('0x900c', True): 65536}` (AlaskaTUX, Japan); `class map iff L8: 87381`;
`record ends at next block: 87381` in all three lin1 files.

Per region, the length-prefixed sections of a record (VERIFIED, `layout.py`):

| Region | Levels 0–7 | Level 8 |
|---|---|---|
| Alpes | 4: heights, colour, material raster, mask | 5: heights, colour, material raster, mask, **class map** |
| AlaskaTUX, Japan | 5: heights, colour, colour 2, material raster, mask | 6: heights, colour, colour 2, material raster, mask, **class map** |

The 40-byte trailer sits between the mask section and the class map. The class map is always the
last section and exists only at level 8.

### 3.1 Sections (0-based)

| Section | Alpes (4) | AlaskaTUX / Japan (5) |
|---|---|---|
| 0 | **heights** (decoded, `tbf-heights.md` (Studio source: `tbf-heights.md`) §0.4); largest (median ≈ 8–15 kB) | same |
| 1 | **colour**: LZ4 → BC1 tile | **colour**: LZ4 → BC1 tile |
| 2 | **layer raster** (min length 18; G-08) | **colour 2**: LZ4 → BC1 tile |
| 3 | "mask": unknown (min length 10) | **layer raster** (G-08) |
| 4 | — | "mask": unknown (min length 10) |
| extra (leaf, last) | **class map** (decoded, `tbf-heights.md` (Studio source: `tbf-heights.md`) §0.5) | **class map** |

- **Colour sections** are raw LZ4 blocks with no frame. They decompress to exactly 8712 B = 33 × 33
  BC1 blocks (8 B each, block rows top to bottom), i.e. a 132 × 132 tile. VERIFIED on every colour
  section in all 6 files:
  - Alpes lin1: s1 87381 ok, 0 fail
  - AlaskaTUX and Japan lin1: s1 87381 and s2 87381 ok, 0 fail
  - each lin0: 315 per colour section

  The check decoded into a 1 MiB buffer, so the output length is exactly 8712, not truncated.
  No other section decodes to 8712 B (all tried, not sampled) (`tbf_audit.py`).
- **BC1 decoding** is standard: 565 endpoints. When c0 > c1 there are 4 colours with 1/3 and 2/3
  interpolation; otherwise 3 colours plus transparent black. Some blocks use the 3-colour mode.
- **Colour 2 (AlaskaTUX/Japan)** is an alternate albedo layer in the same format. At level 5:
  - Alaska: 91.3% of BC1 blocks are identical to section 1; Japan: 46.6% (UNVERIFIED here:
    subagent's inline scan at level 5, not re-run). Japan section 1 looks like a snow-covered state, and section 2 shows
    vegetation and rock. That this is a seasonal or snow variant is UNVERIFIED (image judgement).
- **Constant tiles:** the smallest colour section is 52 B, which looks like a constant tile.
  Section 1 is 52 B in 22,876 Alpes, 36,043 Alaska and 72,518 Japan lin1 nodes (VERIFIED,
  `tbf_trailer.py secs`).
- **Update (T-11):** section 0 (heights) and the leaf extra (class map) are now decoded
  (`tbf-heights.md` (Studio source: `tbf-heights.md`) §0). Only the "mask" section (Alpes s3, AlaskaTUX/Japan s4)
  is still unknown. The rest of this bullet is the P2-06 record.
- **Sections 0, 2/3/4 and extra use an unknown encoding.** Entropy is 6.3–7.97, and zlib, zstd,
  LZ4 and Anvil were already ruled out (protection.md §5). Their lengths correlate with the trailer
  mask popcount (Alpes s0 +0.73, Japan extra +0.86; VERIFIED, `tbf_trailer.py secs`). Decoding them
  is P2-06b; findings and ruled-out hypotheses are in `tbf-heights.md` (Studio source: `tbf-heights.md`).
  The layer raster (Alpes s2, AlaskaTUX/Japan s3) is now decoded: see
  `../world/terrain-surfaces.md` (Studio source: `../world/terrain-surfaces.md`) §2.

### 3.2 Trailer (40 bytes)

| Off | Type | Name | Meaning |
|---|---|---|---|
| 0x00 | f32 | `height_min` | normalised minimum (0..1) over the node's tile, border included |
| 0x04 | f32 | `height_max` | normalised maximum over the same footprint |
| 0x08 | u64 | `layer_mask` | mask in 3-bit groups: group k = bits 3k..3k+2 |
| 0x10 | u8[24] | reserved | always zero |

**`height_min` / `height_max`.** That these are heights is UNVERIFIED; the structure below is VERIFIED.
- `height_min ≤ height_max` in every node of all 6 files.
- Ranges: Alpes 0.0171–0.9278, Alaska 0.0513–0.9814, Japan 6e-8–0.7229.
- Flat nodes (min == max): Alaska has 4,203 nodes, all at its global minimum 0.05132, which fits a
  flat sea. Japan has 62 at 6e-8.
- A parent does **not** strictly contain its 4 children's range. Example: Alpes root max 0.92337,
  but the L1 maximum is 0.92583.
- The parent range does lie inside the range over its children plus a 1-node ring, for every node
  in all three regions (`tbf_trailer.py tree2`). So the bounds come from each node's own downsampled
  tile including its border.
- The values are not quantised to k/255, k/1023, k/4095 or k/65535.

**`layer_mask`.** That the groups are materials or layers is UNVERIFIED; the structure is VERIFIED.
(Resolved in G-08: group k is TerrainMaterialBank group k, and the set of non-zero triples equals
the set of groups in the node's decoded layer raster in 87,381/87,381 nodes; see
`../world/terrain-surfaces.md` (Studio source: `../world/terrain-surfaces.md`) §2.9.)
- The u32 at +0x0C is the high half of this mask, not a flag.
- Per-bit counts come in near-equal triples, e.g. Alaska bits 0–2 = 13467 / 13570 / 13548. Bits
  30–32 form one group across the u32 boundary.
- The highest bit seen is 32 (Alpes) and 41 (AlaskaTUX/Japan), so at most 14 groups.
- Root values: Alpes 0x1_FFFFFE3F, Alaska 0x201_FFFFFFFF, Japan 0x249_FFFFFF04.
- Hierarchy: parent ⊆ OR(children + 1-ring) for all 21,845 interior nodes in every region.
- Some section lengths track groups. Alpes section 2 is at its minimum length exactly when group 6
  is absent (agreement 0.998), and in Japan the extra section's minimum matches group 4 being
  absent (0.996) (`tbf_trailer.py secmask`).

**Bytes 0x10..0x27:** `bytes16..39 nonzero nodes: 0` in all 6 files (VERIFIED, `tbf_trailer.py stats`).

**Effective material set (T-12, contact lead, UNVERIFIED as game behaviour).** Bytes 0x08..0x27 read
as a 256-bit set of material ids (bank entries, the three variants counted separately; only the
low u64 is ever non-zero) are only an authoring-time initial value. The game's per-tile layer set
is that stored set OR the ids present in the tile's 132 × 132 decoded samples (variants applied,
tbf-heights.md §0.6), which explains T-11's 76–87 % agreement. Summit computes any per-tile material
set as mask | present, never the mask alone (`summit_formats::tbf_class::effective_material_set`).

### 3.2.1 AlaskaTUX: trailer range vs FloorHeightData (T-08b)

Question: clamping `ground.r16` (FloorHeightData, FHD below) into the L8 trailer ranges `[6800·hmin, 6800·hmax]` moves 27 % of AlaskaTUX
samples (mean 121 m, max 893 m, mostly raised), against 0.85 M samples in Alpes. Scripts (scratch, no game
data inside; run as `source tools/env.sh; tools/.venv/bin/python -I <script>` from
`$STEEP_DATA/T-08b/trailer/`): `read_tr.py` (L8 trailers to `tr_<R>.npz`), `fit.py`, `idx.py`, `cls.py`,
`map.py`, `grp.py`, `edge.py`, `trees.py`, `fit2.py`; outputs `*.txt` and the map
`diff_mid_trailer_minus_fhd.png` (red = trailer above FloorHeightData) in the same directory.

**Answer: the 6800 scale, offset 0 and the node indexing are right. The disagreement is real: in about 17 % of
the L8 nodes the trailer range sits on a smoothly shifted, higher surface than FloorHeightData
(typically +50..500 m, 91 % of those nodes have `height_min` above the FHD node maximum). No per-region
linear map fixes it. The clamp must stay off for AlaskaTUX.**

- **1. Scale/offset (VERIFIED, `fit.py`, `fit2.py`).** Per node FHD min/max/mid (nodes from the exact
  62.5 m footprint, no border) against `6800·hmin/hmax/mid`, all 65,536 nodes:
  - Alpes: mid `z = 0.9999·h + 0.83`, R² 0.99999, residual |r| p50/p99 0.88 / 10.2 m; 99.6 % of nodes agree to 20 m.
  - AlaskaTUX, all nodes: mid `z = 0.9952·h + 48.2`, R² 0.9947, |r| p50/p90/p99 37 / 65 / 542 m
    (the fit is dragged by the outliers). On the 83.4 % of nodes within 20 m: `z = 0.99963·h + 0.986`,
    R² 0.999994, |r| p50/p99 1.09 / 15.4 m. So a = 1, b ≈ 1 m, the same as Alpes: scale 6800 and offset 0 are correct.
  - Japan: not informative here, the cached `ground.r16` is already trailer-clamped (fit gives a 1.000, FHD range inside the trailer range for 100 % of nodes by construction).
  - Trailer z range AlaskaTUX 348.9999..6673.85 m; FHD 310.86..6673.63 m. The lowest trailer value is the sea
    plane 349.0 (3,466 flat nodes); FHD is 348.9 there too (6,947 nodes with trailer min 349: FHD min median 348.9), so sea is not the cause. FHD has 14.9 % of
    its samples below 349 (UNVERIFIED meaning: below-sea-level seabed/glacier bed outside the water nodes).
- **2. Indexing (VERIFIED, `idx.py`).** Eight variants (swap, flip y, flip x) of the 256×256 FHD node mid grid
  against the trailer mid grid: identity wins by a wide margin. Alpes: 96.6 % of nodes within 5 m, next variant 0.7 %.
  AlaskaTUX: 73.9 % within 5 m (median |diff| 1.47 m), next best (x/y swapped) 6.6 %, median 474 m; one-node shifts all
  11-14 %. Row-major, row = +y, origin -8000 is right for both.
- **3. The disagreeing nodes (VERIFIED, `cls.py`, `map.py`, `grp.py`, `edge.py`).** 10,852 nodes (16.6 %) have
  trailer mid more than 20 m above FHD mid; only 136-161 nodes are lower by more than 20 m.
  - Not no-data, not flat, not sea: FHD range in those nodes is normal (median 52 m against 70 m), trailer range 42 m;
    trailer min minus FHD min p10/p50/p90 = 17 / 177 / 523 m (offset is a smooth shift, not a flat plane).
  - Spatially: 3 large connected regions hold 10,678 of 10,852 nodes (4,614 / 3,797 / 2,267 nodes, 18 / 15 / 9 km2;
    bboxes x -7500..-500 y -3250..4938; x -4812..4000 y -7375..-1688; x 250..6000 y 4125..6750), median offsets
    126 / 182 / 328 m. By Chebyshev ring from the centre: 0-32 nodes 1.8 % bad, 32-64 19 %, 64-96 27 %, 96-112 19 %, 112-120 4 %,
    120-128 0.1 % (so the outer rim and the very centre agree). No quadrant effect (11-21 %).
  - The offset grades smoothly into the agreeing zone: |d jump| between neighbouring nodes p50/p90/p99 = 1.8 / 13.5 / 57 m;
    inside the shifted zones the node-to-node roughness of the trailer (20.3 m) equals that of FHD (20.8 m). It is a smooth
    second surface above FHD, not noise or a step.
  - Layer correlation (`layer_mask` groups, TerrainMaterialBank order): groups 7 (`ICE_CliffThick`) and 8 (`ICE_Moraine`) lie
    for 90.7 % / 99.1 % of their L6 texels inside shifted nodes; nodes with any ice texel (4,795) are shifted in 90 %
    (median +187 m) against 10.7 % of ice-free nodes. Every shifted node has group 4 (`SNOW_POWDER`)
    but that is just the dominant group (82 % of shifted texels). So the shifted zones are largely glacier/ice areas
    (INFERRED; only 50 % of the shifted nodes carry an ice group themselves).
- **4. Vegetation bases (VERIFIED, `trees.py`, `points_AlaskaTUX.bin`).** Points over the whole square: z agrees
  with FHD (|z-FHD| median 0.90 m) and lies inside the trailer range (+-3 m) for 100.0 %. But only 1,405 points (199 nodes of the 10,852)
  fall in shifted nodes, and none in nodes where trailer min exceeds FHD max by more than 50 m: the shifted zones are
  vegetation-free (glaciers), so the vegetation cannot say which surface is right. In the 199 nodes with points both agree (small offsets).
- **Clamp reproduction (VERIFIED, `cls.py`).** Clamping FHD to the trailer at sample level (exact float bounds) moves 10.94 M
  samples (17.1 %) by more than 0.1 m: 10.66 M raised, 0.28 M lowered, mean 194 m, max 893.29 m. This matches the importer's max
  (893 m) and total displacement (17.3 M x 121 m = 2.09e9 against 10.9 M x 194 m = 2.12e9); the importer's 27 % evidently counts
  ~6 M more sub-0.1 m moves (u16 step 0.097 m; not investigated).

**Conclusion and what remains.** Ruled out (VERIFIED): scale/offset, axis swap/flip/shift, no-data, sea plane, flat tiles. What the
trailer encodes in the shifted zones is not established: either the terrain surface the game draws there is 50-500 m above
FloorHeightData (a second heightfield for glaciers or a patched terrain bake; `world-coords.md` near line 428 says FHD is a single copy across the base and patch forges),
or the trailer carries a different quantity there. Which surface physics uses is UNVERIFIED. Recommendation: keep
`--trailer-clamp` off for AlaskaTUX (a clamp would raise the glacier areas onto the trailer surface by up to 893 m and make 62.5 m
steps); a per-region linear map does not help since a = 1, b = 0 already holds where the two agree. A fix needs evidence from the
rendered surface (e.g. a capture of the original through DXVK/MoltenVK over one shifted zone, or the sled/skier z trace there).

## 4. World coordinates

The relative placement is VERIFIED (§2). For a world square of side E with origin (X0, Y0):

```
T_L = E / 2^L                      tile side at level L
s_L = T_L / 128                    texel size
tile (L,x,y) own area = [X0 + x·T_L, X0 + (x+1)·T_L) × [Y0 + y·T_L, Y0 + (y+1)·T_L)
raw texel (j, k) centre = (X0 + (128x + j − 1.5)·s_L,  Y0 + (128y + k − 1.5)·s_L)   j, k ∈ 0..131 (tile texel incl. border)
```

Resolved in P2-09, see `world-coords.md` (Studio source: `world-coords.md`) (VERIFIED there, all three regions):
**E = 16000 m, X0 = Y0 = −8000** (the square [−8000, 8000)² centred on 0, ±1 m). Tile x / texel column
grows with world +X, tile y / texel row grows with world +Y, with no transpose. So s_L = 125/2^L m
(L5 3.906 m, L8 0.488 m), and a level-L stitched-image pixel (px, py) has its centre at
(−8000 + (px + 0.5)·s_L, −8000 + (py + 0.5)·s_L). Image row 0 is world y = −8000, so flip vertically for a
+Y-up view. The header f32 at 0x14 (6800) is the height scale: `height_min/max` × 6800 = metres, offset 0.
Evidence: the trailer-vs-FloorHeightData fit, the colour-vs-slope correlation and the entity overlay check
(world-coords.md §4–§7). Whether world +Y is north is still UNVERIFIED.

## 5. lin0 vs lin1

- **lin0 is a subset of lin1, not a separate level of detail.** In all three regions lin0 has 315
  nodes, each byte-identical to the same node in lin1. VERIFIED: `tools/lab/P2-06/lin0_set.py` →
  `lin0 present 315 byte-identical to lin1 315 different 0` for Alpes, AlaskaTUX and Japan.
- **The index set is the same in all regions** (`same index set across regions: True`). Its exact
  rule, VERIFIED for all three:
  - levels 0, 1 and 4 in full (1 + 4 + 256);
  - plus the 3 × 3 block x, y ∈ {W/2 − 1, W/2, W/2 + 1}, W = 2^L, at each level 2, 3, 5, 6, 7, 8 (6 × 9).

  Per-level counts: `[1, 4, 9, 9, 256, 9, 9, 9, 9]`. The 3 × 3 blocks nest: each lies inside the
  children of the one above it, centred on cell W/2.
- **Why lin0 exists** (UNVERIFIED, inference): it looks like a fixed always-resident or boot set. It
  is a whole-map coarse base (level 4, 16 × 16 tiles) plus full-detail coverage of a viewer at the
  world centre with one ring of neighbours, the set a quadtree streamer would load first.
  Levels 2 and 3 are only partly present even though they are tiny, which argues against
  "lin0 = the coarse pyramid". Confirming this needs the game observed while loading.
