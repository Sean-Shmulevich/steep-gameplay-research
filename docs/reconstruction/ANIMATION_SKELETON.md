# Initial skeleton assembly adapter

`engine.animation_skeleton.assemble_initial_skeleton` connects recovered local
metadata operations to the hierarchy and preparation APIs. It is an independent
composition, not a reconstruction of every branch in the native assembly routine.

## Contract

Supply source records, one 32-byte backing record per source, the byte selector,
per-key rank overrides, numeric owner selector and visibility, two independent
sorted lookup tables, and preset key lists. Backing bytes are required because
initialization preserves some prior bits. The adapter does not assume zeroed
allocation. Tables use `(uint32 key, uint32 encoded_index)` entries; missing tables
may be `None`. Preset names are `standard`, `extended`, and `alternate`. The public
[identifier catalog](../../native/snow_host/authority_channel_identifiers.json)
provides recovered preset keys without animation payloads.

Operations run in this adapter's explicit order:

1. Initialize new metadata records, preserving unspecified backing bytes.
2. Project source parent, span, source/link indices, selector, and key fields.
3. Apply default/override hierarchy ranks.
4. Select authority keys using the owner table and resolve their indices using
   the runtime table. Preserve duplicate selected indices and table order.
5. Decode rank and authority fields for the hierarchy API.

The returned `metadata` and `indices` can be passed to
`engine.animation_preparation.prepare_animation`. `rows` retains the structured
source projection and final packed flags for inspection. Inputs are not mutated.
This adapter emits neither complete native records nor guessed values for their
unknown bytes. Record count is bounded by the recovered 14-bit packed capacity.
No time integration occurs here; poses, coordinate units, numeric services,
request timing and processed hierarchy prefix remain caller responsibilities.

## Evidence and limits

Local rules are documented in [the animation reconstruction findings](CENTRAL_IMPULSE.md):
“Runtime metadata initialization and in-capacity resize,” “Initial source-bone
metadata builder,” “Hierarchy rank producer,” and “Authority selection with
original lookup routines.” Their separate original-instruction receipts validate
local operations. They do not validate this entire composition against the native
assembly routine, including intervening merge/reindex branches.

The integration tests use synthetic source records and poses. They establish
that assembled flags select the intended direction and skip behavior in the
reconstructed hierarchy, and that duplicate work indices and distinct lookup
tables survive the adapter. They are not live-game or complete assembly parity
tests. Owner enum names, merged rigs, mapping-table construction, asset-to-active
rig selection, allocator behavior and scheduler invocation remain unresolved.

Run `python3 -m unittest tests.test_animation_skeleton` from the repository root.
