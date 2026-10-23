# Scheduler smoothing and history policy

This audit closes a documentation-to-implementation gap. The timing producer already exposes the complete local history update and frequency selection. No additional live debugger capture is needed to implement that arithmetic. This does **not** close original-process safe stepping, input freshness, world ownership or the task graph's complete drain boundary.

The [scheduler research](research/scheduler.md) documents the producer and consumed/substep distinction. This pass reread its full saved assembly and independently compared all 158 listed instructions with the studied image; all matched. The 13-entry float32 frequency table was independently reread. No game launched, debugger attached or process memory changed.

## Exact local state

The timing stage owns retained accumulated duration, a float32 history array, history count, next-write index, oldest index, capacity, selected frequency, consumed duration, reciprocal consumed duration, number of substeps and per-substep duration. A smoothing-enable flag and a separate external policy byte select branches.

A valid initialized ring has positive capacity, count between zero and capacity, valid indices, and next-write equal to `(oldest + count) % capacity`. A reconstruction should validate these preconditions. The native arithmetic assumes valid storage; adding rejection for invalid or nonfinite inputs is a reconstruction safety policy.

The history contains **raw incoming frame durations**, not capped accumulated durations, consumed durations or individual substep durations. It is a moving arithmetic mean over samples, not an exponential filter or duration-weighted average.

## Complete smoothing pseudocode

`f32` means round to binary32 at the indicated operation. This describes ordinary finite, nonnegative durations and valid integer/ring state. `trunc` truncates toward zero.

```text
incoming = f32(frame_dt)
acc = f32(retained + incoming)

if smoothing_enabled:
    acc = min(acc, f32(0.06666667014360428))

    history[next_write] = incoming
    count += 1
    if count > capacity:
        overflow = count - capacity
        count = capacity
        oldest += overflow
        if oldest >= capacity:
            oldest -= capacity
    next_write = (next_write + 1) % capacity

    total = f32(0)
    for i in range(oldest, oldest + count):
        total = f32(total + history[i % capacity])
    mean = f32(total / f32(count))
    if mean <= 0:
        table_index = 0
    else:
        ratio = f32(f32(0.2) / mean)
        table_index = min(trunc(f32(ratio + f32(0.5))), 12)
    frequency = FREQUENCIES[table_index]
else:
    next_write = 0
    oldest = 0
    count = 0
    frequency = f32(120)
    # Existing array values are not erased; count excludes them.

if policy_byte == 1:
    frequency = f32(90)

# Continue into the documented epsilon/count/remainder policy.
# History and frequency updates happen even if that policy emits zero steps.
```

The table is indexed in this exact order:

```text
index:       0    1    2   3   4    5   6    7    8   9   10   11   12
frequency: 100  100  100  90  80  100  90  105  120  90  100  110  120
```

The unusual, nonmonotonic entries must not be replaced by a smooth approximation. Summation must follow oldest-to-newest order with float32 rounding after each addition. A running-sum optimization is not guaranteed equivalent at table boundaries.

## Consequences that matter for reconstruction

- The accumulator cap discards excess accumulated time. It does not carry that excess into a second backlog. Our fixed-step mode's backlog retention is a different designed policy.
- A long stall is still recorded in the history at its full incoming duration, even though the accumulator is capped. Recording only the capped duration changes future frequency selection.
- A zero incoming duration still occupies a history slot. The subsequent near-zero check can emit zero substeps while history changes.
- Disabling smoothing clears the logical history and chooses 120. Re-enabling starts a fresh history; old array contents must not become active again.
- Policy exactly one forces 90 after the history update. It does not suppress history collection. Other nonzero policy values alter subdivision rounding/remainder rules without that exact override.
- An arbitrary caller-supplied frequency in an unsmoothed implementation is an extension. The inspected native branch selects 120, then applies the policy-one override.
- The producer uses a caller-owned capacity. The prior live study observed ten entries, but that is not proof that all instances or constructors must always use ten.

## Worked boundary examples

These examples start with no retained duration and an empty valid history, smoothing enabled and policy zero. Input durations are rounded to float32 first. They are calculated examples of the recovered arithmetic, not new runtime measurements.

| Incoming duration | Table index | Frequency | Substeps | Per-substep duration, approximately |
| --- | ---: | ---: | ---: | ---: |
| 1/120 | 12 | 120 | 1 | 0.008333334 |
| 1/60 | 12 | 120 | 2 | 0.008333334 |
| 1/30 | 6 | 90 | 3 | 0.011111111 |
| 1/20 | 4 | 80 | 4 | 0.012500000 |
| 1/15 | 3 | 90 | 6 | 0.011111111 |
| 1 second stall | 0 | 100 | 7 | 0.009523810 |

The last row consumes only the capped interval, while retaining the full one-second sample in its history. Selecting frequency 120 does not imply a universally fixed 1/120-second simulation.

Useful compatibility cases are empty-ring warmup; wraparound and oldest eviction; zero-duration insertion; full stall versus capped accumulator; disabling/re-enabling; policy-one history collection; float32 table-index boundaries; and restoring a checkpoint whose history is partially filled. Changing capacity mid-history needs an explicit reset or migration policy; it is not specified by this local producer.

## What remains genuinely open

The external policy byte's semantic meaning and its full writer/lifetime inventory are not recovered by this arithmetic. Neither are every scheduler instance's initialization, smoothing-toggle ownership, capacity-change behavior, source-clock production and reset lifecycle. Original-game capture needs the selected world and scheduler generation, raw incoming duration and complete ring state to distinguish those cases.

A timing stage that reproduces this formula still cannot safely pause the original engine merely by preventing its next substep. Jobs, completion counters, publication buffers and external readers must reach the appropriate boundaries. Input ingestion must be correlated with the consuming world/substep separately. These are the remaining scheduler-control problems; the local smoothing formula itself should no longer be listed as missing research.

## Evidence receipt

The prior source attribution is retained in the linked scheduler research. Newly verified instruction count: 158. Studied image SHA-256: `32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`. Timing producer's contiguous code-window SHA-256: `6c078e3bab452a7f0a6aefe2628371b667aac3ef92c7169f3141e6340cd34a96`. These identify the checked source without distributing executable bytes or requiring addresses in an implementation API.

## Bounded timing-state reader

`engine.physics_timing_observation.observe_physics_timing` reads the inspected
52-byte timing block, external policy byte, current world interval, and up to
64 history lanes. It requires a freshly qualified timing-owner address, expected
physics-manager identity, build-qualified policy location and exact-read
transport. Two equal sequential samples are required. Work is bounded to 12
reads and 658 bytes; no process writes or engine calls occur.

The returned values include retained duration, consumed duration, reciprocal,
frequency, selected count, elapsed duration, smoothing flag, physical ring bits
and chronological active-ring bits. Unused ring lanes can contain arbitrary
bits; active lanes and timing fields must be in the reader's finite nonnegative
domain. Zero selected steps with nonzero initialized durations is accepted,
consistent with the constructor. Unsupported ring capacity/layout and changing
samples are reported without a partial timing result.

The producer's 12 timing-field offsets and external policy load were rechecked
against the inspected instruction spans. See [reader validation](../../native/snow_host/physics_timing_reader_validation.json).
Synthetic tests cover every read failure, owner/policy change, wrap order,
unused versus active NaN lanes, capacity limit, and initialized zero-step state.
The reader has now been used live; see the transition check below. Current world interval is an
observation, not a proved input to the already-produced batch. Retained state
is sampled after or during whatever phase the caller selected, not reconstructed
pre-update state. Returned pointers are private provenance; strip them from
published receipts. Object lifetime and full-cycle mutation remain unresolved
even when both samples agree.


## Timing transition replay and observed cadence gap

`engine.timing_transition_replay.replay_timing_transition(before, after)` accepts
qualified reader timing dictionaries. It checks unchanged identities and policy,
then requires the count/cursors and untouched ring lanes to match one append.
Only then does it replay the recovered scheduler arithmetic and compare float32
output bits. This is an authored consistency check: full ring cycles or other
writers can alias a single append, so acceptance never proves execution count.

The first live pair spanning one host release request is rejected: the full
10-entry ring advanced from cursor 3 to 9 and six lanes changed. Both snapshots
reported policy 0, smoothing enabled, frequency 100, seven substeps, and consumed
time 0.06666667014360428. Equal capped outputs conceal the history difference;
this pair cannot validate one producer invocation. Resume and cleanup succeeded.
See [sanitized observation](../../native/snow_host/timing_transition_observation.json).

Next experiment: sample the same qualified timing owner repeatedly while the
world remains held, with no release command. Correlate request-token stability,
EndFrame observations and sample timestamps with history changes. This tests
whether timing preparation can advance independently of the held world; it does
not assume a cursor delta equals an invocation count.
