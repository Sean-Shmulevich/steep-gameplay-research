"""Recovered work-object creation decisions, without a native allocator.

Evidence: CENTRAL_IMPULSE.md, Animation work storage initialization.
Backing pose bytes are deliberately unspecified until evaluator gathering.
"""

def plan_work_creation(work_present, skeleton_present, selected_count, allocation_succeeds=True):
    if any(type(x) is not bool for x in (work_present,skeleton_present,allocation_succeeds)):
        raise ValueError('boolean presence/allocation inputs required')
    if type(selected_count) is not int or not 0<=selected_count<=65535:
        raise ValueError('uint16 selected count required')
    if work_present or not skeleton_present or not selected_count:
        return dict(action='unchanged',allocation_requested=False)
    if not allocation_succeeds:
        return dict(action='null_write_path',allocation_requested=True,
                    bytes=1120,alignment=16,graceful_failure=False)
    return dict(action='created',allocation_requested=True,bytes=1120,alignment=16,
        inline_capacity=32,reserve_requested=selected_count>32,
        count=0,elapsed=0.,duration=0.,saved_flag=0,saved_scalar_bits=0,
        saved_context_token=0,pose_contents_initialized=False)
