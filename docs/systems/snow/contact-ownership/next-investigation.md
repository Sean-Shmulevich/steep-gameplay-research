> Findings-only publication. Companion assets, datasets, binaries and raw traces are not distributed. Read [current status](../../../STATUS.md) for qualifications. Source provenance is retained in the repository manifest.

# One decisive read-only experiment

Proposed only. Do not run as part of this static investigation.

Question: when sufficient immersion returns, does the cached skip remain set across a stable positive-contact interval, or does the exception occur only while sequential reads cross writes?

Use the existing guarded read-only transport. Before capture, the human resets to the chosen existing descent and fixes camera and input state. Require the same player, actor, runtime and main-body ownership chain, a sufficient-immersion interval with skip0, then a sampled absence interval that reaches the .04 threshold. Pose similarity alone is not a reset receipt. Record the camera/input preconditions and reject an unmatched reset.

The human repeats the same single descent/landing action. The recorder injects no input, invokes no game functions, attaches no debugger and writes no process memory. Start capture before the action and stop after the first absence-to-contact timer reset or 2 wall seconds, whichever comes first. If no qualifying reset occurs, report no event and stop.

Discover actor/runtime/body through the current membership and ownership checks already used in run36. Do not scan arbitrary address space or reuse old absolute pointers. Cap discovery and reject a changed owner, count outside configured bounds, null/unreadable link or changed process identity. Descriptor/material discovery is unnecessary for this experiment and should not be added until its resource identity and generation guards are designed.

The current transport needs a bounded repeated-read operation to make this experiment dense across a physics step. Prepare and self-test that helper offline before the authorized capture. One native request should reuse the same at-most64 read ranges for a maximum25ms burst, with at most32 alternating groups. Bound the entire capture to80 such requests and2 wall seconds. The Python client must not add a long sleep between groups, which occur inside the native operation. Never infer successful cadence from the requested rate.

Within each native burst, read compact groups in alternating order:

```text
skip -> absence_timer -> immersion -> contact_timer -> update_step
update_step -> contact_timer -> immersion -> absence_timer -> skip
```

Bracket each group with actor/runtime identity checks and available job state. Record actual start/end timestamps for every field read and retain the full membership/ownership guards at burst entry and exit. Keep the existing read-only process rights, process identity checks, range/byte bounds and watchdog; the burst adds strict group-count and time caps. Target <=1ms group cadence. If measured p95 group interval exceeds2ms, report that limit; if gaps exceed5ms around the reset, reject the transition for phase discrimination. Do not substitute a long high-rate unguarded list.

Measured values are a boolean cached skip, dimensionless immersion, contact/absence timers and update step in stored update-time units, job counters/state and wall-clock milliseconds. Timer seconds are conditional on the simulation step's unit binding; do not infer them solely from a value near.01. Record actor and motion snapshots only before/after the short burst if the range budget permits. They are not necessary to answer the timer/skip question.

Expected discriminating outcomes:

- Several complete forward/reverse groups show positive immersion, absence_timer0, advancing contact_timer and skip1 with stable owners and no observed bracket change. This supports a persistent cached-phase offset or alternate skip writer; it weakens a single read-boundary explanation. It still does not identify the executing writer.
- The mismatch appears in one group whose reverse group sees skip0, or field reads show a timer reset within the group. This supports crossing update writes; it does not prove an atomic state ever contained all values.
- Immersion clears after contact_timer advances while absence_timer stays0. This matches the separately recovered post-timer immersion-clearing branch and tests the broader field-equivalence assumption.
- Cached skip changes without the expected timer relation across repeated stable groups. Keep the record-copy writer or another writer open and stop interpreting skip as a pure timer function.

Failure conditions include owner mismatch, short read, process change, watchdog stop, unmeasured cadence, unmatched reset, no qualifying transition, or exhausted budget before a bounded event. Preserve all rejected receipts. Even passing outcomes leave frame scheduler order, universal grounding, exact material, complete crash classification and animation selection unproved.

If static analysis must continue instead, trace one edge: callers that order actor refresh versus the activity tick that enters the environmental update. Inventory direct call sites to the two functions, cap at64 candidate sites, and export at most four selected enclosing functions under24KB each. Stop when the same owner/update invocation is shown to order both calls or when dispatch/virtual scheduling prevents that join. Record the unresolved scheduler object rather than exporting the whole caller graph. Exact endpoints are in PRIVATE_EVIDENCE.md.
