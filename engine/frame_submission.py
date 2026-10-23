"""Recovered outer root-job submission sequence, with supplied services.

Evidence: REQUEST_COMMAND_LIFECYCLE.md, Root submission entry sequence.
Names are descriptive reconstruction choices. This does not select an engine
phase, pin the owner, implement graph setup, or establish event wait semantics.
"""


def submit_root_sequence(*, prepare_service, read_owner, reset_event,
                         prepare_graph, submit_job):
    """Preserve owner reload, flag/event order and conditional graph setup.

    prepare_service() represents global A's virtual +0x10 call. read_owner()
    reads global B afterward. owner provides byte_0, byte_46, byte_58, event,
    root_job. The byte_58 test happens after reset_event returns; its API return
    is ignored. prepare_graph receives the owner; submit_job receives root_job.
    These callbacks are supplied implementations, not recovered service bodies.
    No rollback or native exception behavior is modeled.
    """
    prepare_service()
    owner = read_owner()
    owner['byte_0'] = 1
    owner['byte_46'] = 0
    reset_event(owner['event'])
    if owner['byte_58'] == 0:
        prepare_graph(owner)
    return submit_job(owner['root_job'])
