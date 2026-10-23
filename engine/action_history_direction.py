"""Four-sector history reader, finite mathematical reconstruction.

Evidence: INPUT_TO_ACTION_ROUTE.md, History direction reader and action source.
The reader uses history B, not the curve-remapped history C. No player binding
or live scheduler cadence is inferred. Normalization/trig are scalar substitutes.
"""
import math
import struct
from .action_sample import f32, publish_vector


def history_direction_matches(snapshot, reference, *, magnitude_threshold, sector):
    """Return match and diagnostics for a caller-selected four-sector request.

    Requires finite, nondegenerate direction/reference after the magnitude gate.
    Sector IDs are retained as integers rather than assumed gameplay directions.
    """
    if not isinstance(snapshot, bytes) or len(snapshot) < 0x2e4:
        raise ValueError('history snapshot must contain newest magnitude')
    if type(sector) is not int or not 0 <= sector <= 0xffffffff:
        raise ValueError('sector must be uint32')
    magnitude = f32(struct.unpack_from('<f', snapshot, 0x2e0)[0])
    threshold = f32(magnitude_threshold)
    if magnitude <= threshold:
        return dict(matches=False, selected_sector=None, signed_angle=None, magnitude=magnitude)
    if not isinstance(reference, (list, tuple)) or len(reference) != 4:
        raise ValueError('reference must have four lanes')
    sample = list(struct.unpack_from('<4f', snapshot, 0x1a0))
    a = publish_vector([f32(x) for x in reference])['direction']
    b = publish_vector(sample)['direction']
    if not any(a) or not any(b):
        raise ValueError('direction and reference must be nonzero after magnitude gate')
    products = [f32(x*y) for x,y in zip(a,b)]
    dot = f32(f32(products[0]+products[2])+f32(products[1]+products[3]))
    if dot >= 1:
        angle, selected = 0., 0
    elif dot <= -1:
        angle, selected = f32(math.pi), 1
    else:
        cross_z = f32(f32(b[0]*a[1])-f32(a[0]*b[1]))
        angle = f32(math.acos(dot))
        if cross_z < 0: angle = -angle
        quarter, three_quarters = f32(math.pi/4), f32(3*math.pi/4)
        if -quarter < angle < quarter: selected = 0
        elif -three_quarters < angle < -quarter: selected = 2
        elif quarter < angle < three_quarters: selected = 3
        else: selected = 1
    return dict(matches=sector == selected, selected_sector=selected,
                signed_angle=angle, magnitude=magnitude)
