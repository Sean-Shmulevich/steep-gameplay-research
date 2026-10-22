<!-- Imported authored research, not game payloads. -->
> Source: Studio `steep-wasm`, commit `1344bca03985eb1540236fb2ecd3cbbe8ecdcf14`, `docs/specs/formats/tbf-heights.md`.
> Evidence labels and validation counts below are the source agents' reports;
> the asset-level checks were not rerun for this import. Local source links were
> converted to plain references; their files may not be included here. Historical
> superseded sections remain labeled. Studio-authored runtime policies are not
> evidence of original game behavior.

# `.tbf` heights, class map and material variant (T-11), with the earlier research record

Status: **decoded (T-11).** Section 0 (heights), the leaf "extra" section (class map) and the
per-sample material variant are specified in §0. A lab decoder written from §0 alone reproduces
every captured height tile bit for bit, decodes every node of all three regions with exact stream
consumption, and agrees with every trailer min/max (§0.9). Container layout, the node trailer and
section numbering are in `tbf.md` (Studio source: `tbf.md`) §3. §1–§4 are the research record from before T-11
(P2-06b, T-02, T-06, C-07b), kept as evidence; §0 supersedes them, and §0.10 explains their partial
findings with the decoded codec.

**Provenance and clean room.** §0 is a behaviour description written by the T-11 spec agent after
reading a third-party decoder that was derived from the asset files alone. The owner received it
from a contact and approved its use on 2026-10-16 (`../../prior-art.md` (Studio source: `../../prior-art.md`) #14).
No code from it is in this repository. §0 states behaviour in prose, tables and formulas, and every
number in §0.9 comes from T-11's own lab decoder (`tools/lab/T-11/tbfspec.py`), which was written
from this text. Implementers (T-12 onwards) work from this page and never open the third-party folder.

Tags: every statement in §0 is backed by a check in §0.9 (VERIFIED) unless it is marked UNVERIFIED.

---

## 0. The decoded codec

Notation. Integers are unsigned unless stated otherwise. `>>`, `<<`, `⊕` (xor) and "mod 2^k" (keep k
bits) have their usual meaning. A tile has 132 × 132 samples. Sample (i, j) has column i (towards
world +X) and row j (towards world +Y), i, j ∈ 0..131, and raster index n = 132·j + i (row-major,
i fastest). L is the node's quadtree level (0..8), and (col, row) its position within the level
(tbf.md §2).

### 0.1 Where the data is (record layout)

A node record (tbf.md §3) starts with the u16 magic `0xFEED` (bytes `ED FE`) and a u16 descriptor
word W (bytes 2..3, little-endian). tbf.md's `0C` byte is W's low byte and its `F` byte is W's high
byte.

| Field of W | Bits | Value in the three lin1 files (VERIFIED, all 262,143 records) |
|---|---|---|
| version | W & 0x03FF | 12 |
| layout flags | W & 0x7C00 | 0x0C00 (Alpes), 0x1000 (AlaskaTUX, Japan) |
| class map present | W & 0x8000 | set on exactly the 65,536 level-8 records |

So W is 0x0C0C / 0x8C0C (Alpes) and 0x100C / 0x900C (AlaskaTUX, Japan). With version 12 a record
is a run of length-prefixed sections (`u32 len`, then `len` bytes), then the 40-byte trailer, then
the class map:

| # | Alpes (flags 0x0C00) | AlaskaTUX / Japan (flags 0x1000) |
|---|---|---|
| 0 | **heights** (§0.4) | **heights** (§0.4) |
| 1 | colour (LZ4 → BC1) | colour (LZ4 → BC1) |
| 2 | material raster (§0.6) | colour 2 (LZ4 → BC1) |
| 3 | "mask" section (10-byte empty form; not decoded, §2.3) | material raster (§0.6) |
| 4 | — | "mask" section (not decoded) |
| trailer | 40 bytes (tbf.md §3.2) | 40 bytes |
| last | **class map** (§0.5), only when W & 0x8000 (level 8) | same |

- An Alpes level-8 record has 5 length-prefixed sections, an AlaskaTUX/Japan level-8 record 6, and
  the class map is always the last. Levels 0..7 have no class map. The record ends exactly where the
  next block starts. VERIFIED (`layout.py`).
- The layouts differ in one place: a second colour section exists when the flags field is above
  0x0C00. No other version or flag value occurs in the shipped files, so a reader may reject any
  other value. How other versions would be laid out is UNVERIFIED (the third-party decoder handles
  versions below 12 with extra u32 fields; nothing here can test that).

### 0.2 Range decoder

All three payloads (heights, class map, material raster) use one range decoder, the one in
`../world/terrain-surfaces.md` (Studio source: `../world/terrain-surfaces.md`) §2.4. It decodes a symbol against a
cumulative table P[0..n] in units of 2^-32, where P[0] = 0, P[n] = 2^32 and P is strictly
increasing (symbol s owns [P[s], P[s+1])).

State: `code` (u32), `R` (u32) and a read position. Bytes past the end of the stream read as 0.

1. Start: `code` = the first 4 stream bytes, big-endian; `R` = 2^32 − 1; position 4.
2. Decode a symbol: let B(k) = floor(R · P[k] / 2^32) (a 64-bit product; B(n) = R). The symbol s is
   the largest k in 0..n−1 with B(k) ≤ code. Then `code ← code − B(s)` and `R ← B(s+1) − B(s)`.
3. Renormalise: while R < 2^24, set `R ← R · 256` and `code ← code · 256 + next byte`.

Both values stay below 2^32. The search in step 2 can also be done on P directly: B(k) ≤ code ⟺
P[k] ≤ floor(((code + 1) · 2^32 − 1) / R).

End check: after a payload's last symbol, the read position equals the stream length + 2 (a 2-byte
encoder flush, read with 4 bytes of look-ahead). This holds for every heights, class-map and
material payload in the shipped files (§0.9) and is the integrity check to use.

### 0.3 Bit-plane byte model

Heights and the class map code a stream of **bytes**. Each byte is coded against one of C static
models ("contexts"). A section starts with C × 8 header bytes, and context c uses bytes 8c..8c+7
as p[0..7], one per bit of the byte: p[b] / 256 is roughly the probability that bit b is 1. The
256-entry cumulative table of a context is built by splitting the full interval once per bit,
lowest bit first:

1. Start with one interval of width 2^32 ("no bit decided yet").
2. For b = 0, 1, …, 7, with minimum width m_b = 2^(15−b) (32768, 16384, …, 256): split every current
   interval (there are 2^b of them, one for each value v of bits 0..b−1). If an interval has width
   W, its "bit b = 1" part gets
   s = min(max(floor(W · p[b] / 256), m_b), W − m_b)
   and its "bit b = 0" part keeps W − s. The two parts stand for the byte values v + 2^b and v.
3. After the 8 splits each byte value x has a width w(x). The table is laid out in **increasing byte
   value**: P[x] = w(0) + … + w(x−1), and P[256] = 2^32. The split order defines the widths only.
   The layout is not the tree order.

Properties (they follow from the rule and were asserted for every table built in §0.9): every
interval entering split b is at least 2·m_b wide, so the clamp is always well-formed and every final
width is ≥ 256. When all 8 bytes of a context are 0, byte 0 gets the width 2^32 − 65,280 and each of
the other 255 values exactly 256, i.e. 2^-24 of the interval (VERIFIED, `recon.py` item 1). That one
fact explains the "escape", "token" and "event" findings of the earlier research (§0.10).

The model is static: the tables never change while a payload is decoded. There is no adaptation and
no state carried between tiles.

### 0.4 Heights (section 0)

Layout: bytes 0..31 are four contexts × 8 bytes (§0.3), and bytes 32.. are the range-coded stream
(§0.2).

1. Decode 4 × 17,424 = 69,696 bytes. Byte k (0-based) uses context k mod 4.
2. Group them in fours: sample n's code z_n is bytes 4n..4n+3 read as a **little-endian u32**. So
   context 0 always codes the low byte of a code and context 3 the high byte.
3. Map each z to a signed residual r (sign in bit 0): r = z / 2 if z is even, and r = −(z − 1) / 2
   if z is odd. By this rule z = 1 also means 0. That code never occurs in the shipped data (§0.9),
   but a decoder must apply the rule as written.
4. Rebuild the values h(i, j) mod 2^32 from the residuals in raster order (all arithmetic mod 2^32),
   with h = prediction + r:

| Sample | Prediction |
|---|---|
| (0, 0) | 0 |
| (1, 0) and (0, 1) | h(0, 0) |
| row 0, i ≥ 2 | 2·h(i−1, 0) − h(i−2, 0) (linear extrapolation) |
| column 0, j ≥ 2 | 2·h(0, j−1) − h(0, j−2) |
| i ≥ 1 and j ≥ 1 | h(i−1, j) + h(i, j−1) − h(i−1, j−1) (planar, "gradient") |

   The same thing in closed form (this is how the lab decoder computes it): with h(0, 0) = r(0, 0),
   - h(i, 0) = h(0, 0) + Σ_{a=1..i} Σ_{c=1..a} r(c, 0), and the same along column 0;
   - h(i, j) = h(i, 0) + h(0, j) − h(0, 0) + Σ_{a=1..i} Σ_{b=1..j} r(a, b) for i, j ≥ 1.

   Row 0 and column 0 code second differences (first differences at (1, 0) and (0, 1)), and the
   interior codes mixed second differences.
5. Level scaling: u = h · 2^(8−L) mod 2^32, i.e. a left shift by 8 − L bits.
6. Height: normalised = u / 2^20, and metres = 6800 · u / 2^20 (6800 is the file header's height
   scale, tbf.md §1). Every decoded u is below 2^24, so u / 2^20 is exact in f32. That f32 is
   bit-identical to the game's own height tiles (§0.9).

So a level-L tile is quantised to 2^-(12+L) of the normalised range: about 6.5 mm at L8 and 1.66 m at
L0. Every node of every level is present and decodes on its own. There is no parent/child or
neighbour dependency.

Sample positions (vertex-centred, 2-sample border, stride 128): sample (i, j) of tile (L, col, row)
is at world x = −8000 + col·T + (i − 2)·T/128, y = −8000 + row·T + (j − 2)·T/128, with
T = 16000 / 2^L (the convention of the harvest store and of collision-readback.md). Samples
128..131 of a tile are samples 0..3 of its +X (or +Y) neighbour and decode to identical values
(VERIFIED, §0.9). The colour texels of tbf.md §2 are cell-centred, half a sample away from these
positions.

### 0.5 Class map (last section of a level-8 record)

This uses the scheme of §0.4 with the differences below:

| | Heights | Class map |
|---|---|---|
| contexts / header bytes | 4 / 32 | 2 / 16 |
| bytes decoded | 69,696 | 34,848 (2 × 17,424; byte k uses context k mod 2) |
| code per sample | u32, little-endian | u16, little-endian |
| residual map and predictor | §0.4 steps 3–4 | the same, with all arithmetic mod 2^16 |
| level scaling | 2^(8−L) | none |
| output | u (§0.4) | a u16 value v per sample |

The value v has three fields (VERIFIED, all L8 tiles of all regions):

| Bits of v | Meaning |
|---|---|
| 0..7 | **class** (0..255) |
| 8..14 | always 0 |
| 15 | a per-sample flag: set on 19.0 % (Alpes), 11.1 % (AlaskaTUX) and 37.0 % (Japan) of samples. Its meaning is unknown (§0.11) |

The flag must be decoded, because it is part of the predicted value, and then masked off to get
the class.

Meaning of the class (UNVERIFIED semantics; the values are VERIFIED): snow depth = class / 255 m
under the rendered height (the reading of the third-party lead and C-07b). The values seen fit that
reading: Alpes and AlaskaTUX use 10 and 17 distinct classes between 3 and 76 (76 ≈ 0.30 m powder),
Japan 210 between 3 and 244. Class 0 never occurs. Histograms are in §0.9.

### 0.6 Material raster and per-sample variant (level 8)

The material raster section (§0.1) is the G-08 layer raster, fully specified in
`../world/terrain-surfaces.md` (Studio source: `../world/terrain-surfaces.md`) §2. It starts with an 8-byte key
(ignored) and the symbol count n. terrain-surfaces.md reads n as a u16 whose high byte doubles as
the implicit symbol's value 0. Equivalently: n is the byte at offset 8, followed by n entries
{u8 value, u16 big-endian weight}. The stream follows. Symbol s stands for residual `value[s]`. The
table is the sequential split of terrain-surfaces.md §2.3, the decoder is §0.2, and the XOR predictor
of terrain-surfaces.md §2.5 turns the residuals into codes: prediction = up if left == up-left,
else left (left and up-left are 0 in column 0; up and up-left are 0 in row 0), and
code = residual ⊕ prediction. Every code is 3·g for a TerrainMaterialBank group g.

At level 8, each sample's bank entry (material id) is code + v. The variant v ∈ {0, 1, 2} is a hash
of the sample's global position. Let gx = 128·col + i and gy = 128·row + j, so a sample shared by
two neighbouring tiles has the same (gx, gy). With all arithmetic mod 2^64:

| Step | Operation |
|---|---|
| 1 | x = A·gy + B·gx + C, with A = 0x369DEA0F31A53F85, B = 0xF50798D29FC28000, C = 0xCE0E8D0FDF510C57 |
| 2 | x ← x ⊕ (x >> 21) |
| 3 | x ← x ⊕ (x << 37) |
| 4 | x ← x ⊕ (x >> 4) |
| 5 | x ← x · K, with K = 0x422E19E1D95D2F0D |
| 6 | x ← x ⊕ (x << 20) |
| 7 | x ← x ⊕ (x >> 41) |
| 8 | x ← x ⊕ (x << 5) |
| 9 | v = x mod 3; material id = code + v |

This is the same hash that `../world/collision-readback.md` (Studio source: `../world/collision-readback.md`) §4.4
already uses for the collision readback, where sample indices 0..131 fit the captures five times
better than vertex indices. VERIFIED: the T-11 variant equals the C-06 lab hash on 20/20 random
tiles. The data files cannot confirm the variant on their own: the trailer `layer_mask` bits within
a group match the set of variants present in only 76–87 % of tiles, and just as often with the hash
transposed (§0.9). So the mask is not a variant list. The physics ground material of interior cell
(i, j), i, j ∈ 0..127, is the material of sample (2 + i, 2 + j) (UNVERIFIED; lead statement, as in
collision-readback.md §4.4).

### 0.7 Trailer min/max

The trailer's height_min and height_max (tbf.md §3.2) are the tile's extremes **before**
quantisation. The decoded extremes are those values rounded half-up to the tile's quantum:

  min_k h(i, j) = floor(height_min · 2^(12+L) + 1/2) and the same for the maximum,

with h in units of 2^-(12+L) (h = u >> (8 − L)). This is exact for every node of every level in all
three regions. The decoded min/max differ from the trailer's by −0.4999 to +0.5000 quanta (§0.9). A
reader must not clamp decoded heights to the trailer: a decoded extreme can lie up to half a quantum
outside it (0.83 m at L0, 3 mm at L8).

### 0.8 Procedure summary

For node (L, col, row):

1. Find the record (tbf.md §1–§2) and read W (§0.1).
2. Heights: take section 0, build 4 bit-plane tables from its first 32 bytes, range-decode 69,696
   bytes, assemble u32 little-endian codes, unzigzag, run the predictor mod 2^32, shift left by
   8 − L, and divide by 2^20.
3. At L8, class map: take the last section, build 2 tables from its first 16 bytes, decode 34,848
   bytes, assemble u16 codes, unzigzag, predict mod 2^16, and split class (bits 0..7) from the flag
   (bit 15).
4. At L8, materials: decode the material raster (terrain-surfaces.md §2) and add the variant (§0.6).
5. Check each payload's read position against the stream length + 2.

### 0.9 Verification (T-11 lab, VERIFIED)

Lab: `tools/lab/T-11/` (`tbfspec.py`, the decoder written from §0; `rc_kernel.c`, the §0.2 decoder
in C for the bulk scans, built on first use into `$STEEP_DATA/T-11/build/`; `TBFSPEC_PURE=1` selects
the pure-Python range decoder instead). Run after `source tools/env.sh`, from `tools/lab/T-11`, with
`PY=$STEEP_DATA/shared/lab-venv/bin/python`. Outputs are in `$STEEP_DATA/T-11/*.txt`
(2026-10-16).

| Check | Command | Result |
|---|---|---|
| Captured tiles (harvest store, the game's own GPU tiles, Alpes L0–L8) | `$PY -I check_harvest.py Alpes` | `harvest tiles 1541 samples 26850384 bit-exact tiles 1541` (L0 1/1 … L8 446/446): f32 bits equal at every sample |
| Same with the pure-Python decoder | `TBFSPEC_PURE=1 $PY -I check_harvest.py Alpes --every 10` | `155 … bit-exact tiles 155` |
| Every node, all levels, all regions: stream consumed to len + 2, and decoded min/max == round-half-up(trailer × 2^(12+L)) | `$PY -I scan.py <R>` (`scan_<R>.txt`) | `TOTAL height decode failures (consumption or trailer) 0 of 87381` for Alpes, AlaskaTUX and Japan; for example `L8 nodes 65536 consumed==len+2 65536 \| min==round(trailer_min) 65536 max==round(trailer_max) 65536` |
| (decoded − trailer) in quanta | same | min and max within [−0.4999, +0.5000] at every level in every region |
| Neighbour seams (samples 128..131 == neighbour's 0..3), heights at every level | same | `seams L8 h: x 65280/65280 y 65280/65280`, likewise at L1..L7 in all regions (e.g. `L7 h: x 16256/16256`) |
| Seams of the class map and materials (with variant) at L8 | same | `seams L8 c: x 65280/65280 y 65280/65280`, `seams L8 m: …65280/65280` in all regions |
| Class map stream consumed to len + 2; bits 8..14 | same | `consumed==len+2 65536`, `bits 8..14 nonzero 0` in all regions |
| Material raster consumed; codes multiple of 3; group set == trailer layer_mask groups | same | `65536/65536`, `65536`, `65536` in all regions |
| Residual code z = 1 (negative zero) | same | `nodes with any z==1 residual 0` in all regions |
| Record layout: W values, sections, class map iff L8, record ends at the next block | `$PY -I layout.py` | `W … {'0xc0c': 21845, '0x8c0c': 65536}` (Alpes), `{'0x100c': 21845, '0x900c': 65536}` (AlaskaTUX, Japan); `class map iff L8: 87381`; `record ends at next block: 87381`; 4/5 sections (Alpes) and 5/6 (AlaskaTUX/Japan) |
| Cross-check with the third-party pure-Python reference (run, not copied) | `$PY -I crosscheck_ref.py $STEEP_DATA/shared/leads/height-decoder <R> 300` | `heights 300/300, classmap 151/151, materials 151/151` identical, in each region |
| Variant hash == C-06 lab hash (collision-readback.md §4.4) | `$PY -I check_variant.py 20` (`variant_vs_c06.txt`) | `20 of 20 random L8 tiles` |
| Throughput (1 process, C range kernel) | `$PY -I bench.py Alpes 2000` (`bench.txt`) | heights, random levels: **401 tiles/s**; L8 heights + class map 271 tiles/s; L8 materials with variant 265 tiles/s (Japan 405/268/270). Pure Python: 44/33/126 tiles/s. Full scan with 6 workers: 87,381 nodes in about 337 s per region (≈ 260 nodes/s, every payload decoded) |

**Class map against the C-07b oracle** (`$PY -I check_c07b.py <R>`, `c07b_<R>.txt`). The oracle is
every L8 tile that C-07b's token decoder consumed exactly (tools/lab/C-07b, coverage.py model).

| Region | C-07b-exact tiles | class(0,0) == C-07b base / 2 | constant tiles, no residual on our side | tiles with C-07b events: first event sample agrees / all events agree |
|---|---|---|---|---|
| Alpes | 20,645 | 20,645 | 20,619 / 20,619 | 12 / 10 of 26 |
| AlaskaTUX | 34,320 | 34,320 | 34,298 / 34,298 | 10 / 9 of 22 |
| Japan | 13,744 | 13,744 | 13,740 / 13,740 | 1 / 1 of 4 |

So the oracle's VERIFIED part (base = 2·class, constant tiles) agrees completely. Its decodes of the
52 tiles with events were exact-consumption coincidences: C-07b's own log calls the run law after
the first event unsolved. Our residual at the first event is z = 10 or 11 (±5), not C-07b's ±147.

**Class histograms** (own 128 × 128 area of every L8 tile, `scan_<R>.txt`):

| Region | Distinct classes | Main classes (share) | Constant tiles (value: count) | Mean depth |
|---|---|---|---|---|
| Alpes | 10 (3..76) | 76: 0.833, 3: 0.090, 8: 0.018, 71: 0.015, 53: 0.010, 26: 0.009, 31: 0.008, 17: 0.008, 62: 0.006, 49: 0.005 | 76: 19,946; 3: 673 (20,619) | 0.261 m |
| AlaskaTUX | 17 (3..76) | 76: 0.842, 3: 0.119, 8: 0.009, 71: 0.007, 53: 0.005, 26: 0.004, 31: 0.004 | 76: 30,516; 3: 3,778; 5: 4 (34,298) | 0.258 m |
| Japan | 210 (3..244) | 3: 0.231, 76: 0.128, 5: 0.098, 132: 0.085, 188: 0.057, 80: 0.033, 136: 0.025, 244: 0.020 | 3: 13,470; 5: 258; 76: 12 (13,740) | 0.343 m |

The constant-tile counts equal C-07b's 21-byte "base only" forms exactly (Alpes 19,946 × `97` +
673 × `05`; AlaskaTUX 30,516 + 3,778 + 4; Japan 13,470 + 258 + 12). The classes C-07b named fit the
snow-depth reading (UNVERIFIED semantics): 76 → 0.30 m powder, 3 → 0.012 m rock/bare, 5 → 0.02 m
groomed, 188 and 244 → 0.74 / 0.96 m Japan deep powder. The intermediate Alpes values (8, 17, 26,
31, 49, 53, 62, 71) appear in transition bands (for example 76 → 71 → 62 → 49 → 31 → 17 → 8 → 3
along a slope edge in Alpes (100, 100)), i.e. a smooth depth ramp.

**Materials vs trailer layer_mask** (`scan_<R>.txt`): the material-id set (with variant) of the
bordered tile equals the set of mask bits in 49,992 (Alpes), 56,855 (AlaskaTUX) and 49,782 (Japan)
of 65,536 tiles. On a 383-tile Alpes sample no footprint (full, own, own + 1) and neither hash
orientation does better (274–278 of 383; inline check). Groups whose three entries are one TM
(Japan 0, 2) set only bit 3g+2, as G-08 found. So the mask's per-variant bits do not record the
hash's variants. The variant stays UNVERIFIED from the data files alone, but is supported by the
collision fits (collision-readback.md §4.4).

### 0.10 How the earlier partial findings fit (reconciliation)

Run `$PY -I recon.py` (`recon.txt`) for the numbers marked VERIFIED below.

| Earlier finding | Explanation by §0 |
|---|---|
| P2-06b §1.1: header = "16 u8 counts then 16 zero bytes"; bytes 13..31 always 0; bytes 1..12 non-increasing; byte 1 peaks at 127; Japan byte 12 ≤ 1 | The header is 4 contexts × 8 bit probabilities. Byte k is context k div 8, bit k mod 8. Contexts 2 and 3 (bytes 16..31, the two high bytes of each u32 code) and the top bits of context 1 are always 0, because residuals rarely exceed 2^13. Higher bits are less likely to be 1, hence non-increasing. Byte 1 ≈ 127 means bit 1 ≈ 50 %. VERIFIED header maxima: Alpes `[155, 135, 129, 122, 115, 100, 78, 52, 24, 7, 2, 1, 0, …]`, Japan byte 12 max 1. |
| P2-06b/T-02: flat tiles are a fixed frame with a 24-bit value Z, Z even, Z / hmin = 2^(13+L); Z = 0 gives the bare body `00 80` (121 Japan bodies) | Z is z(0,0) = 2·h(0,0) (a positive residual is even), and h is in units of 2^-(12+L). In a zero-header tile only z(0,0) is non-zero. Each of its non-zero bytes costs one 2^-24 cell (§0.3), and the byte from context 3 is free. Z = 0 leaves only the 2-byte flush. VERIFIED: Japan has 148 zero-header nodes, 121 of them with a 2-byte body (`recon.py`: `zero-header nodes 148, of which body longer than 2 bytes 27`). |
| T-02 §1.4: an "escape-coded base" (a "more" decision of p = 2^-16, then a uniform byte, little-endian varint) starts about half the bodies | A context byte with p = 0 puts the 255 non-zero byte values in the top 65,280 / 2^32 ≈ 2^-16 of the interval, each 256 wide: the "more" decision plus a "uniform byte" is a near-miss description of that single cell. The varint is the u32 z(0,0) read byte by byte in contexts 0..3. VERIFIED: the first coded byte lands in the top 2^-16 in 35,929 / 51,720 / 40,458 nodes (0.411 / 0.592 / 0.463; 0.489 overall, against T-02's 0.492). The "half the nodes without a base" are tiles whose context 0 has non-zero probabilities. |
| T-02: child (0,0) corner ≈ 2 × parent base; tiles coded independently | h(0,0) is the corner height in units of 2^-(12+L), and the unit halves per level. Tiles are independent (§0.4). |
| T-02/T-06 header ↔ residual-size "survival histogram" | p[b] of context 0/1 is the share of residual codes with bit b set, so it tracks the residual magnitude distribution. |
| T-06 searchE/searchI: post-base 3-byte tokens with an exact 24-bit law; heights "in half units" | Every non-zero byte in a p = 0 context costs exactly 24 bits (one 256-wide cell), and runs of zero bytes cost a fraction of a bit each, so zero-header bodies are 3-byte tokens. Token value v = the residual code z. The "half unit" is the zigzag factor 2. |
| T-06 tile 60765 (Alpes L8 (8,152), x-ramp, zero header, "V2 = 95", 14 tokens of ±1 every ~23 samples) | VERIFIED (`recon.py` item 2): z(0,0) = 816,074; z(1,0) = 94 (residual +47, the per-sample slope); row 0 then carries second differences +1/−1 at x = (2,3), (15,16), (38,39), (60,61), (83,84), (107,108), (130,131); there are no residuals outside row 0. T-06's tokens give the same 14 positions and values except the last (T-06 v = 2, true z = 3), the token T-06 fitted with an ad hoc "+1". |
| T-06 K2/C-07b: "V2 byte = zz(dx) + 2" (zz(m) = 2m−1 for m > 0, −2m for m ≤ 0), and C-07b's n = 0 tokens `ff fe XX` → k = XX − 2 | Algebraically zz(m) + 2 = z + 1 for both signs, with the true code z = 2m (m > 0) or 2|m| + 1 (m < 0). The offset of one comes from T-06 framing the cell inside a 2^-16 = 65,536 "escape" region, while the true non-zero region is 65,280 wide (§0.3). VERIFIED for 60765: V2 95 = z 94 + 1. |
| T-06 searchJ/searchK: zero-header run law, a geometric q = 263,175 / 2^32 per sample in a frame without a 1/128 "end cell" | The per-sample non-zero mass of a zero header is 4 × 65,280 = 261,120 / 2^32. Rescaled into T-06's frame without the 1/128 end cell that is 261,120 / (1 − 2^-7) = 263,176.06, within 4·10^-6 of T-06's fit (VERIFIED arithmetic, `recon.py` item 1). The end cell and the "per-32-zero continuation flag" were artefacts of fitting a run model to the floor-truncated product of four static byte symbols (UNVERIFIED as to the exact drift mechanism). |
| T-06 L4 / C-07b: no adaptation (identical byte runs across tiles, event probability unchanged after an event) | The model is static per tile (§0.3). |
| T-06 K2-2: gradient (W+N−NW) predictor in the interior | Correct for the interior. Row 0 and column 0 use linear extrapolation (§0.4). |
| T-06 L3: dense tiles never start `ff ff`; their "base form" not found | In those tiles context 0 has non-zero probabilities, so z(0,0)'s low byte lands in an ordinary cell, not the top 2^-16. |
| C-07b §3.1b: the leaf extra uses the height-section coder; base = 2·class (152 → 76, 6 → 3, 10 → 5, …); q = 255·2^-23 exactly; 512-cell event regions | Same scheme, 2 contexts of u16 (§0.5). The zero-header per-sample non-zero mass is 2 × 65,280 / 2^32 = 255·2^-23 exactly (VERIFIED). Each sample has two bytes with 255 non-zero cells each (510 cells of 2^-24), close to C-07b's measured "512 cells" (the last 2 are UNVERIFIED). |
| P2-06b §3: leaf extra = "per-layer data gated by layer_mask" (favoured) | Wrong reading. It is the class (snow depth) map. Its length tracks the mask because snow classes change where materials change. |

Contradictions with earlier text (each superseded by §0):

- tbf.md §3 described the record header as `ED FE 0C` plus a section-count byte F with n =
  (F & 0x7F)/4 + 1. The bytes are really u16 0xFEED plus the descriptor word W (§0.1). The old
  formula gives the right count for these files only.
- P2-06b §3.1 counted the class-map header as "u8[16] counts c0..c15" followed by a byte 0xFF. The
  16 bytes are 2 × 8 bit probabilities, and the 0xFF is the first stream byte.
- C-07b reported Japan bases "0 (23,419)". No sample in Japan has class 0 (§0.9). Those were
  probably tiles whose first symbol is not in the top cell, counted as base 0 (UNVERIFIED).
- C-07b's coverage counted 26 / 22 / 4 tiles with 1–5 events as exact. 32 of those 52 decode to
  different event positions (§0.9).
- The third-party lead reads the 32 trailer bytes after the two f32 as eight f32 (a "box"). They are
  the u64 layer_mask plus 24 zero bytes (tbf.md §3.2, VERIFIED in G-08 and C-07b). The lead's class
  output also drops bit 15 of the class value (§0.5).
- T-06 searchI's last 60765 token value and the fitted "+1"s (see the table above).

### 0.11 Open points (for T-12 and later)

- The class-map flag (bit 15) is decoded but its meaning is unknown. It forms runs of whole columns
  in some zones (e.g. alternating columns in Alpes (100, 100)) and covers 11–37 % of samples. It is
  not the C-07 checkerboard diagonal. T-12 should keep it (e.g. as a separate layer) and not fold it
  into the class.
  **Resolved (T-12): bit 15 is a coding artefact, masked (owner-relayed, UNVERIFIED).** The depth
  word's high byte is only ever 0x00 or 0x80, so class = word & 0xFF and no flag layer is stored.
  The bit must still be decoded (it takes part in the prediction). T-12 checks (VERIFIED,
  `summit-import terrain-decoded`): high byte 0x00 / 0x80 / other = 924,879,986 / 217,019,278 / 0
  (Alpes), 1,015,591,522 / 126,307,742 / 0 (AlaskaTUX), 719,698,064 / 422,201,200 / 0 (Japan) over
  all 132² samples of all 65,536 L8 tiles; the masked class seams are exact (130,560 / 130,560 pairs
  per region) while the raw words agree on only 55,800 of 130,560 Alpes pairs, which fits an
  artefact rather than terrain data.
- The class map's semantics (snow depth = class / 255 m) and the physics material per interior cell
  (sample (2 + i, 2 + j)) are UNVERIFIED leads. The collision-readback stages (C-06/C-07) are where
  they can be tested.
- The variant hash is defined for level 8 (global sample coordinates 128·col + i). Whether coarser
  levels use it with their own col/row is not defined. Only L8 needs materials for physics.
- The "mask" section (Alpes s3, AlaskaTUX/Japan s4) is still undecoded (§2.3).
  Contact lead (UNVERIFIED): it is a per-sample 0x40 flag stored next to each sample's material id,
  in a second channel of the GPU material-id texture. T-12 partial check (VERIFIED, inline probe
  with `tbf_heights::decode_codes`, every 37th node, 2,362 nodes each in Alpes and Japan): the
  section is the §0.3 bit-plane coder with **one** context (8 header bytes, then the stream; the
  10-byte empty form is 8 zero bytes + the `00 80` flush) and consumes exactly stream length + 2 in
  2,362 / 2,362 nodes per region. The value mapping is not found: raw codes are {0, 255} in Alpes
  and spread in Japan; neither the §0.4 zigzag + planar predictor nor the G-08 XOR predictor yields
  a {0, 0x40} raster. Left for a spec task.
- Record versions other than 12, or other flag values, do not occur. Their layout is not specified.
- Exact-arithmetic notes for implementers: in §0.3, W · p[b] fits in u64 (W ≤ 2^32, p ≤ 255). In
  §0.2, R · P[k] < 2^64. The predictor needs wrapping u32 (heights) or u16 (class) arithmetic, or
  i64 sums reduced at the end as in the closed form. Bytes past the end of a stream read as 0.

---

## Research record before T-11 (P2-06b, G-08, T-02, T-06, C-07b) — superseded by §0

The text below is unchanged apart from banners marking the superseded parts. Its "not decoded"
statements are historical.

Original status notes (pre-T-11):

Container layout, the node trailer and section numbering are in `tbf.md` (Studio source: `tbf.md`) §3.

**Update (G-08):** the sparse layer section (§2) is now **fully decoded**: exact on all 87,381 nodes
of all three regions, with byte-exact re-encode. Format, coder, predictor and meaning are in
`../world/terrain-surfaces.md` (Studio source: `../world/terrain-surfaces.md`) §2–§3. Sections 0, Alpes s3 /
AlaskaTUX+Japan s4 and the leaf extra remain undecoded.

**Update (T-02, time-boxed second attempt):** section 0 is still **not decoded**. No candidate
decoder came close to the accept bar (node min/max within 1 % on ≥ 95 % of nodes), so none was
scored against the trailers. T-02 did show that the base frame which starts about half of all
section-0 bodies is written by the G-08 range coder, and it found what the header bytes track. It also ruled out four more residual-model
families. See §1.4 and rows 12–15 of §1.2.

Clean-room note: everything here comes from statistics over the data files
`$STEEP_DATA/install/PC{Alpes,AlaskaTUX,Japan}_terrainlin1.tbf` (87,381 nodes each). No
executable code was examined. The GDC 2017 Wildlands terrain talk (prior-art #11) was not
used for any finding below.

## How to reproduce

All lab scripts are in `tools/lab/P2-06b/` and are run from their own folder with the repo venv.
In the commands below, `$LAB` means `cd tools/lab/P2-06b/<dir> && ../../../.venv/bin/python`,
and `<dir>` is `s0`, `sparse` or `last_extra` as named. The section-0 scripts read
per-node tables cached in `$STEEP_DATA/P2-06b/s0/tab_*.npz` (built by `s0/scan.py`), and the
leaf-extra scripts read pickles in `$STEEP_DATA/P2-06b/last_extra/` (built by
`last_extra/collect.py` / `ex_load.py`). All outputs quoted below were re-run on 2026-10-11.
Full logs are in `$STEEP_DATA/P2-06b/evidence/`, outside git. Quoted lines are statistics only.

Notation: `L` is the quadtree level (0..8), and `hmin`/`hmax` are the trailer's normalised
`height_min`/`height_max` (tbf.md §3.2).

---

## 1. Section 0 — heights (range-coded, not decoded)

> **Superseded by §0.4 (T-11).** Section 0 is decoded; the findings below are explained in §0.10.

### 1.1 What is known

**Header: 16 × u8 counts, then 16 zero bytes.** Bytes 13..31 are 0 in every node (Japan's byte 12 never goes above 1). So the
header is 16 one-byte counts, not 16 u16 values.
VERIFIED: `$LAB B_hdr3.py` (s0) → `Alpes byte max [155 135 129 122 115 100 78 52 24 7 2 1 0 0]`;
`cd tools/lab/P2-06b && ../../.venv/bin/python doc_checks.py` → `bytes13..31 max 0` in all three
regions, Japan `byte12 max 1`.

**The counts look like a histogram.** Bytes 1..12 are non-increasing in 99.96% of nodes, so they read as a decreasing
pmf, not a cumulative table. VERIFIED: `$LAB B_hdr4.py` (s0) → violations `37` / `59` / `4`
(Alpes / Alaska / Japan); b0 ≤ b1 in `0.975`–`0.987`. Byte 1 peaks hard at 127: `$LAB B_hdr5.py` →
`127:12544` (Alpes). Body length tracks the sum of the counts: `corr body vs sum bytes 0.9815`
(B_hdr4). The relation is not exact. `$LAB B_len.py` → `corr(bodybits, sum h) 0.9819`, and
scaled-histogram static-entropy models leave a 10–90 % spread of 28–34 % of the median
(`$LAB B_hist2.py` → best spread/median `0.338` Alpes, `0.281` Japan). VERIFIED.

**The body starts with a base value at the tile's (0,0) corner, in units of 2^-(13+L).**
- In flat tiles (`hmin == hmax`) the body is a short fixed frame: two marker bytes, then a 24-bit
  little-endian value Z split across marker-separated bytes, then the end bytes `00 80`.
  Z is always even, and Z / hmin = 2^(13+L) exactly. VERIFIED: `$LAB A_flat.py` (s0) → log2 ratio
  `18.0000` / `19.0000` / `20.0000` / `21.0000` at L5–8; `Alpes 653 odd values 0.0`.
- Z = 0 is coded with no prefix at all: the whole body is `00 80`. That is the case for flat
  Japan tiles at sea level (121 such bodies, `hmin·2^(13+L)` ∈ {0.031, 0.063, 0.126}).
  VERIFIED: `doc_checks.py` (as above) → Japan `s0 body == 00 80: 121 hmin*2^(13+L) values [0.031, 0.063, 0.126]`.
- In non-flat tiles that start with the same frame, the base lies inside [hmin, hmax] in
  15,729 / 15,750 Alpes nodes. VERIFIED: `$LAB B_basechk.py` → `n= 15750 … 'outside': 21`.
- It is the (0,0) corner sample: a child in quadrant (0,0) has base ≈ 2 × the parent base, with median
  deviation `0.0055` (Alpes) / `0.0063` (Alaska) of the range. The other quadrants deviate by
  `0.2168`–`0.4316`. VERIFIED: `$LAB B_basepc.py`.

**Quantum scales with tile size.** range × 2^(13+L) is roughly constant at L5–8 (median log2
≈ 14.25–14.45). So each tile is coded with about 14–15 bits of dynamic range, at quantum
2^-(13+L) of the normalised height. Child/parent body-length ratios are 0.866–0.988,
so tiles are coded independently, not as residuals against the parent. VERIFIED: `$LAB B_pc.py`.

**It is a multi-symbol range/arithmetic coder, not a bit-packed code.**
- *A zero header implies the body ends in `0x80`*: 300/300 Alpes, 300/300 Alaska and 148/148 Japan zero-header
  nodes. With a non-zero header, as few as about 0.5 % of bodies end in `0x80`. VERIFIED:
  `$LAB A_end80.py` → `-1: (300, 300, 278)` Alpes, `(300, 300, 293)` Alaska,
  `(148, 148, 128)` Japan; Japan `10: (207, 1, 0)`.
- *No end-marker bit*: the last byte of large bodies is uniform. VERIFIED: `$LAB A_lastbyte.py`;
  `$LAB B_tail2.py` → `last==0: 119` of 29,127, with a 1:2:4… trailing-zero ladder.
- *MSB-first*: in pairs of bodies with a common prefix, the lowest differing bit leans towards 0
  (92/168) and the highest is about uniform. VERIFIED: `$LAB A_diverge.py` → `pairs 168`.
- *Period-3 byte structure in small bodies*: P(high|high) is 0.49 / 0.40 / 0.33 at lags 3 / 6 / 9 for
  100–400 B bodies, against 0.03 at 8–20 kB. VERIFIED: `$LAB A_period.py`.
- *Token arithmetic*: runs of 3-byte groups, read as signed big-endian 24-bit W, satisfy
  W = m·q + c with q constant within a run and usually **not** a power of two. VERIFIED:
  `$LAB A_tokq2.py` → `runs 260 gcd>=16: 182 of which power of two: 17`; m clusters near
  −1024..−1000 and −512..−488. Single nodes give q = 320, 161, 101, 76, 62, 46, 39
  (`$LAB A_tokq.py Alpes 47269 55305`).
  - Integer step sizes with odd factors come from range division (range/total), not from bit fields.
    So the body is the output of a range coder with integer division. The claim that each token is
    a roughly 24-bit uniform symbol (a raw signed sample offset) is UNVERIFIED (inference).
  - *Correction to the earlier lab notes:* q falls by about 0.62 from run to run only in
    hand-picked chains. Over all runs the ratio is `median=0.9897 p10=0.496 p90=0.999`
    (VERIFIED, A_tokq2). Also, A_tokq prints `q=1`/`q=2` for the first run of each node. The
    values 512/255 come out only if the last group of the run is dropped (UNVERIFIED, hand arithmetic).

**Not re-tested** (UNVERIFIED, from the earlier lab notes): the corner sample is the tile
maximum in node 47269, and body bits ≈ 188 × sum(counts) with about 5 % median error.

### 1.2 Hypotheses ruled out for section 0

Each test used a positive control (a synthetic smooth surface encoded the same way) and a null
control (random bytes of equal length). All were VERIFIED on samples from all three regions.

| # | Hypothesis | Command | Key output | Verdict |
|---|---|---|---|---|
| 1 | Quantised heights: fixed w-bit samples (w = 8/10/12/14/16, MSB/LSB, every bit offset) mapped into the trailer's [hmin, hmax] | `$LAB N_quant.py` (s0) | control `raw ratio 0.108`; data `16 msb body>=3000B 0.968` (1.0 = random). The trailer map changes the ratio by ≤ 1.7e-14 (affine). | ruled out |
| 1b | Same, small bodies (< 3000 B, score ≈ 0.78): grid-shaped? | `$LAB N_smalllag.py` (s0) | `{1: 0.847, 3: 0.831, 32: 0.896, 33: 0.877, 34: 0.887, 129: 0.949}`: minimum at lag 3 (token runs), no grid lag | ruled out |
| 1c | Fixed-width raw/delta at 8/10/12/16 bit, grids 33..133 | `$LAB B_raw.py` (s0) | smoothness ratio from `0.992 ('lsb', 16, 1, 0, 132)` up to 1.0029 | ruled out |
| 2 | Delta coding (signed w-bit first differences) | `$LAB N_quant.py` (s0) | mean \|d\|/2^(w−1) data 0.489 vs control 0.063 (uniform = 0.5); the cumulative sum wanders 15 × 2^w | ruled out |
| 3 | Bit-plane coding, planes of side² bits for side 33/65/129/132, packed or row-padded | `$LAB N_bitplane.py` (s0) | control top planes 0.33–0.49; data `side 129 … median +0.0033` vs RAND `+0.0024` | ruled out |
| 4 | Variable-bit-width codes: Rice k=0..6, Exp-Golomb, Elias-gamma, per-block width nibble | `$LAB N_vlc.py` (s0) | small/flat bodies (median 11 B) run out after ≤ 56 codes vs 1,089–17,424 needed; exact-length matches `match data 1/1123 RAND 0/1123` | ruled out |
| 5 | 33×33, 65×65, 129×129, 132×132 or 133×133 grid at a fixed bits-per-sample | `$LAB N_bps.py` (s0), all nodes | 11k–12.6k distinct body lengths per region; no width w=1..16 fits > 0.4 % of nodes; at 33×33 the median is 73 bits/sample | ruled out |
| 6 | Unstructured/compressible body (LZ-family) | `$LAB B_ent.py` (s0) | `pooled byte entropy 7.9994 bits/byte`, zlib-9 ratio 1.0011, bit autocorrelation ≤ 0.0042 at all lags 1..264, incl. 33/65/129/132 | entropy-coded, no raw planes |
| 7 | Prefix codes (Rice/Golomb/JPEG-LS) without a global "all zero" path | `$LAB A_flat.py` (s0) | a whole flat tile is 2 bytes (`00 80`); JPEG-LS run mode would need > 100 bits | ruled out |
| 8 | LZMA-style range coder (needs ≥ 5 init + 5 flush bytes; direct bits) | `$LAB A_rcsim.py` (s0) | simulated `00 32 cd ff fc 32 00`: off-by-one, does not match the observed base frame | ruled out |
| 9 | MQ coder (JPEG 2000) | (byte statistics; `$LAB A_show.py`) | MQ byte stuffing forbids `ff` followed by > `0x8f`, but `ff ff` and `ff fe` are common | ruled out (UNVERIFIED: argued from the notes, no count was re-run) |
| 10 | Backward FSE/zstd-style stream with an end-marker bit | `$LAB A_lastbyte.py` (s0) | last byte uniform in large bodies | ruled out |
| 11 | Header bytes 0..31 as a u16 cumulative-frequency table | `$LAB B_hdr3.py` (s0) | bytes 13..31 always 0 | ruled out |
| 12 | (T-02) Residuals with the base model: zero symbol 65535/65536 and escape 1/65536, escape followed by a u8 literal (varint), one decision per sample, raster of N samples | `$T02/dec2 $SD/zh_bodies.txt 400 17424 17424 1`; `… 400 60000 80000 500` | VERIFIED: `tiles 205`, `N=17424 ok=9 … ev=0`. Exact consumption (`pos == len + 2`, terrain-surfaces.md §2.4) holds on 9 of 205 tiles, and on ≤ 17/205 (`N=79000 ok=17`) for any N in 60k–80k. Decoding finds 0 events, but these tiles are not flat | ruled out |
| 13 | (T-02) Same with a wider event: zero 65536−e, non-zero e (e = 1..64), N ∈ {17424, 16641, 16900, 16384, 17161} | `$T02/dec3 $SD/zh_bodies.txt 400` | VERIFIED: `tiles 205`, best `N=16384 e=11 ok=12` | ruled out |
| 14 | (T-02) Magnitude classes: zero, then K classes of weight w (class k is followed by k raw bits), then an escape of weight e (u8 literal). K = 0..16, w = 1..8, e = 1..4, 4 grid sizes | `$T02/decA $SD/zh_bodies.txt 30` | VERIFIED: best `N=17424 K=3 w=4 e=4 ok=15/49`. Many unrelated settings score 12–15/49 (e.g. K=1 w=3, K=12 w=1), so no setting stands out from the rest | ruled out |
| 15 | (T-02) Any static table whose zero symbol has p ≥ 1 − 2⁻¹⁴, with the residuals coded right after the base in raster order | `$PY report.py` (T-02) | after the base, code/R sits at 0.347–0.397 in 21 of 57 zero-header non-flat tiles. From 0.35, with p(zero) ≥ 1 − 2⁻¹⁴, the first non-zero symbol cannot come before decision `16968` (`67872` at 2⁻¹⁶). So all of a tile's non-zero residuals would fall in its last ≈ 4 rows (the border), in 21 different lake/sea tiles | disfavoured (the count and bound are VERIFIED, `report.py`; the implausibility is an inference) |

Rows 12–15 (T-02) had no synthetic positive control. Their criterion is the G-08 integrity check
(consumption == stream length + 2), and they count as ruled out only because no setting rises above the
level that every setting reaches. Commands are in §1.4.

Earlier phases (P0-05 / tbf.md §3.1) already ruled out zlib, zstd, LZ4, Anvil blocks and DDS.

### 1.3 Open leads for the codec

- (T-02) The coder is now known (§1.4): the G-08 range coder. What is still missing is the symbol
  model after the base, and how nodes without an escape-coded base code their corner. The header
  probably holds a survival histogram of residual bit-lengths (§1.4), which is the best lead for the model.

- Find the exact coder: its precision, how symbols map to cumulative ranges, and what the
  16 header counts model (perhaps residual-magnitude classes). The sparse-section coder (§2)
  is the closest known relative and a good first guess for the arithmetic.
- Known plaintext would break it: the corner base value (known), grid size (the 132×132
  colour/layer raster is the likely candidate, UNVERIFIED) and the quantum 2^-(13+L). Full
  heights from a GPU capture (P2-06c) would supply the rest.

### 1.4 T-02 findings (second attempt)

Lab: `tools/lab/T-02/`. In the commands, `$PY` is `$STEEP_DATA/shared/lab-venv/bin/python`, run from that
folder after `source tools/env.sh`. `$SD` is `$STEEP_DATA/T-02` and `$T02/<x>` is `$SD/<x>`, built with
`cc -O2 -w -o $SD/<x> <x>.c`. `zh.py` writes `zh.pkl`, `after.py` writes `after.pkl`, and
`hdrfhd.py <R> 4` writes `hdrfhd_<R>_4.npz`; `report.py` then prints every number below.
`zh.py` also writes `zh_bodies.txt`, the input of the C scans: one line `reg idx L zmin zmax bodyhex`
for each zero-header tile with zmax − zmin > 1 (205 lines). All outputs were
re-run on 2026-10-14 over every third node (87,381 sampled nodes over the three lin1 files).

**The base frame, where present, is G-08 range-coder output.** The "marker bytes" of §1.1 are the G-08 coder
(terrain-surfaces.md §2.3–§2.4) coding a little-endian varint, one byte at a time:
```
R = 2^32 − 1, code = first 4 body bytes (big-endian)        # G-08 decoder state
base = 0; shift = 0
while decode([0, 2^32 − 2^16, 2^32]) == 1:                  # "more" decision, p = 2^-16, top of the interval
    base |= decode([k · 2^24 for k in 0..256]) << shift     # one uniform byte
    shift += 8
```
- This explains every observation in §1.1. The `ff ff` / `fe ff` prefixes are the 16-bit cost of the
  "more" symbol. Z = 0 codes no "more" decision, so the body is the bare 2-byte G-08 flush `00 80`
  (the encoder's `low + 2^23`, with low = 0). Bases below 2^16 take two groups instead of three
  (e.g. AlaskaTUX `ff ff 1c fe ff 69` = 26908; inline decode in the T-02 session, UNVERIFIED here).
- VERIFIED (`$PY after.py; $PY report.py`): `escape-coded base: nodes 42986 base in
  [floor(zmin),ceil(zmax)]: 0.9076`. The other ≈ 9 % are out of range. That most of them are 1-byte "bases", i.e. tiles whose first
  symbol only happens to land in the top 2⁻¹⁶, is UNVERIFIED (inline check).
- **Half the nodes do not start with the base.** `first decision not escape (body > 2 B): nodes 44355`
  (VERIFIED, `report.py`; counted as decoded base 0 with a body longer than `00 80`. A base whose only
  byte is 0 would be miscounted, but none is expected, because Z = 0 is coded with no escape). In those nodes the first symbol lands anywhere in [0.46, 1) of the interval (e.g. Alpes L6
  `u = (1 − code/2^32)·65536 = 35174.57`, L7 `4.54`; inline check in the T-02 session, UNVERIFIED here).
  So the corner value is coded some other way there, perhaps relative to a prediction (UNVERIFIED).

**The state after the base is not consistent with a high-probability zero symbol.** In zero-header
tiles that are not flat, the first symbol after the base sits at code/R ≈ 0.35 in about a third of
the tiles: `zero-header non-flat with base: n 57 body bytes min/max 11 377 code/R after base in [0.34,0.40): 21`
(VERIFIED, `report.py`; the values cluster at 0.3467–0.3552). These tiles still carry data after the base. A raster
of 17,424 residuals whose zero symbol has p ≥ 1 − 2⁻¹⁴ would have to place all of them in the last ≈ 2
rows (row 15 of §1.2). Flat tiles, though, need p(zero) > 1 − 3.2·10⁻⁴ to stay at `00 80` (`report.py` → `needs eps <
3.18e-04`): 17,424 zeros must cost < 8 bits, or the encoder would emit a byte. So either flat tiles are a special
case, or the residuals are not coded in raster order with one symbol per sample (both UNVERIFIED).

**The header bytes track a survival histogram of residual magnitude.** Using FloorHeightData as
approximate plaintext (`fhd.py`: bilinear FHD heights at the 132 × 132 texel centres of tbf.md §4,
in units of 2^-(13+L)), with gradient-predictor residuals r = X − (A + B − C) and
S_j = P(bit-length(|r|) ≥ j) per tile:
- VERIFIED (`$PY hdrfhd.py <R> 4; $PY report.py`, 256 L4 tiles per region):
  `Alpes_4 … b2~S2 r=0.90 b3~S3 r=0.92 b4~S5 r=0.96 b5~S6 r=0.97 b6~S7 r=0.97 b7~S8 r=0.98`;
  `AlaskaTUX_4 … b1~S1 r=0.84 b2~S3 r=0.89 b4~S5 r=0.86`; `Japan_4 … b2~S1 r=0.95 b3~S4 r=0.94 b4~S5 r=0.93`.
- Reading (UNVERIFIED): b_k for k ≥ 1 is a scaled count of residuals whose bit-length is at least
  about k. That would explain why bytes 1..12 are non-increasing (§1.1, 99.96 %) and why byte 1 saturates
  near 127 (rough tiles with almost no zero residuals, if the scale is about 128). Byte 0 measures
  something else. FHD is 2 m, BC-style quantised data (floor-height.md §2), so low classes are noise there,
  and the exact predictor, scale and class offset could not be pinned down.
- If the reading holds, a zero header means that almost no residual is non-zero. That fits the
  zero-header tiles being lakes and sea (FHD over them is flat or disagrees with the trailer, inline
  check, UNVERIFIED).

**What a next attempt needs.** Exact plaintext for one tile. The P2-06c GPU capture is still the way to
get it. FloorHeightData is too coarse (about 0.03–0.1 m against a quantum of 0.013 m at L6) to give
exact residuals.

---

## 2. Sparse layer sections (Alpes s2, AlaskaTUX s3, Japan s3) — decoded in G-08

> **Superseded by `../world/terrain-surfaces.md` (Studio source: `../world/terrain-surfaces.md`) §2.** The layout
> below still holds. The coder's cumulative table is a sequential split, not H_fix32 (§2.2), and
> the ids are XOR residuals of material codes 3·g (g = TerrainMaterialBank group), which explains
> the 0.64 overlap and the id/mask mismatch noted here. This section is kept as the P2-06b record.

### 2.1 Layout (VERIFIED, all 87,381 nodes × 3 regions, 0 failures)

```
+0    u64 le  key        a C-library rand() output (< 0x8000), not the trailer layer_mask
+8    u16 le  cnt        number of symbols including the implicit one (≥ 1)
+10   u16 be  f0         frequency of the implicit symbol ("none")
+12   (cnt−1) × { u8 id; u16 be f }     ids strictly increasing
...   stream             range-coded raster of 132 × 132 = 17,424 symbols, row-major
```

- `$LAB sp_sum.py 1` (sparse) → Alpes `bad 0 … sum hist [(65533, 17400), …]`;
  AlaskaTUX `bad 0 … sum hist [(17424, 87381)]`; Japan `bad 0 cnt==1 63 min stream len 2 …
  sum hist [(17424, 87381)]`.
- In AlaskaTUX and Japan the frequencies are exact texel counts (sum 17,424 = 132²). In Alpes they
  are normalised to about 16 bits (sum 65,530..65,534).
- A little-endian first value (`$LAB sp_parse.py 1`) gives no constant sum. So f0 is big-endian.
- Minimum lengths. Alpes s2 is 18 B (cnt = 2, 3-byte stream, 2,873 nodes). Japan s3 is 14 B
  (implicit symbol only, 63 nodes, 2-byte stream = coder flush). AlaskaTUX s3 is 18 B.
  VERIFIED: `doc_checks.py` → `sparse s2 min len 18 nodes 2873` (Alpes), `sparse s3 min len 14 nodes 63`
  (Japan), `sparse s3 min len 18 nodes 11877` (AlaskaTUX).
- **Key.** The seed-1 MSVC-style LCG (×214013 + 2531011, output bits 16..30) yields every
  key within its first ~9.2k outputs. At L0–L3 the key equals output[row-major index] exactly (85/85 nodes).
  VERIFIED: `$LAB sp_key.py` → `{0: '1/1', 1: '4/4', 2: '16/16', 3: '64/64', …}`,
  `max key 0x7ffd all<0x8000 True`; `$LAB sp_key3.py` → `not in seq 0` for all three regions.
  That it is a per-tile random seed (e.g. for scattering) is UNVERIFIED. It carries no
  content.
- **Ids vs layer_mask.** Each id is tied strongly to one trailer 3-bit group, but the mapping is not 1:1.
  VERIFIED: `$LAB sp_idmask.py 7` → e.g. Alpes `id 7 … grp 6 P(bit|id)=0.998 P(id|bit)=0.998`,
  Alpes `id 29 … grp 5 … 0.995 … 1.000`. Ids range over 3..54. The reading "id = material/layer
  index, group = coarse class" is UNVERIFIED. This matches tbf.md §3.2: Alpes s2 is minimal exactly when group 6 is absent.

### 2.2 Stream coder

| Hypothesis | Command (sparse) | Key output | Verdict |
|---|---|---|---|
| Static order-0 model with the header counts | `$LAB sp_cost2.py` | `AlaskaTUX nsym 12 … static diff [1. 1.5 2.] enum diff [4.15 7.48 15.13]`; Japan `static diff [1. 1.5 2.]` | **confirmed**: the length matches the static entropy within 1–2 B for every node; the decrementing (enumerative) model is 2–15 B too short |
| Same for Alpes (normalised freqs) | `$LAB sp_cost.py AlaskaTUX Japan Alpes` | `Alpes … actual - predicted bytes: median 2.61 p1 1.42 p99 3.93` | consistent |
| Multiply-first split R·cum/T (32-bit, byte renorm) | `$LAB ev_static_bynsym.py AlaskaTUX 97` | `nsym 3: … mf 1/72`, `nsym 8: … mf 0/123` | rejected for ≥ 3 symbols |
| Decrementing counts (old `sp_map.py`) | `$LAB sp_validate.py AlaskaTUX 97` | `exact 901/901` (trivially true) but bytes consumed minus length is spread from −16 to +2, where a correct decode gives +2 | rejected (`sp_map.py` and the scripts and images built on it have been removed as invalid) |
| Drop a symbol once exhausted | `$LAB ev_excl_validate.py AlaskaTUX 97` | `fit by nsym {2: '137/137', 3: '5/72', 4: '0/63', … 12: '0/194'}` | rejected |
| Static until one symbol is left / mod-2^32 low | `$LAB sp_scan_stop.py Japan 3 20 200`; `$LAB sp_scan_wrap.py Japan 3 20 200` | `fit 121 miss 79`; `fit 21 miss 179` | rejected |
| Other boundary formulas (19 × R0 × top × fill × endianness) | `$STEEP_DATA/P2-06b/sparse/bin/sp_vs $STEEP_DATA/P2-06b/sparse/japan2.txt` (built from `sp_vs.c`) | best `fit 14/178` | rejected |
| **H_fix32**: static model; cumulative probability P(c) = ⌊c·2³²/T⌋; boundary (R·P(c)) >> 32, with the top symbol taking R; 32-bit range starting at 2³²−1; byte renormalisation while R < 2²⁴; 4-byte big-endian init, zero padding | `$LAB sp_r0b.py` | `fixP 32 floor 0xffffffff [True, True, True, True]`: the only family that re-encodes all 4 short known messages byte-exactly | **best fit** |
| H_fix32 decode, sampled | `$LAB ev_fix_by_rare.py AlaskaTUX 7`; `$LAB ev_static_bynsym.py Japan 97` | AlaskaTUX `fix fit total 3636/12483`, `nsym==2 … '1692/1692'`; Japan 2768/12483; Japan `nsym 8: fix 6/199`, `median first-overflow step 11357` | **partial**: exact on every 2-symbol tile and most 3–4 symbol tiles; fails on most ≥ 6 symbol tiles |

"Exact" means 17,424 symbols decoded, the histogram equals the header counts, and consumption equals the
stream length + 2. The ≥ 6 symbol failures diverge late (median step ~11–12k), which points to a
small arithmetic or ordering detail still being wrong. That cause is UNVERIFIED.

**The decoded rasters are real** (VERIFIED, H_fix32-exact tiles only):
- `$LAB ev_verified_struct.py AlaskaTUX 6` → `block var ratio median 10.67` (1.0 = random);
  a rare texel has a rare 8-neighbour with probability `0.847` vs `0.126` expected (Japan
  `11.59`, `0.868 vs 0.193`).
- `$LAB ev_seam_offset.py AlaskaTUX 6` → horizontal `(128, 0.635, 778)` vs `(127, 0.119, …)` and
  `(129, 0.128, …)`, vertical `(128, 0.643, 791)`. So this is a 132×132 row-major raster with tile stride 128,
  i.e. the same 4-texel overlap as the colour tiles (tbf.md §3.1). Overlap agreement is 0.64, not 1.0,
  and the cause is open.

For Alpes, `$LAB sp_fix.py Alpes 2 97` consumes exactly length + 2 in 522 of 901 tiles, and
those histograms track f·17424/T closely (median 0.2σ). Exactness can't be proven, because
true counts are not stored.

**Conclusion:** these sections hold a per-texel **layer/material id map** (132×132), not heights
(UNVERIFIED as to semantics; the structure is VERIFIED).

### 2.3 Alpes s3, AlaskaTUX s4, Japan s4 — a different format

- The minimum is a constant 10-byte "empty" form, u64 0 then u16 0x8000, in 71,321 / 74,911 /
  72,280 nodes. VERIFIED: `$LAB ev_min10.py` (sparse) → e.g. `Japan s4 nodes 87381 len==10 72280
  u64@0 distinct 1 … u16@8 [('0x8000', 72280)]`.
- Longer forms do not parse with the §2.1 layout (key never matches, counts are garbage).
  The u16 at +8 has its top bit set in about 55 % of them. VERIFIED: `$LAB ev_other_secs.py`;
  `ev_min10.py` → `non-min sections 15101 with u16@8 high bit set 8686` (Japan).
- No mask group predicts the empty form (Japan best 0.928 vs base rate 0.827). **Undecoded**;
  no lab script has targeted these sections yet.

---

## 3. Leaf "extra" section (level-8 nodes, F & 0x80) — not decoded

> **Superseded by §0.5 (T-11).** The leaf extra is the class map, decoded; see §0.10 for how the
> findings below fit.

### 3.1 Layout (VERIFIED)

```
u8[16]  counts c0..c15     (Alpes/Alaska use c0..c5; Japan up to c15)
u8      0xFF               (byte 16: Alpes 0.909, Alaska 0.934, Japan 0.694 of nodes)
...     body
```

- Byte 16 fractions: VERIFIED by `doc_checks.py` → `leaf extra byte16==0xFF frac 0.909` / `0.934` / `0.694`
  of 65,536 leaves each.
- **Class A (all counts zero)**: 23,826 Alpes, 37,507 Alaska and 13,973 Japan nodes.
  - The body is 0xFF, then N × 24-bit big-endian tokens, then 0x80.
  - (len − 18) % 3 == 0 and the last byte is 0x80 in 100 % of these nodes.
  - The empty section (21 B) is N = 1.
  - VERIFIED: `$LAB ex_tok3.py` (last_extra).
- **Class A tokens**: the first token minus a fixed constant gives a per-node scale s. About 10 % of the
  other tokens are exact multiples of s, against 0.5 % by chance. The Alpes N = 65 cluster has 673 nodes.
  VERIFIED (Alpes; the script prints Alpes only): `$LAB ex_step.py`, `$LAB ex_hdr0.py`.
  The 628-node Alaska cluster is UNVERIFIED.
- **Class B (counts non-zero)**: the body is not 3-byte aligned and ends in 0x80 in only 27–70 % of nodes.
  Entropy is 7.67–7.82 bits/byte (`$LAB ex_entropy.py` → `H 7.688 / 7.674 / 7.821`). VERIFIED.

### 3.1b C-07b update: the leaf extra is a per-texel "class" raster in the height-section coder (partly decoded)

Lab: `tools/lab/C-07b/` (run with `$STEEP_DATA/shared/lab-venv/bin/python -I`, `STEEP_DATA` set;
`extract.py <Region>` first writes `$STEEP_DATA/C-07b/ex_<Region>.pkl`). Log: `$STEEP_DATA/C-07b/log.md`.

- The 16 count bytes are followed by the same escape-coded base as section 0 (T-02, §1.4): G-08
  coder, "more" = top 2⁻¹⁶ cell, then one uniform byte, little-endian. VERIFIED (`base.py`):
  bases Alpes 152 (54,655 nodes), 6, 142, 106, 62, 124 …; Japan 0 (23,419), 6 (13,602), 152, 160,
  376, 488, 384 …. Base/2 = 76, 3, 5, 188, 244: the class values a third party gave for powder,
  rock, groomed snow and Japan's deep powder (UNVERIFIED semantics: class = depth below surface
  in 1/255 m).
- The 21-byte form is base only: `ff ff 97 ff 80` = 152, `ff ff 05 ff 80` = 6, `ff ff 09 ff 80` = 10,
  ending exactly at len + 2 with code/R = 1/512 after the base. VERIFIED (`base.py`, `after.py`).
- Zero-header bodies are tokens of the section-0 kind (searchJ H6): VERIFIED (`tdist.py`) that
  after the base the code sits at top distance ≤ 0.41117·R in all 6,649 zero-header bodies with
  events = 1 − (1 − q)^17423 with q = 255·2⁻²³ (A = R, no 1/128 end cell); VERIFIED
  (`dsmall.py`) per-sample event region = 512 cells of R>>24 for runs 0..5; VERIFIED
  (`fitq2.py Alpes 137 2889 7715`) the identical 24-byte bodies place their single event at samples
  17423/17421/17420 = (131,131)/(129,131)/(128,131) with one common in-cell offset; VERIFIED
  (`tok2.py`) runs after an event are multiples of ≈130 samples under the same q (events follow
  edges row by row; no visible adaptation of the event probability).
- n = 0 tokens read `ff fe XX` / `ff ff XX` in a byte-aligned 2³² frame, with the value index
  k = XX − 2 / 254 + XX, like the section-0 V2 byte (zz + 2). UNVERIFIED (inference).
- Not solved: the exact cell law for runs after the first deep event (tokens grow to 4 bytes and
  the next token starts byte-aligned), and the coding of non-zero-header bodies. Ruled out for the
  whole raster (VERIFIED, scripts `zdec.py`, `zdec2.py`, `zdec3.py`, `zdec4.py`, `seqz.py`,
  `seq2.py`, `g513.py`, `sub.py`, `subz.py`, `tokz.py`, `j11.py`): G-08 static coder with a
  weight header (no such header exists), a static per-sample table with 3 symbols plus a uniform byte,
  Subbotin-style r = R>>24 tables, re-framing after every event, carry-less normalisation, and
  searchJ's H11 decoder as is. Coverage of the best model (`coverage.py <Region>`; base + closed-form run, A = 2³², q = 255·2⁻²³,
  k = zz in 256-unit cells), exact consumption, VERIFIED: Alpes 20,645 / 65,536, AlaskaTUX 34,320 /
  65,536, Japan 13,744 / 65,536. That is every constant tile plus 26 / 22 / 4 tiles with 1–5 events; no
  node with a non-zero header is decoded.

### 3.2 Hypotheses

| Hypothesis | Command (last_extra) | Key output | Verdict |
|---|---|---|---|
| Sparse-section layout (§2.1) at offset 0 or 16 | `$LAB ex_sparse.py` | 0 % pass | ruled out |
| Raw 2-D raster (u8/i8/u16/i16/u4, offsets 16/19), any lag 32–133 | `$LAB ex_acf.py` | no peak at 32/33/34/64/65/66/128/129/132/133; signed \|r\| ≤ 0.004 | ruled out (raw raster only) |
| Same codec as section 0 | `$LAB ex_family.py` | s0 at L8 ends in 0x80 3–4 % vs extra 28–74 %; repeated 3-grams/kB 2.9 vs 49–89 | different codec |
| Linear length model from the counts | `$LAB ex_regress.py`; `$LAB ex_stats.py` | residual std 210–618 B; length ~0.98 correlated with sum of counts | no exact identity |
| **(a) Detail heights** | `$LAB ex_corr.py`; `$LAB ex_disc.py` | length vs roughness Spearman 0.716 / 0.447 / −0.011; partial (controlling for mask popcount) +0.54 / +0.16 / −0.20; empty-section AUC: roughness 0.831 / 0.724 / 0.593 vs mask popcount 0.985 / 0.911 / 1.000 | **disfavoured** |
| **(b) Material/layer data** | `$LAB ex_disc.py`; `$LAB ex_hdrmask.py`; `$LAB ex_corr.py` | the section is non-empty in 100 % of nodes that have any group in Alpes {8} / Alaska {6,7,8,13} / Japan {4,6} (agreement 97.6 / 94.6 / 99.94 %); length vs colour s1 0.927 (Alpes), vs s3 0.936 (Japan) | **favoured**, as per-layer data gated by layer_mask |

Region figures are Alpes / Alaska / Japan. The verdicts on (a) and (b) are UNVERIFIED inferences from VERIFIED
statistics. The body is entropy-coded, so a compressed detail field is not strictly excluded.
The header counts do not map 1:1 onto mask groups (in Alpes, c0, c1, c3 and c4 all best match group 8).
A good next step is the class-A token stream, starting with the Alpes N = 65 cluster.

---

## 4. Summary (updated by T-11)

| Section | Content | Decoded? |
|---|---|---|
| 0 | heights: 4-context bit-plane byte model, u32 zigzag residuals, planar predictor | **yes** (T-11, §0.4) |
| Alpes s2 / Alaska+Japan s3 | 132×132 terrain material group raster (XOR residuals, static range coder) + per-sample variant hash | **yes** (G-08, `terrain-surfaces.md` (Studio source: `../world/terrain-surfaces.md`) §2; variant §0.6) |
| Alpes s3 / Alaska+Japan s4 | unknown "mask" section; 10-byte empty form | no |
| leaf extra (last section, L8) | class map (snow depth class + bit-15 flag) | **yes** (T-11, §0.5) |

Pre-T-11 text of this section, kept for the record:

>
> | Section | Content (best reading) | Decoded? |
> |---|---|---|
> | 0 | heights: corner base at 2^-(13+L) (G-08 coder, varint; T-02) plus a range-coded body | no: base value only |
> | Alpes s2 / Alaska+Japan s3 | 132×132 terrain material group raster (XOR residuals, static range coder) | **yes** (G-08, `terrain-surfaces.md` (Studio source: `../world/terrain-surfaces.md`) §2) |
> | Alpes s3 / Alaska+Japan s4 | unknown; 10-byte empty form | no |
> | leaf extra | per-layer data gated by layer_mask | no |
>
> None of the hypotheses in the P2-06b plan (quantised heights with the trailer range;
> delta / bit-plane / variable-bit-width coding; a 33×33 or 129×129 grid; leaf extra as detail
> or material ids) yields heights. **Fallback: P2-06c** (plans/03-phase2-assets.md, queued in
> `orchestration/queue.json`; depends on P3-07). It recovers heights from the reference game's GPU
> capture: heightmap textures or terrain vertex buffers as uploaded, mapped to `.tbf` nodes via
> the trailer range and the colour tile. Those samples then serve as known plaintext for another
> attempt at the section-0 coder (§1.3).
>
