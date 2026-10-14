# Frame-clock interval policy

A direct caller of the [shared clock updater](WORLD_CLOCK.md) converts a timer difference, selects a timing policy, applies a minimum and sends the result to a global root clock. [The adapter](../../engine/frame_clock_policy.py) reconstructs the policy block. It excludes the timer read/wait, root-clock membership, accumulated time and deadline update.

## Input conversion and scope

The inspected caller saves its prior timer reading, obtains a new reading and subtracts the old one. It converts the unsigned difference and a global divisor to float32, divides the difference by that divisor, then divides by 1000. The local policy therefore receives a seconds-like value and later multiplies its result by 1000 for the clock updater. The divisor's initialization and timer implementation remain to be verified before treating this as a complete hardware-clock contract.

There is also a wait loop that obtains further timer readings until a stored target is reached. The difference used for this policy is computed before that loop and retained through it. Do not silently recompute elapsed time from the last read in a replacement.

The global clock passed to the updater is also referenced by a world lifecycle path that searches its child list for the three embedded world clocks. The matching helper calls a vector helper on a found entry. The subsequent [constructor audit](CLOCK_OBSERVATION.md) confirms that all three world clocks are appended uniquely to this root collection. Current live child membership and the timing mode active during the animation capture remain unproved.

## Recovered policies

All arithmetic is float32, with rounding after each addition or division. Mode names below are our descriptions; numeric selectors are observed.

| Selector | Output before the common minimum | State changes |
| --- | --- | --- |
| 0 | `1 / configured_rate` | None in this block |
| 1 | A selected entry in a caller-provided interval table | Index/counter transitions below |
| 2 | The smaller of incoming elapsed time and table entry zero | None in this block |
| 3 | Sequential float32 sum of the first 15 history slots, divided by 15 | Writes incoming elapsed at the current history index, then advances/wraps the index |
| Other | Incoming elapsed time | None in this block |

Every mode then applies `max(value, f32(0.0001))`. The driver passes `f32(value * 1000)` to the shared clock updater with accumulation enabled. A fixed rate of one yields a one-second interval before downstream scaling. The passthrough mode also yields one second from a one-second input. These are examples of possible arithmetic, not explanations of the observed live `1.0`.

### Table mode

```text
if elapsed > table[index]:
    new_index = max(index - 1, 0)
    if new_index != index:
        stable_count = 0
    index = new_index
else if stable_count > 10:
    index = min(index + 1, table_count - 1)
else:
    stable_count += 1
value = table[index]
```

The counter is not reset when the index increases. A slow observation at index zero also preserves it. Equality takes the second/third branch, not the slow branch. Table ordering and actual configured values remain external inputs.

### History boundary that must remain visible

The native sum reads exactly 15 floats. The index increment resets only when the resulting byte exceeds 15, so an incoming index of 15 writes a sixteenth location before wrapping to zero. That location overlaps the low 32 bits of the neighboring field used as the wait target earlier in the function. The write is excluded from that invocation's sum.

The adapter keeps 16 explicit slots and returns `neighboring_low_word_float_write` when this happens. It does not mutate a native timer or claim that this boundary occurs in gameplay. The instruction behavior is verified with synthetic state; an external reset or restriction could prevent it live. Do not silently replace this with a conventional 15-slot moving average, or call it a confirmed gameplay bug.

## Validation and next observation

[480 instruction-emulation cases](frame_clock_policy_validation.json) compare interval bits, table index/counter, history index and all 16 history locations. They include all four recognized modes, two unknown modes, index 15, negative/zero elapsed inputs, the minimum and counter boundaries. Four repository tests cover transition examples, the unusual last-slot behavior and adapter guards. Finite numbers, valid table/history indexes and nonnegative signed counters are adapter restrictions; malformed native state and NaN behavior are excluded.

The live animation observation recorded neither this mode nor the root/world clock configuration. A useful next observation captures the driver's mode and rate/table fields, root and world clock intervals, holds and scales, component clock-selection flags, and the animation packet. Passive observations should establish normal cadence first. A debugger pair can then check identity and call flow without using stopped wall time as a frame-duration measurement. An idle/movement comparison also needs an observed movement or active-clip signal; absence of injected input alone does not prove idle.

## Live selected policy

The subsequent [passive baseline](CLOCK_OBSERVATION.md#original-game-baseline) observed mode 2 and a `1.0`-second cap in all ten samples. All three world clocks were found in the root's child list. The 30-valued rate field is inactive in this selected policy. The cap gives a concrete debugger-pause hypothesis for the earlier animation packet, but no controlled interruption experiment has proved it.
