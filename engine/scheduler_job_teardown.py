"""Bounded reconstruction of the graphics job's normal teardown ordering.

Evidence: docs/reconstruction/SCHEDULER_DELEGATES.md, "Job teardown contract".
Inputs are supplied read results, not atomic native snapshots. No native objects
are freed, no callbacks are invoked, and no lifecycle lock is acquired here.
"""


def teardown_trace(wait_enabled: bool, poll_reads, *, delete_storage=False):
    """Inspect teardown using finite (state_u32, count_u32) read pairs.

    A missing releasing observation yields an incomplete trace, never a guessed
    successful drain. `poll_reads` supplies state then count in native read order.
    The iterator is consumed only when the wait flag is enabled.
    """
    events = ["clear_main_invoker", "install_base_table"]
    polls = []
    if wait_enabled:
        for state, count in poll_reads:
            for value in (state, count):
                if type(value) is not int or not 0 <= value <= 0xffffffff:
                    raise ValueError("poll fields must be unsigned 32-bit integers")
            signed_count = count if count < 0x80000000 else count - 0x100000000
            busy = state != 0 or signed_count > 0
            polls.append({"state": state, "count_signed": signed_count, "wait": busy})
            if not busy:
                break
        else:
            return {"completed": False, "events": events, "polls": polls,
                    "boundary": "wait has no supplied releasing observation"}
    events.extend(["clear_completion_invoker", "clear_after_invoker",
                   "clear_before_invoker", "request_list_teardown",
                   "request_lock_teardown"])
    if delete_storage:
        events.append("request_storage_free")
    return {"completed": True, "events": events, "polls": polls,
            "boundary": "local normal path only; not plugin unload permission"}
