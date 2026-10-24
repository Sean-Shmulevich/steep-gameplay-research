"""Compare wrapper-boundary observations with reconstructed local kernels.

Evidence: CENTRAL_IMPULSE.md, First live gate-state comparison. This is authored
analysis plumbing. Exit immersion/counters are supplied observations, not proof
of internal producer order. No actual stack gate value is predicted or checked.
"""
import math
import struct
from .snow_post_pending import update_point_activity, update_point_gate_timer

FIELDS = ('immersion', 'alternate', 'activity', 'timer', 'elapsed', 'total_volume',
          'refill_divisor', 'duration', 'lower_other', 'lower_one')
CONFIG = ('total_volume', 'refill_divisor', 'duration', 'lower_other', 'lower_one')


def decode(sample):
    values = {}
    for name in FIELDS:
        value = sample[name + '_bits']
        if type(value) is not int or not 0 <= value <= 0xffffffff:
            raise ValueError('Expected uint32 bits for ' + name)
        values[name] = struct.unpack('<f', struct.pack('<I', value))[0]
    return values


def bits(value):
    return struct.unpack('<I', struct.pack('<f', value))[0]


def compare_gate_transition(before, after):
    """Accept two already-valid gate_inputs dictionaries from one wrapper.

    Caller verifies attribution, identity, sample validity and capture ordering.
    Missing fields / invalid bit encodings raise. Nonfinite data, changing config
    and arithmetic outside the finite model return explicit untested statuses.
    Stable config at endpoints does not exclude an intermediate configuration swap.
    """
    a, b = decode(before), decode(after)
    if not all(math.isfinite(x) for v in (a, b) for x in v.values()):
        return {'status': 'nonfinite', 'tested': False}
    changed = [k for k in CONFIG if before[k+'_bits'] != after[k+'_bits']]
    if changed:
        return {'status': 'configuration_changed', 'tested': False, 'fields': changed}
    try:
        duration = update_point_activity(b['immersion'], a['activity'], a['alternate'], b['elapsed'])
        predicted = {k: bits(duration[k]) for k in ('activity', 'alternate')}
    except (ValueError, OverflowError):
        return {'status': 'outside_model', 'tested': False}
    result = {'status': 'compared', 'tested': True, 'duration_branch': duration['branch'],
              'duration_expected_bits': predicted,
              'duration_matches': all(predicted[k] == after[k+'_bits'] for k in predicted)}
    try:
        # Unit gates and upper bound are placeholders unused by the timer output.
        timer = update_point_gate_timer(1, 1, a['timer'], b['activity'], b['alternate'],
            b['elapsed'], b['refill_divisor'], b['duration'], b['lower_one'], b['lower_other'], 1)
        result.update(timer_action=timer['action'], timer_expected_bits=bits(timer['timer']),
                      timer_matches=bits(timer['timer']) == after['timer_bits'])
    except (ValueError, OverflowError):
        result.update(timer_action='outside_model', timer_matches=None)
    return result
