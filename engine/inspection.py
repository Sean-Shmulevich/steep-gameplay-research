"""Offline inspection tools for our reconstruction, not original-engine hooks.

Poses are lists (matched by index) or maps from joint name to transforms in the
animation module's schema. Trace rows have unique integer ``tick`` and optional
``body`` and ``state`` dictionaries. Compare only data expressed in the same
coordinate frame and units; these tools do not infer or convert either. Optional
resource ``provenance`` metadata is relayed as supplied, never authenticated.
"""
import copy
import math
from .animation import validate_resources


def inspect_rig(rig, clips):
    """Report bindings/hierarchy; missing channels never imply recovered motion.

    Optional bone.binding_id fields are inspected for duplicates. Clip channel
    keys still bind by bone name, as specified by animation.evaluate.
    """
    bones = rig.get('bones', [])
    names = [b.get('name') for b in bones]
    ids = {}
    for i, bone in enumerate(bones):
        if 'binding_id' in bone:
            key = bone['binding_id']
            if not isinstance(key, (str, int)) or isinstance(key, bool):
                raise ValueError('binding_id must be a string or integer')
            ids.setdefault((type(key).__name__, key), []).append(i)
    errors = []
    try:
        validate_resources(rig, clips)
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        errors.append(str(exc))
    reports = {}
    for name, clip in clips.items():
        channels = clip.get('channels', {})
        reports[name] = {
            'channel_count': len(channels),
            'bound_channels': sorted(n for n in channels if n in names),
            'unknown_channels': sorted(n for n in channels if n not in names),
            'bones_without_channels': [n for n in names if n not in channels],
            'provenance': copy.deepcopy(clip.get('provenance', 'unspecified')),
        }
    return {
        'bone_count': len(bones), 'clip_count': len(clips),
        'hierarchy': [{'index': i, 'name': b.get('name'), 'parent_index': b.get('parent_index')}
                      for i, b in enumerate(bones)],
        'root_indices': [i for i, b in enumerate(bones) if b.get('parent_index') == -1],
        'duplicate_binding_ids': [{'binding_id': key[1], 'bone_indices': indices}
                                  for key, indices in ids.items() if len(indices) > 1],
        'validation_errors': errors, 'clips': reports,
        'provenance': copy.deepcopy(rig.get('provenance', 'unspecified')),
        'provenance_verified': False,
        'units': 'resource-defined; no conversion',
    }


def _vector(value, size):
    if not isinstance(value, (list, tuple)) or len(value) != size:
        raise ValueError('invalid vector size')
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in value):
        raise ValueError('non-finite or non-numeric vector')
    return value


def _angle(a, b):
    a, b = _vector(a, 4), _vector(b, 4)
    na, nb = math.hypot(*a), math.hypot(*b)
    if na == 0 or nb == 0 or not math.isfinite(na) or not math.isfinite(nb):
        raise ValueError('invalid quaternion norm')
    a, b = [x / na for x in a], [x / nb for x in b]
    # Chord formulation remains stable for tiny angular errors and q == -q.
    if sum(x*y for x, y in zip(a, b)) < 0:
        b = [-x for x in b]
    chord = math.dist(a, b)
    return 4 * math.asin(min(1., chord / 2))


def _pose_map(pose):
    if isinstance(pose, dict):
        if any(not isinstance(k, str) for k in pose):
            raise ValueError('pose mapping needs string joint names')
        return pose, 'name'
    if isinstance(pose, (list, tuple)):
        return {str(i): p for i, p in enumerate(pose)}, 'index'
    raise ValueError('pose must be a list or joint-name map')


def compare_poses(a, b):
    """Return translation distances and shortest XYZW rotation errors (radians)."""
    a, mode_a = _pose_map(a)
    b, mode_b = _pose_map(b)
    if mode_a != mode_b:
        raise ValueError('pose matching modes differ')
    rows = []
    for key in sorted(a.keys() & b.keys()):
        pa, pb = a[key], b[key]
        rows.append({'joint': key,
                     'translation_error': math.dist(_vector(pa['translation'], 3), _vector(pb['translation'], 3)),
                     'rotation_error_radians': _angle(pa['quaternion_xyzw'], pb['quaternion_xyzw'])})
    return {'matching': mode_a, 'joints': rows,
            'missing_in_a': sorted(b.keys() - a.keys()), 'missing_in_b': sorted(a.keys() - b.keys()),
            'max_translation_error': max((r['translation_error'] for r in rows), default=None),
            'max_rotation_error_radians': max((r['rotation_error_radians'] for r in rows), default=None),
            'translation_units': 'input pose units; same frame required'}


def _diff(a, b, path=''):
    if isinstance(a, dict) and isinstance(b, dict):
        result = []
        for key in sorted(a.keys() | b.keys()):
            p = path + '/' + str(key).replace('~', '~0').replace('/', '~1')
            if key not in a or key not in b:
                result.append({'path': p, 'kind': 'missing_in_a' if key not in a else 'missing_in_b'})
            else:
                result.extend(_diff(a[key], b[key], p))
        return result
    if type(a) is type(b) and a == b:
        return []
    if isinstance(a, (int, float)) and not isinstance(a, bool) and isinstance(b, (int, float)) and not isinstance(b, bool):
        if not math.isfinite(a) or not math.isfinite(b):
            raise ValueError('trace numeric values must be finite')
        if a == b:
            return []
        return [{'path': path, 'kind': 'numeric', 'delta_b_minus_a': b-a}]
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)) and len(a) == len(b):
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in _diff(x, y, path+'/'+str(i))]
    return [{'path': path, 'kind': 'value', 'a': copy.deepcopy(a), 'b': copy.deepcopy(b)}]


def compare_traces(a, b):
    """Align by tick, never by row position; no interpolation or tolerances.

    All shared-row fields are compared, including body/state. Body orientation
    is compared geometrically so quaternion sign changes are not divergences.
    Duplicate ticks are rejected rather than silently overwriting observations.
    """
    def index(rows):
        def validate(value):
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError('trace numeric values must be finite')
            if isinstance(value, dict):
                if any(not isinstance(k, str) for k in value):
                    raise ValueError('trace dictionaries need string keys')
                for item in value.values():
                    validate(item)
            elif isinstance(value, (list, tuple)):
                for item in value:
                    validate(item)
        out = {}
        for row in rows:
            validate(row)
            tick = row.get('tick')
            if type(tick) is not int or tick < 0 or tick in out:
                raise ValueError('trace ticks must be unique nonnegative integers')
            out[tick] = row
        return out
    aa, bb = index(a), index(b)
    differences = []
    for tick in sorted(aa.keys() & bb.keys()):
        left, right = copy.deepcopy(aa[tick]), copy.deepcopy(bb[tick])
        angle = None
        if 'orientation' in left.get('body', {}) and 'orientation' in right.get('body', {}):
            angle = _angle(left['body'].pop('orientation'), right['body'].pop('orientation'))
        changes = _diff(left, right)
        if angle:
            changes.append({'path': '/body/orientation', 'kind': 'rotation', 'error_radians': angle})
        if changes:
            differences.append({'tick': tick, 'differences': changes})
    missing_a, missing_b = sorted(bb.keys()-aa.keys()), sorted(aa.keys()-bb.keys())
    return {'equal': not differences and not missing_a and not missing_b,
            'compared_ticks': len(aa.keys() & bb.keys()),
            'missing_in_a': missing_a, 'missing_in_b': missing_b,
            'different_ticks': differences,
            'first_difference_tick': min([r['tick'] for r in differences]+missing_a+missing_b, default=None),
            'units': 'input trace units; coordinate frames and tick cadence must match'}
