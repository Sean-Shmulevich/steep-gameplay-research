"""Saved evaluator request prefix, before bank selection and evaluation.

Evidence: CENTRAL_IMPULSE.md, Saved animation request arbitration.
Context values are opaque symbolic tokens; no retain/release is implied.
Scalar values are binary32 bits. This is not a general FIFO or work scheduler.
"""


def arbitrate_request(work_count, saved_flag, saved_scalar, saved_context,
                      scalar, context):
    for value, limit in ((work_count, 65535), (saved_flag, 255),
                         (saved_scalar, 0xffffffff), (scalar, 0xffffffff),
                         (saved_context, 0xffffffffffffffff),
                         (context, 0xffffffffffffffff)):
        if type(value) is not int or not 0 <= value <= limit:
            raise ValueError('unsigned field out of range')
    if work_count and not saved_flag:
        return dict(action='deferred', work_count=work_count, saved_flag=1,
                    saved_scalar=scalar, saved_context=context,
                    effective_scalar=scalar, effective_context=context,
                    consumed_saved=False)
    if work_count:
        work_count = 0
    consumed = bool(saved_flag and scalar & 0x7fffffff == 0 and context == 0)
    if consumed:
        scalar, context = saved_scalar, saved_context
        saved_flag = saved_scalar = saved_context = 0
    return dict(action='continue_evaluation', work_count=work_count,
                saved_flag=saved_flag, saved_scalar=saved_scalar,
                saved_context=saved_context, effective_scalar=scalar,
                effective_context=context, consumed_saved=consumed)
