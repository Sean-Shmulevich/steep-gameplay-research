<!-- Imported authored research, not game payloads. -->
> Source: Studio `steep-wasm`, commit `1344bca03985eb1540236fb2ecd3cbbe8ecdcf14`, `docs/specs/world/terrain-surfaces.md`.
> Evidence labels and validation counts below are the source agents' reports;
> the asset-level checks were not rerun for this import. Local source links were
> converted to plain references; their files may not be included here. Historical
> superseded sections remain labeled. Studio-authored runtime policies are not
> evidence of original game behavior.

# Terrain surfaces: `.tbf` layer raster, terrain material chain, surface maps — G-08

Clean-room spec of the ground's material per location: which terrain material lies on every
texel of the playable heightfield, and the physics surface it maps to. It covers the layer
section of the `.tbf` nodes (fully decoded here, the successor of
`tbf-heights.md` (Studio source: `../formats/tbf-heights.md`) §2), the predictor that turns its symbols into
material codes, the chain `TerrainMaterialBank → TerrainMaterial → CollisionMaterial →
PhysicsMaterial`, per-region tables and statistics, a comparison with placed collision materials,
and the `terrain-surfaces` cache stage. Container layout, node sections and the trailer are in
`tbf.md` (Studio source: `../formats/tbf.md`) §3; the texel grid and world placement are in tbf.md §2/§4 and
`world-coords.md` (Studio source: `../formats/world-coords.md`); PhysicsMaterial / CollisionMaterial records and the
surface-class enum are in `surfaces.md` (Studio source: `../physics/surfaces.md`); placed collision is in
`linkage.md` (Studio source: `../physics/linkage.md`). The visual side (blend shaders) is in
`terrain-blend.md` (Studio source: `../shaders/terrain-blend.md`).

Tags: **VERIFIED** = a command was run here and its key output is quoted; **UNVERIFIED** =
inference, name-based reading or image judgement.

**Clean-room note.** Everything here comes from statistics over the owner's data files:
`$STEEP_DATA/install/PC{Alpes,AlaskaTUX,Japan}_terrainlin1.tbf`, the
`DataPC_STP_<Map>{,_patch_01,_patch_02}.forge` packs and the Summit cache built from them. No
executable code was examined. Quoted values are names, class ids, offsets and statistics only.

## Contents

1. Summary and how to reproduce
2. Layer section: format, range coder, predictor
3. Terrain material chain (3.5 textures, 3.6 tiling: P5-14)
4. Per-region tables and class histograms
5. What the ground is, per region
6. Agreement with placed collision materials
7. Cache stage `terrain-surfaces`
8. Open questions

---

## 1. Summary and how to reproduce

- Every `.tbf` node holds a 132 × 132 **layer raster** in one sparse section: Alpes section 2,
  AlaskaTUX/Japan section 3. It is coded with a static multi-symbol range coder whose
  cumulative table is built by a *sequential split* (§2.3). The decoded symbols are XOR
  residuals against a 3-neighbour predictor (§2.5). The reconstructed value is a **code = 3·g**,
  where g is a terrain material **group**.
- Group g owns entries 3g..3g+2 of the map's `TerrainMaterialBank` material list (three
  variants). All three variants of a group share one PhysicsMaterial, so group → surface is
  well defined (§3).
- The trailer `layer_mask` (tbf.md §3.2) is exactly the set of groups present in the bordered tile:
  bits 3g..3g+2 are non-zero iff group g occurs (87,381 / 87,381 nodes, all levels, all regions).
- Results at L6 (8192², 1.953125 m texels, 256 km²): Alpes is 91 % snow, AlaskaTUX 88 % snow and
  11 % ice (much of it frozen sea), Japan 67 % deep/standard powder, 23 % beach rock and 10 %
  groomed piste (§4, §5).
- The Rust importer (`summit-import terrain-surfaces`) decodes all 4096 L6 nodes per region with
  0 failures and writes `cache/terrain/<R>/{layers.r8,surface.r8,surface.json}` (§7). Its rasters
  are byte-identical to the Python reference.

### How to reproduce

Lab scripts live in `tools/lab/G-08/`. `PY` = `$STEEP_DATA/shared/lab-venv/bin/python`; run from
the repo root after `source tools/env.sh`. Outputs go to `$STEEP_DATA/G-08/{A,B,C,E}/` and
`$STEEP_DATA/captures/g08/`, all outside git.

| Part | Folder | Commands |
|---|---|---|
| Layer section, coder (A) | `sparse/` | `cc -O2 -o $STEEP_DATA/G-08/A/seqdec tools/lab/G-08/sparse/seqdec.c`; `$PY tools/lab/G-08/sparse/extract.py` (dumps the sections to `$STEEP_DATA/G-08/A/sec_*.bin`); `$STEEP_DATA/G-08/A/seqdec $STEEP_DATA/G-08/A/sec_<R>.bin` (add `alpes` for Alpes); `$PY tools/lab/G-08/sparse/eval_rates.py --pure 100`; `hdrstats.py`, `alpesnorm.py 1`, `stitch_l6.py <R>`, `seam.py`, `ptab.py AlaskaTUX 7` |
| Material chain (B) | `materials/` | `summit-import extract DataPC_STP_<Map>{,_patch_01,_patch_02}.forge --id 0x1f48e86884 -o $STEEP_DATA/G-08/B/ext` (from `$STEEP_DATA/install`); then in `tools/lab/G-08/materials`: `$PY banks.py; $PY tm_table.py; $PY census.py; $PY small_tiles.py; $PY corner.py AlaskaTUX 6 13; $PY hyp3.py; NMAX=60 $PY xorpred2.py AlaskaTUX 6 5; $PY stats2.py <R> 2 7; $PY make_idmap.py` |
| Placed collision (C) | `collision/` | `git show 5fa939b:tools/lab/P2-01/patch/forge_index.py > $STEEP_DATA/G-08/C/build/forge_index.py` (P2-01 helper, not on main); `$STEEP_DATA/P0-05/venv/bin/python tools/lab/G-08/collision/packed_dump.py <Map>`; `$PY tools/lab/G-08/collision/placed.py`; `$PY tools/lab/G-08/collision/check.py > $STEEP_DATA/G-08/C/check.out`; `$PY tools/lab/G-08/collision/summary.py` (about 5 min, 230 MB scratch) |
| Analysis (E) | `analysis/` | `cc -O2 -shared -o $STEEP_DATA/G-08/A/libseq.dylib tools/lab/G-08/sparse/libseq.c`; `cc -O2 -shared -o $STEEP_DATA/G-08/E/libxorpred.dylib tools/lab/G-08/analysis/xorpred.c`; in `tools/lab/G-08/analysis`: `for r in Alpes AlaskaTUX Japan; do $PY decode.py $r --all-levels; $PY analyze.py $r; done; $PY report.py`; `$PY hcheck.py` |
| Rust cache stage | `crates/` | `./target/release/summit-import terrain-surfaces --region <R> [-o CACHE] [--png OUT.png]`, or the `terrain-surfaces` stage of `summit-import all` |

Rust code: `crates/summit-formats/src/tbf_layers.rs` (section, coder, predictor),
`terrain_material.rs`, `physics_material.rs`, and `crates/summit-import/src/cli_terrain_surfaces.rs`.
User-facing description: `docs/import.md` (Studio source: `../../import.md`) § `terrain-surfaces`.

---

## 2. Layer section: format, range coder, predictor

### 2.1 Where the section is

| Region | Sections per node (tbf.md §3) | Layer section index |
|---|---|---|
| PCAlpes | 4 | 2 |
| PCAlaskaTUX | 5 | 3 |
| PCJapan | 5 | 3 |

The section is present in every node (87,381 per lin1 file, levels 0..8). A reader can pick the
index from the node's section count (`tbf_layers::layer_section_index`: 4 → 2, 5 → 3).

### 2.2 Byte layout

Offsets are from the start of the section payload, after the `u32` length prefix of tbf.md §3.

```
+0              u64 le   key      a C-library rand() value; not needed for decoding (tbf-heights.md §2.1)
+8              u16 le   n        number of symbols, >= 1 (max seen: Alpes 24, AlaskaTUX 27, Japan 36)
+10             u16 BE   f[0]     weight of symbol 0, the implicit symbol (no id stored)
+12             (n-1) × { u8 id[k]; u16 BE f[k] }      k = 1..n-1, ids strictly increasing
+12+3(n-1)      stream   range-coded symbol indices, to the end of the section
```

- **Weights.** In AlaskaTUX and Japan, `f[k]` is the exact number of texels with symbol k, and the
  weights sum to 17,424 = 132² in every node. In Alpes the weights are normalised:
  `f[k] = floor(count[k] · 65536 / 17424)`, summing to 65,529..65,534. The decoder only needs the
  weights as stored.
- No weight is ever 0. The smallest section is 14 bytes (Japan, 63 nodes with n = 1 and stream
  `00 80`); the smallest in Alpes and AlaskaTUX is 18 bytes.
- **VERIFIED** (A): `$PY tools/lab/G-08/sparse/hdrstats.py AlaskaTUX Japan Alpes` → `AlaskaTUX max n
  27 tiles with a zero weight 0 … sum(f) values [(17424, 87381)]`; `Japan max n 36 tiles with a
  zero weight 0 n==1 tiles 63 {'0080': 63} min section len 14`; `Alpes max n 24 tiles with a zero
  weight 0 … sum(f) values [(65533, 17400), (65531, 16171), …]`.
- **VERIFIED** (A, Alpes normalisation, all nodes): `alpesnorm.py 1` →
  `{'floor(c*65536/17424)': 87381, … 'n': 87381}`.

### 2.3 Range coder: model and cumulative table

A static multi-symbol range coder: 32-bit range R, byte-wise renormalisation while R < 2²⁴,
exact carry propagation and a 2-byte flush in the encoder, and the header weights as a fixed
model for the whole tile.

The cumulative table is the detail that P2-06b was missing. It is **not** `floor(cum · 2³² / T)`.
Each symbol, in header order (symbol 0 first), takes its share of the part of the 2³² interval
that is still unassigned:

```
T    = f[0] + ... + f[n-1]
base = 0; rest = 2^32; left = T; P[0] = 0
for k in 0 .. n-1:
    w      = floor(f[k] * rest / left)     # exact integer maths; f*rest < 2^48 fits in u64
    base  += w
    rest  -= w
    left  -= f[k]
    P[k+1] = base
# at k = n-1, f[k] == left so w == rest and P[n] == 2^32
```

P[k] is the lower end of symbol k's interval in units of 2⁻³². Rejected alternatives, each
failing on many tiles: `floor(cum·2³²/T)` (P2-06b "H_fix32"), a sum of per-symbol
`floor(f·2³²/T)`, "implicit symbol first, the rest share the remainder", and widths from a
permuted cumulative. **VERIFIED** (A): `ptab.py AlaskaTUX 7` → `7 {'cum': 99, 'sum': 410, 'rem':
223, 'seq': 7637, 'n': 7637}` and `4 {'cum': 559, … 'seq': 849, 'n': 849}` (only `seq`, the
sequential split, fits every tile).

### 2.4 Decoder (exact) and encoder

```
code = s[0]<<24 | s[1]<<16 | s[2]<<8 | s[3]        # s = stream; bytes past the end read as 0
pos  = 4
R    = 0xFFFFFFFF
repeat 17424 times:
    B(k) = (R * P[k]) >> 32                         # 64-bit product, then shift; B(0) = 0
    s_ix = largest k in 0..n-1 with B(k) <= code    # linear search is fine (n <= 36)
    a    = B(s_ix)
    b    = (s_ix == n-1) ? R : B(s_ix + 1)          # the top symbol's upper end is R itself
    # code >= b would mean a corrupt stream
    output s_ix
    code = code - a
    R    = b - a
    while R < 2^24:
        code = (code << 8) | next byte (0 past the end); pos += 1
        R    = R << 8
```

- **Integrity checks.** After the last symbol, `pos == stream length + 2` exactly (the 4-byte
  look-ahead runs 2 bytes past the 2-byte flush). The output histogram equals `f[]`
  (AlaskaTUX/Japan) or `floor(count·65536/17424) == f[]` (Alpes). A failure of either means a
  corrupt section; none occur in the shipped data.
- n = 1: every step outputs 0 with a = 0, b = R, R never drops below 2²⁴, and the stream is
  always `00 80`.
- All arithmetic fits in u64: R < 2³², P[k] ≤ 2³², code < R after every step, and code << 8 stays
  below 2³² because R < 2²⁴ before the shift.

The encoder is not needed by the engine; it is the proof of exactness and is used by the Rust
round-trip tests:

```
low = 0 (with carry handling), R = 0xFFFFFFFF, out = []
for each symbol s:
    a = (s == 0) ? 0 : (R * P[s]) >> 32
    b = (s == n-1) ? R : (R * P[s+1]) >> 32
    low += a; R = b - a
    if low >= 2^32: low -= 2^32; add 1 to out[] from the last byte backwards (0xFF -> 0x00 carries on)
    while R < 2^24: out.append(low >> 24); low = (low << 8) mod 2^32; R <<= 8
low += 2^23 (carry as above)
out.append(low >> 24); out.append((low >> 16) & 0xFF)        # 2-byte flush
```

### 2.5 Symbols → residuals → codes (predictor)

Symbol index k ≥ 1 means residual value `id[k]`; index 0 (implicit) means residual **0**. The
132 × 132 residual raster (row-major, x fastest) is turned into codes inside each tile, with no
state shared between tiles:

```
for y in 0..131, x in 0..131:
    if   x == 0 and y == 0: p = 0
    elif y == 0:            p = code[y][x-1]                  # row 0: left
    elif x == 0:            p = code[y-1][x]                  # column 0: above
    else:
        A = code[y][x-1]; B = code[y-1][x]; C = code[y-1][x-1]
        p = (B != C and A == C) ? B : A
    code[y][x] = residual[y][x] XOR p
group = code / 3          # every code is a multiple of 3
```

So the implicit symbol is "same as predicted", not a material. This explains three things A saw
on the raw residuals:

- texel (0,0) is almost always explicit and its id is a multiple of 3 (it is predicted from 0, so the
  residual *is* the code);
- tiles with n = 2 are almost all `[f0 = 17423, f1 = 1]` with the one explicit texel at (0,0)
  (AlaskaTUX 11,877 of 11,877, Japan 17,260 of 17,438): constant tiles;
- residual column/row 0 disagreed with the neighbour's overlap (79.8–92.9 %): those texels are
  predicted without seeing the neighbour. On the reconstructed codes the overlap agrees 100 %
  (§2.7).

Residual statistics only (not materials): the implicit residual 0 covers 87.4 % (AlaskaTUX), 71.8 %
(Japan) and 83.2 % (Alpes) of the stitched L6 image (A, `stitch_<R>.log`: 58,621,430 / 48,203,126
/ 55,866,011 of 67,108,864). Explicit residual values range over 3..54.

Evidence for code = 3·g (B, VERIFIED on the then-exact tiles): no header id is ever 1, 2, 4, 8, 16
or 32; 2-symbol tiles carry an id 3g with g in the trailer mask (340/340, 153/153, 228/228); the
above predictor validates 60/60 AlaskaTUX L6 tiles against 52/60 for an "up" fallback and 50/60 for
"up-left" (`NMAX=60 $PY xorpred2.py AlaskaTUX 6 5`). The full-coverage check is §2.8.

### 2.6 Stitching

The raster uses the colour-tile grid (tbf.md §2): 132 × 132 with a 2-texel border, stride 128.

```
image[128·ty + r][128·tx + c] = code_tile(L, tx, ty)[2 + r][2 + c]      r, c in 0..127
```

Image row = world +Y, column = world +X (tbf.md §4). At L6 this gives 8192² texels of 1.953125 m
over [−8000, 8000)².

### 2.7 Overlap and seams

- **VERIFIED** (E, `decode.py`, `decode_<R>.log`): overlap agreement of texel 128+k of a tile with
  texel k of its right/lower neighbour, k = 0..3, on codes: `overlap h k=0..3 [1. 1. 1. 1.] v [1. 1.
  1. 1.]` for Alpes, AlaskaTUX and Japan.
- **VERIFIED** (E): mismatch rate of adjacent texel pairs across tile seams vs inside tiles (1.0 =
  seamless):

| Region | x seam / interior | ratio | y seam / interior | ratio |
|---|---|---|---|---|
| Alpes | 0.16415 / 0.16256 | 1.010 | 0.16687 / 0.16443 | 1.015 |
| AlaskaTUX | 0.13441 / 0.12469 | 1.078 | 0.13096 / 0.12285 | 1.066 |
| Japan | 0.28449 / 0.28275 | 1.006 | 0.28711 / 0.28351 | 1.013 |

Interior mismatch rates of 12–28 % are expected: transition zones are dithered texel by texel
(image judgement, UNVERIFIED as authoring intent).

### 2.8 Verification

| Check | Result | Tag |
|---|---|---|
| Range decode, every node L0..L8, all regions, with byte-exact re-encode (C lab decoder `seqdec.c`) | `TOTAL nodes 87381 exact 87381 cons_ok 87381 reencode_exact 87381` for AlaskaTUX, Japan and Alpes (re-run 2026-10-11 for this spec) | VERIFIED |
| Reference Python decoder (`eval_rates.py --pure 100`): L5 and L6 in full, L8 sample of 5000 (seed 808) with re-encode, plus 100 L8 tiles on the pure-Python path | Alpes `nodes 1024 exact 1024 (100.00%)`, `nodes 4096 exact 4096 (100.00%)`, `nodes 5000 exact 5000 (100.00%) re-encode byte-exact 5000`, pure path `100/100`; AlaskaTUX and Japan 100.00 % in every column | VERIFIED (A) |
| Predictor + code = 3·g + group in trailer mask, all L6 tiles (`decode.py`) | `Alpes L6 {'tiles': 4096, 'exact': 4096, 'texels': 71368704, 'mult3': 71368704, 'inmask': 71368704, 'tiles_all_ok': 4096}`; AlaskaTUX and Japan identical | VERIFIED (E) |
| Same, random 2000 L8 nodes per region (seed 8) | `L8 sample {'tiles': 2000, 'exact': 2000, 'texels': 34848000, 'mult3': 34848000, 'inmask': 34848000, 'tiles_all_ok': 2000}` | VERIFIED (E) |
| Same, all 87,381 nodes at every level (`--all-levels`) | per level `tiles == exact == mult3_all == inmask_all`, `texels_bad 0`; e.g. `8: {'tiles': 65536, 'exact': 65536, 'mult3_all': 65536, 'inmask_all': 65536, 'texels_bad': 0, 'groupset_eq_mask': 65536}` | VERIFIED (E) |
| Rust decoder unit tests (sequential-split table, n = 1 tile, encoder round trips with exact and normalised weights, predictor, corrupt streams) | `cargo test --release -p summit-formats -- tbf_layers terrain_material physics_material` → `test result: ok. 13 passed; 0 failed` | VERIFIED |
| Rust decoder on real data | see §7.4 | VERIFIED |

"inmask" means bits 3g..3g+2 of the node's trailer `layer_mask` are not all zero. "texels" counts
all 132² texels of every tile, border included.

### 2.9 Group set equals the trailer `layer_mask`

- **VERIFIED** (E, `decode.py`): over the full bordered 132² tile, the set of decoded groups equals
  the set of groups whose `layer_mask` triple is non-zero, in 87,381 / 87,381 nodes at every level
  in all three regions (`groupset_eq_mask` equals `tiles` at every level).
- At L6: `{'full_eq': 4096, 'full_sub': 4096, 'own_eq': 4033, 'own_sub': 4096, …} of 4096` (Alpes;
  AlaskaTUX `own_eq` 3977, Japan 3975). Groups that occur only in the 2-texel border make up the
  difference, so the mask is computed over the bordered tile.
- So `layer_mask` is the list of groups present in the tile. A tile whose mask has one group is
  constant. *Which* bit of a triple is set cannot be derived from the raster, which carries only
  3g; the reading "the bit is the `_01/_02/_03` variant" is UNVERIFIED (§3.4).
- This supersedes the P2-06b finding that ids do not map 1:1 onto mask bits: that compared
  residuals, not codes.

---

## 3. Terrain material chain

### 3.1 Where it is

Each map's whole-map DataBlock entry `0x1f48e86884` (`Cell21844_DataBlock`) in
`DataPC_STP_<Map>{,_patch_01,_patch_02}.forge` holds one `TerrainMaterialBank_<Map>` record and the
TerrainMaterials it lists. **VERIFIED** (B, `banks.py`; and the Rust importer, §7.4):

| Region (forge map) | Bank name | Bank id | Record length | Material list | Groups |
|---|---|---|---|---|---|
| Alpes (Alpes) | `TerrainMaterialBank_Alps` | `0x4485cad19e` | 431 B | 33 | 11 |
| AlaskaTUX (Alaska) | `TerrainMaterialBank_Alaska` | `0x11babbf170f` | 521 B | 42 | 14 |
| Japan (Japan) | `TerrainMaterialBank_Japan` | `0xd6ce6db5b0` | 461 B | 42 | 14 |

The group counts match the highest trailer `layer_mask` bits (32 and 41, tbf.md §3.2).

### 3.2 Record layouts

All records begin with the usual `{u64 id, u32 class, u8 1}` prefix (types.md §1–§2).

**TerrainMaterialBank** (class `0x4be94285`), consumes the record exactly:

| Field | Type | Meaning | Tag |
|---|---|---|---|
| header | `u64 id, u32 class, u8 1` | | VERIFIED |
| list 1 | `u32 n; n × {u8 1, u8 0, u64 ref}` | TextureSet refs (`*TER_DetailTexture_*_Set`) | VERIFIED (structure, names) |
| list 2 | `u32 n; n × {u8 1, u8 0, u64 ref}` | ordered TerrainMaterial refs: group g = entries 3g..3g+2 | VERIFIED |
| tail | `u8 1, u8 1, u64 ref` | `STP_<MAP>_TerrainDisplacementsArray` | VERIFIED (name); use UNVERIFIED |

**TerrainMaterial** (`TM_*`, class `0x01724188`, fixed 199 bytes). Full byte map (P5-14; Kaitai:
`terrain-material.ksy` (Studio source: `terrain-material.ksy`)). Census over the 117 bank entries (Alpes 33, Alaska 42,
Japan 42) of the `_patch_02` entries; all 294 TM copies (3 maps × 3 layers) are 199 B and byte-identical
across layers for every id. **VERIFIED**: `tools/lab/P5-14/tiling/census.py` → `byte map covers 0..199
exactly: OK, fields 42`; `check_ksy.py` → `terrain-material.ksy: 294 ok, 0 errors`; `layers.py` prints no
diff. Field names after a value census are readings and UNVERIFIED unless tagged.

| Off | Type | Field | Census / meaning | Tag |
|---|---|---|---|---|
| +0x00 | `u64, u32, u8` | id, class, 1 | class = crc32("TerrainMaterial") | VERIFIED |
| +0x0d | `u8 0, u64` | `texture_set` (bare ref) | → TextureSet (`0xd70e6670`), root of its own entry (§3.5) | VERIFIED |
| +0x16 | u32 | — | 0 ×117 | VERIFIED |
| +0x1a | `u8 0, u64` | `source` (bare ref) | resolves to no record or entry in any forge (`refs.out`: unresolved 33/36/30); 9 Alpes SNOW TMs share one id. Ignore | values VERIFIED; "editor source" UNVERIFIED |
| +0x23 + 28·k, k = 0..3 | `u64 0, u32 0xa79767ed, f32 r,g,b,a` | `color[k]`: 4 embedded `Color` objects (crc32("Color") = `0xa79767ed`) | rgb identical across the 4 in 98/99 unique TMs (exception `TM_ALA_ROCKS_Calcaire_01`: A,B,A,B); a = 1.0 | structure VERIFIED; "tint" UNVERIFIED |
| +0x93 | f32 | `f93` | 29 distinct, 0.19..3.5; 1.0 ×51; ±10 % between variants of a group | values VERIFIED; tiling candidate #1 (§3.6) UNVERIFIED |
| +0x97 | f32 | `f97` | 12 distinct; 200 ×86, 50 ×9, 10, 6, 3, 0.8, … | values VERIFIED; meaning UNVERIFIED |
| +0x9b | f32 | `f9b` | 18 distinct; 1.0 ×43, 0.025 ×39, else 0.19..10 | values VERIFIED; meaning UNVERIFIED |
| +0x9f | u32 | **`detail_index`** | index into the bank's list 1 (detail TextureSets), §3.5 | VERIFIED (Alpes 33/33, Alaska 42/42 by name; Japan out of range, §3.5) |
| +0xa3 | f32 | `fa3` | always exactly k/255; ice 70..93, snow 31..41, rock 18..49 (Alpes, ×255) | values VERIFIED; "reflectance" UNVERIFIED |
| +0xa7 | f32 | `fa7` | always exactly k/255; 0 ×24, 170 ×14, 151 ×14 (×255) | values VERIFIED; "gloss" UNVERIFIED |
| +0xab..+0xb0 | 6 × u8 | flags | each 0/1; +0xac always 0; +0xaf/+0xb0 = 1 on snow, +0xab = 1 on most rock/ice | values VERIFIED; meanings UNVERIFIED |
| +0xb1 | f32 | `fb1` | 50 ×96, 5 ×18 (Japan GROOMED), 8 ×3 (Japan SNOW_ROAD) | values VERIFIED; meaning UNVERIFIED |
| +0xb5 | `u8 1, u8 0, u64` | **`collision_material`** | → CollisionMaterial in the same entry | VERIFIED |
| +0xbf | u32 | — | 0 ×117 | VERIFIED |
| +0xc3 | u32 | `slot_index` | 0..42. Alpes: = 4·g + variant number − 1 (33/33). Alaska/Japan: = bank index for 33/42 and 30/42 (duplicated GROOMED entries reuse another value) | values VERIFIED; meaning UNVERIFIED (§8) |

This corrects the G-08 reading: the old "+0x2b 4 × 28 B tint entries" are the `Color` objects at
+0x23 (the 8 "unknown" bytes are the next object's zero `obj_id`), the old "+0x93 7 × f32" holds a
u32 at +0x9f, and the old "+0xaf 8 flag bytes" are flags + `fb1` + the CM ref header.

**CollisionMaterial** (`0x74f7311d`, 52 B) → PhysicsMaterial ref at +0x0f; **PhysicsMaterial**
(`0x6aead073`, 759 B) → `surface_type` u32 at +0x0d, friction f32 at +0x2e7, restitution f32 at
+0x2eb. Both are specified in surfaces.md §2.1–§2.2 and §4.

### 3.3 Patch resolution

Records are resolved per id across the base pack and its patch layers, highest layer wins
(surfaces.md §1). This matters twice:

- the AlaskaTUX base layer bank has 33 entries; `_patch_01` adds the GROOMED groups 11–13
  (B, VERIFIED);
- base-layer PhysicsMaterials carry other friction values (surfaces.md §1).

In the current install all three banks and every terrain PM resolve to layer 2 (`_patch_02`):
**VERIFIED** (`surface.json` `"bank": {… "layer": 2 …}` and `pm_layer 2` for every group of every
region).

### 3.4 Groups and variants

- Group g = bank entries 3g, 3g+1, 3g+2; the raster stores only 3g, never which variant.
- Variant names are not always `_01/_02/_03`: e.g. Alpes `TM_ALP_ROCKS_Calcaire_04, _02, _03` and
  `TM_ALP_ROCKS_Flysch_01, _02, _04` (bank order). **VERIFIED** (`summit-import terrain-surfaces`
  group lines, §7.4).
- Where one TM fills all three entries of a group (Japan groups 0–2 and 11–13, AlaskaTUX 11–13),
  only trailer bit 3g+2 is ever set (B, VERIFIED). Elsewhere all three bits occur in near-equal
  counts (tbf.md §3.2). Whether the bit picks the visual variant is UNVERIFIED.
- All three variants of every group share one CM and PM. **VERIFIED** by an assert in E's
  `decode.py` and by the importer, which refuses to run otherwise (`docs/import.md`).
- The raster code is not the PM `surface_type` and not a CM list index (counter-examples: code 27
  is `ICE_Ocean → PM_Ice_Water` in AlaskaTUX and `ICE_RiverLake → PM_Ice` in Japan). B, VERIFIED.
- `TerrainProceduralSetBank` (`0x65c3c7d0`) → `TerrainProceduralSet` (`0x2f45393e`, entry 0
  `TPS_EMPTY_INDEX0`) → up to 6 `TPM_*` (`0x4323218d`) → 3 TMs each also exist. No link from them
  to the `.tbf` raster was found (B). Open (§8).

### 3.5 TerrainMaterial → textures (P5-14)

Chain per bank entry: `TM +0x0d → TextureSet` (base textures) and `TM +0x9f → bank list 1[i] →
TextureSet` (detail textures). TextureSet records (202 B) and their slot refs are specified in
`material.md` (Studio source: `../formats/material.md`) §4; slot index = role (0 diffuse, 1 normal, 3 height, 7 mask1).
TextureMaps are converted by the `textures` stage (`texture.md` (Studio source: `../formats/texture.md`)).

**Base TextureSets.** **VERIFIED** (`tools/lab/P5-14/mapping/mapping.py` → `117 TM rows; 15 list1 rows;
45 id hits`; `grep -c "NOT FOUND\|not in cache" tm_map.tsv list1.tsv` → `0`, `0`; spot check of
`STP_TER_ROCKS_Calcaire_04_Set` by a raw read of its extracted entry: filled slots `0, 1, 3, 7`):

- Every TM's TextureSet is the **root of its own entry** (entry id = set id) in the base pack
  `DataPC_STP_<Map>.forge`, one copy, never patched. Exception: Alaska `SNOW_GROOMED_01..03_Set` exist only
  in `DataPC_STP_Alaska_patch_01`. None is in the whole-map entry.
- All 117 referenced sets are 202 B. The 95 distinct terrain sets fill **exactly slots 0, 1, 3, 7**
  (`{('TM','0'): 95, ('TM','1'): 95, ('TM','3'): 95, ('TM','7'): 95}`): no specular (slot 2), no
  Diffuse1..5.
- Formats (from `cache/textures/index.tsv`): diffuse 2048² BC1, normal 2048² BC7, height 2048² R8 (95 each);
  mask1 32² BC1 (64) or 2048² BC1 (31: all Japan, Alaska GROOMED, the Alaska copy of `STP_JAP_TER_ICE_ROAD_01_Set`).
- All slot targets are TextureMap entry roots, 0 missing: `DataPC_STP_Alpes` 112, `DataPC_STP_Alaska` 118,
  `DataPC_STP_Alaska_patch_01` 7, `DataPC_STP_Japan` 62, plus 2 shared.
- Variants usually have their own set but often share the diffuse map and differ in the normal map (e.g. all
  Alpes `SNOW_POWDER` use `SNOW_POWDER_01_DiffuseMap`). Alpes snow and RiverLake sets share
  `Terrain-Ground-Black_HeightMap` (flat by name; pixels not inspected, UNVERIFIED).
- Names do not always match: Alpes `SNOW_THIN_SNOWPARK_03` uses the `_01` set; Japan `POWDER_52/74/96CM`
  use the `60/90/120CM` sets; Japan `GROOMED_SNOW_2CM_0x` and `GROOMED_COMPETITION_SNOW_2CM_0x` share
  `STP_JAP_TER_SNOW_GROOMED_0x_Set`; Alaska `SNOW_ROAD_01` uses `STP_JAP_TER_ICE_ROAD_01_Set`,
  `ICE_CliffThick` the `ICE_THICK` sets and `ICE_Ocean` the `ICE_SeaIce` sets. A reader must follow the ref,
  never the name.

**Detail TextureSets (bank list 1).** The list-1 sets (`*_DetailTexture_*_Set`; Alpes 7, Alaska 7, Japan 1)
live **inside** the whole-map entry `0x1f48e86884` (used copy: layer 2). Each fills only slot 0 (1024² BC1)
and slot 1 (1024² BC7). Diffuse maps are mostly shared: 5 of 7 Alpes detail sets use
`STP_TER_DetailTexture_Granite_DiffuseMap`; only Snow and IceLakes have their own. **VERIFIED** (`list1.tsv`).
Their ids occur in no record except the bank (raw u64 search, `idhits.tsv`, 45 hits, all in
`TerrainMaterialBank_*` list 1): the link is **positional**, through the TM's u32 `detail_index` at +0x9f.
**VERIFIED** by name agreement (`census.py` → `detail_index -> bank list 1` lines): Alpes 33/33, Alaska
42/42 (Flysch → Granite, the only Alpes rock without its own set; Alaska `ICE_Ocean → SeaIce`,
`ICE_CliffThick → IceCliff`). **Japan**: list 1 holds only `STP_TER_JAP_DetailTexture_Snow_Set`, yet
`ROCKS_Beach` (1), `ICE_RiverLake` (3) and `SNOW_ROAD` (5) are out of range (9 of 42 entries). Whether the
engine clamps, skips detail or reads elsewhere is UNVERIFIED (§8).

`TerrainSplattingNoise_Set` (slot 0 only, 2048² BC1) is in each whole-map entry but **not** in list 1; its
only referrer is the Entity `Terrain_TemplateMap` (`0x0984415e`), whose embedded `TerrainSettings`
(`0x988994d8` = crc32 name) holds the ref. **VERIFIED** (`other_sets.out`, `xref.out`).

**Mapping tables.** Generated by `tools/lab/P5-14/spec/spec_tables.py` (names without the
`STP_TER_` / `STP_ALA_TER_` / `STP_JAP_TER_` prefix; all values **VERIFIED** from the records as above).
Slot formats are as listed above. The last column shows the three tiling candidates (§3.6).

#### Alpes

| g | idx | TM | TextureSet | 0 diffuse | 1 normal | 3 height | 7 mask1 | +0x9f detail set | +0x93 / +0x97 / +0x9b |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 0 | `TM_ALP_ROCKS_Calcaire_04` | `ROCKS_Calcaire_04_Set` | ROCKS_Calcaire_04_DiffuseMap | ROCKS_Calcaire_04_NormalMap | ROCKS_Calcaire_04_HeightMap | ROCKS_Calcaire_04_Mask1Map | 6 DetailTexture_Calcaire_Set | 0.35 / 200 / 0.35 |
| 0 | 1 | `TM_ALP_ROCKS_Calcaire_02` | `ROCKS_Calcaire_02_Set` | ROCKS_Calcaire_02_DiffuseMap | ROCKS_Calcaire_02_NormalMap | ROCKS_Calcaire_02_HeightMap | ROCKS_Calcaire_02_Mask1Map | 6 DetailTexture_Calcaire_Set | 0.35 / 200 / 0.35 |
| 0 | 2 | `TM_ALP_ROCKS_Calcaire_03` | `ROCKS_Calcaire_03_Set` | ROCKS_Calcaire_03_DiffuseMap | ROCKS_Calcaire_03_NormalMap | ROCKS_Calcaire_03_HeightMap | ROCKS_Calcaire_03_Mask1Map | 6 DetailTexture_Calcaire_Set | 0.35 / 200 / 0.35 |
| 1 | 3 | `TM_ALP_ROCKS_Dolomie_04` | `ROCKS_Dolomie_04_Set` | ROCKS_Dolomie_04_DiffuseMap | ROCKS_Dolomie_04_NormalMap | ROCKS_Dolomie_04_HeightMap | ROCKS_Dolomie_04_Mask1Map | 5 DetailTexture_Dolomie_Set | 0.25 / 50 / 0.27 |
| 1 | 4 | `TM_ALP_ROCKS_Dolomie_02` | `ROCKS_Dolomie_02_Set` | ROCKS_Dolomie_02_DiffuseMap | ROCKS_Dolomie_02_NormalMap | ROCKS_Dolomie_02_HeightMap | ROCKS_Dolomie_02_Mask1Map | 5 DetailTexture_Dolomie_Set | 0.25 / 50 / 0.25 |
| 1 | 5 | `TM_ALP_ROCKS_Dolomie_03` | `ROCKS_Dolomie_03_Set` | ROCKS_Dolomie_03_DiffuseMap | ROCKS_Dolomie_03_NormalMap | ROCKS_Dolomie_03_HeightMap | ROCKS_Dolomie_03_Mask1Map | 5 DetailTexture_Dolomie_Set | 0.25 / 50 / 0.26 |
| 2 | 6 | `TM_ALP_ROCKS_Flysch_01` | `ROCKS_Flysch_01_Set` | ROCKS_Flysch_01_DiffuseMap | ROCKS_Flysch_01_NormalMap | ROCKS_Flysch_01_HeightMap | ROCKS_Flysch_01_Mask1Map | 1 DetailTexture_Granite_Set | 0.25 / 200 / 0.025 |
| 2 | 7 | `TM_ALP_ROCKS_Flysch_02` | `ROCKS_Flysch_02_Set` | ROCKS_Flysch_02_DiffuseMap | ROCKS_Flysch_02_NormalMap | ROCKS_Flysch_02_HeightMap | ROCKS_Flysch_02_Mask1Map | 1 DetailTexture_Granite_Set | 0.25 / 200 / 0.025 |
| 2 | 8 | `TM_ALP_ROCKS_Flysch_04` | `ROCKS_Flysch_04_Set` | ROCKS_Flysch_04_DiffuseMap | ROCKS_Flysch_04_NormalMap | ROCKS_Flysch_04_HeightMap | ROCKS_Flysch_04_Mask1Map | 1 DetailTexture_Granite_Set | 0.25 / 200 / 0.025 |
| 3 | 9 | `TM_ALP_ROCKS_Gneiss_01` | `ROCKS_Gneiss_01_Set` | ROCKS_Gneiss_01_DiffuseMap | ROCKS_Gneiss_01_NormalMap | ROCKS_Gneiss_01_HeightMap | ROCKS_Gneiss_01_Mask1Map | 2 DetailTexture_Gneiss_Set | 0.3 / 200 / 0.3 |
| 3 | 10 | `TM_ALP_ROCKS_Gneiss_02` | `ROCKS_Gneiss_02_Set` | ROCKS_Gneiss_02_DiffuseMap | ROCKS_Gneiss_02_NormalMap | ROCKS_Gneiss_02_HeightMap | ROCKS_Gneiss_02_Mask1Map | 2 DetailTexture_Gneiss_Set | 0.3 / 200 / 0.3 |
| 3 | 11 | `TM_ALP_ROCKS_Gneiss_04` | `ROCKS_Gneiss_04_Set` | ROCKS_Gneiss_04_DiffuseMap | ROCKS_Gneiss_04_NormalMap | ROCKS_Gneiss_04_HeightMap | ROCKS_Gneiss_04_Mask1Map | 2 DetailTexture_Gneiss_Set | 0.3 / 200 / 0.3 |
| 4 | 12 | `TM_ALP_ROCKS_Granite_04` | `ROCKS_Granite_04_Set` | ROCKS_Granite_04_DiffuseMap | ROCKS_Granite_04_NormalMap | ROCKS_Granite_04_HeightMap | ROCKS_Granite_04_Mask1Map | 1 DetailTexture_Granite_Set | 0.32 / 10 / 0.32 |
| 4 | 13 | `TM_ALP_ROCKS_Granite_02` | `ROCKS_Granite_02_Set` | ROCKS_Granite_02_DiffuseMap | ROCKS_Granite_02_NormalMap | ROCKS_Granite_02_HeightMap | ROCKS_Granite_02_Mask1Map | 1 DetailTexture_Granite_Set | 0.31 / 10 / 0.31 |
| 4 | 14 | `TM_ALP_ROCKS_Granite_03` | `ROCKS_Granite_03_Set` | ROCKS_Granite_03_DiffuseMap | ROCKS_Granite_03_NormalMap | ROCKS_Granite_03_HeightMap | ROCKS_Granite_02_Mask1Map | 1 DetailTexture_Granite_Set | 0.29 / 10 / 0.29 |
| 5 | 15 | `TM_ALP_SNOW_THIN_01` | `SNOW_THIN_01_Set` | SNOW_CRUNCHY_01_DiffuseMap | SNOW_THIN_01_NormalMap | Terrain-Ground-Black_HeightMap | SNOW_CRUNCHY_03_Mask1Map | 0 DetailTexture_Snow_Set | 1 / 200 / 0.025 |
| 5 | 16 | `TM_ALP_SNOW_THIN_02` | `SNOW_THIN_02_Set` | SNOW_THIN_02_DiffuseMap | SNOW_THIN_02_NormalMap | Terrain-Ground-Black_HeightMap | SNOW_CRUNCHY_03_Mask1Map | 0 DetailTexture_Snow_Set | 1 / 200 / 0.025 |
| 5 | 17 | `TM_ALP_SNOW_THIN_03` | `SNOW_THIN_03_Set` | SNOW_CRUNCHY_01_DiffuseMap | SNOW_THIN_03_NormalMap | Terrain-Ground-Black_HeightMap | SNOW_CRUNCHY_03_Mask1Map | 0 DetailTexture_Snow_Set | 1 / 200 / 0.025 |
| 6 | 18 | `TM_ALP_SNOW_CRUNCHY_01` | `SNOW_CRUNCHY_01_Set` | SNOW_CRUNCHY_01_DiffuseMap | SNOW_CRUNCHY_01_NormalMap | Terrain-Ground-Black_HeightMap | SNOW_CRUNCHY_01_Mask1Map | 0 DetailTexture_Snow_Set | 1 / 200 / 1 |
| 6 | 19 | `TM_ALP_SNOW_CRUNCHY_02` | `SNOW_CRUNCHY_02_Set` | SNOW_CRUNCHY_02_DiffuseMap | SNOW_CRUNCHY_02_NormalMap | Terrain-Ground-Black_HeightMap | SNOW_CRUNCHY_02_Mask1Map | 0 DetailTexture_Snow_Set | 1 / 200 / 1 |
| 6 | 20 | `TM_ALP_SNOW_CRUNCHY_03` | `SNOW_CRUNCHY_03_Set` | SNOW_CRUNCHY_03_DiffuseMap | SNOW_CRUNCHY_03_NormalMap | Terrain-Ground-Black_HeightMap | SNOW_CRUNCHY_03_Mask1Map | 0 DetailTexture_Snow_Set | 1 / 200 / 1 |
| 7 | 21 | `TM_ALP_SNOW_POWDER_01` | `SNOW_POWDER_01_Set` | SNOW_POWDER_01_DiffuseMap | SNOW_POWDER_01_NormalMap | Terrain-Ground-Black_HeightMap | SNOW_POWDER_01_Mask1Map | 0 DetailTexture_Snow_Set | 1 / 200 / 1 |
| 7 | 22 | `TM_ALP_SNOW_POWDER_02` | `SNOW_POWDER_02_Set` | SNOW_POWDER_01_DiffuseMap | SNOW_POWDER_02_NormalMap | Terrain-Ground-Black_HeightMap | SNOW_POWDER_02_Mask1Map | 0 DetailTexture_Snow_Set | 1 / 200 / 1 |
| 7 | 23 | `TM_ALP_SNOW_POWDER_03` | `SNOW_POWDER_03_Set` | SNOW_POWDER_01_DiffuseMap | SNOW_POWDER_03_NormalMap | Terrain-Ground-Black_HeightMap | SNOW_POWDER_03_Mask1Map | 0 DetailTexture_Snow_Set | 1 / 200 / 1 |
| 8 | 24 | `TM_ALP_ICE_Cliff_01` | `ICE_Cliff_01_Set` | ICE_Cliff_01_DiffuseMap | ICE_Cliff_01_NormalMap | ICE_Cliff_01_HeightMap | ICE_Cliff_01_Mask1Map | 3 DetailTexture_IceCliff_Set | 0.8 / 50 / 0.4 |
| 8 | 25 | `TM_ALP_ICE_Cliff_02` | `ICE_Cliff_02_Set` | ICE_Cliff_02_DiffuseMap | ICE_Cliff_02_NormalMap | ICE_Cliff_02_HeightMap | ICE_Cliff_02_Mask1Map | 3 DetailTexture_IceCliff_Set | 0.7 / 50 / 0.4 |
| 8 | 26 | `TM_ALP_ICE_Cliff_03` | `ICE_Cliff_03_Set` | ICE_Cliff_03_DiffuseMap | ICE_Cliff_03_NormalMap | ICE_Cliff_03_HeightMap | ICE_Cliff_03_Mask1Map | 3 DetailTexture_IceCliff_Set | 0.8 / 50 / 0.4 |
| 9 | 27 | `TM_ALP_ICE_RiverLake_01` | `ICE_RiverLake_01_Set` | ICE_RiverLake_01_DiffuseMap | ICE_RiverLake_01_NormalMap | Terrain-Ground-Black_HeightMap | ICE_RiverLake_01_Mask1Map | 4 DetailTexture_IceLakes_Set | 1 / 200 / 0.025 |
| 9 | 28 | `TM_ALP_ICE_RiverLake_02` | `ICE_RiverLake_02_Set` | ICE_RiverLake_02_DiffuseMap | ICE_RiverLake_02_NormalMap | Terrain-Ground-Black_HeightMap | ICE_RiverLake_02_Mask1Map | 4 DetailTexture_IceLakes_Set | 0.9 / 200 / 0.025 |
| 9 | 29 | `TM_ALP_ICE_RiverLake_03` | `ICE_RiverLake_03_Set` | ICE_RiverLake_03_DiffuseMap | ICE_RiverLake_03_NormalMap | Terrain-Ground-Black_HeightMap | ICE_RiverLake_03_Mask1Map | 4 DetailTexture_IceLakes_Set | 1.1 / 200 / 0.025 |
| 10 | 30 | `TM_ALP_SNOW_THIN_SNOWPARK_01` | `SNOW_THIN_SNOWPARK_01_Set` | SNOW_POWDER_01_DiffuseMap | SNOW_THIN_SNOWPARK_01_NormalMap | Terrain-Ground-Black_HeightMap | SNOW_POWDER_02_Mask1Map | 0 DetailTexture_Snow_Set | 1 / 200 / 0.025 |
| 10 | 31 | `TM_ALP_SNOW_THIN_SNOWPARK_02` | `SNOW_THIN_SNOWPARK_02_Set` | SNOW_POWDER_01_DiffuseMap | SNOW_THIN_SNOWPARK_02_NormalMap | Terrain-Ground-Black_HeightMap | SNOW_POWDER_02_Mask1Map | 0 DetailTexture_Snow_Set | 1.1 / 200 / 0.025 |
| 10 | 32 | `TM_ALP_SNOW_THIN_SNOWPARK_03` | `SNOW_THIN_SNOWPARK_01_Set` | SNOW_POWDER_01_DiffuseMap | SNOW_THIN_SNOWPARK_01_NormalMap | Terrain-Ground-Black_HeightMap | SNOW_POWDER_02_Mask1Map | 0 DetailTexture_Snow_Set | 0.9 / 200 / 0.025 |

List 1: 0 `DetailTexture_Snow_Set`, 1 `DetailTexture_Granite_Set`, 2 `DetailTexture_Gneiss_Set`, 3 `DetailTexture_IceCliff_Set`, 4 `DetailTexture_IceLakes_Set`, 5 `DetailTexture_Dolomie_Set`, 6 `DetailTexture_Calcaire_Set`

#### Alaska

| g | idx | TM | TextureSet | 0 diffuse | 1 normal | 3 height | 7 mask1 | +0x9f detail set | +0x93 / +0x97 / +0x9b |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 0 | `TM_ALA_ROCKS_Calcaire_01` | `ROCKS_Calcaire_01_Set` | ROCKS_Calcaire_01_DiffuseMap | ROCKS_Calcaire_01_NormalMap | ROCKS_Calcaire_01_HeightMap | ROCKS_Calcaire_01_Mask1Map | 6 DetailTexture_Calcaire_Set | 0.45 / 6 / 0.19 |
| 0 | 1 | `TM_ALA_ROCKS_Calcaire_02` | `ROCKS_Calcaire_02_Set` | ROCKS_Calcaire_02_DiffuseMap | ROCKS_Calcaire_02_NormalMap | ROCKS_Calcaire_02_HeightMap | ROCKS_Calcaire_02_Mask1Map | 6 DetailTexture_Calcaire_Set | 0.46 / 6 / 0.21 |
| 0 | 2 | `TM_ALA_ROCKS_Calcaire_03` | `ROCKS_Calcaire_03_Set` | ROCKS_Calcaire_03_DiffuseMap | ROCKS_Calcaire_03_NormalMap | ROCKS_Calcaire_03_HeightMap | ROCKS_Calcaire_03_Mask1Map | 6 DetailTexture_Calcaire_Set | 0.47 / 6 / 0.22 |
| 1 | 3 | `TM_ALA_ROCKS_Granite_01` | `ROCKS_Granite_01_Set` | ROCKS_Granite_01_DiffuseMap | ROCKS_Granite_01_NormalMap | ROCKS_Granite_01_HeightMap | ROCKS_Granite_01_Mask1Map | 1 DetailTexture_Granite_Set | 0.4 / 3 / 0.3 |
| 1 | 4 | `TM_ALA_ROCKS_Granite_02` | `ROCKS_Granite_02_Set` | ROCKS_Granite_02_DiffuseMap | ROCKS_Granite_02_NormalMap | ROCKS_Granite_02_HeightMap | ROCKS_Granite_02_Mask1Map | 1 DetailTexture_Granite_Set | 0.41 / 3 / 0.31 |
| 1 | 5 | `TM_ALA_ROCKS_Granite_03` | `ROCKS_Granite_03_Set` | ROCKS_Granite_03_DiffuseMap | ROCKS_Granite_03_NormalMap | ROCKS_Granite_03_HeightMap | ROCKS_Granite_03_Mask1Map | 1 DetailTexture_Granite_Set | 0.39 / 3 / 0.29 |
| 2 | 6 | `TM_ALA_SNOW_THIN_01` | `SNOW_THIN_01_Set` | SNOW_CRUNCHY_01_DiffuseMap | SNOW_THIN_01_NormalMap | Terrain-Ground-Black_HeightMap | SNOW_CRUNCHY_03_Mask1Map | 0 DetailTexture_Snow_Set | 1 / 200 / 0.025 |
| 2 | 7 | `TM_ALA_SNOW_THIN_02` | `SNOW_THIN_02_Set` | SNOW_THIN_02_DiffuseMap | SNOW_THIN_02_NormalMap | Terrain-Ground-Black_HeightMap | SNOW_CRUNCHY_03_Mask1Map | 0 DetailTexture_Snow_Set | 1 / 200 / 0.025 |
| 2 | 8 | `TM_ALA_SNOW_THIN_03` | `SNOW_THIN_03_Set` | SNOW_CRUNCHY_01_DiffuseMap | SNOW_THIN_03_NormalMap | Terrain-Ground-Black_HeightMap | SNOW_CRUNCHY_03_Mask1Map | 0 DetailTexture_Snow_Set | 1 / 200 / 0.025 |
| 3 | 9 | `TM_ALA_SNOW_CRUNCHY_01` | `SNOW_CRUNCHY_01_Set` | SNOW_CRUNCHY_01_DiffuseMap | SNOW_CRUNCHY_01_NormalMap | Terrain-Ground-Black_HeightMap | SNOW_CRUNCHY_01_Mask1Map | 0 DetailTexture_Snow_Set | 1 / 200 / 1 |
| 3 | 10 | `TM_ALA_SNOW_CRUNCHY_02` | `SNOW_CRUNCHY_02_Set` | SNOW_CRUNCHY_02_DiffuseMap | SNOW_CRUNCHY_02_NormalMap | Terrain-Ground-Black_HeightMap | SNOW_CRUNCHY_02_Mask1Map | 0 DetailTexture_Snow_Set | 1 / 200 / 1 |
| 3 | 11 | `TM_ALA_SNOW_CRUNCHY_03` | `SNOW_CRUNCHY_03_Set` | SNOW_CRUNCHY_03_DiffuseMap | SNOW_CRUNCHY_03_NormalMap | Terrain-Ground-Black_HeightMap | SNOW_CRUNCHY_03_Mask1Map | 0 DetailTexture_Snow_Set | 1 / 200 / 1 |
| 4 | 12 | `TM_ALA_SNOW_POWDER_01` | `SNOW_POWDER_01_Set` | SNOW_POWDER_01_DiffuseMap | SNOW_POWDER_01_NormalMap | Terrain-Ground-Black_HeightMap | SNOW_POWDER_01_Mask1Map | 0 DetailTexture_Snow_Set | 1 / 200 / 1 |
| 4 | 13 | `TM_ALA_SNOW_POWDER_02` | `SNOW_POWDER_02_Set` | SNOW_POWDER_01_DiffuseMap | SNOW_POWDER_02_NormalMap | Terrain-Ground-Black_HeightMap | SNOW_POWDER_02_Mask1Map | 0 DetailTexture_Snow_Set | 1 / 200 / 1 |
| 4 | 14 | `TM_ALA_SNOW_POWDER_03` | `SNOW_POWDER_03_Set` | SNOW_POWDER_01_DiffuseMap | SNOW_POWDER_03_NormalMap | Terrain-Ground-Black_HeightMap | SNOW_POWDER_03_Mask1Map | 0 DetailTexture_Snow_Set | 1 / 200 / 1 |
| 5 | 15 | `TM_ALA_SNOW_STEEP_01` | `SNOW_STEEP_01_Set` | SNOW_STEEP_01_DiffuseMap | SNOW_STEEP_01_NormalMap | Terrain-Ground-Black_HeightMap | SNOW_STEEP_01_Mask1Map | 0 DetailTexture_Snow_Set | 0.9 / 200 / 0.025 |
| 5 | 16 | `TM_ALA_SNOW_STEEP_02` | `SNOW_STEEP_02_Set` | SNOW_STEEP_02_DiffuseMap | SNOW_STEEP_02_NormalMap | Terrain-Ground-Black_HeightMap | SNOW_STEEP_02_Mask1Map | 0 DetailTexture_Snow_Set | 1.1 / 200 / 0.025 |
| 5 | 17 | `TM_ALA_SNOW_STEEP_03` | `SNOW_STEEP_03_Set` | SNOW_STEEP_03_DiffuseMap | SNOW_STEEP_03_NormalMap | Terrain-Ground-Black_HeightMap | SNOW_STEEP_01_Mask1Map | 0 DetailTexture_Snow_Set | 1 / 200 / 0.025 |
| 6 | 18 | `TM_ALA_ICE_Cliff_01` | `ICE_Cliff_01_Set` | ICE_Cliff_01_DiffuseMap | ICE_Cliff_01_NormalMap | ICE_Cliff_01_HeightMap | ICE_Cliff_01_Mask1Map | 3 DetailTexture_IceCliff_Set | 0.5 / 0.8 / 0.4 |
| 6 | 19 | `TM_ALA_ICE_Cliff_02` | `ICE_Cliff_02_Set` | ICE_Cliff_02_DiffuseMap | ICE_Cliff_02_NormalMap | ICE_Cliff_02_HeightMap | ICE_Cliff_02_Mask1Map | 3 DetailTexture_IceCliff_Set | 0.5 / 0.8 / 0.7 |
| 6 | 20 | `TM_ALA_ICE_Cliff_03` | `ICE_Cliff_03_Set` | ICE_Cliff_03_DiffuseMap | ICE_Cliff_03_NormalMap | ICE_Cliff_03_HeightMap | ICE_Cliff_03_Mask1Map | 3 DetailTexture_IceCliff_Set | 0.57 / 0.8 / 0.8 |
| 7 | 21 | `TM_ALA_ICE_CliffThick_01` | `ICE_THICK_01_Set` | ICE_THICK_01_DiffuseMap | ICE_THICK_01_NormalMap | ICE_THICK_01_HeightMap | ICE_THICK_01_Mask1Map | 3 DetailTexture_IceCliff_Set | 0.2 / 3.1 / 0.5 |
| 7 | 22 | `TM_ALA_ICE_CliffThick_02` | `ICE_THICK_02_Set` | ICE_THICK_02_DiffuseMap | ICE_THICK_02_NormalMap | ICE_THICK_02_HeightMap | ICE_THICK_02_Mask1Map | 3 DetailTexture_IceCliff_Set | 0.21 / 1.4 / 0.4 |
| 7 | 23 | `TM_ALA_ICE_CliffThick_03` | `ICE_THICK_03_Set` | ICE_THICK_03_DiffuseMap | ICE_THICK_03_NormalMap | ICE_THICK_03_HeightMap | ICE_THICK_03_Mask1Map | 3 DetailTexture_IceCliff_Set | 0.19 / 3 / 0.4 |
| 8 | 24 | `TM_ALA_ICE_Moraine_01` | `MORAINE_01_Set` | MORAINE_01_DiffuseMap | MORAINE_01_NormalMap | MORAINE_01_HeightMap | MORAINE_01_Mask1Map | 2 DetailTexture_Moraine_Set | 0.4 / 6.5 / 0.025 |
| 8 | 25 | `TM_ALA_ICE_Moraine_02` | `MORAINE_02_Set` | MORAINE_02_DiffuseMap | MORAINE_02_NormalMap | MORAINE_02_HeightMap | MORAINE_02_Mask1Map | 2 DetailTexture_Moraine_Set | 0.6 / 8 / 0.025 |
| 8 | 26 | `TM_ALA_ICE_Moraine_03` | `MORAINE_03_Set` | MORAINE_03_DiffuseMap | MORAINE_03_NormalMap | MORAINE_03_HeightMap | MORAINE_03_Mask1Map | 2 DetailTexture_Moraine_Set | 0.45 / 8 / 0.025 |
| 9 | 27 | `TM_ALA_ICE_Ocean_01` | `ICE_SeaIce_01_Set` | ICE_SeaIce_01_DiffuseMap | ICE_SeaIce_01_NormalMap | ICE_SeaIce_01_HeightMap | ICE_SeaIce_01_Mask1Map | 4 DetailTexture_SeaIce_Set | 0.75 / 5.3 / 0.025 |
| 9 | 28 | `TM_ALA_ICE_Ocean_02` | `ICE_SeaIce_02_Set` | ICE_SeaIce_02_DiffuseMap | ICE_SeaIce_02_NormalMap | ICE_SeaIce_02_HeightMap | ICE_SeaIce_02_Mask1Map | 4 DetailTexture_SeaIce_Set | 0.68 / 5 / 0.025 |
| 9 | 29 | `TM_ALA_ICE_Ocean_03` | `ICE_SeaIce_03_Set` | ICE_SeaIce_03_DiffuseMap | ICE_SeaIce_03_NormalMap | ICE_SeaIce_03_HeightMap | ICE_SeaIce_03_Mask1Map | 4 DetailTexture_SeaIce_Set | 0.92 / 6 / 0.025 |
| 10 | 30 | `TM_ALA_SNOW_ROAD_01` | `ICE_ROAD_01_Set` | ICE_ROAD_01_DiffuseMap | ICE_ROAD_01_NormalMap | Terrain-Ground-Black_HeightMap | ICE_ROAD_01_Mask1Map | 5 DetailTexture_SnowRoad_Set | 0.6 / 200 / 1 |
| 10 | 31 | `TM_ALA_SNOW_ROAD_02` | `ICE_ROAD_02_Set` | ICE_ROAD_02_DiffuseMap | ICE_ROAD_02_NormalMap | Terrain-Ground-Black_HeightMap | ICE_ROAD_02_Mask1Map | 5 DetailTexture_SnowRoad_Set | 0.6 / 200 / 1 |
| 10 | 32 | `TM_ALA_SNOW_ROAD_03` | `ICE_ROAD_03_Set` | ICE_ROAD_03_DiffuseMap | ICE_ROAD_03_NormalMap | Terrain-Ground-Black_HeightMap | ICE_ROAD_03_Mask1Map | 5 DetailTexture_SnowRoad_Set | 0.45 / 200 / 1 |
| 11 | 33 | `TM_ALA_SNOW_GROOMED_01` | `SNOW_GROOMED_01_Set` | SNOW_GROOMED_03_DiffuseMap | SNOW_GROOMED_01_NormalMap | SNOW_GROOMED_03_HeightMap | SNOW_GROOMED_01_Mask1Map | 0 DetailTexture_Snow_Set | 1 / 200 / 1 |
| 11 | 34 | `TM_ALA_SNOW_GROOMED_01` | `SNOW_GROOMED_01_Set` | SNOW_GROOMED_03_DiffuseMap | SNOW_GROOMED_01_NormalMap | SNOW_GROOMED_03_HeightMap | SNOW_GROOMED_01_Mask1Map | 0 DetailTexture_Snow_Set | 1 / 200 / 1 |
| 11 | 35 | `TM_ALA_SNOW_GROOMED_01` | `SNOW_GROOMED_01_Set` | SNOW_GROOMED_03_DiffuseMap | SNOW_GROOMED_01_NormalMap | SNOW_GROOMED_03_HeightMap | SNOW_GROOMED_01_Mask1Map | 0 DetailTexture_Snow_Set | 1 / 200 / 1 |
| 12 | 36 | `TM_ALA_SNOW_GROOMED_02` | `SNOW_GROOMED_02_Set` | SNOW_GROOMED_03_DiffuseMap | SNOW_GROOMED_02_NormalMap | SNOW_GROOMED_03_HeightMap | SNOW_GROOMED_03_Mask1Map | 0 DetailTexture_Snow_Set | 1 / 200 / 1 |
| 12 | 37 | `TM_ALA_SNOW_GROOMED_02` | `SNOW_GROOMED_02_Set` | SNOW_GROOMED_03_DiffuseMap | SNOW_GROOMED_02_NormalMap | SNOW_GROOMED_03_HeightMap | SNOW_GROOMED_03_Mask1Map | 0 DetailTexture_Snow_Set | 1 / 200 / 1 |
| 12 | 38 | `TM_ALA_SNOW_GROOMED_02` | `SNOW_GROOMED_02_Set` | SNOW_GROOMED_03_DiffuseMap | SNOW_GROOMED_02_NormalMap | SNOW_GROOMED_03_HeightMap | SNOW_GROOMED_03_Mask1Map | 0 DetailTexture_Snow_Set | 1 / 200 / 1 |
| 13 | 39 | `TM_ALA_SNOW_GROOMED_03` | `SNOW_GROOMED_03_Set` | SNOW_GROOMED_03_DiffuseMap | SNOW_GROOMED_03_NormalMap | SNOW_GROOMED_03_HeightMap | SNOW_GROOMED_03_Mask1Map | 0 DetailTexture_Snow_Set | 1 / 200 / 1 |
| 13 | 40 | `TM_ALA_SNOW_GROOMED_03` | `SNOW_GROOMED_03_Set` | SNOW_GROOMED_03_DiffuseMap | SNOW_GROOMED_03_NormalMap | SNOW_GROOMED_03_HeightMap | SNOW_GROOMED_03_Mask1Map | 0 DetailTexture_Snow_Set | 1 / 200 / 1 |
| 13 | 41 | `TM_ALA_SNOW_GROOMED_03` | `SNOW_GROOMED_03_Set` | SNOW_GROOMED_03_DiffuseMap | SNOW_GROOMED_03_NormalMap | SNOW_GROOMED_03_HeightMap | SNOW_GROOMED_03_Mask1Map | 0 DetailTexture_Snow_Set | 1 / 200 / 1 |

List 1: 0 `DetailTexture_Snow_Set`, 1 `DetailTexture_Granite_Set`, 2 `DetailTexture_Moraine_Set`, 3 `DetailTexture_IceCliff_Set`, 4 `DetailTexture_SeaIce_Set`, 5 `DetailTexture_SnowRoad_Set`, 6 `DetailTexture_Calcaire_Set`

#### Japan

| g | idx | TM | TextureSet | 0 diffuse | 1 normal | 3 height | 7 mask1 | +0x9f detail set | +0x93 / +0x97 / +0x9b |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 0 | `TM_JAP_SNOW_GROOMED_SNOW_2CM_01` | `SNOW_GROOMED_01_Set` | SNOW_GROOMED_01_DiffuseMap | SNOW_GROOMED_01_NormalMap | ICE_RiverLake_01_HeightMap | SNOW_GROOMED_01_Mask1Map | 0 JAP_DetailTexture_Snow_Set | 1 / 200 / 1 |
| 0 | 1 | `TM_JAP_SNOW_GROOMED_SNOW_2CM_01` | `SNOW_GROOMED_01_Set` | SNOW_GROOMED_01_DiffuseMap | SNOW_GROOMED_01_NormalMap | ICE_RiverLake_01_HeightMap | SNOW_GROOMED_01_Mask1Map | 0 JAP_DetailTexture_Snow_Set | 1 / 200 / 1 |
| 0 | 2 | `TM_JAP_SNOW_GROOMED_SNOW_2CM_01` | `SNOW_GROOMED_01_Set` | SNOW_GROOMED_01_DiffuseMap | SNOW_GROOMED_01_NormalMap | ICE_RiverLake_01_HeightMap | SNOW_GROOMED_01_Mask1Map | 0 JAP_DetailTexture_Snow_Set | 1 / 200 / 1 |
| 1 | 3 | `TM_JAP_SNOW_GROOMED_SNOW_2CM_02` | `SNOW_GROOMED_02_Set` | SNOW_GROOMED_02_DiffuseMap | SNOW_GROOMED_02_NormalMap | ICE_RiverLake_01_HeightMap | SNOW_GROOMED_02_Mask1Map | 0 JAP_DetailTexture_Snow_Set | 1 / 200 / 0.025 |
| 1 | 4 | `TM_JAP_SNOW_GROOMED_SNOW_2CM_02` | `SNOW_GROOMED_02_Set` | SNOW_GROOMED_02_DiffuseMap | SNOW_GROOMED_02_NormalMap | ICE_RiverLake_01_HeightMap | SNOW_GROOMED_02_Mask1Map | 0 JAP_DetailTexture_Snow_Set | 1 / 200 / 0.025 |
| 1 | 5 | `TM_JAP_SNOW_GROOMED_SNOW_2CM_02` | `SNOW_GROOMED_02_Set` | SNOW_GROOMED_02_DiffuseMap | SNOW_GROOMED_02_NormalMap | ICE_RiverLake_01_HeightMap | SNOW_GROOMED_02_Mask1Map | 0 JAP_DetailTexture_Snow_Set | 1 / 200 / 0.025 |
| 2 | 6 | `TM_JAP_SNOW_GROOMED_SNOW_2CM_03` | `SNOW_GROOMED_03_Set` | SNOW_GROOMED_03_DiffuseMap | SNOW_GROOMED_03_NormalMap | ICE_RiverLake_01_HeightMap | SNOW_GROOMED_03_Mask1Map | 0 JAP_DetailTexture_Snow_Set | 1 / 200 / 0.025 |
| 2 | 7 | `TM_JAP_SNOW_GROOMED_SNOW_2CM_03` | `SNOW_GROOMED_03_Set` | SNOW_GROOMED_03_DiffuseMap | SNOW_GROOMED_03_NormalMap | ICE_RiverLake_01_HeightMap | SNOW_GROOMED_03_Mask1Map | 0 JAP_DetailTexture_Snow_Set | 1 / 200 / 0.025 |
| 2 | 8 | `TM_JAP_SNOW_GROOMED_SNOW_2CM_03` | `SNOW_GROOMED_03_Set` | SNOW_GROOMED_03_DiffuseMap | SNOW_GROOMED_03_NormalMap | ICE_RiverLake_01_HeightMap | SNOW_GROOMED_03_Mask1Map | 0 JAP_DetailTexture_Snow_Set | 1 / 200 / 0.025 |
| 3 | 9 | `TM_JAP_SNOW_STEEP_30CM_01` | `SNOW_STEEP_30CM_01_Set` | SNOW_ALL_Vista_DiffuseMap | SNOW_STEEP_30CM_01_NormalMap | ICE_RiverLake_01_HeightMap | SNOW_STEEP_30CM_01_Mask1Map | 0 JAP_DetailTexture_Snow_Set | 1.5 / 200 / 1 |
| 3 | 10 | `TM_JAP_SNOW_STEEP_30CM_02` | `SNOW_STEEP_30CM_02_Set` | SNOW_ALL_Vista_DiffuseMap | SNOW_STEEP_30CM_02_NormalMap | ICE_RiverLake_01_HeightMap | SNOW_STEEP_30CM_02_Mask1Map | 0 JAP_DetailTexture_Snow_Set | 1.5 / 200 / 10 |
| 3 | 11 | `TM_JAP_SNOW_STEEP_30CM_03` | `SNOW_STEEP_30CM_03_Set` | SNOW_ALL_Vista_DiffuseMap | SNOW_STEEP_30CM_03_NormalMap | ICE_RiverLake_01_HeightMap | SNOW_STEEP_30CM_03_Mask1Map | 0 JAP_DetailTexture_Snow_Set | 1.5 / 200 / 10 |
| 4 | 12 | `TM_JAP_SNOW_POWDER_30CM_01` | `SNOW_POWDER_30CM_01_Set` | SNOW_ALL_Vista_DiffuseMap | SNOW_POWDER_30CM_01_NormalMap | ICE_RiverLake_01_HeightMap | SNOW_POWDER_30CM_01_Mask1Map | 0 JAP_DetailTexture_Snow_Set | 3.5 / 200 / 1 |
| 4 | 13 | `TM_JAP_SNOW_POWDER_30CM_02` | `SNOW_POWDER_30CM_02_Set` | SNOW_ALL_Vista_DiffuseMap | SNOW_POWDER_30CM_02_NormalMap | ICE_RiverLake_01_HeightMap | SNOW_POWDER_30CM_02_Mask1Map | 0 JAP_DetailTexture_Snow_Set | 3.5 / 200 / 1 |
| 4 | 14 | `TM_JAP_SNOW_POWDER_30CM_03` | `SNOW_POWDER_30CM_03_Set` | SNOW_ALL_Vista_DiffuseMap | SNOW_POWDER_30CM_03_NormalMap | ICE_RiverLake_01_HeightMap | SNOW_POWDER_30CM_03_Mask1Map | 0 JAP_DetailTexture_Snow_Set | 3.5 / 200 / 1 |
| 5 | 15 | `TM_JAP_SNOW_POWDER_52CM_01` | `SNOW_POWDER_60CM_01_Set` | SNOW_ALL_Vista_DiffuseMap | SNOW_POWDER_60CM_01_NormalMap | ICE_RiverLake_01_HeightMap | SNOW_POWDER_60CM_01_Mask1Map | 0 JAP_DetailTexture_Snow_Set | 2 / 200 / 1 |
| 5 | 16 | `TM_JAP_SNOW_POWDER_52CM_02` | `SNOW_POWDER_60CM_02_Set` | SNOW_ALL_Vista_DiffuseMap | SNOW_POWDER_60CM_02_NormalMap | ICE_RiverLake_01_HeightMap | SNOW_POWDER_60CM_02_Mask1Map | 0 JAP_DetailTexture_Snow_Set | 2 / 200 / 1 |
| 5 | 17 | `TM_JAP_SNOW_POWDER_52CM_03` | `SNOW_POWDER_60CM_03_Set` | SNOW_ALL_Vista_DiffuseMap | SNOW_POWDER_60CM_03_NormalMap | ICE_RiverLake_01_HeightMap | SNOW_POWDER_60CM_03_Mask1Map | 0 JAP_DetailTexture_Snow_Set | 3.5 / 200 / 1 |
| 6 | 18 | `TM_JAP_SNOW_POWDER_74CM_01` | `SNOW_POWDER_90CM_01_Set` | SNOW_ALL_Vista_DiffuseMap | SNOW_POWDER_90CM_01_NormalMap | ICE_RiverLake_01_HeightMap | SNOW_POWDER_90CM_01_Mask1Map | 0 JAP_DetailTexture_Snow_Set | 3.5 / 200 / 1 |
| 6 | 19 | `TM_JAP_SNOW_POWDER_74CM_02` | `SNOW_POWDER_90CM_02_Set` | SNOW_ALL_Vista_DiffuseMap | SNOW_POWDER_90CM_02_NormalMap | ICE_RiverLake_01_HeightMap | SNOW_POWDER_90CM_02_Mask1Map | 0 JAP_DetailTexture_Snow_Set | 2 / 200 / 1 |
| 6 | 20 | `TM_JAP_SNOW_POWDER_74CM_03` | `SNOW_POWDER_90CM_03_Set` | SNOW_ALL_Vista_DiffuseMap | SNOW_POWDER_90CM_03_NormalMap | ICE_RiverLake_01_HeightMap | SNOW_POWDER_90CM_03_Mask1Map | 0 JAP_DetailTexture_Snow_Set | 3.5 / 200 / 1 |
| 7 | 21 | `TM_JAP_SNOW_POWDER_96CM_01` | `SNOW_POWDER_120CM_01_Set` | SNOW_ALL_Vista_DiffuseMap | SNOW_POWDER_120CM_01_NormalMap | ICE_RiverLake_01_HeightMap | SNOW_POWDER_120CM_01_Mask1Map | 0 JAP_DetailTexture_Snow_Set | 3.5 / 200 / 1 |
| 7 | 22 | `TM_JAP_SNOW_POWDER_96CM_02` | `SNOW_POWDER_120CM_02_Set` | SNOW_ALL_Vista_DiffuseMap | SNOW_POWDER_120CM_02_NormalMap | ICE_RiverLake_01_HeightMap | SNOW_POWDER_120CM_02_Mask1Map | 0 JAP_DetailTexture_Snow_Set | 3.5 / 200 / 1 |
| 7 | 23 | `TM_JAP_SNOW_POWDER_96CM_03` | `SNOW_POWDER_120CM_03_Set` | SNOW_ALL_Vista_DiffuseMap | SNOW_POWDER_120CM_03_NormalMap | ICE_RiverLake_01_HeightMap | SNOW_POWDER_120CM_03_Mask1Map | 0 JAP_DetailTexture_Snow_Set | 3.5 / 200 / 1 |
| 8 | 24 | `TM_JAP_ROCKS_Beach_01` | `ROCKS_Beach_01_Set` | ROCKS_Beach_01_DiffuseMap | ROCKS_Beach_01_NormalMap | ROCKS_Beach_01_HeightMap | ROCKS_Beach_01_Mask1Map | 1 **out of range** | 1.5 / 200 / 0.29 |
| 8 | 25 | `TM_JAP_ROCKS_Beach_02` | `ROCKS_Beach_02_Set` | ROCKS_Beach_01_DiffuseMap | ROCKS_Beach_01_NormalMap | ROCKS_Beach_01_HeightMap | ROCKS_Beach_01_Mask1Map | 1 **out of range** | 1.5 / 200 / 0.32 |
| 8 | 26 | `TM_JAP_ROCKS_Beach_03` | `ROCKS_Beach_03_Set` | ROCKS_Beach_01_DiffuseMap | ROCKS_Beach_01_NormalMap | ROCKS_Beach_01_HeightMap | ROCKS_Beach_01_Mask1Map | 1 **out of range** | 1.5 / 200 / 0.32 |
| 9 | 27 | `TM_JAP_ICE_RiverLake_01` | `ICE_RiverLake_01_Set` | ICE_RiverLake_01_DiffuseMap | ICE_RiverLake_01_NormalMap | ICE_RiverLake_01_HeightMap | ICE_RiverLake_01_Mask1Map | 3 **out of range** | 1 / 50 / 0.5 |
| 9 | 28 | `TM_JAP_ICE_RiverLake_02` | `ICE_RiverLake_02_Set` | ICE_RiverLake_02_DiffuseMap | ICE_RiverLake_02_NormalMap | ICE_RiverLake_01_HeightMap | ICE_RiverLake_02_Mask1Map | 3 **out of range** | 1 / 50 / 0.4 |
| 9 | 29 | `TM_JAP_ICE_RiverLake_03` | `ICE_RiverLake_03_Set` | ICE_RiverLake_03_DiffuseMap | ICE_RiverLake_03_NormalMap | ICE_RiverLake_01_HeightMap | ICE_RiverLake_03_Mask1Map | 3 **out of range** | 1 / 50 / 0.4 |
| 10 | 30 | `TM_JAP_SNOW_ROAD_01` | `ICE_ROAD_01_Set` | ICE_ROAD_01_DiffuseMap | ICE_ROAD_01_NormalMap | ICE_RiverLake_01_HeightMap | ICE_ROAD_01_Mask1Map | 5 **out of range** | 0.5 / 10 / 1 |
| 10 | 31 | `TM_JAP_SNOW_ROAD_02` | `ICE_ROAD_02_Set` | ICE_ROAD_02_DiffuseMap | ICE_ROAD_02_NormalMap | ICE_RiverLake_01_HeightMap | ICE_ROAD_01_Mask1Map | 5 **out of range** | 0.5 / 200 / 1 |
| 10 | 32 | `TM_JAP_SNOW_ROAD_03` | `ICE_ROAD_03_Set` | ICE_ROAD_03_DiffuseMap | ICE_ROAD_03_NormalMap | ICE_RiverLake_01_HeightMap | ICE_ROAD_01_Mask1Map | 5 **out of range** | 0.5 / 200 / 1 |
| 11 | 33 | `TM_JAP_SNOW_GROOMED_COMPETITION_SNOW_2CM_01` | `SNOW_GROOMED_01_Set` | SNOW_GROOMED_01_DiffuseMap | SNOW_GROOMED_01_NormalMap | ICE_RiverLake_01_HeightMap | SNOW_GROOMED_01_Mask1Map | 0 JAP_DetailTexture_Snow_Set | 1 / 200 / 0.025 |
| 11 | 34 | `TM_JAP_SNOW_GROOMED_COMPETITION_SNOW_2CM_01` | `SNOW_GROOMED_01_Set` | SNOW_GROOMED_01_DiffuseMap | SNOW_GROOMED_01_NormalMap | ICE_RiverLake_01_HeightMap | SNOW_GROOMED_01_Mask1Map | 0 JAP_DetailTexture_Snow_Set | 1 / 200 / 0.025 |
| 11 | 35 | `TM_JAP_SNOW_GROOMED_COMPETITION_SNOW_2CM_01` | `SNOW_GROOMED_01_Set` | SNOW_GROOMED_01_DiffuseMap | SNOW_GROOMED_01_NormalMap | ICE_RiverLake_01_HeightMap | SNOW_GROOMED_01_Mask1Map | 0 JAP_DetailTexture_Snow_Set | 1 / 200 / 0.025 |
| 12 | 36 | `TM_JAP_SNOW_GROOMED_COMPETITION_SNOW_2CM_02` | `SNOW_GROOMED_02_Set` | SNOW_GROOMED_02_DiffuseMap | SNOW_GROOMED_02_NormalMap | ICE_RiverLake_01_HeightMap | SNOW_GROOMED_02_Mask1Map | 0 JAP_DetailTexture_Snow_Set | 1 / 200 / 0.025 |
| 12 | 37 | `TM_JAP_SNOW_GROOMED_COMPETITION_SNOW_2CM_02` | `SNOW_GROOMED_02_Set` | SNOW_GROOMED_02_DiffuseMap | SNOW_GROOMED_02_NormalMap | ICE_RiverLake_01_HeightMap | SNOW_GROOMED_02_Mask1Map | 0 JAP_DetailTexture_Snow_Set | 1 / 200 / 0.025 |
| 12 | 38 | `TM_JAP_SNOW_GROOMED_COMPETITION_SNOW_2CM_02` | `SNOW_GROOMED_02_Set` | SNOW_GROOMED_02_DiffuseMap | SNOW_GROOMED_02_NormalMap | ICE_RiverLake_01_HeightMap | SNOW_GROOMED_02_Mask1Map | 0 JAP_DetailTexture_Snow_Set | 1 / 200 / 0.025 |
| 13 | 39 | `TM_JAP_SNOW_GROOMED_COMPETITION_SNOW_2CM_03` | `SNOW_GROOMED_03_Set` | SNOW_GROOMED_03_DiffuseMap | SNOW_GROOMED_03_NormalMap | ICE_RiverLake_01_HeightMap | SNOW_GROOMED_03_Mask1Map | 0 JAP_DetailTexture_Snow_Set | 1 / 200 / 0.025 |
| 13 | 40 | `TM_JAP_SNOW_GROOMED_COMPETITION_SNOW_2CM_03` | `SNOW_GROOMED_03_Set` | SNOW_GROOMED_03_DiffuseMap | SNOW_GROOMED_03_NormalMap | ICE_RiverLake_01_HeightMap | SNOW_GROOMED_03_Mask1Map | 0 JAP_DetailTexture_Snow_Set | 1 / 200 / 0.025 |
| 13 | 41 | `TM_JAP_SNOW_GROOMED_COMPETITION_SNOW_2CM_03` | `SNOW_GROOMED_03_Set` | SNOW_GROOMED_03_DiffuseMap | SNOW_GROOMED_03_NormalMap | ICE_RiverLake_01_HeightMap | SNOW_GROOMED_03_Mask1Map | 0 JAP_DetailTexture_Snow_Set | 1 / 200 / 0.025 |

List 1: 0 `JAP_DetailTexture_Snow_Set`

### 3.6 Tiling scale

**No TM field can be VERIFIED as the tiling scale from data alone.** The records carry no field names,
no terrain-shader GPU capture exists (terrain-blend.md §1: the heightfield shader is not in the data), the
base diffuse maps are all 2048², so the texture size cannot calibrate units, and the only Material using an
`STP_*TER_*` texture (`STP_MAT_SnowFragment`) is unrelated (`summit-import material --all` → one hit).
Candidates, best first (values VERIFIED, roles UNVERIFIED):

1. **f32 +0x93.** Per family (Alpes rocks 0.25..0.35, snow and ice 0.7..1.1; Alaska rocks 0.39..0.47; Japan
   powder 2..3.5) and jittered about ±10 % between the variants of one group (Alpes Granite 0.32/0.31/0.29,
   RiverLake 1/0.9/1.1, SNOWPARK 1/1.1/0.9), which is how repeats are usually broken up. Readings:
   repeats per metre (a rock tile of 2.9..4 m, snow 1 m) or a multiplier on a map-wide scale.
2. **f32 +0x9b.** 1 or 0.025 (= 1/40) on most entries; equal to +0x93 on Alpes Calcaire/Gneiss/Granite. A
   detail-texture tiling relative to the base, or a strength.
3. **f32 +0x97.** 200 by default; 10 on Granite, 50 on Dolomie and ice. Too large for repeats per metre;
   more likely a distance or an exponent.
4. **f32 +0xb1.** 50 / 5 / 8 only.

Map-wide candidates: `Terrain_TemplateMap` embeds `VisualTerrainComponent` (`0x6e155158`; floats such as
`5,5,5,5, 15,15,15, 31, 200,500,200,100, …, 50,50,50,50`) and `TerrainSettings` (after the noise ref: Alpes
`100, 0.05, 1.25`, Japan `500, 0.008, 5`). Class names VERIFIED by crc32 (`classes.out`); values VERIFIED
(`templatemap.out`); meanings UNVERIFIED.

What settles it (follow-up): a DXVK/MoltenVK capture of one terrain draw (allowed path, CLAUDE.md rule 3),
matching the per-layer constants (terrain-blend.md uses `CB3:6.xy`, `14.xy`, `20.xy`, `21.xy` as tilings)
against the bound TMs' 0.35 / 0.25 / 1.0. Another route is measuring the repeat period in footage against
known geometry. Until then a renderer can use `uv = world_xz · f93 / S` with one global `S` tuned by eye
(UNVERIFIED).

Reproduce (§3.5, §3.6): `PY=$STEEP_DATA/shared/lab-venv/bin/python`; `L=tools/lab/P5-14`; `$PY
$L/mapping/step1.py; $PY $L/mapping/mapping.py; $PY $L/mapping/other_sets.py >
$STEEP_DATA/P5-14/A/other_sets.out; $PY $L/mapping/render.py > $STEEP_DATA/P5-14/A/render.out`; in
`$L/tiling`: `$PY census.py; $PY refs.py; $PY xref.py; $PY layers.py; $PY classes.py; $PY nicefloats.py Alpes
Terrain_TemplateMap; <HOME>/steep-wasm/tools/.venv/bin/python check_ksy.py` → `terrain-material.ksy: 294 ok, 0 errors` (needs
`kaitai-struct-compiler`); `$PY $L/spec/spec_tables.py`. Inputs: G-08's extracted whole-map entries
(§1, part B), `$STEEP_DATA/P2-03/lab/records.tsv`, `$STEEP_DATA/cache/textures/index.tsv`. Outputs under
`$STEEP_DATA/P5-14/{A,B}/`.

---

## 4. Per-region tables and class histograms

All values below are **VERIFIED** from `$STEEP_DATA/cache/terrain/<R>/surface.json` (written by
`summit-import terrain-surfaces`, §7) and agree with E's `histograms.tsv` / `group_stats.tsv`.
km² = texels × 3.8147 m² (1.953125² m) / 10⁶; % of the 67,108,864-texel L6 image (256 km²).
Friction is the PM f32 at +0x2e7, rounded (raw values such as 0.7000008 and 0.69999999 both show as
0.70). Restitution is 0.05 for every terrain PM. "TM family" is the TM name without its variant
suffix.

### 4.1 Alpes (11 groups)

| g | code | TM family | CM | PM | st | friction | km² | % |
|---|---|---|---|---|---|---|---|---|
| 0 | 0 | ALP_ROCKS_Calcaire | CM_Rock | PM_Rock | 4 | 1.00 | 0.50 | 0.20 |
| 1 | 3 | ALP_ROCKS_Dolomie | CM_Rock | PM_Rock | 4 | 1.00 | 1.35 | 0.53 |
| 2 | 6 | ALP_ROCKS_Flysch | CM_Rock | PM_Rock | 4 | 1.00 | 0 | 0 |
| 3 | 9 | ALP_ROCKS_Gneiss | CM_Rock | PM_Rock | 4 | 1.00 | 0.57 | 0.22 |
| 4 | 12 | ALP_ROCKS_Granite | CM_Rock | PM_Rock | 4 | 1.00 | 7.27 | 2.84 |
| 5 | 15 | ALP_SNOW_THIN | CM_SNOW_Thin_Ground | PM_SNOW_Thin_Ground | 37 | 0.70 | 27.08 | 10.58 |
| 6 | 18 | ALP_SNOW_CRUNCHY | CM_SNOW_Crunchy_Ground | PM_SNOW_Crunchy_Ground | 28 | 0.70 | 38.86 | 15.18 |
| 7 | 21 | ALP_SNOW_POWDER | CM_SNOW_Powder_Ground | PM_SNOW_Powder_Ground | 37 | 0.70 | 167.10 | 65.27 |
| 8 | 24 | ALP_ICE_Cliff | CM_Ice | PM_Ice | 27 | 0.10 | 8.52 | 3.33 |
| 9 | 27 | ALP_ICE_RiverLake | CM_Ice_Water | PM_Ice_Water | 26 | 0.10 | 3.93 | 1.53 |
| 10 | 30 | ALP_SNOW_THIN_SNOWPARK | CM_SNOW_Thin_SParkPipe_Ground | PM_SNOW_Thin_SParkPipe_Ground | 35 | 0.25 | 0.82 | 0.32 |

By surface_type: 37 75.85 %, 28 15.18 %, 4 3.79 %, 27 3.33 %, 26 1.53 %, 35 0.32 %. Group 2
(ROCKS_Flysch) never occurs.

### 4.2 AlaskaTUX (14 groups)

| g | code | TM family | CM | PM | st | friction | km² | % |
|---|---|---|---|---|---|---|---|---|
| 0 | 0 | ALA_ROCKS_Calcaire | CM_Rock | PM_Rock | 4 | 1.00 | 1.46 | 0.57 |
| 1 | 3 | ALA_ROCKS_Granite | CM_Rock | PM_Rock | 4 | 1.00 | 1.00 | 0.39 |
| 2 | 6 | ALA_SNOW_THIN | CM_SNOW_Thin_Ground | PM_SNOW_Thin_Ground | 37 | 0.70 | 20.50 | 8.01 |
| 3 | 9 | ALA_SNOW_CRUNCHY | CM_SNOW_Crunchy_Ground | PM_SNOW_Crunchy_Ground | 28 | 0.70 | 42.46 | 16.59 |
| 4 | 12 | ALA_SNOW_POWDER | CM_SNOW_Powder_Ground | PM_SNOW_Powder_Ground | 37 | 0.70 | 152.56 | 59.59 |
| 5 | 15 | ALA_SNOW_STEEP | CM_SNOW_Thin_Ground | PM_SNOW_Thin_Ground | 37 | 0.70 | 9.34 | 3.65 |
| 6 | 18 | ALA_ICE_Cliff | CM_Ice | PM_Ice | 27 | 0.10 | 4.11 | 1.61 |
| 7 | 21 | ALA_ICE_CliffThick | CM_Ice | PM_Ice | 27 | 0.10 | 1.25 | 0.49 |
| 8 | 24 | ALA_ICE_Moraine | CM_Ice_Water | PM_Ice_Water | 26 | 0.10 | 1.44 | 0.56 |
| 9 | 27 | ALA_ICE_Ocean | CM_Ice_Water | PM_Ice_Water | 26 | 0.10 | 21.08 | 8.23 |
| 10 | 30 | ALA_SNOW_ROAD | CM_SNOW_Powder_Ground | PM_SNOW_Powder_Ground | 37 | 0.70 | 0.42 | 0.17 |
| 11 | 33 | ALA_SNOW_GROOMED (`_01` ×3) | CM_SNOW_Groomed_Snow_2CM | PM_SNOW_Groomed_Snow_2CM | 31 | 0.70 | 0 | 0 |
| 12 | 36 | ALA_SNOW_GROOMED (`_02` ×3) | CM_SNOW_Groomed_Snow_2CM | PM_SNOW_Groomed_Snow_2CM | 31 | 0.70 | 0 | 0 |
| 13 | 39 | ALA_SNOW_GROOMED (`_03` ×3) | CM_SNOW_Groomed_Snow_2CM | PM_SNOW_Groomed_Snow_2CM | 31 | 0.70 | 0.37 | 0.14 |

By surface_type: 37 71.42 %, 28 16.59 %, 26 8.80 %, 27 2.10 %, 4 0.96 %, 31 0.14 %. Notable links:
`ALA_SNOW_STEEP → CM_SNOW_Thin_Ground`, `ALA_SNOW_ROAD → CM_SNOW_Powder_Ground`,
`ALA_ICE_Moraine → CM_Ice_Water`.

### 4.3 Japan (14 groups)

| g | code | TM family | CM | PM | st | friction | km² | % |
|---|---|---|---|---|---|---|---|---|
| 0 | 0 | JAP_SNOW_GROOMED_SNOW_2CM (`_01` ×3) | CM_SNOW_Groomed_Snow_2CM | PM_SNOW_Groomed_Snow_2CM | 31 | 0.70 | 19.89 | 7.77 |
| 1 | 3 | JAP_SNOW_GROOMED_SNOW_2CM (`_02` ×3) | CM_SNOW_Groomed_Snow_2CM | PM_SNOW_Groomed_Snow_2CM | 31 | 0.70 | 0 | 0 |
| 2 | 6 | JAP_SNOW_GROOMED_SNOW_2CM (`_03` ×3) | CM_SNOW_Groomed_Snow_2CM | PM_SNOW_Groomed_Snow_2CM | 31 | 0.70 | 0.62 | 0.24 |
| 3 | 9 | JAP_SNOW_STEEP_30CM | CM_SNOW_Groomed_Competition_Snow_2CM | PM_SNOW_Groomed_Competition_Snow_2CM | 39 | 0.70 | 2.27 | 0.88 |
| 4 | 12 | JAP_SNOW_POWDER_30CM | CM_SNOW_Powder_30CM | PM_SNOW_Powder_30CM | 37 | 0.70 | 41.51 | 16.22 |
| 5 | 15 | JAP_SNOW_POWDER_52CM | CM_SNOW_Powder_52CM | PM_SNOW_Powder_52CM | 25 | 0.70 | 48.28 | 18.86 |
| 6 | 18 | JAP_SNOW_POWDER_74CM | CM_SNOW_Powder_74CM | PM_SNOW_Powder_74CM | 25 | 0.70 | 45.88 | 17.92 |
| 7 | 21 | JAP_SNOW_POWDER_96CM | CM_SNOW_Powder_96CM | PM_SNOW_Powder_96CM | 25 | 0.70 | 36.23 | 14.15 |
| 8 | 24 | JAP_ROCKS_Beach | CM_Rock | PM_Rock | 4 | 1.00 | 58.93 | 23.02 |
| 9 | 27 | JAP_ICE_RiverLake | CM_Ice | PM_Ice | 27 | 0.10 | 0.18 | 0.07 |
| 10 | 30 | JAP_SNOW_ROAD | CM_SNOW_Groomed_Competition_Snow_2CM | PM_SNOW_Groomed_Competition_Snow_2CM | 39 | 0.70 | 1.80 | 0.70 |
| 11 | 33 | JAP_SNOW_GROOMED_COMPETITION_SNOW_2CM (`_01` ×3) | CM_SNOW_Groomed_Competition_Snow_2CM | PM_SNOW_Groomed_Competition_Snow_2CM | 39 | 0.70 | 0.04 | 0.01 |
| 12 | 36 | JAP_SNOW_GROOMED_COMPETITION_SNOW_2CM (`_02` ×3) | CM_SNOW_Groomed_Competition_Snow_2CM | PM_SNOW_Groomed_Competition_Snow_2CM | 39 | 0.70 | 0.23 | 0.09 |
| 13 | 39 | JAP_SNOW_GROOMED_COMPETITION_SNOW_2CM (`_03` ×3) | CM_SNOW_Groomed_Competition_Snow_2CM | PM_SNOW_Groomed_Competition_Snow_2CM | 39 | 0.70 | 0.15 | 0.06 |

By surface_type: 25 50.93 %, 4 23.02 %, 37 16.22 %, 31 8.01 %, 39 1.75 %, 27 0.07 %. Notable links:
`JAP_SNOW_STEEP_30CM` and `JAP_SNOW_ROAD → CM_SNOW_Groomed_Competition_Snow_2CM`;
`JAP_ICE_RiverLake → CM_Ice`, whereas `ALP_ICE_RiverLake → CM_Ice_Water`. No terrain TM in any
region uses PM_Water, PM_Concrete, PM_Asphalt or PM_Stone_Wall (B, VERIFIED).

### 4.4 `surface_type` merges PhysicsMaterials

`surface_type` is one value per PM *class* (surfaces.md §4), and several terrain PMs share one:

| Region | surface_type | PMs merged | groups |
|---|---|---|---|
| Alpes | 37 | PM_SNOW_Thin_Ground, PM_SNOW_Powder_Ground | 5, 7 |
| AlaskaTUX | 37 | PM_SNOW_Thin_Ground, PM_SNOW_Powder_Ground | 2, 4, 5, 10 |
| Japan | 25 | PM_SNOW_Powder_52CM, _74CM, _96CM | 5, 6, 7 |

(VERIFIED, `surface.json` `surface_classes`.) Japan's PM_SNOW_Powder_30CM is also class 37. So a
consumer that needs the exact PM (snow depth from the NNcm names, thin vs powder, or the PM's own
fluid parameters) must read `layers.r8` and map the group through `surface.json`'s `groups`
table, not `surface.r8`.

### 4.5 Coarse classes

| Region | snow | ice (Ice + Ice_Water) | rock | groomed | park |
|---|---|---|---|---|---|
| Alpes | 233.04 km² (91.0 %) | 12.45 (4.9 %) | 9.69 (3.8 %) | – | 0.82 (0.3 %) |
| AlaskaTUX | 225.29 (88.0 %) | 27.89 (10.9 %) | 2.45 (1.0 %) | 0.37 (0.1 %) | – |
| Japan | 171.91 (67.2 %) | 0.18 (0.07 %) | 58.93 (23.0 %) | 24.99 (9.8 %) | – |

VERIFIED (E, `analyze.py` → `histograms.tsv`, `coarse` rows). Japan's "groomed" includes
`SNOW_STEEP_30CM` and `SNOW_ROAD`, whose CM is the competition piste.

---

## 5. What the ground is, per region

### 5.1 Per-group statistics

Method (E, `analyze.py`): altitude and slope from `cache/terrain/<R>/ground.r16` (2 m
FloorHeightData), bilinear at the L6 texel centres; slope by central difference on the L6 grid;
medians and p10/p90 from 0.5 m and 0.05° histograms; colour = per-channel median of the section-1
BC1 colour over each tile's own 128² area, decoded per L6 node. All values **VERIFIED** (E,
`group_stats.tsv`); groups with 0 texels are omitted.

| Region | Group (TM family) | alt median (p10–p90) m | slope median (p10–p90) ° | colour median RGB |
|---|---|---|---|---|
| Alpes | 0 ROCKS_Calcaire | 2436 (1279–3208) | 71.8 (58.7–78.9) | 126,130,129 |
| Alpes | 1 ROCKS_Dolomie | 1988 (1315–3397) | 73.1 (61.9–79.5) | 132,130,132 |
| Alpes | 3 ROCKS_Gneiss | 1962 (1126–2869) | 72.6 (63.0–78.6) | 107,105,101 |
| Alpes | 4 ROCKS_Granite | 3726 (2310–4923) | 74.4 (65.6–80.4) | 115,113,115 |
| Alpes | 5 SNOW_THIN | 3040 (1522–4652) | 60.6 (45.0–68.9) | 219,219,222 |
| Alpes | 6 SNOW_CRUNCHY | 2866 (1365–4546) | 52.6 (38.2–62.2) | 219,219,222 |
| Alpes | 7 SNOW_POWDER | 2543 (825–4304) | 33.1 (14.6–50.0) | 219,219,222 |
| Alpes | 8 ICE_Cliff | 3223 (1677–4776) | 67.6 (56.9–73.7) | 151,157,156 |
| Alpes | 9 ICE_RiverLake | 1337 (641–3414) | 0.03 (0.03–14.8) | 74,109,115 |
| Alpes | 10 SNOW_THIN_SNOWPARK | 1588 (668–3144) | 32.2 (16.7–50.5) | 219,219,222 |
| AlaskaTUX | 0 ROCKS_Calcaire | 2388 (1147–3529) | 72.9 (62.5–78.9) | 107,105,107 |
| AlaskaTUX | 1 ROCKS_Granite | 2749 (1229–4222) | 73.0 (64.8–78.0) | 74,76,74 |
| AlaskaTUX | 2 SNOW_THIN | 3021 (1304–4945) | 59.2 (42.0–67.5) | 219,219,222 |
| AlaskaTUX | 3 SNOW_CRUNCHY | 2981 (1309–4865) | 52.2 (35.6–62.4) | 219,219,222 |
| AlaskaTUX | 4 SNOW_POWDER | 2289 (358–4440) | 34.3 (1.6–53.5) | 219,219,222 |
| AlaskaTUX | 5 SNOW_STEEP | 2976 (1188–4893) | 63.6 (38.5–71.4) | 219,219,222 |
| AlaskaTUX | 6 ICE_Cliff | 2655 (1250–4095) | 67.8 (58.1–73.5) | 132,138,140 |
| AlaskaTUX | 7 ICE_CliffThick | 349 (349–2652) | 0.03 (0.03–53.2) | 206,210,214 |
| AlaskaTUX | 8 ICE_Moraine | 1905 (723–3107) | 38.8 (20.2–60.3) | 137,138,140 |
| AlaskaTUX | 9 ICE_Ocean | 349 (349–349) | 0.03 (0.03–0.03) | 165,171,173 |
| AlaskaTUX | 10 SNOW_ROAD | 739 (473–1767) | 11.9 (3.2–36.9) | 208,210,214 |
| AlaskaTUX | 13 SNOW_GROOMED | 1422 (1183–1753) | 30.4 (15.1–46.2) | 217,220,222 |
| Japan | 0 GROOMED_SNOW_2CM | 1494 (792–3117) | 36.6 (14.6–56.4) | 244,243,244 |
| Japan | 2 GROOMED_SNOW_2CM | 1477 (790–3022) | 36.2 (12.4–56.9) | 244,243,244 |
| Japan | 3 SNOW_STEEP_30CM | 2035 (659–3536) | 63.2 (46.2–71.2) | 244,243,244 |
| Japan | 4 SNOW_POWDER_30CM | 1770 (608–3451) | 52.0 (14.8–68.5) | 244,243,244 |
| Japan | 5 SNOW_POWDER_52CM | 1684 (650–3503) | 46.4 (19.2–61.8) | 244,243,244 |
| Japan | 6 SNOW_POWDER_74CM | 1640 (646–3454) | 39.4 (21.3–56.6) | 244,243,244 |
| Japan | 7 SNOW_POWDER_96CM | 1653 (661–3463) | 40.7 (24.6–55.5) | 244,243,244 |
| Japan | 8 ROCKS_Beach | 285 (35–499) | 38.4 (10.6–63.5) | 107,101,93 |
| Japan | 9 ICE_RiverLake | 3526 (2518–3987) | 20.0 (6.2–46.1) | 156,174,181 |
| Japan | 10 SNOW_ROAD | 1754 (815–2931) | 42.2 (20.0–60.7) | 222,223,222 |
| Japan | 11 GROOMED_COMPETITION | 1464 (1335–1560) | 34.7 (22.2–44.9) | 244,243,244 |
| Japan | 12 GROOMED_COMPETITION | 1543 (1258–1990) | 31.8 (20.1–40.8) | 244,243,244 |
| Japan | 13 GROOMED_COMPETITION | 1592 (1237–2127) | 35.3 (22.9–44.9) | 244,243,244 |

**Caveat: `ground.r16` is not always the visible terrain.** FloorHeightData lies below the
rendered terrain in places (G-08/C, world-coords.md §5.1). **VERIFIED** (E, `hcheck.py` →
`hcheck.log`, trailer range × 6800): share of L6 nodes whose ground minimum is more than 20 m below
the trailer minimum is Alpes 0.018, AlaskaTUX 0.172, Japan 0.149; median ground min − trailer min
is +2.1 to +2.9 m; Japan ICE_RiverLake has `31944` texels with ground inside the trailer range ±5 m
and `13117` below it. So the AlaskaTUX and Japan altitude/slope figures are approximate, and the
Japan ICE_RiverLake row (3526 m, 20°) is the least reliable. Re-run once `.tbf` heights are decoded
(§8).

### 5.2 Reading (UNVERIFIED; names plus the VERIFIED statistics above)

- **Common pattern.** Rock and cliff ice sit on the steepest ground (≈ 70° median). "STEEP" and
  "THIN" snow are steeper (≈ 60°) than crunchy snow (≈ 52°), which is steeper than powder (≈ 33°).
  Lakes and sea are flat. Rock colours are grey/brown and lake ice blue-green; all snow groups
  saturate to the same white. This is independent evidence that the group → TM mapping and the
  geometry are right.
- **Alpes.** Mostly standard powder (65 %) on moderate slopes, with crunchy and thin snow on
  steeper ground and bare rock (mainly Granite, high up) on cliffs. Cliff ice at altitude, frozen
  lakes and rivers on flat valley floors (image check: the ICE_RiverLake patches coincide with flat
  floors in the hillshade), and a small snowpark-pipe class (0.8 km²) around 1600 m. Friction is
  0.70 on snow, 0.25 in the snowpark class, 0.10 on ice and 1.0 on rock.
- **AlaskaTUX.** Similar snow mix (60 % powder) plus a large frozen sea: ICE_Ocean (21 km²) and
  ICE_CliffThick sit at exactly the region minimum, 348.8 m, which matches the 4,203 flat trailer
  nodes in tbf.md §3.2. ICE_Moraine (sloped, 39°) is also `Ice_Water`. Groomed snow is only group
  13 (0.37 km², ≈ 1400 m), and SNOW_ROAD is low and gentle (739 m, 12°) but uses the powder PM.
- **Japan.** A depth-graded powder world: 30/52/74/96 cm powder classes cover 67 %, with the 30 cm
  class on the steepest of them (52°). Groomed pistes (8 %) and competition snow, which also covers
  `SNOW_STEEP_30CM` and `SNOW_ROAD`, make up the rest of the snow. ROCKS_Beach (23 %) is low ground
  (median 285 m, p90 499 m), i.e. below the z = 500 m sea planes (§6.1): much of it is shore and
  sea bed under placed water, which is why placed water lies over it (§6.3). Lake ice (`PM_Ice`) is
  rare.

---

## 6. Agreement with placed collision materials

### 6.1 Placed collision rasters (G-08/C)

Placed static collision (snow-park features, buildings, ice blocks, lakes, rocks) was rasterised
onto the same L6 grid. The terrain itself has no collision trimesh (linkage.md §5), so this is
the only independent per-location material source in the data.

- **Objects.** Every Entity, EntityGroup and embedded child of the patch-resolved region pack with
  its world matrix and its single shape ref (physics component `0x228f402a`, linkage.md §1.1),
  deduplicated by object id (duplicates are byte-identical: `dup objs with shapes 514 identical 514`
  in Alpes, VERIFIED). Shapes are placed as in linkage.md §6: a CompoundShape child at
  `p_w = [p,1]·C_i·M_object` (row vectors), no group placement matrices; capsules, spheres and
  trimeshes without a material list (region polygons) are skipped.
- **Materials.** Each triangle takes its CM from the per-triangle table (shapes.md §2.3). Triangles
  with a non-world PM are dropped: PM_AutoActivationShapes, PM_Capsule, PM_DropZone,
  PM_FX_SnowFrag, the three ragdoll PMs, PM_VOL_Branch/_Branch_Snow/_Bush and
  PM_SNOW_Powder_Roof_CamOnly (chosen by name and flags, UNVERIFIED as game behaviour). Null CM refs
  (id 0) occur only in drop-zone/balloon helpers and are dropped (VERIFIED by a probe over all
  cached trimeshes).
- **Raster** (`raster.c`). Every texel centre inside a triangle's xy projection (edges inclusive)
  takes z from the triangle plane. A triangle that covers no texel centre is written once at its
  centroid texel, so rails and small rocks survive. Vertical triangles are skipped. Ground h is
  `ground.r16`, bilinear at the texel centre.
  - `on_ground`: CM of the topmost sample with |z − h| ≤ 1.5 m;
  - `any_cover`: CM of the topmost sample at any height; `any_cover_dz` stores z_top − h as f16;
  - `*_with_packed`: plus packed instances (world-entities.md §5) with their template's shape and
    the instance matrix `diag(scale)·Rᵀ(q)` + position, `_FAKE` groups excluded. That instances
    inherit their template's collision is **UNVERIFIED** (linkage.md §6).

**VERIFIED** (C, `placed.py` → `placed_<R>_stats.json`):

| Region | objects placed | trimesh leaves | triangles | on_ground texels | any_cover texels | on_ground with packed |
|---|---|---|---|---|---|---|
| Alpes | 28,329 | 28,219 | 4,815,612 | 124,087 | 313,234 | 3,165,430 |
| AlaskaTUX | 11,048 | 11,024 | 953,824 | 22,270 | 71,706 | 1,775,422 |
| Japan | 12,389 | 12,294 | 2,886,999 | 194,774 | 16,191,235 | 2,005,771 |

Top on_ground CMs (entities/groups/children only): Alpes CM_Wood_Hard 20,255, CM_Stone_Wall 17,583,
CM_Concrete 15,361; AlaskaTUX CM_Wood_Hard_NORagdoll 5,465, CM_Wood_SNOW 1,707, CM_Concrete 1,566;
Japan CM_Water 174,808, CM_Rock 2,785, CM_Wood_Hard_NORagdoll 2,569. With packed instances CM_Rock
dominates everywhere (Alpes 2,368,912, AlaskaTUX 1,628,389, Japan 1,792,969), and Alpes gains
CM_Ice 447,356 from packed ice blocks. Japan's any_cover is mostly CM_Water (16,037,153 texels):
sea planes at z = 500 (104 `SeaTile` and 9 `COL` leaves, all at min z 500.00) and lake planes
(`Pool_Default`) whose rectangles reach past the shore.

### 6.2 Method of comparison (E)

- Placed material: the PM of the C legend. Terrain material: group → PM (§4).
- Rates are fractions of placed texels, under three rules: exact `surface_type`; **coarse** class
  (snow / groomed / park / ice incl. Ice_Water / rock / water / vegetation / man-made / special);
  **lenient** class (snow+groomed+park, ice+water, rock).
- "Terrain-like" (t-l) restricts to placed texels whose coarse class is snow, groomed, park, ice,
  rock or water.

### 6.3 Results

**VERIFIED** (E, `report.py` → `agreement.md`, `agreement.json`):

| Region | Variant | Placed texels | t-l share | t-l exact st | t-l coarse | t-l lenient | t-l excl. water: coarse / lenient |
|---|---|---|---|---|---|---|---|
| Alpes | on_ground | 124,087 | 27.1 % | 64.7 % | 74.6 % | 86.5 % | 74.6 % / 86.5 % |
| Alpes | on_ground_with_packed | 3,165,430 | 89.9 % | 29.0 % | 29.2 % | 29.3 % | 29.2 % / 29.3 % |
| Alpes | any_cover, \|dz\| < 3 m | 82,862 | 43.1 % | 63.9 % | 75.5 % | 90.2 % | – |
| AlaskaTUX | on_ground | 22,270 | 28.3 % | 52.0 % | 54.3 % | 87.8 % | – |
| AlaskaTUX | on_ground_with_packed | 1,775,422 | 97.5 % | 13.7 % | 13.7 % | 13.8 % | – |
| AlaskaTUX | any_cover, \|dz\| < 3 m | 16,030 | 42.3 % | 48.1 % | 51.1 % | 94.5 % | – |
| Japan | on_ground | 194,774 | 94.6 % | 0.3 % | 1.5 % | 3.6 % | 29.0 % / 70.4 % (9,404 texels) |
| Japan | on_ground_with_packed | 2,005,771 | 98.4 % | 1.4 % | 1.5 % | 1.7 % | 1.7 % / 1.9 % |
| Japan | any_cover, \|dz\| < 3 m | 378,383 | 97.7 % | 0.2 % | 0.8 % | 2.0 % | 29.9 % / 78.6 % (9,428 texels) |

Over all placed texels (no t-l restriction), exact surface_type agreement is 0.1–27.5 %.

Key cells of the coarse confusion tables (placed class → terrain class, texels; VERIFIED, E):

- Alpes on_ground: man-made over terrain snow 86,480 of 88,765; placed snow over terrain snow
  23,991 (96.2 %); placed park over SNOWPARK 1,004 of 4,203.
- With packed: placed rock over snow 1,440,343, rock 804,265, ice 124,150 (Alpes); over snow
  1,292,556, rock 231,269 (AlaskaTUX); over snow 1,713,168, rock 27,074 (Japan).
- AlaskaTUX on_ground: placed groomed over terrain groomed 1,428 of 1,443 (99.0 %); placed park over
  terrain groomed 1,521 of 2,011.
- Japan on_ground: placed water over terrain ROCKS_Beach 135,641 of 174,808; placed park over
  groomed 1,738 of 2,393; placed groomed over groomed 233 of 241 (96.7 %).

### 6.4 Interpretation (UNVERIFIED; the counts above are VERIFIED)

- Placed meshes are objects on top of the terrain, not the heightfield. In on_ground, 72–73 % of
  placed texels in Alpes and AlaskaTUX are man-made, vegetation or special materials, nearly all on
  terrain snow. Disagreement there is expected, not an error.
- The `*_with_packed` rates are low because packed `PM_Rock` meshes (boulders, cliff pieces) sit on
  snow terrain. Packed linkage itself is UNVERIFIED (§6.1).
- Placed `PM_Water` is a water surface over a bed. No terrain TM uses PM_Water, so it can never
  match; in Japan the water planes lie over ROCKS_Beach, and this one class causes Japan's ≈ 1 %
  rate. Without water, Japan reaches 29 % coarse and 70–79 % lenient.
- Park meshes sit on SNOWPARK (Alpes) or GROOMED terrain (AlaskaTUX, Japan); the lenient rule counts
  these as agreement.
- For genuinely terrain-hugging, terrain-like placed surfaces (on_ground and any_cover |dz| < 3,
  excluding water), agreement is 74.6–75.5 % coarse / 86.5–90.2 % lenient in Alpes and 51–54 % /
  87.8–94.5 % in AlaskaTUX. Exact surface_type is lower (48–65 %) because it separates powder, thin
  and crunchy snow, which placed meshes and the terrain do not paint identically.

### 6.5 Caveats

- **Height reference.** `on_ground` is defined against `ground.r16`, which lies below the rendered
  terrain in places. **VERIFIED** (C, `check.py` → `check.out`): only 89.6 % (Alpes), 61.9 %
  (AlaskaTUX) and 38.0 % (Japan) of L8 nodes have a trailer range matching FloorHeightData within
  5 m; pivot z − h medians are +0.01 / +0.01 / +0.22 m in matching nodes and +3.96 / +0.54 / +9.85 m
  in the others, while 90–99 % of pivots lie inside the trailer height range. Example: the Alpes
  Aoste snow-park quarter-pipes sit 60–67 m above FloorHeightData (1595 m) but inside the trailer
  range 1646–1687 m. So on_ground misses surfaces that sit on the visible terrain; it should be
  re-run against the `.tbf` render heights once decoded. That the `.tbf` is the visible surface
  there is UNVERIFIED.
- **Lakes.** The Japan BigLake_03 plane (z = 2362.32) counts as on_ground only along its shoreline
  (2,120 texels); inside it lies above the FloorHeightData lake bed. Use `any_cover_dz` for lake
  surfaces.
- **Merged shapes.** An EntityGroup "Merged Shape" can duplicate its child's shape at the same
  position (Alpes Chapel_01C_S_020). The raster is unaffected; whether the game loads both is
  UNVERIFIED.
- The C rasters (`$STEEP_DATA/G-08/C/placed_<R>_L6.npz`, previews `placed_<R>_L6*.png`) are lab
  outputs only; no cache stage writes them.

---

## 7. Cache stage `terrain-surfaces`

### 7.1 Command and stage

`summit-import terrain-surfaces --region <R> [--dir INSTALL] [-o CACHE_DIR] [--level 6] [--png
OUT.png]` (regions: Alpes, AlaskaTUX, Japan) writes `CACHE_DIR/terrain/<R>/` (default
`$STEEP_DATA/cache`). It is also the `terrain-surfaces` stage of `summit-import all`, one unit per
region (`crates/summit-import/src/cli_all.rs`). A node that fails to decode makes the command exit
non-zero **without writing anything**. Failure conditions: consumed ≠ stream + 2, histogram ≠
weights (§2.4), a code that is not a multiple of 3, a group past the bank, or a group whose three
variants have different PMs. Full flag description: `docs/import.md`.

### 7.2 Files

Grid (all files): size × size texels (8192² at L6), row-major u8, **row = world +Y** with row 0 at
y = −8000, column = world +X, no flip. Texel (r, c) covers `[−8000 + c·t, −8000 + (c+1)·t) ×
[−8000 + r·t, −8000 + (r+1)·t)`, t = 16000 / size (1.953125 m at L6), sampled at its centre. This is
the stitched-image convention of tbf.md §4; flip vertically for a +Y-up view.

| File | Size (L6) | Content |
|---|---|---|
| `layers.r8` | 67,108,864 B | group g (0..13) per texel |
| `surface.r8` | 67,108,864 B | `surface_type` of group g's PM (surfaces.md §4); terrain values 4, 25, 26, 27, 28, 31, 35, 37, 39 |
| `surface.json` | 11–14 kB | metadata and tables, below |

Sizes VERIFIED (`ls -la $STEEP_DATA/cache/terrain/*/`: `layers.r8` and `surface.r8` 67M each,
`surface.json` 11k / 13k / 14k for Alpes / AlaskaTUX / Japan; the full 67,108,864-value comparison is
in §7.4).

`surface.json` (`format` `summit-terrain-surfaces`, `version` 1):

- grid: `region`, `map`, `tbf`, `files`, `encoding`, `level`, `size`, `extent_m` 16000, `origin_m`
  [−8000, −8000], `texel_m`, `sample`, `row_axis` `"y"`, `layers_value`, `surface_value`;
- `bank`: entry, name, id, layer, forge layers read, group count;
- `groups[]`: `group`, `code`, `bank_entries`, `tm[]` and `tm_ids[]` (bank order), `cm`/`cm_id`,
  `pm`/`pm_id`/`pm_layer`, `surface_type`, `friction`, `restitution`, `texels`, `fraction`;
- `surface_classes[]`: per surface_type the PM and CM names, groups, friction values, overview
  `rgb`, texels, fraction;
- `decode`: nodes, decoded, missing, failures (+ up to 10 examples), section count and index,
  `texels_outside_trailer_mask`, seconds.

`--png OUT` writes a 2048² RGB false-colour overview of `surface.r8` (most frequent class per 4 × 4
block, palette = `surface_classes[].rgb`), row 0 at y = −8000 like the rasters. The `.r8` files
are in the cache's gzip list (`r8`, docs/import.md); budget ≈ 0.14 GB per region
(docs/disk-budget.md).

### 7.3 Overview images (outside git)

`$STEEP_DATA/captures/g08/` (VERIFIED, `ls`):

| File | Source | Content |
|---|---|---|
| `surface_<R>.png` | `summit-import … --png` | 2048², surface_type palette, row 0 = y −8000 |
| `ref_surface_<R>.png` | E `report.py` | false colour by terrain PM, 4 × 4 majority, flipped so +Y is up |
| `ref_layers_<R>.png` | E `report.py` | false colour by group, TM family legend, +Y up |
| `agreement_<R>.png` | E `report.py` | on_ground_with_packed vs terrain, coarse class: green agree, red disagree on a terrain-like placed material, blue placed object material, grey terrain only, over a ground.r16 hillshade lit from the NW |

### 7.4 Verification of the Rust stage

Re-run for this spec into a scratch cache (not the real one):

```
./target/release/summit-import terrain-surfaces --region Alpes -o $STEEP_DATA/G-08/F/cache
```

**VERIFIED** output (first line, then group lines such as):

```
terrain-surfaces Alpes: TerrainMaterialBank_Alps (DataPC_STP_Alpes+DataPC_STP_Alpes_patch_01+DataPC_STP_Alpes_patch_02) 11 groups; L6 8192² nodes 4096 decoded 4096 missing 0 failures 0 (section 2 of 4) texels outside trailer mask 0; chain 0.4 s, total 0.8 s -> <HOME>/SteepLab/G-08/F/cache/terrain/Alpes
  group  7 code 21 TM_ALP_SNOW_POWDER_01,TM_ALP_SNOW_POWDER_02,TM_ALP_SNOW_POWDER_03 CM_SNOW_Powder_Ground  PM_SNOW_Powder_Ground  st 37 fr 0.7000 texels   43804095 (0.6527)
  class 37 PM_SNOW_Powder_Ground,PM_SNOW_Thin_Ground  texels 50902280 (0.7585)
```

AlaskaTUX: `14 groups; L6 8192² nodes 4096 decoded 4096 missing 0 failures 0 (section 3 of 5)
texels outside trailer mask 0; chain 0.2 s, total 0.6 s`. Japan: same counts, `chain 0.6 s, total
1.0 s` (2.4 s with `--png`). Runtimes are warm-cache release builds; the commit that added the stage
quotes about 2–2.5 s per region.

| Check | Result | Tag |
|---|---|---|
| Scratch output vs real cache (`cmp`) | `layers.r8` and `surface.r8` identical for all three regions | VERIFIED |
| Rust rasters vs E's Python reference (`layers_<R>_L6.npy`, `surface_<R>_L6.npy`) | `equal 67108864 of 67108864` for both rasters in all three regions | VERIFIED |
| Group table vs B's `tm_table.tsv` (TM, CM, PM, surface_type, group per bank entry) | Alpes `bank entries 33 json entries 33 mismatches 0`; AlaskaTUX `42 … 42 … 0`; Japan `42 … 42 … 0` | VERIFIED |
| `--png` reproducible | scratch `surface_Japan.png` (`PNG image data, 2048 x 2048, 8-bit/color RGB`) is byte-identical to `captures/g08/surface_Japan.png` | VERIFIED |

---

## 8. Open questions and follow-ups

1. **Variant choice.** The raster gives only the group. Which of the three TMs (`_01/_02/_03`, or
   bank order) is drawn where is not known; the trailer bit in the triple is the best lead
   (UNVERIFIED). This matters for visuals, not for physics (one PM per group).
2. **Other undecoded sections.** Alpes s3 / AlaskaTUX+Japan s4 (10-byte empty form; non-empty
   forms start with 8 usually equal bytes, e.g. `05`×8; the u16 at +8 never yields weights summing
   to 17,424; `s4probe.py AlaskaTUX 4` → `{('flag0','other'): 449, 'empty10': 5795,
   ('flag1','other'): 478}`, VERIFIED, A) and the leaf "extra" section (tbf-heights.md §3) are still
   undecoded. Both correlate with specific groups, so they may be per-layer data (UNVERIFIED).
3. **Procedural sets.** `TerrainProceduralSetBank` / `TPS_*` / `TPM_*` reference TMs but have no
   known link to the raster. Their role (scatter, detail placement) is UNVERIFIED.
4. **TerrainMaterial unknown fields.** The roles of f32 +0x93/+0x97/+0x9b/+0xa3/+0xa7/+0xb1, the six
   flag bytes, why there are four `Color` objects, and the dead `source` id at +0x1a (§3.2). `slot_index`
   +0xc3 fits a `TerrainDisplacementsArray` slice (64×64 R8, 33/33/42 slices) for Alaska/Japan, but Alpes
   reaches 42 with 33 slices (UNVERIFIED).
5. **Height reference.** Re-run C's `on_ground` and E's altitude/slope statistics against the `.tbf`
   render heights once section 0 is decoded (tbf-heights.md §1, P2-06c), and check whether terrain
   collision uses FloorHeightData or the render heights (linkage.md §5).
6. **Key field.** The u64 key (a rand() output) is unused by the decoder; its purpose (per-tile seed
   for scattering?) is UNVERIFIED.
7. **Colour 2 vs groups.** AlaskaTUX/Japan colour section 2 (tbf.md §3.1) was not correlated with
   groups here.
8. **Placed vs terrain priority.** How the game combines a placed collision surface with the terrain
   surface below it (e.g. park pipes on GROOMED, water over beach rock) is not known.
9. **Which level to use.** The cache uses L6 (1.95 m). L7/L8 rasters decode the same way
   (all-level check, §2.8) if finer surface boundaries are needed.
10. **Tiling scale and units** (§3.6): needs a terrain GPU capture or a footage measurement.
11. **Japan detail indices out of range** (§3.5): 9 bank entries point at list-1 positions 1/3/5 of a
    1-entry list.
12. **Map-wide terrain settings.** `Terrain_TemplateMap` → `VisualTerrainComponent` / `TerrainSettings`
    floats (§3.6) are not decoded.
