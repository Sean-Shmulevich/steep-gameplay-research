"""Recovered serial command-record construction by copying retained references.

Evidence: REQUEST_COMMAND_LIFECYCLE.md, Command record attachment ownership.
The native associated acquisition uses reload/CAS retry; this serial model requires
stable source fields and retained objects. It is not a concurrent lifetime pin.
"""


def copy_record(destination, source):
    """Copy known fields, increment holders and acquire the associated reference.

    Records use kind, holder_08, holder_10, payload_18_30, invoker,
    payload_38_60 and associated. Payload blocks are immutable bytes. Padding
    represented by any other destination fields remains untouched. This is a
    construction helper: overwritten destination references are NOT released.
    Source/destination identity alias follows original store order, including
    clearing associated before reading it. uint32 increments wrap, even at zero
    and maximum counts; those cases do not establish valid native ownership.
    """
    destination['kind'] = source['kind']
    for key in ('holder_08', 'holder_10'):
        holder = source[key]
        destination[key] = holder
        holder['status'] = (holder['status'] + 1) & 0xffffffff
    destination['payload_18_30'] = source['payload_18_30']
    destination['invoker'] = source['invoker']
    destination['payload_38_60'] = source['payload_38_60']
    destination['associated'] = None
    associated = source['associated']
    if associated is not None:
        associated['count'] = (associated['count'] + 1) & 0xffffffff
    destination['associated'] = associated
    return destination
