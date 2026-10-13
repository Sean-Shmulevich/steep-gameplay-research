# Reconstruction testbench

Studio's replay, VFS and debug API documents describe its own reconstruction infrastructure. They do not demonstrate deterministic stepping of the original game. Its fixed-tick replay and native/browser hashes are useful design precedents; the original scheduler remains a separate problem.

Proposed API: `loadScenario(description)`, `setInput(tick, actions)`, `step(count)`, `state()`, `startCapture(fields)`, `stopCapture()`. Scenario descriptions include schema version, content hashes, initial state, random seed, coordinate convention and all substitute policies. Serialize input by simulation tick; keep wall-clock input latency as separate telemetry. Make one core dispatcher serve both a headless process and a browser adapter.

Capture input ingestion, substep entry and publication with their own sequence numbers when instrumenting code we control. Snapshots should contain body pose/velocity, contact and material identity, raw/shaped input, trick target, animation state/phase and active policy. Record unavailable fields explicitly. Compute hashes only over canonical fields with fixed float encoding and ordering; exclude wall-clock timestamps.

For passive external sampling, read identity before and after each bounded group, record start/end times and reject a changed identity. Matching identities do not guarantee atomicity or catch every swap-away-and-back case. Do not infer scheduler order from close host timestamps. The included [bounded sampler](../../testbench/capture.py) has an injected backend, no game attachment or memory addresses, and cannot interrupt a blocked backend call; production backends must enforce their own timeout.

The [selected contact observations](../../data/observations/README.md) are useful for schema and qualitative transition checks. They are sparse, non-atomic and input alignment was not verified. Their original capture failed the cadence gate. Do not use them as frame-by-frame ground truth or fit acceleration from sparse samples without reporting that limitation.

Studio's VFS suggests another useful boundary: validated root-relative paths, whole-file/range reads, native/browser adapters and request/byte counters. Use half-open ranges and distinguish HTTP partial responses from full responses before slicing. Put a byte budget and eviction policy on caches; the documented unbounded cache is a limitation, not a recommended production default. Keep archive extraction separate from runtime loading.
