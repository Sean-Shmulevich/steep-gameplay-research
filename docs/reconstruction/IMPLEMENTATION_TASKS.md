# Implementation work packages

These packages can become an independent source tree. Each must keep recovered rules, equivalent math and designed substitutes distinguishable. Review the [machine-readable contracts](../../contracts/systems.json) before assigning work.

| Package | Dependencies | Deliverable | Acceptance boundary |
| --- | --- | --- | --- |
| Math and clocks | None | Float32 helpers, frame conversion, typed tick/phase/event clocks | Threshold tests; no implicit unit conversion |
| Asset adapter | Math | Versioned descriptors, patched resource IDs, bounded readers | Synthetic corruption tests; missing resources fail explicitly |
| Input shaping | Clocks | Axis shaping, smoothing, speed blend | Press/hold/release and threshold crossings; record ingestion tick |
| Snow contact | Math, material adapter | Cell clipping, relative motion, force/impulse kernels | Dry/wet boundaries, moving support, no duplicate dt |
| Body integration | Snow | Explicit mass/inertia and impulse ownership | Linear/angular momentum checks; separate rider mass |
| Tricks | Input, body | Target generation and delayed response | Visual/body target separation; reset traces; no borrowed universal cap |
| Clip and skeleton | Asset adapter, clocks | Playback, blends, hierarchy | Inclusive wrap, ordering, LOD retention, synthetic bind roundtrip |
| Landing pose | Clip and skeleton, contact history | Proven alignment/tilt plus configurable selection | Air/contact transitions; visual correction does not inject impulse |
| Walking | Body, contact query | Designed controller behind unresolved adapter | Explicit substitute label; slopes, feet, moving support |
| Environment | Clocks, material adapter | Time-of-day and ordered weather overlays | Pause and wrap branches; no assumed weather/grip coupling |
| Camera/scoring/air | Relevant subsystem contracts | Implement chapter-local rules incrementally | Unknown producers configurable; sport-specific tests |
| Testbench | All published state | Scenario, input journal, snapshots, hashes | Repeatability in our simulator; no claim about original replay |

For each package, deliver source, a short evidence map, boundary tests, open inputs and one headless scenario. Keep the first runnable vertical slice narrow: one invented slope, one board body, one input stream, one synthetic skeleton. Rendering and broad asset import should follow stable telemetry, not hide missing state.

When a producer is unknown, define its type and record the chosen substitute beside the scenario. Do not tune a hidden constant and then call the resulting formula recovered. Require separate review when changing frames, units, integration order or ownership across packages.
