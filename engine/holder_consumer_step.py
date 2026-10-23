"""One serial deferred-holder iteration with supplied callbacks.

Evidence: ANIMATION_CONTEXT_RETIREMENT.md, Callback-sensitive holder consumption.
Caller supplies outer synchronization and valid ring storage. No drain guarantee.
"""


def consume_holder_step(registry, *, payload_virtual48, dispatch_payload,
                        append_output, cleanup_holder):
    """Pop one item, retaining the payload captured before callbacks.

    Callbacks may change mode, holder status/payload and enqueue more work.
    The initial low24 gate is not repeated after callbacks. Mode is read after
    virtual48; queued-bit clearing uses current status. Cleanup rechecks belong
    to its supplied implementation. Return diagnostics are authored API.
    """
    ring=registry['ring']
    if ring['count'] <= 0:
        return dict(consumed=False, payload_action=None, cleanup_called=False)
    slot=ring['head']
    ring['head']=(slot+1)%ring['capacity']
    ring['count']-=1
    holder=ring['slots'][slot]
    eligible=holder['status'] & 0xffffff == 0
    payload=holder['payload']
    action=None
    if eligible:
        if payload is not None:
            payload_virtual48(payload)
            if registry['mode']==0:
                dispatch_payload(payload); action='dispatch'
            else:
                append_output(payload); action='append'
        holder['status'] &= ~(1<<24)
        cleanup_holder(registry,holder)
    else:
        holder['status'] &= ~(1<<24)
    return dict(consumed=True,payload_action=action,cleanup_called=eligible)
