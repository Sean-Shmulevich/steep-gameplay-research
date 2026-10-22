# Mod-loader handoff

Start with [build and run](../native/snow_host/BUILD_AND_RUN.md). The public tree
now includes the authored game adapter; build-specific addresses alone are no
longer a reason to withhold integration source. Compiled game payloads and assets
remain excluded.

## What another engineer can build

- Native host, startup launcher and checked loader.
- Plugin API and step/player logging examples.
- Pause/step/resume, player reads, velocity/placement adapter, passive animation
  readers and Python command client.
- Independent reconstruction, reference formulas, synthetic workbenches and tests.
- Snow-update observation DLL with synthetic Windows/Wine validation. It includes a synthetic-tested slot installer/restorer and is not a normal
  host plugin. Live installation remains untested.

A clean export of the staged publication passed 1,635 tests and built both the
fixture and game-adapter host variants with MinGW warnings treated as errors.
This validation did not launch the game. Earlier live acceptance is recorded in
[native host findings](../native/snow_host/README.md#post-update-end-to-end-acceptance-passed)
and its JSON receipts. Scope those results to their reported sessions/builds.

## Next engineering milestone

Install the snow-update observation probe at the verified actor slot, measure
pending impulse and both bodies before/after eligible updates, and correlate the
records to the same request/substep. Then test one bounded native impulse that
preserves spin. Current velocity assignment resets angular velocity.

The probe core, reader and reversible slot installer are implemented and
synthetic-tested. The opt-in capture plugin now supplies held-mode player acquisition, owner/counter
resolution, bounded observation and QPC-tagged JSONL export. Its complete lifecycle
is synthetic-tested. Fresh acquisition, slot installation and capture still need
validation together in a bounded live game session. Drained capture does not permit unloading cached
callbacks. Keep DLL/context pinned, forward late calls, and never overwrite an
unexpected callback on restoration. Captured body reads are sequential, and a
wrapper interval includes other snow forces. Exact consumer observation remains
the stronger attribution test.

## Other agents' work included

The catch-up includes animation banks/blending/skeletons, scheduler and dependency
models, replay-record inspection, central-impulse math, examples and evidence
receipts already present in the shared research tree. Passing reconstructed tests
is not proof of native engine equivalence.

The [Studio map update](reconstruction/MAP_DECODING_UPDATE.md) imports six pinned
specifications, including the decoded height/class/material codec. Their reported
asset-validation results were inspected but not rerun here. The Studio browser
runtime's collision proxies, placement rules and authored animations must remain
separate from recovered original behavior.
