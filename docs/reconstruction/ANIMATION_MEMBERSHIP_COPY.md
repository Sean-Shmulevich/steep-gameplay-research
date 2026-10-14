# Animation membership copy

The configured `UpdatePreActionGather` task contains a copy block that fills the exact animation-time job described in [batch binding](ANIMATION_BATCH_BINDING.md). This closes the source-array-to-job-array join. It does not yet identify registry insertion/removal rules or prove that a live player belongs to the array.

## Recovered behavior

```text
copy_animation_membership(scheduler_owner):
    registry_owner = scheduler_owner.source_owner
    enter_helper(registry_owner.animation_registry_guard)
    n = registry_owner.animation_registry_count
    if n != 0:
        if n > animation_job.capacity:
            replacement = allocate(n * pointer_size)
            animation_job.count = 0
            release_old_storage_if_present()
            animation_job.storage = replacement
            animation_job.capacity = n
        else:
            animation_job.count = 0
        if n > 0:
            copy n pointers from registry array to job storage
            animation_job.count += n
    leave_helper(registry_owner.animation_registry_guard)
```

This pseudocode assumes valid nonnegative counts and successful allocation. The original uses signed count comparisons. Invalid counts, allocation failure and overflowing allocation sizes are outside the portable API's supported domain.

The pointer copy preserves source order and receiver identity. It copies references, not component state. Later edits to a source array slot do not replace the corresponding copied job slot; changes to the referenced component can still be observed when it runs. The selected batch visitor reads job entries at invocation time and visits a claimed span in reverse. Multiple spans do not imply a global reverse order.

An empty source skips both copying and destination count reset. Existing destination storage, capacity and active count survive this block. The [claim-lifecycle follow-up](ANIMATION_CLAIM_LIFECYCLE.md) now proves an ordinary path to zero: the selected worker reduces this same count as it claims ranges. Fully claimed work can therefore leave zero for an empty gather, even while callbacks are still running. Cross-request exclusion and partial-claim handling remain open.

Calls around the source read/copy pass the source owner's adjacent guard object. The copy and allocation paths lie between those calls. Their synchronization implementation and interactions with registry writers have not been validated here. The portable API requires the caller to supply a stable source sequence.

## Runnable API

```python
from engine.animation_membership import AnimationMembership
from engine.animation_batch import visit_animation_batch

membership = AnimationMembership()
membership.copy_registry(['first', 'second'])
seen = []
visit_animation_batch({'callback': seen.append}, membership.storage, membership.count)
assert seen == ['second', 'first']

membership.copy_registry([])
assert membership.count == 2  # this block alone does not reset an empty source
```

`storage` length represents allocated capacity; `count` identifies its active prefix. A smaller nonempty source reuses storage and leaves its inactive tail intact. Growth replaces storage with exactly the required capacity. The method returns a diagnostic Boolean indicating growth. Python references replace native pointers and allocation. No worker runs automatically, and no locking or receiver-lifetime guarantee is added.

## Evidence and validation

The original copy block matched the portable model in 180 isolated cases. Counts zero through eight and capacities zero through nine were combined with previous active counts of zero and full capacity. Checks covered destination count, capacity, storage replacement, all stored entries including inactive tails, and helper-call order. Allocation, release, byte copy and surrounding helper calls were stubbed; the original branch and field-update instructions ran. See the [receipt](animation_membership_validation.json).

Four repository tests cover empty-source preservation, retained capacity/tail and object identity, copy-to-visitor composition, and invalid destination counts. These tests do not establish native job ordering, registry ownership or live player membership.

Static anchors:

- Setup `140905dd0` loads copy routine `140914660` at `1409066c5` and stores its callable record at scheduler owner+`0x370`, with owner context at `+0x380`. The configured task is owner+`0x1d8`, labeled `UpdatePreActionGather` and `Ai::UpdatePreActionGather`.
- The first block of `140914660`, through `14091476d`, loads registry owner from `[scheduler_owner]`. Source array is registry owner+`0x530`, signed count `+0x538`, and the adjacent helper object `+0x540`.
- Destination storage/count/capacity are scheduler owner+`0x3c88`/`0x3c90`/`0x3c94`. These equal animation-time job+`0x198`/`0x1a0`/`0x1a4` for the job at owner+`0x3af0`.
- Nonempty-source copying calls `141c6afb0` at `140914755`; empty source branches directly to the closing helper call. The larger gather routine continues with other lists outside this validation scope.

The [stage-dependency follow-up](ANIMATION_STAGE_DEPENDENCIES.md) now connects this gather to the animation job and its ordinary downstream completion/rearm route. Next evidence needed: source registration/removal, live receiver identity, and exceptional-mode storage exclusion. Source-array copying, ordinary consumption to zero, and the ordinary static completion route are established; live membership and safe process control remain open.
