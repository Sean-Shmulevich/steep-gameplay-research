# Animation source registry and removal ordering

The animation-time source at world+`0x530` is event-registry slot 16. The established world registry starts at world+`0x110`, has 53 entries, and places each pointer-vector header at registry+`0x20 + 0x40 * slot`:

```text
world_source_offset(slot) = 0x130 + 0x40 * slot
world_source_offset(16) = 0x530
```

This joins the [animation membership copy](ANIMATION_MEMBERSHIP_COPY.md) to the indexed registration mechanism previously inspected for motion and preloop jobs. It identifies the source container, not its current listeners. A concrete KinoComponent activation call or live membership observation is still needed to associate a particular component with this slot.

## Insertion and removal

The indexed insertion wrapper selects the entry and enables exact-pointer duplicate checking. The entry writer acquires its guard, calls a membership search that also acquires the same guard, and appends only if the pointer is absent. Existing listeners keep their order on this path. The nested acquisition is observed; native lock semantics are not reproduced by the serial API.

```text
register(entry, listener):
    if exact listener pointer is already present:
        return
    ensure_capacity_for_one_more()
    increment count
    storage[count - 1] = listener
```

Count publication precedes the pointer store inside the guarded region. This is not a lock-free publication recipe. The indexed wrapper has no bounds check; the portable API restricts selectors to the constructed 53-entry range.

Removal searches for the first exact pointer match. It fills the removed position with the last active entry, then reduces count. Removing the last entry only reduces count. Missing listeners leave the array unchanged.

```text
remove(entry, listener):
    index = first_exact_match(entry.active_pointers, listener)
    if no match:
        return false
    if index + 1 < count:
        copy one pointer from storage[count - 1] to storage[index]
    count -= 1
    return true
```

The inner search/erase helper returns that Boolean. The outer removal wrapper calls its closing helper afterward, so the portable API's Boolean is not asserted to be the outer wrapper's native return. No listener destructor, refcount adjustment or pointer clearing appears in the inspected inner removal path. This does not establish the listener's wider lifetime protocol.

Removal preserves capacity and leaves the old last pointer in the now-inactive tail slot. It does not shift the whole tail. For `[A, B, C, D]`, removing B produces active entries `[A, D, C]`. A subsequent single-range animation visit runs C, D, A. This explains one way batch order can change without sorting, randomization or object-type substitution.

A registry change does not rewrite an already-copied job array. Removing B after gathering `[A, B, C, D]` leaves that copied array unchanged. Whether B remains safe to invoke depends on the surrounding completion/lifetime protocol; registry removal itself does not cancel captured work.

## Runnable API

```python
from engine.event_registry import WorldEventRegistry, ANIMATION_TIME_SLOT
from engine.animation_membership import AnimationMembership
from engine.animation_batch import visit_animation_batch

registry = WorldEventRegistry()
for token in (10, 20, 30, 40):
    registry.register(ANIMATION_TIME_SLOT, token)
assert registry.register(ANIMATION_TIME_SLOT, 20) is False
assert registry.remove(ANIMATION_TIME_SLOT, 20) is True
assert registry.snapshot(ANIMATION_TIME_SLOT) == [10, 40, 30]

batch = AnimationMembership()
batch.copy_registry(registry.snapshot(ANIMATION_TIME_SLOT))
seen = []
visit_animation_batch({'callback': seen.append}, batch.claim(3))
assert seen == [30, 40, 10]
```

Tokens are caller-assigned uint64 identities. No native pointers are dereferenced. `snapshot` returns a list copy under the adapter's serial ownership assumption; it is not a native atomic snapshot. Python allocation replaces native capacity management. `register_listener` and `remove_listener` expose the corresponding active-list operations for externally owned token lists. The duplicate-checking insertion path does not remove duplicates already present through other means; removal deletes the first match and may leave another.

## Validation and boundaries

The original indexed insertion/removal wrappers, searches and last-entry erase helper matched the portable active-list behavior in 2,016 isolated cases. Cases cover slots 0, 16 and 52; lengths zero through twenty; unique and duplicate initial arrays; present, absent and null tokens; and full/spare capacity. Lock/unlock, growth and eight-byte copy helpers were stubbed. Checks include removed-list order, inactive last-slot preservation, capacity retention and nested helper-call counts. See the [receipt](event_registry_validation.json).

Four repository tests cover slot isolation and duplicate suppression, removal changing the next animation batch while leaving a prior copy intact, first-match/missing/last-entry removal, and explicit adapter bounds. The registry-layout evidence was rechecked against the analyzed image.

Evidence anchors: world constructor `1408ae9a0`, registry constructor `140851060`, indexed insertion `14085b9b0`, entry writer `14085b590`, duplicate search `140862c40`, indexed removal `140893bf0`, search/erase `1411e6ec0`, last-entry replacement helper `14115b870`. The latter passes an eight-byte copy from the last active entry to the matched index, then decrements count. These are not the ordered-shift helpers used for other scheduler arrays.

The missing join remains component-specific registration: which lifecycle/type-descriptor path inserts KinoComponent into slot 16, what unregisters it, and which such component belongs to the live player. Literal slot-16 calls found in other component routines do not establish that identity. Input freshness, native locking and safe step control remain separate questions.
