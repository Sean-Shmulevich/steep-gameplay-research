# Reconstruction progress and next work

Status: active implementation. Scheduler reconstruction is now the main priority; see [release gates and experiments](SCHEDULER_ROADMAP.md). The requested full reconstruction is not complete. This file is the continuation point across implementation passes; do not restart or replace the existing prototypes casually.

## Implemented and integrated

- Standard-library source tree with explicit Z-up/XYZW conventions and synthetic scenarios.
- Snowboard, ski, walking, wingsuit and paraglider update paths.
- Shared input snapshots, tick stepping, recovered unsmoothed schedule option and state publication.
- Complete owned-state checkpoint/restore and command replay including frame scheduling and paused state.
- Synthetic rig/clip runtime, crossfade/additive animation, hierarchy and palette helpers.
- Environment clock/weather, camera spring/follow state and event-driven scoring.
- Terrain/material queries, swept obstacle collision, fault rollback and incident history.
- Rig/pose/trace inspection, contact-cell and IK probe functions and local browser/HTTP inspector.

These modules mix recovered local arithmetic and documented substitutes. Read README and module evidence before assigning fidelity.

## Passes completed in this implementation run

1. Independent modules and a headless integrated simulation.
2. Replay/transaction hardening, checkpoint continuation and camera state.
3. Browser inspection and numerical slope-contact regression fix; standalone contact/IK probes.
4. Optional six-cell rigid hull with rotating inertia and conserved world angular momentum; recovered 60 Hz sampling, inclusive wrapping and lazy graph readiness kernels.

5. Serializable pose graphs, ordered blending/masks/selectors, checkpointed graph clocks and transactional resource/tuning APIs.
6. Read-only archive framing/codec adapter and typed private rig/clip importer with independent translation/rotation tracks. Private corpus checks completed; payloads remain outside this repository.

7. Recovered smoothing/ring/table policy, constructor and conditional ingestion-job ordering audits, bounded runtime phase traces and headless scheduler experiments.
8. Action-binding reset writer and owner teardown follow-ups; owned pause/step controller with exclusive submissions and stale-token rejection. Native exclusion remains unproved.
9. Preserved standalone rig assembly, root-motion extraction, procedural pose stages, motion-state observer and provider-boundary modules. These are not yet wired into the default gameplay selector.

10. Further action callback/map closure, range-consumption arithmetic, optional child lifecycle tracing and queued backend completion. New local action/range kernels have synthetic boundary tests; no native execution claimed.

## Next implementation priorities

Scheduler work takes precedence over the broader backlog below: prove active membership/request identity, action-payload freshness, owner lifetime and submission exclusion. Implement and validate the owned dependency executor, then compare against a separately authorized original execution trace. See [scheduler roadmap](SCHEDULER_ROADMAP.md).

1. Refine the implemented rigid_cells mode with recovered face-area/contact selection, layered materials and original mass/body representation choices. The current six-cell box, volume weights and substrate are synthetic. Preserve separate pressure/contact contributions and elapsed/derivative intervals.
2. Connect a verified active rider graph to the implemented graph runtime. Graph arithmetic is available; authored graph wiring and timing remain unresolved. The default selector remains a labeled independent design.
3. Trace and implement active base/addon rig assembly and authored UID-to-compiled-key conversion. Until resolved, use explicit caller policies and report missing joints before fallback.
4. Extend the implemented local archive/pose adapter to additional validated resource types. Current checks cover every available archive index and selected compressed resources, not every payload. Do not publish extracted payloads or Studio-authored tracks.
5. Extend procedural layers with explicit IK request mappings, landing inputs and actor-to-pose timing. A callable target kernel is not a complete full-body solver.
6. Trace original action-vector writers and sample publication. Use these findings to refine compatibility scheduling; our input generation remains a designed feature.
7. Add terrain streaming, actual mesh rendering, material/lighting pipeline and local asset visualization after coordinate/binding tests. The current canvas is a diagnostic view.
8. Refine tricks, landing/crash classification, ragdoll, respawn, air zones, walking snow-depth behavior, scoring event ownership and camera arbitration using the existing research and focused new checks.
9. Add audio, persistence/version migration, packaging and performance work after the behavioral interfaces stabilize. No original networking or online service compatibility is claimed.

## Acceptance gates for every pass

Add evidence and tests for the changed behavior. Run the full suite when shared state or interfaces change. Preserve source manifests, no game payloads, no absolute machine paths, and valid links. Keep synthetic, asset-decoded, binary-derived, video-estimated and Studio-authored categories explicit. Update this file with completed work, actual test results and the next concrete task.

Validation checkpoint: see [validation scope](VALIDATION.md) for the current suite and private adapter checks. The earlier 121-test checkpoint included the gentle-curvature regression. Five synthetic 3,600-tick sport scenarios plus their replays matched hashes with zero recorded faults. Browser step control and canvas rendering were checked; an extension resource failure and missing favicon were observed, with the favicon reference then corrected. Full game parity and production rendering remain unverified.
