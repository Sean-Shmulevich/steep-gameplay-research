"""Recovered animation-time receiver visitor over caller-owned Python objects.

Local reverse order and callback capture are recovered. Native range claiming,
thread context, membership and concurrent receiver lifetime are not modeled.
"""


def visit_animation_batch(job, receivers, count=None):
    """Capture callback once; read each receiver at invocation time, in reverse.

    The supplied sequence stands in for a fixed native pointer-array base. Edits
    to its entries remain visible; replacing another reference to it does not.
    Return visited indices as diagnostics, not the native routine's return.
    """
    if count is None:
        count = len(receivers)
    if type(count) is not int or not 0 <= count <= min(len(receivers), 0x7fffffff):
        raise ValueError('count must fit the supplied span and signed int32')
    callback = job['callback']
    if count and not callable(callback):
        raise ValueError('nonempty batch requires a callback')
    visited = []
    for index in range(count - 1, -1, -1):
        callback(receivers[index])
        visited.append(index)
    return visited
