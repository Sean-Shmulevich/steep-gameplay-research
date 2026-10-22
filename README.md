# Steep gameplay research

Research notes, equations, pseudocode, and bounded runtime observations about **Steep** movement, snow contact, tricks, animation, camera, scoring, and environment systems.

This repository contains findings, selected executable reference math, synthetic tests and reconstruction guidance. It now also contains an independent experimental engine source tree. It is not original engine source, a complete playable port, or a complete decompilation. It contains no game executable, asset archive, extracted animation tracks, textures, meshes, audio, save data, memory dump, or video. Names, resource identifiers, offsets, and hashes appear where they help identify what was studied.

## Run the independent engine

`python3 -m engine.cli --serve --port 8770` starts the local inspection lab. See [engine setup and API](engine/README.md) and [active reconstruction progress](engine/PROGRESS.md). The engine combines recovered local kernels with explicitly labeled substitute policies and synthetic content.

Current priority: [scheduler reconstruction and modding release gates](engine/SCHEDULER_ROADMAP.md). The reconstructed scheduler now exposes smoothing decisions, frame plans and bounded execution traces. The optional [recovered queue policy](docs/reconstruction/QUEUE_POLICY_MODEL.md) adds category ordering, affinity and occupancy selection. Original-game pause/step safety remains unresolved.

## Build the mod loader

The [standalone native build](native/snow_host/BUILD_AND_RUN.md) includes the
build-specific game adapter, startup launcher, plugin API, sample plugins and
observation sources. It builds without the private research workspace. Running
against the game requires your own compatible installation and runtime setup.
Reviewed authored C/C++ headers and C sources are publishable; game payloads and
raw decompiler exports remain excluded.

The [map decoding update](docs/reconstruction/MAP_DECODING_UPDATE.md) summarizes
Studio's terrain height/class/material results and separates measured asset
behavior from authored browser collision and placement policies.

## Start here

The [native module loader experiment](native/mod_loader/README.md) now has a
single command for the configured local research workspace: launch the original
game, pause, load an attachment-only DLL, resume, verify, and clean up. It needs
the existing private runtime tools and game installation; the public repository
contains source and findings only. The [Snow mod host](native/snow_host/README.md)
builds on it: a host with a local command channel, native plugins, player APIs,
and pause/step/resume. Its v0.7 startup launcher has loaded the host before any
observed game window, then passed controlled stepping after reaching gameplay.

- [Current findings and open questions](docs/STATUS.md)
- [Full research index](docs/INDEX.md)
- [Evidence conventions and limitations](docs/EVIDENCE.md)
- [Source and resource references](docs/SOURCES.md)
- [Guidance for implementation agents](AGENTS.md)
- [Engine reconstruction plan and proposed source layout](docs/ENGINE_RECONSTRUCTION.md)

| Topic | Entry point |
| --- | --- |
| Snow forces, carving, input shaping, springs | [Snow guide](docs/systems/snow/CLIENT_GUIDE.txt) |
| Spins, flips, grabs, and motion resets | [Tricks guide](docs/systems/tricks/OVERVIEW.txt) |
| Skeleton, clips, blending, and procedural pose | [Animation guide](docs/systems/animations/OVERVIEW.txt) |
| Landing pose | [Landing guide](docs/systems/animations/landing-pose/CLIENT_GUIDE.txt) |
| Camera | [Camera guide](docs/systems/camera/CLIENT_GUIDE.txt) |
| Wingsuit and paraglider | [Air sports](docs/systems/air/CLIENT_GUIDE.txt) |
| Scoring | [Scoring guide](docs/systems/scoring/CLIENT_GUIDE.txt) |
| Time of day and weather | [Latest environment pseudocode](docs/systems/world/environment-runtime/pseudocode.md) |
| Walking and walking through snow | [Research leads, not recovered implementation](docs/systems/walking/research-plan.md) |

## Recent findings

- A sampled main-body inverse mass exactly matched the float32 reciprocal of an authored hull volume multiplied by its density. This distinguishes that body from the separate rider tuning mass; it is not a universal mass for every representation.
- Contact queries connect to per-cell fluid profiles and force evaluation. A retained collision-mask summary must not be mistaken for a material pointer.
- Time-of-day progression, pause gates, weather scalar interpolation, and ordered preset overlays have concrete pseudocode. Track time decoding and weather-to-grip coupling remain open.
- A trick target reaches entity transforms. The specific snowboard notification inspected performs no body assignment; other component and child paths remain unresolved.
- Live movement was observed alongside contact return and loss. Sampling gaps prevent a precise conclusion about update ordering.

The chapters contain much more local arithmetic than these summaries. A recovered formula does not establish that its branch is active for every sport, material, or animation state.

## Organization and provenance

The public layout groups findings by system, not research session. Source-run identifiers remain only as provenance or quoted context inside reports. Some earlier documentation calls the project `snow_game` and uses neutral asset aliases. Those are historical presentation names for this same research, not evidence of a different game. Resource IDs and GUIDs are more reliable matching anchors than aliases. Read the status page before interpreting older claims embedded in a chapter.

Except for the reviewed modules listed in [Executable references](reference/README.md), historical companion `reference.py`, `named_data.json`, raw instruction exports, verification receipts, and game resources mentioned in historical chapters are **not bundled**. Claims that a local reference or verification suite ran describe the original research workspace, not the new synthetic test suite shipped here. The prose and inline examples can be read without owning the binary; reproducing static analysis requires the corresponding local build and tooling.

## Reconstruction additions

See the [animation pipeline](docs/reconstruction/ANIMATION_PIPELINE.md), [asset decoding strategy](docs/reconstruction/ASSET_PIPELINE.md), [implementation tasks](docs/reconstruction/IMPLEMENTATION_TASKS.md) and [testbench design](docs/reconstruction/TESTBENCH.md). Studio documentation was reviewed read-only; its provenance and unverified boundaries are preserved.

For the latest focused results, see [modding and probes](docs/reconstruction/MODDING_AND_PROBES.md), [skeletal joins](docs/reconstruction/research/skeleton.md), [animation binding](docs/reconstruction/research/animation.md), and [shared action storage](docs/reconstruction/research/input-probes.md). These are offline findings, not new live-game validation.

## Repository checks

Run `python3 -m unittest discover -s tests -v` for reference and synthetic fixture tests. Run `python3 scripts/verify_repository.py` to check this publication's text-only inventory, provenance hashes, and internal Markdown links. This checks packaging, not gameplay correctness.

Independent research; not affiliated with or endorsed by Ubisoft. See [NOTICE](NOTICE.md).
