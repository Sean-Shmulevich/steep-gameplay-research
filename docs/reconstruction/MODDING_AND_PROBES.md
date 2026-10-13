# Reconstruction, mods and experiments

A reconstructed engine would let us change code, step a controlled simulation, inspect complete state and replace content through explicit adapters. That control applies to our implementation. It does not establish that the original game executes the same branches or produce an automatic mod loader for it.

| Approach | What it makes possible | What it cannot establish alone |
| --- | --- | --- |
| Independent simulator | Exact input journals, seeded scenarios, stepping, full state capture and parameter sweeps | Original-game fidelity |
| Asset adapter | Locally supplied rigs/clips/materials in a versioned intermediate format | Original runtime selection, legal redistribution rights or original archive writeback |
| Original-game passive probes | Observe selected live state and validate inferred joins | Atomic snapshots or deterministic stepping without additional boundaries |
| Original-game hooks or mods | Potential event traces, controlled overrides and custom experiments | Safety or compatibility merely from knowing a static function |
| Paired experiments | Compare a narrow behavior in both implementations | Whole-engine equivalence from one matching scenario |

## Practical sequence

Start with a narrow executable loop: input shaping → snow contact → body integration → animation pose → telemetry. Use an invented slope and rig until the asset adapter is checked. Give every unknown producer a named configurable implementation, so experiments can distinguish a recovered formula from a substitute policy.

For skeletal work, compare local sampling, model propagation, remapping and palette output separately. Freeze physics while inspecting pose; freeze animation while checking momentum. These are useful controls in our implementation, not assumed safe operations in the original scheduler.

A mod API can then expose scenario creation, materials, tuning, replacement clips, graph inputs and camera settings. Every override should carry its source, scope and reset behavior. Resource replacement requires skeleton/channel compatibility and explicit missing-joint behavior. Start with our own loader; writing replacement original archives or patching a live game is a separate project.

For original-game probes, prefer a bounded event recorder over broad mutable hooks. Establish object lifetime, callback signature, thread ownership and a stable publication point before adding a hook. Record sequence numbers, not only wall-clock time. A save file or a register dump is not a complete simulation checkpoint: jobs, queues, allocator state, external input and random state may also matter.

## Highest-value result

We do not need to reconstruct the entire renderer, audio stack, menus or networking to gain a useful physics/animation laboratory. The first milestone is a small inspectable implementation whose inputs, intermediate states and outputs can be compared with known local formulas and bounded observations. Broader reconstruction should follow evidence and practical needs, not a guessed coverage percentage.
