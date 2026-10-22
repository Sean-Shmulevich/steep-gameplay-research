# Offline animation pool sessions

The session adapter exposes recovered pool reuse, release and pose-work wrapper
cleanup as a stateful inspection API. It does not connect to the game, allocate
native memory, run animation work or establish a scheduler boundary.

```sh
python3 -m engine.animation_pool_session engine/examples/animation_pool_input.json
```

Use `--output result.json` to save the result. Every operation reports its resulting
bank/pool state and requested external services. The input SHA-256 identifies the
supplied scenario. The example is synthetic and exercises acquisition, a second
acquisition requiring allocation, release, reuse and temporary-wrapper cleanup.

## Input and service boundaries

Schema `animation-pool-session-v1` accepts named `banks`, ordered `entries`, and
1 to 256 `operations`. Bank state has uint32 `flags` and uint16 `auxiliary_mask`
and `auxiliary_count`. Each entry references a bank name and supplies uint16
`occupied_mask`, `initialized_mask`, and `representation_word`.

Bank names define identity. Different names remain distinct even with equal
contents; repeating a name models shared references. The session copies input
state, and snapshots are detached copies. This is our API design, not an original
engine naming or serialization format.

Supported operations:

- `acquire`: supplies `request_mask`, binary `representation`, three-bit `mode`,
  and a source token. Returns `reused` with bank identity or `allocation_required`.
  A miss does not invent a bank or change pool state.
- `release`: supplies `bank` and `request_mask`. Reports whether an entry matched.
- `cleanup`: supplies `output` and `input` wrapper descriptions, each with primary
  and alternate bank names or null, flags, index/request mask, header and storage
  token. Executes output cleanup before input cleanup.

The JSON runner requires explicit service policy
`record_calls_without_pose_copy`. It records requested pose-copy, auxiliary-clear
and storage-free calls with `executed: false`. It applies the recovered caller's
mask, count and flag updates, but does not copy pose records or free storage.
Thus its result is an ownership/control-flow inspection, not a complete bank
conversion or animation result.

Python callers can use `AnimationPoolSession` with explicit `copy_selected`,
`clear_auxiliary` and `free_storage` callbacks. Copy and clear callbacks receive
actual session bank objects, so their changes remain visible to later operations.
Callbacks must implement any required record/storage effects. Exceptions can leave
partially changed session state; the API provides no rollback guarantee.

## Evidence and remaining work

Rules come from [pool reuse](CENTRAL_IMPULSE.md#animation-bank-pool-reuse),
[release](CENTRAL_IMPULSE.md#animation-bank-release) and
[wrapper cleanup](CENTRAL_IMPULSE.md#pose-work-wrapper-cleanup). Their original-
instruction receipts cover bounded synthetic states. The session tests establish
composition, identity, input isolation and explicit service/miss reporting.
Neither type of test proves live concurrency, safe retained pointers or native
allocation behavior. Growth, allocation misses and whole-job execution remain
unimplemented boundaries.


## Execute copying on supplied pose bytes

```sh
python3 -m engine.animation_pool_session engine/examples/animation_pool_copy_input.json
```

Policy `copy_supplied_pose_bytes` executes recovered masked/full copy rules.
Provide `sources` keyed by the acquisition's source token. Each source supplies
`data` and a 32-byte `parent_header` as JSON byte arrays. Partial-copy sources
supply `group_count`; their destination banks supply `group_words` and
`descriptors`. Full-copy sources supply three `bulk_boundaries`. Each byte array
is bounded to 1 MiB. The reference's layout checks still apply.

Service traces mark executed copies true and include selected groups or full-copy
regions. Result snapshots include changed bytes. Auxiliary clear and storage free
are still recorded with executed false. Bank reuse sets bit 26 before copy and
clears bit 27 afterward, preserving the destination parent header on this route.
The example tests partial copying, release/reuse, cleanup and full copying while
preserving destination bytes outside the copied region. All data is synthetic.


## Explicit allocation services for Python callers

For reconstruction callers that supply storage, `acquire_pose_bank` in
`reference.animation_bank_pool` combines reuse, new-slot initialization,
construction and full-copy seeding. See the [service contract](CENTRAL_IMPULSE.md#explicit-service-acquisition-api).
Run `python3 -m engine.examples.animation_pool_allocation_demo` for a synthetic
allocation/release/reuse cycle. Allocation is not provided implicitly by the JSON
runner. Exceptions can leave partial publication, and no native heap/lifetime
or concurrency guarantees are implied.


Copy metadata may be supplied through an attached `profile`. It takes precedence
over flat fixture fields: source profile owns `group_count`/`bulk_boundaries`, and
destination profile owns `group_words`/`descriptors`. Allocation-created banks keep
their supplied profile, enabling later partial copies and use as a copy source.
The allocation demo exercises full initialization followed by partial reuse.
