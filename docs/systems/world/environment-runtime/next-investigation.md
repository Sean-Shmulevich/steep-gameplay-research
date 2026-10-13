> Findings-only publication. Companion assets, datasets, binaries and raw traces are not distributed. Read [current status](../../../STATUS.md) for qualifications. Source provenance is retained in the repository manifest.

# Next environment step

Resolve the exact authored scalar track evaluator called by `1407f3230` at `1407f327b`, virtual slot `+68`. This is the first unselected dynamic target on the recovered resource-to-time path. Do this static trace before a live observation, because the current evidence cannot map authored 2880 or stored interval codes to the recovered `24`/`100` arguments.

The receiver is `resource.entries[resource.property_map[property_index]].track`, with entry stride `58`, entries pointer `resource+10`, map pointer `resource+1c`, and track pointer `entry+8`. The sampler tests track word `+10` before calling `+68`; XMM1 receives the recovered supplied time, R8 is output storage and R9 points to a cursor hint initialized from a constant. Use this provenance, not a heap or offset-only match.

The decoded resource type seed is `AnimTrackLinearFloat`, CRC32 `cfd66aad`, and the frozen executable contains its class-name string at `141f22ec0`. The old decoder and exact bounds are in `analysis/fourth-pass/snow/environment/decode_weather.py` and `EVIDENCE.json`.

Bound the next pass as follows:

1. Inventory at most 32 aligned qword references to that exact class-name string. Select only the descriptor whose type identifier agrees with `cfd66aad`; reject mere string references and unrelated subclasses.
2. Follow that descriptor's factory/constructor to the track vtable. Export at most four selected factory/serializer/constructor roots, each at most 24 KB. Verify each selected instruction and table slot directly against the same image.
3. Export the proved table's `+68` target, at most 24 KB, plus at most three directly reached time-search helpers. Recover the conversion of the float argument into cumulative interval/key coordinates, search comparisons, endpoint/duplicate behavior and actual interpolation arithmetic.
4. Compare the result symbolically against both callers: ordinary/alternate time of day passes the `24`-domain value; weather passes its scalar multiplied by 100. Preserve any distinct track-specific scaling. Do not choose an hour/second interpretation from the constants alone.

Stop once the key-time adapter and endpoint rules are recovered, or at the first unselected dynamic receiver. If descriptor/factory identity is not proved within these caps, report its exact unresolved pointer slot and stop. Do not enlarge into whole-binary decompilation. No game launch, process reads, memory changes, debugger, hooks or remote operations are part of this next step.

The remaining named preset selection and aggregate-record writer are separate boundaries. This one experiment closes authored-time interpretation; it does not establish live preset selection, exclusive writers, wind forces, rendering units or grip coupling.
