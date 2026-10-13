"""Owned gameplay phase graph; topology is designed, not recovered game wiring.

Each call creates and drains a fresh serial MixedScheduler. Context and handlers
are transient. The Engine owns numerical state, checkpointing and rollback.
"""
from .mixed_scheduler import MixedScheduler
from .trace import Trace

PHASES = ('physics', 'environment', 'scoring', 'animation', 'camera')


class _ForwardTrace:
    def __init__(self, destination, fields):
        self.local = Trace(512)
        self.destination = destination
        self.fields = fields

    def emit(self, kind, **fields):
        self.local.emit(kind, **fields)
        self.destination.emit('gameplay_job', job_event=kind, **self.fields, **fields)

    def snapshot(self):
        return self.local.snapshot()


def run(phases, context, trace, **trace_fields):
    """Execute all five phase(context) callbacks once, then reach ready terminal.

    Exceptions propagate to the enclosing Engine transaction; this function does
    not undo arbitrary callback side effects. No live graph survives the call.
    Trace forwarding is synchronous and bounded by the destination's capacity.
    """
    if set(phases) != set(PHASES) or any(not callable(phases[name]) for name in PHASES):
        raise ValueError('All five callable gameplay phases are required')
    definitions = []
    handlers = {}
    for index, name in enumerate(PHASES):
        definitions.append(dict(id=name, kind='range' if index == 0 else 'callback',
                                successors=[PHASES[index+1] if index+1 < len(PHASES) else 'ready'],
                                handler=name, **({'receivers':['player']} if index == 0 else {})))
        def execute(ctx, receiver, phase=phases[name]):
            phase(ctx)
        handlers[name] = dict(version='owned-gameplay-v1', callback=execute)
    definitions.append(dict(id='ready', kind='terminal'))
    scheduler = MixedScheduler(definitions, handlers, max_transitions=1000)
    scheduler.trace = _ForwardTrace(trace, trace_fields)
    scheduler.submit('physics', context)
    count = scheduler.run_ready(context, max_dispatches=len(PHASES))
    result = scheduler.snapshot()
    if count != len(PHASES) or result['queue'] or result['dispatches'] or result['fault'] or result['jobs']['ready']['terminal_begins'] != 1:
        raise RuntimeError('Gameplay phase graph did not drain')
    return result
