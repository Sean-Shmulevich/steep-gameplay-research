# Instructions for agents using this research

This repository contains findings and an independent experimental engine under engine/. It is not original engine source, a complete port or a complete extracted dataset. Do not tell a user that it contains any of those.

## Reading order

1. Read README.md and docs/STATUS.md.
2. Read docs/EVIDENCE.md before assigning confidence to a formula or observation.
3. Use docs/INDEX.md to select the relevant system. Read that system's guide, current pseudocode, findings and unresolved boundary before coding.
4. Read docs/ENGINE_RECONSTRUCTION.md for the proposed implementation layout and validation sequence.
5. Use SOURCE_MANIFEST.json to identify an original research source. Its paths name external local artifacts; do not assume those files exist in this checkout.

## Studio evidence

Studio contains both original-asset research and its own replacement animations and video-based estimates. Keep asset-decoded, binary-derived, video-estimated and Studio-authored substitute claims separate. A successful test of a substitute does not establish original behavior. Consult STUDIO_SOURCES.json and docs/reconstruction/ASSET_PIPELINE.md before importing further material.

Read engine/PROGRESS.md and engine/CONTRACT.md before extending the runtime. Run the tests appropriate to your changes; the full suite includes loopback HTTP tests.

## Implementing a system

- Extract its inputs, outputs, coordinate frame, units, activation gates, persistent state and update cadence into a short contract first. Explicitly mark unknowns.
- Preserve branch conditions, operation order, axis remaps, scalar-versus-vector distinctions and float32-sensitive boundaries described by the evidence.
- Cite the exact repository document and section for each implemented rule. Offsets are evidence anchors, not portable API fields.
- Keep three categories separate in code and documentation: recovered local behavior, derived equivalent mathematics, and an invented or tuned substitute.
- An unavailable asset/data file is a missing dependency. Do not manufacture its contents and label them recovered. Small synthetic fixtures are appropriate when clearly labeled.
- A formula with a missing producer is a configurable interface, not a license to guess the producer silently.
- Reconstructed classes, filenames and module boundaries are our design choices. Do not imply that they were original engine names.
- Do not apply the indexed physical-pose follower's caps to player tricks without proving the consumer. Do not treat immersion as a universal grounded flag. Do not assume weather changes grip or walking uses the snow-board controller.
- Source pointers and resource IDs are build-specific. Never reuse saved heap addresses in another game session.

## Tests and progress

- Test meaningful boundary cases and state transitions, not only example arithmetic: threshold crossings, release/reset, missing input, pause, blend ordering and sign/frame conversions.
- Keep headless simulation tests separate from renderer/animation tests. Rendering frame rate must not silently determine simulation time.
- A deterministic reconstructed simulator does not prove deterministic replay of the original game.
- Report what was implemented, its evidence, tests performed, remaining uncertainty and any substituted behavior. Do not publish an unsupported engine-coverage percentage.
- Failed or inconclusive experiments remain evidence. A valid identity guard does not turn sequential reads into an atomic snapshot.

## Editing or publishing this repository

- Organize public material by system. Keep chronological scratch runs, raw traces and large exports outside this repository.
- Preserve original evidence and superseding corrections in source manifests and clearly labeled notes. Do not erase provenance to make a claim appear stronger.
- Never add game executables, assets, decoded animation payloads, raw dumps, saves, credentials or local machine paths. Resource names, identifiers and links to research sources may be documented.
- Keep all internal links valid and run python3 scripts/verify_repository.py before a publication update.
- Do not launch, attach to, inject input into, or modify a game merely because a document describes an experiment. Follow the current user's authorized task and the environment's permissions.
- When multiple agents work together, assign system ownership, coordinate shared interfaces, and preserve each other's edits.
