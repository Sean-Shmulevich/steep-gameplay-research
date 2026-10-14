# Engine mode writers and per-stage copies

The owner mode byte used by the two Step-routing branches is copied from the global mode byte at named engine stages. It is not an unrelated setting. A further in-graph writer clears that copied mode only on a route already selected by a zero value. These findings strengthen the ordinary stable-mode interpretation while leaving external writer timing open.

This extends [the root-to-Step route audit](ENGINE_ROOT_STEP_ROUTE.md). All field names below are explanatory aliases. No game was launched or attached to.

## The owner predicate reads a stage copy

Two recovered callbacks copy the same pair of bytes from the global engine owner into their receiver:

```text
copy_mode_pair(receiver):
    receiver.owner_mode = global_engine.mode
    receiver.owner_companion = global_engine.companion
```

The two byte loads and stores are separate operations. This is not an atomic two-byte snapshot.

One callback is bound to `BeginEngineFrame`, with label `Engine::BeginEngineFrame`. It calls another engine helper before copying the pair. The other callback consists of the pair copy itself and is bound to `PreActionStep`, with label `Engine::PreActionStep`.

Setup places PreActionStep after the registered single-threaded and multithreaded universe-component stages, and before the fork leading to the two owner-mode branches:

```text
BeginEngineFrame
    -> global-mode branch
    -> universe-stage chain
    -> PreActionStep: refresh owner_mode and owner_companion
    -> fork
    -> owner-mode branch A
    -> owner-mode branch B through its separate predecessor
```

The last two lines describe forked dependency routes, not a sequential call order. Both owner predicates read the receiver's copied `owner_mode`. The global predicate reads `global_engine.mode` directly.

This distinction matters if the global mode changes during the universe stages. The later PreActionStep copy can observe a different value than the earlier global-mode branch did. That is a concrete refresh point within the request. A single global-mode sample cannot be assigned to every branch in that request.

## The clear writer is guarded by a zero selection

A third callback stores a zero word over the receiver's owner-mode pair:

```text
pre_action_world_step(receiver):
    receiver.owner_mode = 0
    receiver.owner_companion = 0
```

It is bound to `PreActionWorldStep` and lies on owner branch A's false route. Consequently, in the ordinary topology with no intervening external writer, it writes zero after that branch already observed zero.

This does not by itself create a false/true disagreement between the two owner predicates. If the pair copy produced nonzero owner mode, branch A takes the bypass and does not execute this clear callback through its ordinary false route. If the copy produced zero, the clear preserves the owner predicate value even if the other branch reads it before or after the clear.

```text
# Restricted to the reviewed in-graph writes after PreActionStep:
copied = global_engine.mode
owner_mode = copied

if branch_A_reads(owner_mode) == 0:
    clear_pair_on_false_route()  # owner_mode remains zero

branch_B_reads(owner_mode)
```

The companion byte can change from nonzero to zero in that clear. It is not used by the two reviewed owner-mode predicates, so that change must not be confused with a routing disagreement in these particular branches.

## Global mode has explicit set and clear transitions

A compact global setter checks whether the mode is zero. Only in that case does it store the caller's byte into a neighboring field, set mode to one, clear another neighboring byte, set the companion byte to one, and invoke a notification helper.

```text
request_mode(caller_byte):
    if global_engine.mode == 0:
        global_engine.request_argument = caller_byte
        global_engine.mode = 1
        global_engine.neighbor_flag = 0
        global_engine.companion = 1
        notify_mode_transition()
```

Two other inspected routines contain the same set sequence with a constant request argument of one, inside larger engine/world-processing flows. The global mode therefore has real writers beyond construction; it cannot be treated as an immutable configuration constant.

A corresponding larger transition routine acts when mode is exactly one. Depending on its input it runs preparatory helpers, then clears mode, performs world-list/service work, and finally clears the companion byte.

```text
clear_mode(input_flag):
    clear_separate_global_flag()
    if global_engine.mode != 1:
        return
    if not input_flag:
        run_transition_preparation()
    global_engine.mode = 0
    process_world_and_service_transitions()
    global_engine.companion = 0
```

The helper names in this pseudocode deliberately retain unknown semantics. Setup labels the first conditional job `CheckEngineStop`, which supports describing the field as an engine stop-routing gate. It does not establish that it is the user pause menu, application shutdown, a loading state, or one specific user action. The companion and argument fields remain operation-level facts rather than guessed enum meanings.

Construction initializes the four-byte group containing the global mode, companion and adjacent flags. The decoded initial mode and companion bytes are both zero. Construction alone does not explain later transition timing.

## Stability and reconvergence implications

The strongest supported conclusions are local:

- BeginEngineFrame and PreActionStep refresh the owner pair at concrete dependency stages.
- A changed global mode between the early global branch and PreActionStep can affect later owner routing.
- After the reviewed PreActionStep copy, the identified in-graph clear does not change the owner predicate's value on its own ordinary reachable route.
- The two owner branches still evaluate separately. Their equality requires the absence of another relevant write between those evaluations.

The compact global setter uses ordinary byte stores and contains no lock or scheduler wait. That does not prove concurrent mutation is permitted: its callers may serialize it. Conversely, the callback's stage position does not prove all global writers are serialized with it. This bounded pass did not recover an exhaustive writer inventory or every setter caller.

A complete reconvergence claim must combine this writer behavior with the [alternate dependency-release rules](ALTERNATE_DEPENDENCY_RELEASE.md). A branch selected before a mode transition cannot be retrospectively changed by applying the new mode to the entire graph. A recorder should preserve the early global read, the PreActionStep copied value and both owner-predicate evaluations separately until the caller synchronization is proved.

## Verification scope

The pair-copy callbacks, zero-word writer, their callable bindings and labels, and the setup edges around PreActionStep were decoded directly from the analyzed image. The global setter, clear transition and additional set sites were located through references to the global owner and inspected at instruction boundaries. Leaf functions were inspected even when absent from unwind metadata.

The analyzed image SHA-256 is `32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`. The search was bounded to the established owner references and relevant engine callbacks. Indirect aliases, packed writes elsewhere, and externally serialized caller rules remain outside its completeness claim. No executable bytes or machine-local paths are included here.

## Recovered stop-mode callers

A later pass located concrete callers of the compact setter and the clear routine. Field aliases are unchanged; offsets remain private.

**Confirmed window close.** The game's window procedure handles `WM_CLOSE`. Ordinarily it routes to a quit-confirmation path and returns zero. When `wParam` equals the internal constant `0xC0FFEE`, it instead sets a global shutdown flag, performs a service call, calls the compact setter with request argument 1, and continues into shutdown. Application exit therefore enters the stop-routing mode before teardown.

```text
window_procedure(WM_CLOSE, wParam):
    if close_already_pending or wParam != 0xC0FFEE:
        show_quit_confirmation(); return 0
    set_shutdown_flag()
    service_call()
    request_mode(1)          # compact setter
    continue_shutdown()
```

**Keyboard command dispatcher.** A dispatcher that consumes a queue of virtual-key codes contains two cases for code `0x08` (Backspace), one per state of a second gate byte. Each toggles stop mode: if the engine reports stopped, it clears the mode, otherwise it calls the setter (argument 0 or 1). These cases sit on the path taken when the dispatcher's first gate byte is zero. [A live test](live_engine_mode_backspace_validation.json) sent Backspace twice during gameplay: the mode bytes did not change and consecutive frames differed. The dispatcher's input source in the retail build is unresolved, so this is a recovered but not demonstrated trigger.

**World-processing flow.** A routine with two direct callers inside the larger engine/world flow either calls the mode transition routine or, when stop mode is set and a separate global byte allows it, calls the clear routine. It precedes further world-service work. Its user-facing meaning is not assigned.

These callers, plus the [menu observation](ENGINE_FRAME_GRAPH_COVERAGE.md#live-check-the-in-game-menu-is-not-the-stop-mode), support describing stop mode as an engine-level world-suspension state used around shutdown and engine-driven transitions, not the in-game menu.
