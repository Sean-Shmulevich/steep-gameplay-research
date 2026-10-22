<!-- Imported authored research, not game payloads. -->
> Source: Studio `steep-wasm`, commit `1344bca03985eb1540236fb2ecd3cbbe8ecdcf14`, `docs/specs/formats/floor-height.md`.
> Evidence labels and validation counts below are the source agents' reports;
> the asset-level checks were not rerun for this import. Local source links were
> converted to plain references; their files may not be included here. Historical
> superseded sections remain labeled. Studio-authored runtime policies are not
> evidence of original game behavior.

# FloorHeightData (`0x92ada771`): terrain height grid (P4-04)

This is a clean-room spec, written only from the owner's `DataPC*.forge` files (read-only). The
machine-readable layout is `floor-height.ksy` (Studio source: `floor-height.ksy`). It builds on the following:
- the P2-03 description in `types.md` (Studio source: `types.md`) §6, entry `0x92ada771`;
- the world placement in `world-coords.md` (Studio source: `world-coords.md`) §1–§2;
- the entity fit in `world-entities.md` (Studio source: `world-entities.md`) §10;
- patch layering in `forge.md` (Studio source: `forge.md`) §6.

Evidence tags:
- **VERIFIED**: a command was run on Steep data in P4-04 and its output is quoted.
- **UNVERIFIED**: an inference, or a claim quoted from an earlier spec that was not re-run here.

Lab scripts are in `tools/lab/P4-04/`. They only read data and write under `$STEEP_DATA/P4-04/`.
Run them from the repo root after `source tools/env.sh`, with `PY=$STEEP_DATA/P0-05/venv/bin/python`.

| Script | Purpose |
|---|---|
| `fhd_extract.py` | finds every `0x92ada771` row in the P2-03 census (`$STEEP_DATA/P2-03/lab/records.tsv`, all 27 forges) and writes each record's `data` to `$STEEP_DATA/P4-04/rec/<forge>__<id>.bin` |
| `fhd_decode.py check` / `stats` | decoder written from this spec. `check` compares it with the P2-09 oracle caches. `stats` prints the §5 numbers |
| `ksy_blocks_check.py` | compiles the `.ksy`, reads every typed block of every copy and compares it with numpy (run with `tools/.venv/bin/python` of the main checkout, which has kaitaistruct) |
| `patches.py roots` / `scan` / `whiteroom` | patch layers and references (§4), the WhiteRoom copy (§6) |
| `placement.py <Map> <cps\|veg>` | sample-position convention (§3.2) |
| `japan_fit.py Japan Alpes` / `split <Map> 1000` | Japan's weaker fit (§7) |

## 1. Record

Each copy is one record per map. Each one is its own entry, named `FloorHeightData_0X<id>`, and is
the only record in that entry (VERIFIED: census rows with `rec 0`, `nrec 1` in
`$STEEP_DATA/P2-03/lab/records.tsv`, see §4). The record holds the usual object data `{u64 id, u32 type, u8 1, …}`
(types.md §1.2). Offsets below are into that data.

| Total size | Layout |
|---|---|
| 21 + 8·n + 50 bytes | head (21) · n blocks (8 each) · tail (50). Every byte is covered. |

### 1.1 Head (21 bytes)

| Off | Type | Field | Value |
|---|---|---|---|
| 0x00 | u64 | object id | the record id |
| 0x08 | u32 | type id | `0x92ada771` |
| 0x0c | u8 | lead | 1 |
| 0x0d | u32 | unknown | 0 in all 4 copies |
| 0x11 | u32 | n = block count | 4,194,304 (2048²) in the three maps, 0 in WhiteRoom |

### 1.2 Blocks (n × 8 bytes)

Each block holds a 4 × 4 group of samples:

| Off | Type | Field |
|---|---|---|
| +0 | u16 | lo: raw value for selector 0 |
| +2 | u16 | hi: raw value for selector 3 |
| +4 | u32 | sel: 16 × 2-bit selectors. Selector i (bits 2i, 2i+1) is block-local sample (y = i div 4, x = i mod 4) |

- Blocks are row-major: block k = R · (width/4) + C, so there are 2048 blocks per row.
- Sample (r, c) of the full grid is in block (R, C) = (r div 4, c div 4) at selector i = 4·(r mod 4) + (c mod 4).

### 1.3 Tail (50 bytes, offset from the tail start)

| Off | Type | Field | Alpes | Alaska | Japan | WhiteRoom |
|---|---|---|---|---|---|---|
| +0 | u32 | unknown | 0 | 0 | 0 | 0 |
| +4 | f32 | scale (m per raw unit) | 0.09449737 | 0.09709114 | 0.07502320 | 0 |
| +8 | f32 | offset (m at raw 0) | 115.98743 | 310.76364 | 0.0 | 0 |
| +12 | f32 | origin x (world x of column 0) | −8192 | −8192 | −8192 | 0 |
| +16 | f32 | origin y (world y of row 0) | −8192 | −8192 | −8192 | 0 |
| +20 | f32 | unknown | −6000 | −6000 | −6000 | 0 |
| +24 | u32 | unknown | 0 | 0 | 0 | 0 |
| +28 | u32 | width (samples per row) | 8192 | 8192 | 8192 | 0 |
| +32 | u32 | height (rows) | 8192 | 8192 | 8192 | 0 |
| +36 | u8 | unknown (has-grid flag? UNVERIFIED) | 1 | 1 | 1 | 0 |
| +37 | u8 | block size (samples per block side) | 4 | 4 | 4 | 4 |
| +38 | 3 B | zero | 0 | 0 | 0 | 0 |
| +41 | f32 | spacing (m between samples) | 2.0 | 2.0 | 2.0 | 2.0 |
| +45 | u8 | unknown | 1 | 1 | 1 | 1 |
| +46 | u8 | unknown | 1 | 1 | 1 | 1 |
| +47 | 3 B | zero (end of data) | 0 | 0 | 0 | 0 |

- VERIFIED: hexdumps of the 4 extracted copies (`xxd` of the first 21 and last 50 bytes), and the
  `ksy-run` output in §8. From the same hexdumps: the three map tails are byte-identical except for
  scale and offset, and in all 4 copies (width/4)·(height/4) = n (`fhd_decode.py` asserts it).
- The −6000 at +20 is not used by the decode. It could be a height floor or a minimum, but that is
  UNVERIFIED.

## 2. Decode

For block (R, C) and selector i:

```
s    = (sel >> 2i) & 3
raw  = lo + (hi − lo) · s / 3              (not rounded to an integer)
h    = raw · scale + offset                (metres, z up)
row  r = 4R + i div 4                      column c = 4C + i mod 4
```

- **Bit-exact order.** The P2-09 caches are float32, computed in this order:
  `t = f32(hi − lo) · f32(s); t = t / 3; t = t + lo; h = t · scale + offset`.
  Evaluating the same formula in float64 differs from them by at most 0.000488 m. VERIFIED by
  `fhd_decode.py check`:
  `Alpes shape=(8192, 8192) … max|d|=0.0 array_equal=True (float64-order decode: max|d|=0.000488)`.
  An engine may use either order. Only the lab comparison needs the float32 order.
- **lo ≤ hi.** In all 12,582,912 map blocks, lo ≤ hi: `lo>hi 0` for each map. VERIFIED, `fhd_decode.py stats`.
  The formula does not depend on this.
- **Selectors.** VERIFIED (`fhd_decode.py stats`). All four selector values occur, e.g. Alpes `s0 18878907 s1 16689072 s2 16522697 s3 15018188`.
  Blocks with lo = hi still carry non-zero selectors (Alpes `[3692699, 1455, 59039, 157175]`).
  Those selectors have no effect.
- **Raw range.** VERIFIED (`fhd_decode.py stats`): raw values span the full u16 range, Alpes
  `all 0..65534`, Alaska and Japan `all 0..65535`. So scale normalises each map's height range to
  16 bits (inference, UNVERIFIED).

## 3. Placement in world coordinates

### 3.1 Grid and axes

Sample (r, c) lies at

```
x = origin_x + spacing · c = −8192 + 2c        y = origin_y + spacing · r = −8192 + 2r
```

- Row = world y and column = world x, with no flip and no transpose. This frame is shared with the
  128 m cell grid and with entity positions (z up).
  - VERIFIED in P2-03 / P2-09: world-coords.md §1, CellPointSet median |z−h| 0.51 m (Alpes).
  - VERIFIED in P2-09: world-entities.md §10, where axis-swapped and Y-up alternatives are off by
    hundreds of metres.
  - Not re-run in P4-04 beyond §3.2, which uses the same frame.
- The grid covers the 16,384 m square [−8192, 8192) (VERIFIED: tail origin −8192, 8192 samples,
  spacing 2.0, §1.3), the same square as the WorldRoot cell grid (128 × 128 cells, 128 m, origin −8192;
  types.md §6 WorldRoot, VERIFIED in P2-03, not re-run here).
- The terrain quadtree (`.tbf`) covers only [−8000, 8000)² (world-coords.md §2). That leaves a
  192 m margin on every side (arithmetic from the two extents; §5.1).

### 3.2 Sample-position convention: corner, not centre

Samples sit **on** the grid points (−8192 + 2c, −8192 + 2r). They are not at cell centres (+1 m),
and heights between samples are bilinear. VERIFIED, `$PY tools/lab/P4-04/placement.py <Map> <cps|veg>`.

Method:
- Bilinear height at independent world points:
  - CellPointSet positions, 400 seeded records per map;
  - 300k seeded vegetation and rock entity rows from `$STEEP_DATA/P2-09/entities_<Map>.csv`,
    excluding rows at (0,0,0) and rows with |x| or |y| ≥ 8000.
- Points with |z − h_corner| ≥ 20 m (buildings, lifts, gross outliers) are dropped once, so every
  hypothesis is scored on the same set.
- Each set is scored at the corner and centre conventions, and over a 13 × 13 scan of shifts of
  ±1.5 m in 0.25 m steps.
- A gradient regression estimates the residual shift.

| Map / points (n used / n) | median \|z−h\| corner | centre (+1,+1) | scan argmin | regression (dx, dy) m |
|---|---|---|---|---|
| Alpes CellPointSet (16200 / 16714) | 0.492 | 0.848 | (+0.25, −0.25): 0.464 | −0.006, −0.016 |
| Alpes vegetation (297965) | 0.528 | 0.724 | (+0.25, 0): 0.521 | +0.092, +0.011 |
| Alaska CellPointSet (13618) | 0.530 | 0.747 | (−0.25, +0.25): 0.501 | +0.029, +0.058 |
| Alaska vegetation (298273) | 0.695 | 0.936 | (+0.25, +0.25): 0.680 | +0.084, +0.085 |
| Japan vegetation (200592 / 300000) | 2.180 | 2.340 | (0, 0): 2.180 | +0.012, +0.008 |
| Japan CellPointSet (1241) | 3.533 | 3.517 | (+0.25, +1.00): 3.326 | noisy (n = 555) |

- For Alpes and Alaska the argmin falls within one scan step (0.25 m) of the corner position, and the
  regression puts the shift below 0.1 m. Japan vegetation agrees (argmin exactly at the corner).
  Japan's CellPointSet set is too small and noisy to separate corner from centre (it slightly
  prefers centre); its points are dominated by the north mismatch of §7.
- Nearest-sample lookup is worse than bilinear (Alpes vegetation 0.699 vs 0.528).
- Re-run by the coordinator:
  `placement.py Alpes cps` → `ARGMIN dx=+0.25 dy=-0.25 med|dz|=0.464 (corner 0,0: 0.492; centre +1,+1: 0.848)`.
- Consequence (derived from §3.1, UNVERIFIED as engine behaviour): the last column (c = 8191) is x = 8190. The grid does not reach x = 8192. To sample a
  point in [8190, 8192), clamp to the last column.

## 4. Patch layers: which copy wins

There is exactly one FloorHeightData copy per map, in the base map forge. No patch forge and no
non-map forge carries one, so nothing overrides it.

- **Census.** VERIFIED, `$PY tools/lab/P4-04/patches.py roots` → `census 0x92ada771 rows: 4`. The
  4 rows are:

  | Forge | Record id | Data size |
  |---|---|---|
  | `DataPC_STP_Alpes` | `7a954cace2` | 33,554,503 |
  | `DataPC_STP_Alaska` | `10af88ff48e` | 33,554,503 |
  | `DataPC_STP_Japan` | `d6ce6dae1f` | 33,554,503 |
  | `DataPC_STP_WhiteRoom` | `d8d3d913ec` | 71 |

- **References.** Every WorldRoot (`0xfbb63e47`) copy references its map's base FloorHeightData by
  the u64 id. That holds in the base, `_patch_01` and `_patch_02`. VERIFIED, `patches.py roots`:
  - `ROOT DataPC_STP_Alpes_patch_02 rec 7a954c6bd0 … fhd-id hits: Alpes@0x18e765`;
  - Alaska: base `@0x1522ca`, both patches `@0x1523c0`;
  - Japan `@0x13916e`;
  - WhiteRoom `@0xafc`.
- **No other ids.** A byte scan of all 27 forges for the 4 ids finds no reference outside the
  WorldRoot copies and the records themselves. VERIFIED, `patches.py scan` →
  `$STEEP_DATA/P4-04/scan_fhd_ids.txt`; all 15 non-map forges report `hits 0`. Coverage gap: every
  forge reports `undecodable 2`, i.e. 54 entries were not scanned. By the scanning agent's listing
  these are the GlobalMetaFile (first) and PrefetchingFileInfos (last) entries of each forge, which
  are index data, not records (UNVERIFIED, not re-listed by the coordinator). The census itself
  (`census 0x92ada771 rows: 4`) does not depend on this scan.
- **Rule.** Resolve the WorldRoot by the forge.md §6 rule (highest layer wins). Then follow its
  FloorHeightData id, which always resolves to the base-forge record.

## 5. Heights, no-data and the margin

### 5.1 No-data and the margin

There is no explicit no-data flag. What the 192 m margin holds:

- **South margin (y < −8000), all-zero blocks.** In all three maps, the first 49,176 blocks in
  storage order (data bytes 21…393,429, end-exclusive) are entirely zero (lo = hi = sel = 0). That is block rows 0–23 (the whole south
  margin) plus blocks 0–23 of block row 24 (x < −8000 for y −8000…−7994). These samples decode to
  h = offset: 115.99 m for Alpes, 310.76 m for Alaska and 0 m for Japan. VERIFIED, `fhd_decode.py stats`:
  `fully zero blocks (lo=hi=sel=0): 49176; leading run in storage order: 49176 blocks = data bytes
  21..393429 (end-exclusive)` (Alpes, Alaska; Japan has the same leading run and 72,209 fully zero
  blocks in total) and `samples in lo==hi==0 blocks: 786816; inside: 0, ring: 786816` (Alpes).
- **Not an extraction artefact.** The P2-03 block reader has no zero-fill path: every chunk is
  either stored or zstd-decoded from the file (VERIFIED, `$STEEP_DATA/P2-03/lab/blocks.py`). The zero
  run ends at data byte 393,429, which is not chunk-aligned. Why the authoring tool wrote these
  zeros is UNVERIFIED.
- **Other margins.** The rest of the margin holds values extended from the edge. For example, Alpes
  row y = 0 is constant from x = 7992 outward (world-coords.md §2, VERIFIED in P2-09, not re-run here).
- **Raw 0 is not a no-data marker on its own.**
  - Japan has offset 0 and 24,862 more lo = hi = 0 blocks inside the map (23,033 of them also have
    sel = 0). VERIFIED, `fhd_decode.py stats`: `lo==hi==0 samples inside: 397792, extent world x
    -7728..-226, y -7992..2846; interior lo==hi==0 blocks 24862`. These are probably sea level
    (UNVERIFIED).
  - Japan also has 78,888 raw-0 samples in ordinary blocks with lo = 0; Alpes has 8 and Alaska 10.
  - Recommendation (not a data claim): an engine should treat every sample as a height and clamp lookups to the quadtree square
    [−8000, 8000)² when it needs real terrain.

### 5.2 Per-region height statistics

Heights are in metres over the 8192 × 8192 samples. VERIFIED by
`$PY tools/lab/P4-04/fhd_decode.py stats` (exit 0). Row sets:
- **all**: every sample;
- **raw ≠ 0**: samples whose raw value is not 0;
- **inner raw ≠ 0**: the same, limited to |x|, |y| ≤ 8000.

| Region | Set | n | Min | p1 | Median | p99 | Max |
|---|---|--:|--:|--:|--:|--:|--:|
| Alpes | all | 67,108,864 | 115.99 | 115.99 | 2616.48 | 5840.64 | 6308.78 |
| Alpes | raw ≠ 0 | 66,322,040 | 116.08 | 340.61 | 2636.23 | 5844.32 | 6308.78 |
| Alpes | inner raw ≠ 0 | 64,015,993 | 116.08 | 336.45 | 2674.13 | 5854.81 | 6308.78 |
| AlaskaTUX | all | 67,108,864 | 310.76 | 310.76 | 2246.37 | 5916.39 | 6673.63 |
| AlaskaTUX | raw ≠ 0 | 66,322,038 | 311.15 | 348.92 | 2275.82 | 5921.37 | 6673.63 |
| AlaskaTUX | inner raw ≠ 0 | 64,015,991 | 311.15 | 348.92 | 2344.43 | 5936.03 | 6673.63 |
| Japan | all | 67,108,864 | 0.00 | 0.00 | 1272.52 | 4425.09 | 4916.65 |
| Japan | raw ≠ 0 | 65,845,368 | 0.03 | 22.06 | 1306.83 | 4435.08 | 4916.65 |
| Japan | inner raw ≠ 0 | 63,539,321 | 0.03 | 21.16 | 1303.43 | 4283.15 | 4916.65 |

Block counts:

| Region | lo < hi | lo = hi | lo > hi | lo = hi = 0 |
|---|--:|--:|--:|--:|
| Alpes | 3,949,906 | 244,398 | 0 | 49,176 |
| AlaskaTUX | 3,404,138 | 790,166 | 0 | 49,176 |
| Japan | 3,975,004 | 219,300 | 0 | 74,038 |

## 6. WhiteRoom copy

The WhiteRoom record has no grid. VERIFIED (`xxd`, `patches.py whiteroom`):
- It is 71 bytes: the 21-byte head with n = 0, then the 50-byte tail.
- In the tail, scale, offset, origin, width, height, +20 and +36 are all 0. Only the format constants
  are set: block size 4, spacing 2.0, and +45 = +46 = 1.
- Its WorldRoot (base and both patches) describes a 1024 m map: `cell 128 m origin (-512,-512) side 8 levels 4`.
- That WorldRoot references only this empty record. The id scan found no other height source
  among FloorHeightData ids. Other height-bearing types were not searched.
- Recommendation: an engine should treat a record with n = 0 (or width = 0) as "no height field". For WhiteRoom it
  should fall back to collision or meshes.

## 7. Japan's weaker fit (cause open; registration ruled out in P5-27)

Japan fits placed objects much worse than Alpes and Alaska (VERIFIED in P2-09, not re-run here):
- world-coords.md §4: `.tbf` L7 median |d| 4.58 m, against 0.79 m for Alpes;
- world-entities.md §10: 29.1 % of entities within 2 m.

P4-04 narrowed this down to a regional disagreement in the north. VERIFIED,
`$PY tools/lab/P4-04/japan_fit.py Japan Alpes > $STEEP_DATA/P4-04/japan_fit.txt` and
`japan_fit.py split Japan 1000 > $STEEP_DATA/P4-04/japan_split.txt`:

- **The south fits.** For y < +1000: `Japan south y<1000: n=152048 med|dz| 1.73 within 2 m 54.2%
  within 20 m 95.3%`. That is close to Alpes and Alaska.
- **The north does not.** For y ≥ +1000: `Japan north y>=1000: n=150191 med|dz| 36.28 within 2 m 8.9%`.
  - The per-1 km tile median of signed dz is ±10…±230 m from y ≈ +2000 upward, with both signs.
  - The north grid itself looks like normal terrain: `median |d2h/dx2| 1.000 m` in the north against
    0.825 m in the south.
- **Ruled out:**
  - **Wrong scale or offset.** A robust affine fit of z against raw gives
    `a=0.0750008 b=+0.408 (tail scale 0.0750232 offset 0.000) … med|res| 5.553 (tail: 5.606)`.
  - **Misregistration.** A global shift scan of ±16 m finds its best at (0, 0). A north-only scan of
    ±64 m improves the median only to 27.4 m at (+4, −28).
  - **Clipping.** Raw 65535 occurs in 0.0000 % of samples, and the bad points have raw 10000–30000.
  - **A different tail layout.** The Japan tail differs from Alpes and Alaska only in scale and offset.
- **Likely cause (UNVERIFIED).** Japan's FloorHeightData north of y ≈ +1000 is out of date relative
  to the terrain that the objects were placed on, which is also the rendered `.tbf` terrain
  (world-coords.md §5.1 locates its tbf-vs-FHD mismatch in the same region).
- **Advice (recommendation).** Until this is resolved, an engine should prefer the `.tbf` height range or collision
  meshes over FloorHeightData for Japan's north.
- **P5-27 follow-up (negative result).** No registration rule fixes it: tail scale/offset, bit
  interpretation, horizontal origin or shift, per-tile shifts and rotations and flips, tile reordering,
  and smooth vertical datums are all ruled out. CellPointSet, placed collision, placed entities and the
  `.tbf` trailer ranges agree with each other in the north, and FHD alone differs. The mismatch is in
  the base pack. The §2–§3 rule stays unchanged for all maps. Residual tables and evidence:
  `world-coords.md` (Studio source: `world-coords.md`) §8.

## 8. Checks (P4-04 Accept)

All checks were VERIFIED on 2026-10-11.

- **Kaitai parse.** `tools/sv fmt-lab ksy-run docs/specs/formats/floor-height.ksy $STEEP_DATA/P4-04/rec/<copy>.bin`
  exits 0 for all 4 copies. Example output:
  `{"head":{"id":526490840290,"type_id":2460854129,"lead":1,"unk_0d":0,"num_blocks":4194304},"grid":{},"tail":{…` (Alpes).
  - The block grid is a parse instance, so the default output stays small.
  - `--instances` expands it. On Japan this took 15 s and wrote a 348 MB JSON to
    `$STEEP_DATA/P4-04/out/` (2.8 GB RSS).
  - `tools/.venv/bin/python tools/lab/P4-04/ksy_blocks_check.py` (main checkout venv) compares all typed blocks of all 4 copies with numpy and prints
    `KSY-BLOCKS PASS`.
- **Bit-exact decode.** `$PY tools/lab/P4-04/fhd_decode.py check` → `max|d|=0.0 array_equal=True` for
  Alpes, AlaskaTUX and Japan, then `CHECK PASS`. The oracle is `$STEEP_DATA/P2-09/cache/fhd_<Region>.npy`,
  written by `tools/lab/P2-09/coords/fhd_cache.py`.
- **Statistics.** The §5.2 table.

## 9. Open questions

- Meaning of the head u32 at 0x0d and of tail +0, +20 (−6000), +24, +36, +45 and +46.
- The cause of Japan's north mismatch (§7). P5-27 ruled out every registration and datum explanation
  (world-coords.md §8); a stale terrain revision is the remaining inference (UNVERIFIED).
- Why the south margin is stored as zeros while the other margins are edge-extended (§5.1).
