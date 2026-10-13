# AI update job queue assignments

A focused follow-up connects the common base constructor to the already mapped
AI global update provider. The direct-call scan found 261 calls aligned to decoded
instructions inside exception-directory ranges. That is a bounded candidate
inventory, not an exhaustive count of all constructor invocations. The results
below come from manual inspection of one owner constructor and its setup method.

## Named jobs and construction rules

All rows below receive category **1** at construction. The base constructor zeros
required and excluded masks. Values describe the inspected construction/setup
path; later runtime writes have not been ruled out.

| Debug label | Base byte limit | Explicit limit writes observed |
| --- | ---: | --- |
| AIEngineGlobalUpdateSetup | 1 | Constructor sets 1 after base initialization |
| AIEngineGlobalUpdateStep1 | 255 | Setup sets 1 |
| AIEngineGlobalUpdateStep2 | 255 | Setup sets 1 |
| AIGlobalUpdateStep3 | 255 | No additional limit store identified in inspected setup |
| UpdateCoordinatorMultiThreaded | 255 | No additional limit store identified in inspected setup |
| UpdateCoordinatorSingleThreaded | 255 | Setup sets 1 |
| CoordinatorManagerUpdate | 1 | Constructor sets 1 after base initialization |

The base limit for rows without an override is the signed-minimum/byte-conversion
rule in [queue producers](SCHEDULER_QUEUE_PRODUCERS.md), evaluated at construction.
The value 255 is an argument, not proof of 255 simultaneous executions. A limit
of one also does not establish workload size or callback count. Job-kind-specific
eligibility still matters.

## Establishing the category

The owner constructor first initializes two repeated members using category one.
Its loop counter starts at two and reaches zero at loop exit. Later category
arguments computed as that counter plus one are therefore one, not three.
Other job constructions use an explicitly zeroed argument register plus one.
Tracing the loop exit is necessary to recover these constants correctly.

The setup method associates member receivers with debug labels and connects them
in the provider graph. See [provider chains](ENGINE_PROVIDER_CHAINS.md) for the
execution edges. Names establish stage identities; they do not identify a live
player or prove which receiver population is active.

## A nearby helper does not assign category

Several setup calls pass zero to a short helper. Its decoded behavior is:

```text
set_auxiliary_mode(job, mode):
    job.auxiliary_mode = uint32(mode)
    if uint32(mode - 1) <= 1:
        job.excluded_mask = 0
```

The mode field is separate from category. Zero leaves the excluded mask unchanged;
one and two clear it. The [worker-context follow-up](WORKER_THREAD_CONTEXT.md) now joins this field to temporary TLS execution-mode save/restore. The mode values themselves remain semantically unnamed. Do not translate
these zero-valued calls into category-zero assignments or unconditional mask
resets. The function name above is descriptive pseudocode, not an original name.

## Evidence and remaining work

This pass inspected decoded constructor calls, member-relative stores, loop
control, setup label assignments and the complete short mode helper in the image
with SHA-256 `32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`.
No original game execution or live configuration was observed.

The remaining targets are later category/mask writers, concrete virtual eligibility
for these receiver types, and equivalent assignments in the player motion/input
chain. These AI values should not become universal scheduler defaults or be
silently assigned to the independent gameplay graph.
