"""Recovered ingestion gate order, with caller-supplied reads and helpers.

Evidence: MOTION_MEMBERSHIP_OBSERVATION.md, Motion ingestion gates,
original-instruction validation. Valid/stable controller resolution is supplied
by the caller. This excludes actor preparation before the activity test, the
auxiliary actor path, ingestion itself, carrier processing and dispatch.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class MotionInputGate:
    ingestion_enabled: bool
    preparation: str | None
    stopped_at: str | None
    events: tuple[str, ...]


def resolve_motion_input_gate(read_flag, predicate_a, predicate_b,
                              prepare_a, prepare_b):
    """Read each flag at its branch and re-read skip after chosen preparation.

    read_flag names: active, controller_blocked, motion_enabled, skip_ingestion.
    Predicates and flag reads must return bools. Preparation callbacks may change
    caller-owned state; these effects are not rolled back on errors. Their actual
    bodies are unresolved dependencies, not guessed implementations.
    """
    if any(not callable(x) for x in (read_flag, predicate_a, predicate_b, prepare_a, prepare_b)):
        raise ValueError('all gate providers must be callable')
    events = []
    def boolean(name, callback):
        events.append(name)
        result = callback()
        if type(result) is not bool:
            raise ValueError(name + ' must return bool')
        return result
    def flag(name):
        return boolean(name, lambda: read_flag(name))
    for name, stop_value in (('active', False), ('controller_blocked', True),
                             ('motion_enabled', False)):
        if flag(name) is stop_value:
            return MotionInputGate(False, None, name, tuple(events))
    preparation = None
    if boolean('predicate_a', predicate_a):
        preparation = 'prepare_a'
        events.append(preparation)
        prepare_a()
    elif boolean('predicate_b', predicate_b):
        preparation = 'prepare_b'
        events.append(preparation)
        prepare_b()
    skip = flag('skip_ingestion')
    return MotionInputGate(not skip, preparation,
                           'skip_ingestion' if skip else None, tuple(events))


def preparation_mode_matches(mode, preparation):
    """Concrete actor predicates for the inspected actor table.

    A tests raw actor mode == 9; B tests mode == 5. Values are build-qualified
    actor modes, not portable sport IDs. Call at predicate evaluation time;
    do not reuse a mode snapshot across helper effects or actor replacement.
    """
    if type(mode) is not int or not 0 <= mode < 1 << 32:
        raise ValueError('uint32 actor mode required')
    if preparation not in ('a', 'b'):
        raise ValueError('preparation must be a or b')
    return mode == (9 if preparation == 'a' else 5)
