"""Synthetic full wrapper order around reconstructed callback completion.
Run: python3 -m engine.examples.worker_completion_probe
No native hooks, game state, OS threads, or real worker notification.
"""
import json
from engine.mixed_scheduler import MixedScheduler
from engine.worker_execution_wrapper import execute_worker_wrapper


def probe():
    scheduler = MixedScheduler([dict(id='parent', kind='callback', successors=['child']),
                                dict(id='child', kind='callback')])
    scheduler.submit('parent');token = scheduler.reserve('parent')
    queue = dict(change_counter=scheduler.snapshot()['queue_change'],
                 workers=[dict(wake_counter=-1)])
    observations = []
    def sample(phase):
        observations.append(dict(phase=phase, **scheduler.teardown_wait_status('parent')))
    def body(job):
        scheduler.execute_callback(token);sample('body_return')
        queue['change_counter'] = scheduler.snapshot()['queue_change']
    def complete(job):
        scheduler.finish_dispatch(token);sample('completion_return')
        queue['change_counter'] = scheduler.snapshot()['queue_change']
    report = execute_worker_wrapper(context='synthetic-worker',
        job=dict(mode=0, diagnostic_scope=None),
        tls=dict(execution_mode=255, scheduler_context='synthetic-worker'),queue=queue,
        body=body,complete=complete,before_job=lambda c:None,after_job=lambda c:None,
        diagnostic_begin=lambda s:None,diagnostic_end=lambda:None,
        notify_worker=lambda i:sample('notify_worker'))
    return dict(scope='synthetic serial composition; not native thread or global drain proof',
                observations=observations,wrapper=report,queued_jobs=scheduler.snapshot()['queue'])


if __name__ == '__main__':
    print(json.dumps(probe(), indent=2))
