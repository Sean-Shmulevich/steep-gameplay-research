"""Recovered local callback body for one submitted request's context cleanup.

Evidence: ANIMATION_CONTEXT_RETIREMENT.md, request callback binding and cleanup.
Receiver/holder objects and services are supplied; no native ownership or callback
invocation cadence is established by this serial implementation.
"""


def complete_request_context(context, target, holders, *, services):
    """Run normal-return operations for the selected completion callback.

    context: value:uint32, weak_holder, strong_holder, parameter, flags (3 bytes).
    target is the caller-resolved object reached through the callback's third arg.
    holders map identities to status:uint32 and weak:uint32. Release services may
    mutate state, so holder identities are reloaded at their native boundaries.
    Services are bound adapters for omitted manager/resource-wrapper receivers.
    apply_holder receives context so it can access or replace weak_holder.
    Callback input validity/lifetime is the caller's responsibility.
    """
    def word(value):
        if type(value) is not int or not 0 <= value <= 0xffffffff:
            raise ValueError('uint32 field required')
        return value

    services['activate'](1)
    target['value'] = word(context['value'])
    services['refresh'](target)
    # Bound adapter receives the holder field by reference through context.
    services['apply_holder'](target, context)
    if context['flags'][0]:
        services['optional0'](context['parameter'])
    if context['flags'][1]:
        services['optional1']()
    if context['flags'][2]:
        services['optional2'](target)
    allocation = services['allocation_token'](context)
    strong = context['strong_holder']
    holders[strong]['status'] = (word(holders[strong]['status']) - 1) & 0xffffffff
    if holders[strong]['status'] & 0xffffff == 0:
        services['release_strong'](strong)
    weak = context['weak_holder']
    old = word(holders[weak]['weak'])
    holders[weak]['weak'] = (old - 1) & 0xffffffff
    if old == 1 and word(holders[weak]['status']) & 0xffffff == 0:
        services['release_weak'](weak)
    services['free_context'](context, allocation)
    return dict(native_lifecycle_proved=False)
