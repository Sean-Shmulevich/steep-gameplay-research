"""Bounded sequential sampling. Identity stability is not atomicity."""
import time


def capture(read_identity, read_fields, max_groups=100, max_seconds=1., clock=time.monotonic):
    if max_groups < 0 or max_seconds < 0:
        raise ValueError("Negative capture bound")
    started = clock()
    rows = []
    for index in range(max_groups):
        begin = clock()
        if begin - started >= max_seconds:
            break
        before = read_identity()
        fields = read_fields()
        after = read_identity()
        end = clock()
        rows.append(dict(index=index, start=begin-started, end=end-started,
                         accepted=before == after and end-started <= max_seconds,
                         fields=fields if before == after and end-started <= max_seconds else None))
        if end - started >= max_seconds:
            break
    return dict(atomic=False, rows=rows)
