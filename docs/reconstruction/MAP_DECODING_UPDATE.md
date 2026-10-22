# Map decoding update from Studio

Studio's `steep-wasm` checkout contains newer terrain research than this repository's
earlier asset overview. This import is pinned to commit
`1344bca03985eb1540236fb2ecd3cbbe8ecdcf14`. The six source documents and their
before/after hashes are listed in [STUDIO_MAP_SOURCES.json](../../STUDIO_MAP_SOURCES.json).
They contain authored specifications and reported measurements, not extracted
terrain tiles, meshes or animation payloads. No asset-level validation was rerun
for this publication.

## What changed

| System | New information | Evidence boundary |
|---|---|---|
| TBF height payload | Static byte probability models, range decoder, residual mapping, predictor, level scaling and sample coordinates are specified | Studio reports bit-exact agreement on 1,541 captured tiles, 26,850,384 samples |
| Whole terrain tree | Every level can decode independently; no parent/neighbor reconstruction dependency | Studio reports zero stream-consumption/trailer-bound failures across 262,143 nodes in three regions |
| Class map | Same predictor with 16-bit arithmetic and two byte contexts; class in low byte, flag in bit 15 | Values decoded; the flag's meaning and class-to-snow-depth interpretation remain unresolved |
| Material assignment | Raster XOR predictor plus deterministic three-way variant hash | Do not equate trailer layer masks with complete per-sample material sets; cell-to-sample collision mapping retains an explicit unresolved boundary |
| FloorHeightData | Separate block-compressed coarse height grid, placement and patch layers | It is not interchangeable with the decoded rendered TBF terrain |
| Browser collision and placement | Decoded-ground switch, ride proxies, course lines and spawn adjustments | These are Studio-authored implementation policies; they do not establish the original collision solver or placement rules |

The decisive commits include `7e2b735c` for the T-11 codec specification and
`66f75f5a` for T-12's Rust implementation and decoded-ground stage. The latest
snapshot also includes T-13c halfpipe placement/ride-proxy work. Those source
commit claims were inspected read-only on Studio; no Studio branch was changed.

## Start with these specifications

- [TBF container](studio-map/tbf.md): node lookup, record structure and trailers.
- [Height/class/material codec](studio-map/tbf-heights.md): use section 0. The
  later pre-T-11 research is retained history and explicitly superseded.
- [Terrain surfaces](studio-map/terrain-surfaces.md): material raster decoder,
  material-bank relationships and limitations.
- [Floor-height grid](studio-map/floor-height.md): separate coarse grid and world
  placement.
- [Map structure](studio-map/map.md): map/region/entity relationships.
- [Terrain harvesting](studio-map/terrain-harvest.md): captured-height provenance
  and earlier fallback integration.

The height codec's implementation-sensitive details include unsigned modular
arithmetic; a nonstandard residual mapping where code 1 also maps to zero;
linear extrapolation along the first row/column and a planar predictor inside;
level scaling by `2^(8-L)`; and a 132-by-132 sample tile with a two-sample border
and stride 128. Stream consumption is expected to end at payload length plus two
because of decoder lookahead. Trailer min/max are pre-quantization bounds; do not
clamp decoded heights to them. Read the complete specification before implementing.

For reconstruction this substantially improves the terrain-query input side:
we can implement actual slopes, normals and material selection against decoded
data instead of fitting a terrain approximation to footage. It does not recover
snow adhesion, friction, leg springs or collision contacts by itself. Connect
material results to the recovered fluid/contact model only after matching the
material identifiers and sampling convention.

## Provenance and exclusions

The T-11 document explicitly credits an owner-approved third-party asset-only
decoder as its lead. Its authors describe their specification-to-implementation
separation and their own validation. We preserve that attribution; this import
does not independently certify the claimed clean-room process. No third-party
decoder source was copied here.

Studio also contains authored animations and video-fitted behavior. Those are not
included as recovered original animations. The imported map documents retain
UNVERIFIED labels and authored-policy distinctions. The recent Rust decoder and
browser implementation remain in Studio; this commit supplies their detailed
specifications, not a claim that the native mod host can already load new maps.
