"""Serial model of record cleanup, not a native lifetime or unload guarantee.

Evidence: REQUEST_COMMAND_LIFECYCLE.md, Record final-reference cleanup.
Dictionary objects represent supplied live references; their identities may alias.
Native exchange/decrements are atomic, while this detached Python model is serial.
"""


def cleanup_record(record, *, destroy_associated, release_holder):
    """Detach associated reference, release it, clear invoker, release holders.

    record uses associated, invoker, holder_10 and holder_08 keys. Associated
    objects have uint32 count; holders have uint32 status. Native holder pointer
    fields remain unchanged. Services may update holder state and must return normally; exceptions expose partial progress without rollback.
    """
    associated = record['associated']
    record['associated'] = None
    if associated is not None:
        old = associated['count']
        associated['count'] = (old - 1) & 0xffffffff
        if old == 1:
            destroy_associated(associated)
    record['invoker'] = None
    for key in ('holder_10', 'holder_08'):
        holder = record[key]
        holder['status'] = (holder['status'] - 1) & 0xffffffff
        if holder['status'] & 0xffffff == 0:
            release_holder(holder)
