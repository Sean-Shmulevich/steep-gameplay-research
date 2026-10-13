> Findings-only publication. Companion assets, datasets, binaries and raw traces are not distributed. Read [current status](../../../STATUS.md) for qualifications. Source provenance is retained in the repository manifest.

# Environment instruction evidence

Source is the frozen RVA-aligned `analysis/steep-memory-image.exe`, preferred base `140000000`, SHA-256 `32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`. All work was static/offline. `verification.json` is the byte/decoder receipt; `verify.py` can rerun it.

## Search bounds and selected ownership

`candidates.py` decoded aligned exception-table entries starting in `1407f0000..140850000`. It collected 54 indirect `+50/+58` call/jump candidates below cap64, with sixteen-instruction local receipts in `candidate-windows.asm`. Exactly six initial selected caller roots were `140846c40`, `140805790`, `140825440`, `140828ff0`, `14082af00`, `14082cde0`. The two useful shared-controller roots are the first two and binding root `14082af00`; the other selected roots were not promoted as environment-clock proof. In particular, shared slots with output-buffer arguments or a global diagnostic receiver are rejected as getter ownership evidence.

`joins.py` inventories the prior controller tables and direct references in the requested range. The base table `141eb6528` has abstract getters; time-of-day table `141eb65f8` has serializer `140821860`, and weather table `141eb6660` has serializer `1408218f0`. Both concrete tables have `+50=140517b20`, `+58=1408293c0`, `+60=14051ab10`. Their `+30` methods return metadata globals; those slots are not playback functions.

`direct_refs.py` performs exact E8 target searches in bounded exception-table code entries below RVA `1e00000`, then validates instruction alignment and caps each target inventory at64. It is a targeted reference inventory, not whole-program analysis. Follow-up roots were selected through these direct edges. `ownership.py` separately found no direct controller table references in `140850000..140940000`; that negative search did not establish absence of embedded construction.

Concrete ownership join:

- Constructor `1408ad1d0` calls `1407fd5c0` with receiver `aggregate+50` at `1408ad21c`, then `aggregate+e0` at `1408ad228`. That constructor installs `141eb65f8`. It calls `1407fd5f0` with receiver `aggregate+170` at `1408ad234`; that constructor installs weather table `141eb6660`. Wind constructor is called on `aggregate+200`, but full wind class recovery is outside this pass.
- `1408c4a90` decodes owner's resource record `+58`. At `1408c4ad5..4b04`, if owner byte `+d8` and byte `+99` are set and aggregate qword `+168` differs from empty resource record `143301d40`, it chooses aggregate+e0, otherwise aggregate+50. It stores that pointer in owner+20. It stores aggregate+170 in owner+28 and aggregate+200 in owner+30 at `1408c4b08..1a`.
- `1408c3790` calls this selection at `1408c37a8`, then binds those same owner+20/+28/+30 receivers through `14082aea0` and `140845b10`. `14082aea0` directly calls `14082af00`, which obtains decoded resource through receiver's virtual+58, stores it to receiver+18 and records property-owner contexts+50/+58. This supplies the `base_resource` used by the later property evaluator.
- Time-of-day serializer `140821860` requests CRC `f0c85018` into controller+88 at `1408218c5..d4`. Weather serializer `1408218f0` requests CRC `887004dc` into the same field. These align with the prior named type mappings. `140517b20` decodes controller+88 by its record sign/availability; `1408293c0` is the alternate decode with `14119f8d0` mask involvement.

The selected aggregate's top-level named asset and the owner+58 record writer remain unresolved. Its embedded controller classes and owner receiver offsets are proved. No live selection is inferred.

## Evaluation and clock producers

`1409138c0` gates on owner byte+98 or force DL, obtains `delta` from owner+10 object float+1060, then locally calls `1408c5410`, `1408e9660`, `1408c5540`, `1408e9750` in that order. It later evaluates owner+30 wind at clock+38 times100 via `1409139c2..d6`. Its selected clock state pointer is owner+a0. The unit of object+1060 is not assigned here.

`1408e9660`, requiring owner+10 and owner byte+98, reads owner+20, then passes `[owner+a0]+0` to `140846c40` at `1408e9694..9f`. It also copies that clock float into a downstream object+1698. Additional downstream virtual targets are not selected as renderer equations.

`1408e9750` calls `140915bc0` or `140915a50` based on owner byte+144, then `1409152c0` and `140913ad0`, before evaluating owner+28 at `[owner+a0]+18` times100 at `1408e9785..97a2`. Those helpers expose further selection/region branches, so the countdown producer is not asserted as the exclusive scalar writer. `1409152c0` operates on another scalar output and region query; its full semantics are not promoted as the weather evaluation coordinate.

Complete leaf receipt `1408c5410-leaf-window.asm` reaches ret `1408c5530`:

- If owner dword+3e4 !=-1, read source pointer from owner+370 indexed8, source+8 object+a0 state+10, multiply source+14 and store owner+390 cycle duration (`1408c5410..543c`).
- Require duration>0. Divide delta by verified float60 (`141df4058`). Progression gates are owner byte+3f4 mask02, state dword+4>0, external R8B true, or global byte `14312ee7d` true. At `1408c548c..5498`, multiply by verified24 (`141eb9f4c`), divide duration, add/store state+0.
- At `1408c54a3..54bb`, clock>=24 subtracts24 once, clamps with MAX/MIN to0..24. Owner+398 increments. Owner+394 increments modulo7 using an unsigned multiply/divide reduction. State+0c target>=24 subtracts24 once (`1408c54f2..5500`).
- Independently, state+4<=0, state byte+8 and clock>=state+0c cause clock=target and state+4 increment (`1408c5505..552d`). No repeated wrap loop or negative-clock wrap appears in this leaf.

`1408c5540` stops immediately on external R9B. It obtains a modifier from downstream context resource+1138 and checks an additional context gate. At `1408c5595..55b4`, state+28 remaining becomes MAX(remaining-delta*modifier+34,0). If remaining>0, divide by state+24 and interpolate start state+1c to destination state+20 using `destination + ratio*(start-destination)`. Otherwise use destination. Clamp0..1 and store state+18 at `1408c55de..55ee`. Units and divisor validity are unresolved.

## Property consumer and preset formulas

`140846c40` reads concrete receiver virtual+50, then initializes receiver+18 if needed. It calls weight updater `1408474e0`. Bound property pointers are receiver+6c/count+76, active flags receiver+78. The evaluator constructs/binds a property when needed, dispatches on property descriptor's low5 type bits, then commits the cooked value through `140843f10`. It does not decode a key-time scale itself.

Type-dispatch jump table is RVA8470d0. Types10 dispatch to `140846f9d`, which zero-initializes float output and calls `1407f5830` with XMM2 preserving evaluator XMM1, property index R9D and receiver RCX. Types0..3 use byte helper, types6..7 integer helper, types12..13 vectors, type14 another vector/helper case. Verification records all fifteen table entries. Only scalar float formula is translated here.

`1407f5830` obtains controller virtual+50. If null or receiver+18 null, it returns. If primary decoded resource equals receiver+18, it samples directly through `1407f3230`; otherwise `1407f32f0` chooses base/primary/bound fallback by property maps. It loops receiver+8, count receiver+12, entry stride50. For each overlay with valid decoded resource and mode+8 !=2, map[property_index]!=-1, and authored entry byte+10 enabled, it samples the overlay at the same supplied time. At `1407f591c..5931` it performs `(sample-current)*overlay+0c + current`. Disabled authored entry invalidates that resource map entry to-1. List order is preserved.

`1407f3230` reads resource+1c map[property], skips missing, finds entry via resource+10 and stride58, then track pointer entry+8 (`1407f323e..3253`). It tests track word+10 nonzero and calls track vtable+68 at `1407f327b`, with supplied time moved from XMM2 to XMM1 at `1407f3278`, output R8 and cursor-hint R9. This is the first unselected dynamic target. No interpolation, cumulative interval scale, duplicate endpoint or wrap rule is inferred inside it.

Preset insertion `140805790` uses overlay mode+8, duration float+10, manual flag+15, manually supplied weight+0c, start tick+18, end tick+20, clock-source pointer+30, active+38, completion callback+40 and callback data+48. Receiver+85 bypasses insertion/update. At `140805966..59d3`, verified integer30000 is converted to float, multiplied by duration, unsigned-truncated and added to the current tick. Ordinary conversion arithmetic is described; NaN/overflow inputs are not given gameplay meaning. Manager caller `1408c4700` supplies the clock pointer from owner+10 object+1048 and selected controller+20/+28/+30, subject to receiver/resource gates.

`1408474e0` skips automatic weight refresh when receiver+85, invalid overlay resource, manual flag+15 or inactive+38. At `14084757e..5d5`, it computes current-start over end-start with unsigned integer-to-float correction; zero duration gives active?1:0, and the selected refresh branch is active. Clamp0..1, mode1 complement, store weight+0c (`1408475d9..5fb`). End/zero-weight cleanup and optional callback are bounded in the same export. The callback at `1408476d2` is an unselected lifecycle target and does not establish renderer or physics coupling.

## Prior data and unresolved edges

Read both existing environment guides, `property_tracks.json`, named weather data, second-pass findings, run37 environment plan and input timing's exact weather follow-up. Authored type `AnimTrackLinearFloat` has CRC `cfd66aad`, independently recomputed from the executable class name. Its string is at `141f22ec0`. The old exact parser preserves interval codes and duplicate authored endpoints. No new code in this pass converts them.

Clock numeric constants, scaling and pointer identity are new static evidence. Real elapsed units, scheduler invocation cadence, aggregate/name selection, exclusive writers, hold ownership, transition clock rate, track time adapter and rendering/property terminal units remain open. No weather-to-contact or wind-to-rider edge was recovered. The run37 no-weather-to-grip finding remains a scoped negative trace, not a proof that no possible connection exists.
