"""Synthetic animation pipeline; no original assets or gameplay selector policy.

Schema: rig={bones:[{name,parent_index,local_bind}]}; clips maps names to
{duration,loop,channels:{bone_name:[{time,translation,quaternion_xyzw}]}}.
All times are seconds. State={clip,time, transition?:{clip,time,elapsed,duration},
additive?:{clip,time,weight}}. inputs.clip requests a crossfade (fade_seconds,
default .2). Selection, linear/slerp interpolation and modulo looping are our
engine choices. Hierarchy composition and palette math use recovered references
(docs/systems/animations/skeleton and skinning). Additive channels are DELTAS,
translation plus right-multiplied rotation, not absolute bind poses. evaluate
copies state and never writes its rig, clips, inputs or physical body.
"""
import copy
import math
import bisect
from reference import skeleton, skinning, animation_blending, animation_playback


def _finite(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(label + ' must be finite')
    return value


def _vector(value, n, label):
    if not isinstance(value, (list, tuple)) or len(value) != n:
        raise ValueError(label + ' has wrong size')
    return [_finite(x, label) for x in value]


def _quat(q):
    q = _vector(q, 4, 'quaternion')
    norm = math.sqrt(sum(x*x for x in q))
    if norm < 1e-12:
        raise ValueError('zero quaternion')
    return [x/norm for x in q]


def _pose(p):
    return {'translation': _vector(p['translation'], 3, 'translation'),
            'quaternion_xyzw': _quat(p['quaternion_xyzw'])}


def _identity():
    return {'translation': [0., 0., 0.], 'quaternion_xyzw': [0., 0., 0., 1.]}


def validate_resources(rig, clips):
    """Reject malformed resources; report unmatched channels without guessing."""
    bones = rig['bones']
    if not bones or not clips:
        raise ValueError('rig and clips must be nonempty')
    names = [b['name'] for b in bones]
    if any(not isinstance(n, str) or not n for n in names) or len(set(names)) != len(names):
        raise ValueError('bone names must be unique nonempty strings')
    for i, b in enumerate(bones):
        parent = b['parent_index']
        if type(parent) is not int or parent < -1 or parent >= len(bones):
            raise ValueError('invalid parent index')
        _pose(b['local_bind'])
        seen = {i}
        while parent != -1:
            if parent in seen:
                raise ValueError('cyclic hierarchy')
            seen.add(parent)
            parent = bones[parent]['parent_index']
            if type(parent) is not int or parent < -1 or parent >= len(bones):
                raise ValueError('invalid ancestor index')
    missing = {}
    for name, clip in clips.items():
        policy=clip.get('sampling_policy','seconds_slerp')
        if policy not in ('seconds_slerp','recovered_60hz'):raise ValueError('Unsupported sampling policy')
        if clip.get('wrap_policy','modulo') not in ('modulo','inclusive'):raise ValueError('Unsupported wrap policy')
        duration = _finite(clip['duration'], 'clip duration')
        if duration <= 0 or type(clip['loop']) is not bool:
            raise ValueError('clip needs positive duration and explicit boolean loop')
        missing[name] = sorted(set(clip['channels']) - set(names))
        for channel in clip['channels'].values():
            if isinstance(channel,dict):
                if not channel or set(channel)-{'translation','rotation'}:raise ValueError('Unknown separate track kind')
                for kind,keys in channel.items():
                    if not keys:raise ValueError('Empty separate track')
                    last=-1.
                    for key in keys:
                        t=_finite(key['time'],'key time')
                        if not 0<=t<=duration+1e-5 or t<last:raise ValueError('Unordered separate track')
                        if policy=='recovered_60hz' and abs(t*60-round(t*60))>1e-5:raise ValueError('Expected 60 Hz key ticks')
                        last=t
                        _vector(key['value'],3 if kind=='translation' else 4,'track value')
                        if kind=='rotation':_quat(key['value'])
            else:
                keys=channel
                if not keys:raise ValueError('empty channel')
                last=-1.
                for key in keys:
                    t=_finite(key['time'],'key time')
                    if not 0<=t<=duration or t<=last:raise ValueError('key times must be strictly increasing within clip')
                    if policy=='recovered_60hz' and abs(t*60-round(t*60))>1e-5:raise ValueError('Recovered sampler requires authored 60 Hz key ticks')
                    last=t;_pose(key)
    return {'missing_channels': {n: m for n, m in missing.items() if m}}


def _slerp(a, b, weight):
    a, b = _quat(a), _quat(b)
    dot = sum(x*y for x, y in zip(a, b))
    if dot < 0:
        b, dot = [-x for x in b], -dot
    dot = min(1., dot)
    if dot > .9995:
        return _quat([x + weight*(y-x) for x, y in zip(a, b)])
    angle = math.acos(dot)
    sa, sb = math.sin((1-weight)*angle), math.sin(weight*angle)
    return _quat([(sa*x+sb*y)/math.sin(angle) for x, y in zip(a, b)])


def _blend(a, b, weight):
    return {'translation': [x+weight*(y-x) for x, y in zip(a['translation'], b['translation'])],
            'quaternion_xyzw': _slerp(a['quaternion_xyzw'], b['quaternion_xyzw'], weight)}


def _time(clip, value):
    value = _finite(value, 'playback time')
    if value < 0:
        raise ValueError('negative playback time')
    if not clip['loop']:return min(value,clip['duration'])
    if clip.get('wrap_policy')=='inclusive':return animation_playback.inclusive_wrap(value,0.,clip['duration'])
    return value % clip['duration']


def _sample(clip, time, name, fallback):
    recovered=clip.get('sampling_policy')=='recovered_60hz'
    keys = clip['channels'].get(name)
    if keys is None:
        return copy.deepcopy(fallback)
    if isinstance(keys,dict):
        result=copy.deepcopy(fallback)
        for kind,track in keys.items():
            result['translation' if kind=='translation' else 'quaternion_xyzw']=_sample_separate(track,time,kind,recovered)
        return result
    if recovered:
        # The integer tick chooses a segment; interpolation still uses continuous time.
        frame=math.trunc(animation_playback.mul(animation_playback.f32(time),60.))
        frames=[round(key['time']*60) for key in keys]
        i=max(0,min(bisect.bisect_right(frames,frame)-1,len(keys)-1))
        if i==len(keys)-1:return _pose(keys[i])
        left,right=keys[i],keys[i+1]
        weight=max(0.,min(1.,(time-left['time'])/(right['time']-left['time'])))
        return {'translation':animation_blending.linear_blend(left['translation'],right['translation'],weight),
                'quaternion_xyzw':animation_blending.bone_rotation_blend(left['quaternion_xyzw'],right['quaternion_xyzw'],weight)}
    if time <= keys[0]['time']:
        return _pose(keys[0])
    for left, right in zip(keys, keys[1:]):
        if time <= right['time']:
            weight=(time-left['time'])/(right['time']-left['time'])
            return _blend(_pose(left), _pose(right), weight)
    return _pose(keys[-1])


def _models(bones, local):
    out = [None]*len(bones)
    def visit(i):
        if out[i] is None:
            p = bones[i]['parent_index']
            out[i] = skeleton.native_compose(_identity() if p < 0 else visit(p), local[i])
        return out[i]
    return [visit(i) for i in range(len(bones))]


def evaluate(rig, clips, state, dt, inputs):
    diagnostics = validate_resources(rig, clips)
    dt = _finite(dt, 'dt')
    if dt < 0:
        raise ValueError('negative dt')
    s = copy.deepcopy(state)
    s.setdefault('clip', next(iter(clips)))
    s.setdefault('time', 0.)
    if s['clip'] not in clips:
        raise ValueError('unknown active clip')
    request = inputs.get('clip', s.get('transition', {}).get('clip', s['clip']))
    if request not in clips:
        raise ValueError('unknown requested clip')
    target = s.get('transition', {}).get('clip', s['clip'])
    if request != target:
        if 'transition' in s:
            raise ValueError('finish active crossfade before retargeting')
        fade = _finite(inputs.get('fade_seconds', .2), 'fade duration')
        if fade < 0:
            raise ValueError('negative fade')
        if fade == 0:
            s['clip'], s['time'] = request, 0.
        else:
            s['transition'] = {'clip': request, 'time': 0., 'elapsed': 0., 'duration': fade}
    active = clips[s['clip']]
    s['time'] = _time(active, _time(active, s['time']) + dt)
    local = [_sample(active, s['time'], b['name'], _pose(b['local_bind'])) for b in rig['bones']]
    alpha = 0.
    if 'transition' in s:
        tr = s['transition']
        if tr['clip'] not in clips or _finite(tr['duration'], 'fade duration') <= 0:
            raise ValueError('invalid transition')
        elapsed = _finite(tr['elapsed'], 'fade elapsed')
        if elapsed < 0:
            raise ValueError('negative fade elapsed')
        tr['elapsed'] = elapsed + dt
        tr['time'] = _time(clips[tr['clip']], _time(clips[tr['clip']], tr['time']) + dt)
        alpha = min(1., tr['elapsed']/tr['duration'])
        other = [_sample(clips[tr['clip']], tr['time'], b['name'], _pose(b['local_bind'])) for b in rig['bones']]
        local = [_blend(a, b, alpha) for a, b in zip(local, other)]
        if alpha == 1:
            s['clip'], s['time'] = tr['clip'], tr['time']
            del s['transition']
    if 'additive' in s:
        layer = s['additive']
        weight = _finite(layer['weight'], 'additive weight')
        if layer['clip'] not in clips or not 0 <= weight <= 1:
            raise ValueError('invalid additive layer')
        clip = clips[layer['clip']]
        layer['time'] = _time(clip, _time(clip, layer.get('time', 0.)) + dt)
        for bone, pose in zip(rig['bones'], local):
            delta = _sample(clip, layer['time'], bone['name'], _identity())
            pose['translation'] = [a+weight*b for a, b in zip(pose['translation'], delta['translation'])]
            pose['quaternion_xyzw'] = _quat(skeleton.qmul(pose['quaternion_xyzw'], _slerp([0,0,0,1], delta['quaternion_xyzw'], weight)))
    diagnostics.update({'policy': 'synthetic selector and interpolation; recovered normalized hierarchy',
                        'sampling_policy':active.get('sampling_policy','seconds_slerp'),'wrap_policy':active.get('wrap_policy','modulo'),
                        'crossfade_weight': alpha, 'body_mutated': False, 'lod': 'all bones evaluated'})
    return {'state': s, 'local_pose': local, 'model_pose': _models(rig['bones'], local), 'diagnostics': diagnostics}


def palette(rig, model_pose, mesh_names, inverse_binds, root=None, origin_shift=None, scale=1.):
    """Report unresolved names BEFORE applying recovered first-resolved fallback."""
    if len(mesh_names) != len(inverse_binds) or len(model_pose) != len(rig['bones']):
        raise ValueError('palette input length mismatch')
    scale = _finite(scale, 'scale')
    if scale <= 0:
        raise ValueError('positive scale required')
    for matrix in inverse_binds:
        if len(matrix) != 4:
            raise ValueError('inverse bind must be 4x4')
        for row in matrix:
            _vector(row, 4, 'inverse bind')
    names = {b['name']: i for i, b in enumerate(rig['bones'])}
    resolved = [names.get(n) for n in mesh_names]
    missing = [n for n, i in zip(mesh_names, resolved) if i is None]
    mapping = skinning.remap_mesh_joints(resolved)
    rows = [] if not mapping else skinning.native_skinning_palette(
        inverse_binds, mapping, [_pose(p) for p in model_pose], _pose(root or _identity()),
        _vector(origin_shift if origin_shift is not None else [0,0,0], 3, 'origin shift'), scale)
    return {'rows': rows, 'joint_map': mapping, 'missing_mesh_joints': missing}


def default_resources():
    """Invented three-joint rig, static idle, one-second knee bend, additive lean."""
    rig = {'bones': [{'name': n, 'parent_index': p, 'local_bind': {'translation': t, 'quaternion_xyzw': [0,0,0,1]}}
                     for n, p, t in [('root', -1, [0,0,1]), ('knee', 0, [0,0,-.4]), ('foot', 1, [0,0,-.4])]]}
    def key(t, angle, translation):
        return {'time': t, 'translation': translation, 'quaternion_xyzw': [0, math.sin(angle/2), 0, math.cos(angle/2)]}
    clips = {'idle': {'duration': 1., 'loop': True, 'channels': {}},
             'bend': {'duration': 1., 'loop': False, 'channels': {'knee': [key(0, 0, [0,0,-.4]), key(1, .7, [0,0,-.4])]}},
             'lean': {'duration': 1., 'loop': True, 'channels': {'root': [key(0, .2, [0,0,0])]}}}
    return rig, clips


def _sample_separate(keys,time,kind,recovered):
    query=math.trunc(animation_playback.mul(animation_playback.f32(time),60.)) if recovered else time
    coordinates=[round(key['time']*60) if recovered else key['time'] for key in keys]
    i=max(0,min(bisect.bisect_right(coordinates,query)-1,len(keys)-1))
    a=keys[i]['value']
    if i==len(keys)-1:return list(a) if kind=='translation' else _quat(a)
    left,right=keys[i],keys[i+1]
    weight=max(0.,min(1.,(time-left['time'])/(right['time']-left['time'])))
    if kind=='translation':return animation_blending.linear_blend(a,right['value'],weight)
    return animation_blending.bone_rotation_blend(a,right['value'],weight) if recovered else _slerp(a,right['value'],weight)
