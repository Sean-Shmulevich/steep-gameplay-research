"""Local thread lifecycle transitions, not a native stop/join API.

Evidence: WORKER_THREAD_CONTEXT.md, Base thread entry and destruction race.
CAS and the destructor's later state load are separate operations. Callers own
serialization; state codes retain their inspected numeric values.
"""
from .queue_policy import _i32


def entry_cas(state):
    _i32(state)
    return dict(state=2 if state == 1 else state, enter_body=state == 1)


def destructor_cas(state):
    _i32(state)
    return dict(state=3 if state == 1 else state)


def destructor_wait_required(observed_state):
    _i32(observed_state)
    return observed_state != 0


def destructor_after_wait(state, adapter_result):
    """Zero result triggers exchange-to-zero; other results leave state alone.

    Protected adapter cleanup and OS status identity remain unresolved. This
    function describes the caller branch, not successful thread termination.
    """
    _i32(state)
    _i32(adapter_result)
    return dict(state=0 if adapter_result == 0 else state,
                exchange_to_zero=adapter_result == 0)
