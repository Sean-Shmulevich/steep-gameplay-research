"""ID-84 callback orchestration, with unresolved engine services explicit.

Evidence: CENTRAL_IMPULSE.md, ID-84 callback edge independence. The notification
ID and value are ignored by this local callback. No live ownership is acquired.
"""


def notification_84(controller, markup_id, value_byte, sentinel, *, available,
                    entity, actor_type, lookup, dispatch, vector_service, accumulate):
    """Run the observed normal-return service order; return an authored diagnostic.

    Services represent native operations, not replacements inferred from names.
    vector_service mutates a four-lane temporary initialized to positive zero.
    dispatch's return value is ignored. Exceptions propagate; no rollback exists.
    """
    if not available(controller) & 0xff:
        return 'interface_unavailable'
    owner = entity(controller)
    token = actor_type()
    actor = lookup(owner, token)
    if actor is None or actor == 0:
        return 'actor_absent'
    dispatch(actor)
    vector = [0.0, 0.0, 0.0, 0.0]
    vector_service(actor, vector)
    accumulate(actor, vector)
    return 'services_completed'
