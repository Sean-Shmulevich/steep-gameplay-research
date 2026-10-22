"""Static-derived filter/attempt/fallback orchestration.

Evidence: CENTRAL_IMPULSE.md, Result conversion orchestration.
Conversion callbacks remain unresolved dependencies, not substitute pose solvers.
"""
from reference.animation_result_filter import filter_result_records
from reference.snow import f32


def convert_result_records(records, threshold, context, output, *, attempt, fallback):
    """Run the recovered normal-path ordering over supplied record bytes.

    attempt(context, filtered, start, count, output, weight, option0, option1)
    returns an integer whose low byte is tested. fallback(context, original,
    output) is called on low-byte zero. Both may mutate output. Return metadata
    is authored; native return-value semantics and allocator cleanup are omitted.
    Callback exceptions propagate; no native exception recovery is inferred.
    """
    original = [bytes(record) for record in records]
    value = f32(threshold)
    # MAXSS source is +0: unordered comparisons and equal signed zeros select it.
    cutoff = value if value > 0.0 else 0.0
    filtered = filter_result_records(original, cutoff)
    result = attempt(context, filtered, 0, len(filtered), output, 1.0, 0, 0)
    used_fallback = (int(result) & 0xff) == 0
    if used_fallback:
        fallback(context, original, output)
    return {'threshold': cutoff, 'filtered_count': len(filtered),
            'used_fallback': used_fallback}
