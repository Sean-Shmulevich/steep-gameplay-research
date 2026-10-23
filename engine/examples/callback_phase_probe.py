"""Synthetic callback phases, dependency completion and dispatch accounting.

Run: python3 -m engine.examples.callback_phase_probe
This does not attach to the game or install native hooks.
"""
import json
from engine.mixed_scheduler import MixedScheduler


def probe():
    observations = []
    def handler(phase):
        def observe(context, receiver):
            observations.append(dict(phase=phase, **scheduler.teardown_wait_status('frame')))
        return dict(version='synthetic-v1', callback=observe)
    scheduler = MixedScheduler([
        dict(id='frame', kind='callback', reservation_handler='reservation',
             before_handler='before', handler='main',
             after_handler='after', successors=['dependent']),
        dict(id='dependent', kind='terminal')],
        {phase: handler(phase) for phase in ('reservation', 'before', 'main', 'after')})
    scheduler.submit('frame')
    token = scheduler.reserve('frame')
    scheduler.execute_callback(token)
    observations.append(dict(phase='dispatch_body_returned', **scheduler.teardown_wait_status('frame')))
    scheduler.finish_dispatch(token)
    observations.append(dict(phase='dispatch_accounting_returned', **scheduler.teardown_wait_status('frame')))
    return dict(scope='synthetic reconstructed scheduler; no native hook or unload guarantee',
                observations=observations,
                dependent_begins=scheduler.snapshot()['jobs']['dependent']['terminal_begins'])


if __name__ == '__main__':
    print(json.dumps(probe(), indent=2))
