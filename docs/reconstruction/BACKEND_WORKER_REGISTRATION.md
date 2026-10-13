# Backend consumer callback registration and entry context

This pass connects the previously inspected queued consumer to a callback supplied by backend worker setup. It closes the missing local callback-address chain. The protected platform launch and notification helpers remain opaque, and no original worker was started or observed.

## Why the first direct-call search missed it

The consumer has no aligned direct call from a normal exception-table function in the bounded search. A 41-byte wrapper immediately before it has no exception-table entry and tail-jumps into the consumer. That wrapper waits for a shared manager pointer, loads it, and forwards its incoming integer argument as the consumer's worker index.

```text
worker_wrapper(argument):
    while shared_manager_pointer == null:
        continue
    queued_consumer(shared_manager_pointer, low32(argument))
```

This establishes the values forwarded at that boundary. The shared pointer load does not retain the manager or establish safe destruction. No memory-order or shutdown protocol follows from the spin alone.

The backend setup routine supplies this wrapper address as a callback argument to its launch-preparation helper. The helper stores the callback and its argument into a temporary descriptor and passes a distinct entry bridge plus that descriptor to a protected helper.

```text
prepare_worker_launch(callback, argument, lifecycle_hooks_enabled, ...):
    descriptor.callback = callback
    descriptor.argument = argument
    descriptor.copied = false
    descriptor.lifecycle_hooks_enabled = lifecycle_hooks_enabled
    protected_launch_helper(entry_bridge, descriptor, ...)
    ... protected platform operations ...
    wait until descriptor.copied
    return launch_result
```

The platform helper is deliberately not renamed a particular operating-system API. Protected/opaque bytes occur around these calls, so only directly inspected stores and callback relationships are claimed. The complete meaning of the launch flags, returned handle and worker-argument preparation remains separate work.

## Entry bridge copies context before acknowledgement

The entry bridge loads callback, argument and the lifecycle flag into local storage before setting the descriptor's copied byte. It then runs registered lifecycle callbacks when enabled and calls the saved callback with the saved argument.

```text
entry_bridge(descriptor):
    callback = descriptor.callback
    argument = descriptor.argument
    hooks_enabled = descriptor.lifecycle_hooks_enabled
    descriptor.copied = true

    if hooks_enabled:
        for hook in registered_lifecycle_callbacks:
            hook(true)
    callback(argument)
    ... exit-side lifecycle branch ...
```

The callback slot and argument remain in local registers across this part of the routine. The producer-side wait therefore acknowledges descriptor copying, not completion of the worker callback. That byte must not be treated as a worker-completion generation.

The exit-side lifecycle branch is visible but is not needed to establish this entry chain. The callbacks' individual implementations and any thread-local initialization they perform are unresolved. The evidence supports preserving the callback context; it does not prove a particular TLS schema.

## Reconstructed chain and limits

```text
backend setup
    -> supplies manager-wait wrapper to launch preparation
    -> descriptor(callback, argument, lifecycle flag)
    -> protected launch with entry bridge
    -> entry bridge copies descriptor and runs optional lifecycle callbacks
    -> wrapper waits for shared manager
    -> queued consumer
    -> normal callback record
    -> decrement not-started, invoke callback, decrement outstanding
```

The last sequence was established in the [completion follow-up](BACKEND_COMPLETION_FOLLOWUP.md). Its earlier statement that concrete consumer registration was missing is narrowed by this new wrapper/descriptor chain. The protected platform launch, concrete live thread identity and safe manager lifetime remain unproved.

For an owned executor, immutable callback bindings and explicit entry context are useful interfaces. Directly invoking the original consumer from an arbitrary external thread would skip normal entry plumbing and still lack manager lifetime and submission exclusion. This report does not implement or authorize that experiment.

## Static verification

The callback-address instruction, wrapper tail jump, descriptor stores and entry-bridge loads were decoded directly from the same frozen image used by the surrounding scheduler research. The wrapper was read within its contiguous 41-byte leaf body. Other function hashes concatenate their exception-table fragments in address order. Protected helper bodies were not treated as decoded ordinary code.

| Role | Bytes | SHA-256 |
| --- | ---: | --- |
| Launch preparation | 149 | `0ef1f6f6d1d41da95edbf0b5619570d0ce8bbb70dec9e4f3d1ffa0f00d10475b` |
| Entry bridge | 157 | `45558a307ab523c9bf78ec85c813a91bc92f5243e362be41edda9c4c2dbe8f7a` |
| Backend worker setup | 343 | `8890890d6af99e45f7d76b449f2337844563fe79c452afd5a11543d133f801b2` |
| Shared-manager wait wrapper | 41 | `fe71955ef3a2cf59135de70767ec1cd9fbb2e8d7e7a26a6c095a9ac389635ac8` |

Image SHA-256: `32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`. No executable bytes, raw instructions or process state are included.
