# Shared action storage for motion ingestion and snow sampling

This pass is offline static analysis of the existing analyzed image. No process was launched, attached to, written to, or sent input. This is original-game evidence, not Studio substitute behavior. Scratch instruction exports stay outside the public repository.

## New closure

The previously unresolved constructor-bound vector callback is only 34 bytes. It reads the constructing input manager's current context selector, calls the same action lookup used by ordinary motion ingestion, then copies the same four-lane field. Consequently, under matching manager identity, selector, action ID, lookup result and unchanged binding, the snow sampler and motion ingestion read the **same action storage location**. They do not necessarily read the same version of its contents.

The callback does not perform vector shaping, coordinate conversion, normalization, or timestamp checking. Those operations must occur upstream or downstream, if present. The meaning of the fourth lane is not established by a 16-byte copy.

Portable descriptive pseudocode (names are ours):

```text
sampleSnowActionVector(capturedManager, actionId):
    selector = capturedManager.currentContextSelector
    payload = lookupActionPayload(capturedManager, selector, actionId)
    return copyFourLanes(payload.vector)

sampleMotionActionVector(manager, actionId):
    selector = manager.currentContextSelector
    payload = lookupActionPayload(manager, selector, actionId)
    return readFourLanes(payload.vector)
```

The existing helper returns a pointer to an action payload, or a shared fallback payload. The new callback copies from the vector member after the helper returns. The analyzed image's fallback vector contains four zero float bit patterns. This establishes the image default, not an immutable runtime guarantee or an exclusive writer set.

## Lookup precedence and concurrency boundary

The existing action resolver gives a concrete selection model that a reconstruction can express without binary addresses:

```text
lookupActionPayload(manager, selector, actionId):
    enterManagerReadAccounting(manager)
    if unsigned(selector) < manager.contextCount:
        action = resolveAction(manager.contexts[selector], actionId)
    else:
        action = null
    result = action.payload if action != null else fallbackPayload
    leaveManagerReadAccounting(manager)
    return result

resolveAction(context, actionId):
    for group in context.threeGroupsInStoredOrder:
        for binding in reverse(group.bindings):
            valueSlot = mapLookup(binding.actionMap, zeroExtend32(actionId))
            if valueSlot != null and *valueSlot != null:
                return *valueSlot
            if binding.blocker != null and binding.blocker.enabled:
                return null
    return null
```

The ordering, reverse traversal and blocker early exit follow inspected instructions. Group names and blocker semantics beyond this stopping behavior are unresolved. The internal map representation is tagged and multi-case; this pass does not claim a complete portable decoder for it.

The read accounting uses atomic increments/decrements and contention bits, but its decrement occurs **before** the newly traced vector load. Therefore this helper cannot by itself prove that vector copying is atomic with input publication, or that the vector is pinned for the entire read. Other lifetime/synchronization guarantees could exist elsewhere; this is not evidence of a game defect. The manager selector is also loaded before entering that helper.

No source sequence, timestamp, frame number, or physics substep number is read by the new callback. A stable pointer and unchanged selector establish a narrower identity claim than freshness.

## Most useful next static and runtime probes

1. Resolve the selected action object's construction and the writers of its four-lane vector. Begin with the actual map value type/creation path; a global scan for stores at a common displacement would produce ambiguous owners. Trace both whole-payload copies and direct vector stores.
2. Determine whether the input manager has a distinct commit/publish operation surrounding those writers. Follow a concrete writer to any sample counter, timestamp or double-buffer swap; do not label unrelated atomic reader accounting a sample generation.
3. Before a live probe, implement a bounded read-only parser for the **observed** tagged-map variant, with pointer/count bounds and unsupported-tag failure. Revalidate receiver ownership and selector before/after lookup. Do not call the original game's lookup routine from the inspector as a shortcut.
4. Record manager global identity, callback-captured manager identity, binding identity, selector, selected action pointer and vector along with existing carrier/motion samples. Reject cross-owner comparisons and separately label fallback results. Address stability alone does not pin lifetime.
5. Once a writer-side generation is proved, capture that generation at motion consumption, snow consumption and publication. Until then, report transition windows and repeated values, not exact input age or same-substep consumption.

## What reconstruction and mods gain

For our simulator, a common `ActionStore` interface now has stronger evidence than two invented unrelated input sources. Preserve distinct motion and snow read moments, context precedence, fallback behavior and the state-vector override. An explicit immutable input snapshot and input generation would be a useful **new design**, not a recovered native feature.

For the original executable, the tiny vector callback is a candidate observation boundary: its input action ID and returned vector could help tag actual snow consumption. An observation hook would still require version checks, calling-convention preservation, reentrancy controls and a bounded recorder. A full engine reconstruction does not install that hook, make a native mod API appear, or prove it safe. This pass installed no hook.

Full reconstruction would make our replacement engine easier to pause, step, inspect and modify because we own its state and update boundaries. It would not automatically close native sample freshness or reproduce original scheduler behavior. The highest-value immediate work is the action-vector writer/publication boundary, rather than recreating unrelated engine systems first.
