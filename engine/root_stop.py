"""Recovered root-stop request prefix with opaque service adapters.

Evidence: REQUEST_COMMAND_LIFECYCLE.md, Root stop request and persistent flag.
No original-game API invocation, lifetime pin or successful-stop receipt implied.
"""


def request_root_stop(*, configure_service, followup_service, get_optional_receiver,
                      invoke_receiver, read_owner, set_global_requested):
    """Preserve service order, repeated receiver lookup and late owner read.

    configure_service receives the observed numeric arguments 0x40, 0xf, True;
    their subsystem meanings remain unresolved. The first receiver lookup is a
    null test only; a second lookup supplies the actual virtual-call receiver.
    Services must provide valid objects when the native path would dereference
    them. There is no synthesized fallback for an invalid second result.
    """
    configure_service(0x40, 0xf, True)
    followup_service()
    if get_optional_receiver() is not None:
        invoke_receiver(get_optional_receiver())
    owner = read_owner()
    set_global_requested(1)
    if owner is not None:
        owner['byte_46'] = 1
