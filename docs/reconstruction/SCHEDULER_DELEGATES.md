# Scheduler delegate dispatch contracts

The constructor-bound graphics delegate and a branch-job delegate share an
invocation adapter. Their enclosing dispatch contracts must remain distinct.

## Common invocation adapter

RVA `0x8ab390` receives function storage in RCX and receiver in RDX. It moves the
receiver to RCX and tail-jumps through the first qword of function storage.
The [invoker check](../../native/snow_host/graphics_delegate_invoker_validation.json)
verifies exact forwarding and preservation of the caller's return address.
It does not strip tags or determine a callback's return type.

The graphics binding is documented under
[graphics delegate invocation](ANIMATION_CONTEXT_RETIREMENT.md#graphics-delegate-invocation-adapter).
Its owner-relative delegate is not interchangeable with the existing probe's
image-backed virtual slot. Native installation remains unimplemented here.

## Branch dispatcher

Dispatcher RVA `0x11d14c0` has the following locally inspected behavior:

```text
branch_dispatch(job):
    lock(job + 8)
    receiver = job.delegate.context_word & ~3
    result = job.delegate.invoker(&job.delegate.function_storage, receiver)
    if low_byte(result) != 0:
        helper_A(job + 0x1b8)
        helper_B(job + 0x70)
    else:
        helper_A(job + 0x70)
        helper_B(job + 0x1b8)
    unlock(job + 8)
```

The delegate begins at job +0x198; context is +0x1a8 and invoker +0x1b0.
The two list services are `0x11d29e0` and `0x11e7ba0`, respectively. Their
semantics are deliberately not inferred from this caller alone. The dispatcher
appears as a stored function pointer at image RVA `0x28f53d0`; that reference
alone does not identify every receiver or establish the graphics-job route.

A [16-case connected instruction check](../../native/snow_host/branch_delegate_validation.json)
executes both this dispatcher and the common invoker. It tests all four context
tag combinations and predicate results 0, 1, 255 and 256. The last case follows
the false branch because only AL is tested. The check verifies decoded receiver,
lock/predicate/list-service/unlock order and the two selected list addresses.
The predicate, lock and list services are intercepted. Callbacks return normally;
no exception cleanup or concurrency guarantee is established.

## Remaining graphics binding gap

This branch dispatcher supplies concrete evidence of upstream tag stripping for
one scheduler job type. It cannot close the graphics route by analogy: it consumes
a predicate return byte, while the inspected graphics binding alone establishes
no such predicate contract. To install a graphics-phase observer, first identify
the concrete job table and its dispatch slot, follow that body into the delegate,
and qualify owner lifetime and slot ownership. Keep an observation wrapper's
calling convention tied to that confirmed route.


## Concrete graphics dispatcher now identified

The [live binding capture](../../native/snow_host/graphics_job_live_binding.json)
qualifies the graphics job at engine owner +0x218. Three startup samples agree:
table RVA `0x1e89618`, slot +0x40 target `0x65b1e0`, main delegate callback
`0x656c20`, invoker `0x8ab390`, and masked context equal to the engine owner.
Selector +0x5a was zero in those samples. This closes the concrete-table and
upstream-decoding gaps above for this observed binding. It does not sample the
callback's execution or establish selector stability across frame gates.

```text
graphics_job_dispatch(job):
    if (job.before.context & ~3) != 0 or job.before.function != null:
        job.before.invoker(&job.before.function, job.before.context & ~3)
    job.main.invoker(&job.main.function, job.main.context & ~3)
    if (job.after.context & ~3) != 0 or job.after.function != null:
        tail_call job.after.invoker(&job.after.function, job.after.context & ~3)
```

The before, main and after delegates begin at job +0xf0, +0x198 and +0x110.
Each record is 32 bytes. The main call is unconditional; its return is not used
for branch selection. Optional eligibility checks function/context, not whether
the invoker field is nonzero. A tag-only context with null function is skipped.
Do not assume a context-only record is safe with every invoker implementation.

A [32-case connected instruction check](../../native/snow_host/graphics_dispatch_validation.json)
executes this concrete dispatcher and the common invoker. It varies all context
tags, optional callback presence and callback return bytes. It verifies exact
before/main/after ordering, decoded receivers and normal return stack balance.
Synthetic callbacks supply no evidence about native mutation or exception safety.

The before/after records are candidates for bounded phase observation. No native
installation was attempted. An installer must preserve existing callbacks,
qualify the full descriptor and owner, prevent concurrent inconsistent updates,
and account for callers that already loaded an invoker. Image-vtable swapping
rules do not automatically establish those owner-relative delegate guarantees.
The read-only session stopped cleanly with saves/settings restored and original
DLL verified. No private heap addresses are included in the public receipt.
