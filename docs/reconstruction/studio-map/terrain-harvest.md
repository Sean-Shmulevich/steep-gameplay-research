<!-- Imported authored research, not game payloads. -->
> Source: Studio `steep-wasm`, commit `1344bca03985eb1540236fb2ecd3cbbe8ecdcf14`, `docs/specs/world/terrain-harvest.md`.
> Evidence labels and validation counts below are the source agents' reports;
> the asset-level checks were not rerun for this import. Local source links were
> converted to plain references; their files may not be included here. Historical
> superseded sections remain labeled. Studio-authored runtime policies are not
> evidence of original game behavior.

# Harvested terrain heights (T-09)

The game uploads every decoded `.tbf` height tile to the GPU. The owner's DXMT texture logger dumps
those uploads, which gives Summit the game's exact heights wherever the owner has played (CLAUDE.md
rule 3: the GPU stream through our own translation layer; no executable code examined). The
contact's map export is not used (its heights come from an emulated decoder).

Tags: VERIFIED means a command was run on the owner's captures here and its output is quoted or kept
under `$STEEP_DATA/T-09/`; UNVERIFIED means a lead or an inference.

Sources: `$STEEP_DATA/captures/t-06/handoff-mont-fleuri-20261014` (395 dumps) and
`handoff-snowpark-empereur-20261014` (1,360 dumps), Alps, with their `tile_positions.json` links.
Code: `summit-import harvest` (store), `summit-import ground-harvest` (stage),
docs/import.md (Studio source: `../../import.md`). Lab: `tools/lab/T-09/` (`trailers.py`, `quant.py`, `overlap.py`, `levels.py`, `check.py`, `edgecheck.py`; run with `$STEEP_DATA/shared/lab-venv/bin/python -I`).

## 1. Tile data (VERIFIED)

- A dump is 132 × 132 little-endian float32, row-major, `a[j][i]` with row j = +y and column i = +x.
  Metres = value · 6800 at every level (collision-readback.md (Studio source: `collision-readback.md`) §1).
- Geometry: T = 16000 / 2^L, origin (−8000 + col·T, −8000 + row·T), sample (i, j) at
  origin + ((i − 2)·T/128, (j − 2)·T/128). Samples 2..130 span the tile square.
- Orientation and overlap: over all neighbour pairs among the 1,541 unique tiles,
  `a[:, 128:132] == b[:, 0:4]` for the +x neighbour (1,273 / 1,273 pairs exact) and
  `a[128:132, :] == b[0:4, :]` for the +y neighbour (1,285 / 1,285 exact). The transposed and the
  flipped readings agree on 1 and 2 pairs only (max differences 3,676 m and 4,311 m).
- Quantisation: every value of a level-L tile is an exact multiple of 2^−(12+L) (all levels 0..8
  in both handoffs; a coarser step 2^−(10+L) or 2^−(11+L) does not fit). That is 6.6 mm at L8 and
  0.104 m at L4.
- Trailer: the lin1 `.tbf` node of (L, col, row) holds normalised min/max (trailer f32 0/1,
  `formats/tbf.md` §3.2). The tile's min/max over all 132² samples matches them within half a
  quantisation step: |Δ| ≤ 0.0032 m at L8, 0.0515 m at L4 (0.5 · 6800 · 2^−(12+L)), for all 1,755
  dumps; none matches exactly, so the trailer is taken before the quantisation. Interior-only
  ranges (samples 2..130) miss by up to 193 m. The harvest tool rejects a tile outside that bound.
- Levels: L4 at coincident sample positions equals L8 to within the L4 step (35,640 points, mean
  |Δ| 0.026 m, max 0.052 m): the coarse levels are decimations of the same heights.

## 2. Linking a dump to its tile

- **Handoffs (used):** `tile_positions.json` maps each dump to (size, col, row), from the owner's
  `match_tiles.py`. All 1,541 tiles pass the trailer check (VERIFIED, `$STEEP_DATA/T-09/harvest.out`:
  stored 1,541, rejected 0, conflicts 0; overlap check 2,558 / 2,558 pairs exact).
- **Slot-9 sessions (future):** each terrain draw's VS cbuffer slot 9 holds the tile origin (f32 x, y
  at bytes 0..8), T (f32 at byte 20) and the atlas slot texel offset + 2 (i32 x, y at bytes 24..32)
  (C-06 §1, VERIFIED on the readback draws). The texlog's atlas copy/update rows would give
  upload → slot. No texlog we hold has those rows (C-06 §1), so the row layout the tool expects
  (event `update`/`copy` on the 7920² R32_FLOAT atlas, `left`/`top` = slot, `dump` = upload) is
  UNVERIFIED; the path is tested on a synthetic fixture only.

## 3. Coverage (Alps, VERIFIED, `index.json` / `ground_harvest.json`)

| level | tile | spacing | tiles stored / of level | square area exact (finest) | feather band |
|---|---|---|---|---|---|
| L4 | 1000 m | 7.81 m | 122 / 256 (47.7 %) | 24.94 % | 4.02 % |
| L5 | 500 m | 3.91 m | 220 / 1,024 (21.5 %) | 11.81 % | 1.12 % |
| L6 | 250 m | 1.95 m | 402 / 4,096 (9.8 %) | 7.59 % | 1.73 % |
| L7 | 125 m | 0.98 m | 278 / 16,384 (1.7 %) | 0.73 % | 0.52 % |
| L8 | 62.5 m | 0.49 m | 446 / 65,536 (0.68 %) | 0.68 % | 0.41 % |
| all | | | | 45.76 % | 7.81 % |

L0..L3 are stored too (1, 4, 16, 52 tiles) but not used: they are coarser than the collision levels.
AlaskaTUX and Japan: no captures (0 %).

Lead (contact, UNVERIFIED): the game keeps all 256 L4 tiles loaded and collides with them map-wide,
with L8 only within ~100–200 m of the rider. The captures fit that only in part: 122 of 256 L4
tiles over two sessions. Either the dump caught only part of the resident set or the lead
overstates it.

## 4. How close the built ground is (VERIFIED, `tools/lab/T-09/check.py`, `$STEEP_DATA/T-09/check.out`)

At the 2 m nodes the stage marks exact (29,285,974 nodes), the raster equals the bilinear tile height
to the u16 quantisation: max 0.047 m (half the 0.0945 m step), 0 before quantisation.

At the captured samples themselves (samples 2..130 of every stored tile, bilinear in the raster):

| level | ground_harvest.r16: mean / p50 / p99 / max | ground_fix.r16 (before): mean / p50 / p99 / max |
|---|---|---|
| L4 | 0.152 / 0.069 / 1.23 / 11.2 m | 1.247 / 0.534 / 10.5 / 68.4 m |
| L5 | 0.113 / 0.047 / 1.03 / 11.2 m | 0.973 / 0.501 / 7.59 / 43.8 m |
| L6 | 0.099 / 0.040 / 0.96 / 11.2 m | 1.938 / 0.558 / 49.6 / 68.5 m |
| L7 | 0.095 / 0.031 / 1.05 / 8.3 m | 1.660 / 0.610 / 25.8 / 44.3 m |
| L8 | 0.089 / 0.029 / 0.98 / 7.9 m | 2.684 / 0.703 / 31.0 / 44.5 m |

The rest at the samples is the 2 m grid: a 0.49 m (L8) sample between nodes, or a 7.8 m (L4)
vertex peak, cannot be held by a bilinear 2 m raster, plus ±0.047 m quantisation. Exact heights at
the samples need the tiles at their own resolution (follow-up). For reference, each coarser level alone (bilinear in its tiles) against the L8 samples: L4 0.50, L5 0.21, L6 0.077, L7 0.024 m mean; ground_fix 2.68 m (`tools/lab/T-09/levels.py`, `$STEEP_DATA/T-09/levels.out`).

Seams: all 2,442 pairs of stored same-level neighbours (L4..L8) agree exactly on their 4 shared
sample rows; bilinear on either side of a seam reads the same samples, so the built surface has no
seam step (0.000 m).

## 5. The coverage edge (VERIFIED, `ground_harvest.json`, `tools/lab/T-09/edgecheck.py`)

The surface is continuous at a coverage edge: the first ring outside carries the full correction of
its nearest covered node, and the rest blends to the base. Per level, |D(out) − D(in)| over the
covered/band neighbour pairs (D = harvest − base before that level), against a hard switch (|D(in)|):

| level | pairs' jump p99 / max | hard switch p99 / max |
|---|---|---|
| L4 (vs ground_fix) | 0.53 / 2.67 m | 9.70 / 33.3 m |
| L5 | 0.15 / 1.45 m | 2.74 / 10.9 m |
| L6 | 0.08 / 2.52 m | 1.44 / 8.1 m |
| L7 | 0.016 / 0.73 m | 0.68 / 2.9 m |
| L8 | 0.009 / 1.52 m | 0.39 / 1.5 m |

The maxima sit at inside corners, where a band node has two covered neighbours whose corrections
differ (cliffs). `edgecheck.py` measures the surface itself across the final edges (inside the
square, 170,508 pairs), as the second difference |Δh_edge − (Δh_in + Δh_out)/2|: built 0.33 mean /
3.59 p99 m; ground_fix itself at the same pairs 1.40 / 7.70 m; a hard switch 1.73 / 11.6 m; the
harvested surface inside 0.15 / 1.28 m. Above ground_fix's own roughness at the pair the blend adds
0.043 m mean, 0.95 m p99, 8.1 m max. So the 0.5 m target holds for the value (no step) and at the
99th percentile of the inter-level edges, not for every kink at the L4 → ground_fix edge, where
ground_fix itself is rougher than 0.5 m at node scale. Whole-map L4 coverage removes that edge.

## 6. Sim and park gate (VERIFIED, `$STEEP_DATA/T-09/park_*.out`)

- Switch off: `c05_park_gate` passes (5 parks, p95 ≤ 0.04 m, 0 ticks under the drawn ground); 190
  replays match (`sv replay rerecord --check`).
- Switch on (`t09_park_gate_harvest`, cache overlay with the stage's files): the Alps slopestyle
  park passes (p95 0.02, max 0.12 m, 0 ticks under, 0 crashes); its line lies outside the exact
  coverage (111 of 201 points on ground_fix, 90 in the L4 feather band; |harvest − ground_fix| along
  the line 0.09 m mean, 0.38 m max). The four Alaska parks are skipped (no Alaska captures).
