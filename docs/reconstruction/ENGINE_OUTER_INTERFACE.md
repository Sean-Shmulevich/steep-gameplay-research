# Outer engine interface: candidate implementation and missing binding

A concrete static interface object has a method table that fits the outer caller's slots, including a method that checks the already identified global stop-request flag and invokes the engine stop-request routine. The unresolved edge is whether this object is actually passed to the outer routine. This pass does **not** close that receiver binding.

See [Engine event consumer](ENGINE_EVENT_CONSUMER.md) for the confirmed outer sequence: caller-supplied interface, start/reset/root submission, another interface callback, exact engine-event consumption, then cleanup.

## Concrete table and stored object

The inspected image contains a pointer-sized static object whose first word points to a four-entry method table. Its entries resolve to:

| Slot used by the outer interface | Candidate implementation |
|---|---|
| Initial method | A tail jump to the verified no-op routine |
| Callback between engine start and event consumption | Service calls, global-request test, conditional engine stop request |
| Method immediately before engine start | The verified no-op routine |
| Further method | Service cleanup calls, ending in a virtual service call |

The table pointer and function targets are directly present in the image. This proves an available concrete implementation and its stored object; it does not prove runtime selection. A separate constructor was not needed to observe the static table-pointer initialization, but the object's initialization/lifetime policy has not been reconstructed.

## Candidate callback's exact request relationship

The candidate callback does not read fields from its interface receiver. It invokes a method on a global service, calls a no-op helper, performs another service routine, and then reads the global request flag. The flag getter is a short leaf that returns the byte verbatim.

That flag is exactly the global byte set by the stop-request writer described in the event-consumer audit. The final conditional call is the same writer, which also sets alternate mode on the non-null global engine owner.

```text
candidate_outer_callback(interface):
    global_service.callback()
    no_op()
    service_update()
    if global_request_flag != 0:
        request_engine_stop_candidate()
```

This closes the candidate callback-to-request relationship without assigning the service callback an invented message-loop role. The service callback and service update may themselves perform substantial work; their completion or blocking behavior is not established here. In particular, the callback shown above contains no explicit loop of its own.

Because the request writer sets the same flag that this callback reads, the flag is not a fresh event-consumption result. The shown path can repeat a previously issued request. Its reset policy remains outside this finding.

## Missing outer receiver edge

The outer routine preserves its second argument as the interface receiver. The candidate static object would fit its method accesses, but no verified caller instruction has yet been found that passes that object into the outer routine.

The searches checked direct calls, direct tail jumps and full-width absolute references to the outer entry; bounded relative-address scans covered ordinary code and the inspected protected-code region. A separate search located the concrete table pointer in static storage, but ordinary-code relative references to that static object were not found. Negative searches do not exclude transformed calls, aliases, partial-address construction or another entry point.

Accordingly, the supported relationship is:

```text
confirmed outer_run:
    interface = caller_supplied_argument
    interface.before_run()
    start_engine_cycle()
    interface.callback()
    consume_engine_event()

confirmed candidate object:
    before_run = no_op
    callback = candidate_outer_callback

unresolved:
    caller_supplied_argument == candidate_object
```

The remaining useful target is the outer routine's caller or a verified construction of its interface argument. Resolving more event imports would not establish that missing receiver identity. A reconstruction may supply this candidate interface explicitly as a fixture, but must label that selection as supplied rather than recovered.

## Evidence boundary

The static object/table, function targets, candidate callback, request-flag getter and stop-request writer were inspected in the analyzed image with SHA-256 `32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`. Table compatibility is a lead; the callback's global flag and direct stop-request call are recovered local behavior. No game execution, attachment or emulation was performed, and no executable payload is included.
