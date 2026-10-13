> Findings-only publication. Companion assets, datasets, binaries and raw traces are not distributed. Read [current status](../../../STATUS.md) for qualifications. Source provenance is retained in the repository manifest.

# Run38 environment findings

This offline pass joins both time-of-day and weather controllers to a shared property evaluator and recovers their different evaluation arguments. It also recovers scalar preset overlay order and transition-weight arithmetic. The final key-time adapter remains behind a concrete unresolved track virtual call.

## New versus prior

Run37 established weather's table, resource getter and serializer. Its secondary scan did not reach evaluation or a clock. The authored catalogs already contained 78 time-of-day records, 54 weather/wind records and verified property hashes. These are prior data inventories, not new runtime coverage.

New byte-checked joins are:

- The selected aggregate constructs time-of-day controllers at its ordinary and alternate member locations, plus weather and wind controllers. The update owner selects the same member locations. This closes the class ownership ambiguity of the shared getter slots.
- The owner's ordinary/alternate time-of-day controller evaluates at a stored clock value. Weather evaluates at a distinct scalar multiplied by 100. Wind has a third scalar multiplied by 100. Weather therefore does not simply consume the time-of-day clock.
- The time-of-day writer advances by `delta / 60 * 24 / cycle_duration`, subject to several independent gates. It performs one subtraction of 24 followed by clamping to `[0,24]`, increments two counters and updates one counter modulo 7. It can stop at a stored target. The code does not establish the unit of `delta` or `cycle_duration`; naming either seconds or minutes is premature.
- Weather's scalar has a countdown-driven interpolation producer. On that path, the remaining countdown decreases by `delta * modifier_rate`, then the scalar interpolates between stored endpoints and clamps to `[0,1]`. Some gates preserve the previous scalar. Other called selection helpers remain outside the recovered writer set.
- The shared evaluator maps a property to an authored track and passes its supplied float time to the track's virtual evaluator. For scalar float properties, it computes a base value, then applies active preset overlays in list order with `value += weight * (sample - value)`. Each overlay receives the same evaluation argument. This is ordered composition, not normalization of all weights into a single weighted mean.
- Automatic preset weights use a separate integer clock and a duration code `trunc(float32(30000) * requested_duration)`. Weights clamp elapsed fraction to `[0,1]`; mode 1 complements the fraction. A manual-weight flag skips that refresh. The unit of the integer clock is unresolved.

The alternate time-of-day selection requires two owner flags and an available alternate resource. This gives a concrete selection condition without interpreting the catalog's `_MV` suffix as a gameplay mode. Selection of a named aggregate asset, spatial override precedence and complete modifier ownership remain open.

## Boundary and limits

The decisive remaining edge is the virtual call on the authored track inside the property sampler. The receiver is obtained from the selected resource's property map and entry array, not from an arbitrary object with a matching offset. The sampler passes the supplied float directly to that call. The track's concrete class table and evaluator body were not selected in this pass.

Consequently, no conversion of authored 2880, serialized 12000 interval codes or duplicate endpoint times is claimed. The recovered runtime domains `24` and `100` do not supply that conversion by themselves. A 24-valued time-of-day clock is observed; actual calendar/hour units and the scheduler's delta unit still need evidence.

No weather-to-grip edge was found or assumed. No snowfall accumulation, material replacement, rider aerodynamic coupling or shader equation is claimed. Wind's third controller evaluation does not prove that its outputs reach rider forces.

## Verification

The frozen RVA-aligned image has SHA-256 `32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`. The initial getter-slot inventory found 54 aligned candidates in the requested world range, below its cap of 64. Exactly six initial caller roots were exported, each below 24 KB. Subsequent exports follow selected direct producer, constructor and helper edges. Target-specific direct-call inventories are capped at 64; no whole-program analysis was run.

`private/verify.py` checks every exported instruction span against the image, independently decodes each span, verifies 39 controller table entries and checks the selected constants. It passed. The report records the actual instruction and file totals. Linear disassembly includes an embedded property-type jump table; its data bytes are not treated as executable control flow. No game launch, live process access, remote operation, hook or memory write occurred.

Exact addresses, ownership chains, gates and evidence files are in [private/EVIDENCE.md](evidence.md). Address-free formulas are in [CLIENT_LOGIC.md](pseudocode.md). The one bounded follow-up is in [NEXT_STEP.md](next-investigation.md).
