"""Deterministic visual motion observer for the owned reconstruction.

The complete original landing selector and animation scheduling are unresolved:
see docs/reconstruction/ANIMATION_PIPELINE.md, "Landing without inventing a
selector", and docs/STATUS.md. EVERY phase selection and default timer here is
designed behavior. Physics diagnostics may contain recovered numerical kernels;
that does not upgrade this observer's state machine to recovered code.

Call after physics publishes a body. This module never modifies the body,
diagnostics, configuration or clips. A crash phase is a visual/requested state;
it does not stop physics, respawn the player or apply a second landing impulse.
Published contact transitions are observed at the end of an interval. Their exact
within-step times are unknown, so a newly entered phase starts at age zero.
"""
import copy
import math

PHASES = ('grounded', 'takeoff', 'airborne', 'landing_recovery', 'crash')
EVIDENCE = 'designed_motion_selection_and_timing_from_published_physics'
DEFAULTS = dict(takeoff_duration=.08, landing_duration=.2, crash_duration=.8)


def _duration(value, name):
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ValueError(name + ' must be a nonnegative finite number')
    if not math.isfinite(value) or value < 0:
        raise ValueError(name + ' must be a nonnegative finite number')
    return float(value)


def _configuration(config):
    if not isinstance(config, dict) or set(config) - set(DEFAULTS) - {'clips'}:
        raise ValueError('unknown motion configuration field')
    result = {name: _duration(config.get(name, default), name) for name, default in DEFAULTS.items()}
    clips = config.get('clips', {})
    if not isinstance(clips, dict) or set(clips) - set(PHASES) - {'landing_clean', 'landing_sketchy'}:
        raise ValueError('clip mapping must use motion phase names')
    if any(not isinstance(value, str) or not value for value in clips.values()):
        raise ValueError('clip mappings must contain nonempty identifiers')
    result['clips'] = clips
    return result


def _signals(body, diagnostics):
    if not isinstance(body, dict) or type(body.get('grounded')) is not bool:
        raise ValueError('published body requires boolean grounded')
    if not isinstance(diagnostics, dict):
        raise ValueError('diagnostics must be an object')
    for flag in ('crashed', 'landing_clean'):
        if flag in diagnostics and type(diagnostics[flag]) is not bool:
            raise ValueError(flag + ' must be boolean')
    crashed = diagnostics.get('crashed', False)
    quality = 'clean' if diagnostics.get('landing_clean', True) else 'sketchy'
    events = diagnostics.get('events', [])
    if not isinstance(events, list) or len(events) > 256:
        raise ValueError('diagnostic events must be a bounded list')
    for event in events:
        if not isinstance(event, dict):
            raise ValueError('diagnostic event must be an object')
        if event.get('type') == 'landing':
            q = event.get('quality', quality)
            if q not in ('clean', 'sketchy', 'crash'):
                raise ValueError('unknown landing quality')
            quality = q
            crashed = crashed or q == 'crash'
    if crashed:
        quality = 'crash'
    return body['grounded'], crashed, quality


def _validate_state(state):
    expected = {'schema_version', 'phase', 'phase_time', 'time', 'previous_grounded',
                'previous_crashed', 'landing_quality', 'transition_sequence', 'evidence'}
    if set(state) != expected or state.get('schema_version') != 1:
        raise ValueError('invalid motion checkpoint schema')
    if state['phase'] not in PHASES or state['landing_quality'] not in (None, 'clean', 'sketchy', 'crash'):
        raise ValueError('invalid motion checkpoint phase or quality')
    _duration(state['time'], 'state time')
    _duration(state['phase_time'], 'phase time')
    if state['phase_time'] > state['time']:
        raise ValueError('phase age exceeds observer time')
    if type(state['previous_grounded']) is not bool or type(state['previous_crashed']) is not bool:
        raise ValueError('invalid motion checkpoint signals')
    if type(state['transition_sequence']) is not int or state['transition_sequence'] < 0:
        raise ValueError('invalid transition sequence')
    if state['evidence'] != EVIDENCE:
        raise ValueError('invalid motion checkpoint provenance')


def _request(work, cfg, events):
    clip_key = work['phase']
    if clip_key == 'landing_recovery' and work['landing_quality'] in ('clean', 'sketchy'):
        specific = 'landing_' + work['landing_quality']
        if specific in cfg['clips']:
            clip_key = specific
    return dict(phase=work['phase'], phase_time=work['phase_time'],
                clip=cfg['clips'].get(clip_key), events=events,
                landing_quality=work['landing_quality'], evidence=EVIDENCE)


def update(state, body, diagnostics, dt, config=None):
    """Observe one physics publication and return a bounded animation request.

    Config defaults are designed seconds: takeoff_duration=.08,
    landing_duration=.2, crash_duration=.8. Zero durations are supported.
    clips maps phase names to caller-supplied clip IDs. Optional landing_clean /
    landing_sketchy keys override landing_recovery. Missing mapping returns None;
    no original resource selection is guessed and no clip is synthesized here.

    On first observation establish current phase without emitting a fabricated
    takeoff/landing. A grounded->air edge enters takeoff. An air->ground edge
    enters landing_recovery or crash. Crash rising edges may also arrive while
    airborne; the crash visual phase lasts until its timer expires. Continued
    crash=True does not restart the timer. A new crash requires a false->true
    edge. Ground loss during landing recovery begins takeoff immediately.

    Each call emits at most two transitions. Age overruns of a phase timer are
    retained in the next phase only for timer-driven transitions. New observed
    contact/crash edges take priority and start age zero. Zero dt validates and
    returns the current request without consuming any new edge or transition;
    an empty state is initialized once. This supports restore validation.
    """
    if not isinstance(state, dict):
        raise ValueError('state must be an object')
    dt = _duration(dt, 'dt')
    cfg = _configuration({} if config is None else config)
    grounded, crashed, quality = _signals(body, diagnostics)
    if state:
        _validate_state(state)
        work = copy.deepcopy(state)
        work['time'] = _duration(work['time'] + dt, 'accumulated time')
        work['phase_time'] = _duration(work['phase_time'] + dt, 'accumulated phase age')
    else:
        work = dict(schema_version=1, phase='crash' if crashed else 'grounded' if grounded else 'airborne',
                    phase_time=0.0, time=dt, previous_grounded=grounded,
                    previous_crashed=crashed, landing_quality='crash' if crashed else None,
                    transition_sequence=0, evidence=EVIDENCE)
    events = []
    if dt == 0:
        _validate_state(work)
        if not state:
            state.update(work)
        return _request(work, cfg, events)

    def transition(target, reason, age=0.0):
        old = work['phase']
        if old == target:
            return
        work['transition_sequence'] += 1
        work['phase'], work['phase_time'] = target, age
        events.append(dict(type='motion_transition', sequence=work['transition_sequence'],
                           source=old, target=target, reason=reason,
                           time=work['time'], evidence=EVIDENCE))

    ground_changed = grounded != work['previous_grounded']
    fresh_crash = crashed and not work['previous_crashed']
    if fresh_crash:
        work['landing_quality'] = 'crash'
        transition('crash', 'published_crash_edge')
    elif work['phase'] != 'crash' and ground_changed:
        if grounded:
            work['landing_quality'] = quality
            transition('crash' if crashed else 'landing_recovery', 'published_contact_return')
        else:
            work['landing_quality'] = None
            transition('takeoff', 'published_contact_loss')

    phase = work['phase']
    timer_key = {'takeoff': 'takeoff_duration', 'landing_recovery': 'landing_duration', 'crash': 'crash_duration'}.get(phase)
    if timer_key and work['phase_time'] >= cfg[timer_key]:
        age = work['phase_time'] - cfg[timer_key]
        target = 'grounded' if grounded else 'airborne'
        transition(target, 'designed_phase_timer_elapsed', age)
    work['previous_grounded'], work['previous_crashed'] = grounded, crashed
    _validate_state(work)
    state.clear()
    state.update(work)
    return _request(work, cfg, events)
