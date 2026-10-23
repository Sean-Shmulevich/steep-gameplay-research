"""Constructor-selected input history curves, with finite float32 evaluation.

Evidence: INPUT_TO_ACTION_ROUTE.md, Constructor-selected history curves.
Channel and constructor flag are explicit; no live configuration is inferred.
"""
import struct
from .action_sample import f32


def history_curve_config(channel, *, alternate_center=False):
    """Return detached constructor defaults; channel is zero or one."""
    if type(channel) is not int or channel not in (0, 1):
        raise ValueError('channel must be 0 or 1')
    if type(alternate_center) is not bool:
        raise ValueError('alternate_center must be boolean')
    pi = f32(3.1415927410125732)
    if channel == 1:
        return dict(threshold=1., points=((0., 0.), (1., pi)))
    points = [(0., 0.)]
    if alternate_center:
        points.append((0.008333333767950535, 0.))
    points.extend([
        (0.0277777761220932, 0.013962633907794952 if alternate_center else 0.01745329238474369),
        (0.0555555522441864, 0.0872664600610733),
        (0.1111111044883728, 0.1745329201221466),
        (0.1666666716337204, 0.3490658402442932),
        (0.2222222089767456, 0.6981316804885864), (1., pi)])
    return dict(threshold=f32(0.9961947202682495), points=tuple(points))


def evaluate_history_curve(value, points):
    """Evaluate finite, strictly increasing knots in original operation order.

    All inclusive matching segments execute; the last match wins at a knot.
    Outside the knot range the original evaluator returns zero, not an endpoint.
    Duplicate/nonincreasing knots are outside this adapter's supported domain.
    """
    value = f32(value)
    points = tuple((f32(x), f32(y)) for x, y in points)
    if len(points) < 2 or any(a[0] >= b[0] for a, b in zip(points, points[1:])):
        raise ValueError('at least two strictly increasing finite knots required')
    result = 0.
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x0 <= value <= x1:
            slope = f32(f32(y1-y0) / f32(x1-x0))
            result = f32(f32(f32(value-x0) * slope) + y0)
    return result


def initial_history_snapshot(channel, *, alternate_center=False):
    """Create detached zero histories with the selected constructor threshold.

    Native pointers and auxiliary containers are omitted, left zero. Curve knots
    remain in history_curve_config rather than being encoded as process memory.
    This is adapter state, not a native object suitable for writing into a game.
    """
    config = history_curve_config(channel, alternate_center=alternate_center)
    state = bytearray(0x3c0)
    struct.pack_into('<f', state, 0x50, config['threshold'])
    return bytes(state)
