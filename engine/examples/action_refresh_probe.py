"""Run two synthetic refresh requests through a recovered partial PreAI chain.

Evidence: INPUT_TO_ACTION_ROUTE.md, sections "Composed PreAI registration
validation" and "Category worker return and dependency release".
No game payloads, native threads or original device-source evaluation.
"""
import json
import struct
from engine.action_refresh import reset_action, refresh_groups
from engine.mixed_scheduler import MixedScheduler


def run_probe():
    actions = {'steer': bytes(160)}
    events, observations = [], []
    request = 0

    def gather(context, receiver):
        # Population supplied by this fixture; native map/gather is not emulated.
        scheduler.prepare_range('Category4', ['manager'])
        scheduler.prepare_range('Category5', ['synthetic-followup'])
        events.append(['gather', request])

    def refresh(context, receiver):
        def evaluate(snapshot):
            events.append(['evaluate', request])
            return snapshot[:0x60] + struct.pack('<f', 0.75) + snapshot[0x64:]

        def reset_binding(name):
            actions[name] = reset_action(actions[name], owner_suppressed=request == 2,
                                         evaluate=evaluate)

        refresh_groups([['steer'], [], []], reset_binding=reset_binding,
                       blocker_enabled=lambda _: False)
        events.append(['refresh', request, struct.unpack_from('<f', actions['steer'], 0x60)[0]])

    def followup(context, receiver):
        events.append(['category5', request])

    definitions = [
        dict(id='BeforeAISetup', kind='callback', handler='gather', successors=['Category4']),
        dict(id='Category4', kind='range', handler='refresh', chunk_size=100000,
             max_concurrency=2, successors=['Category5']),
        dict(id='Category5', kind='range', handler='followup', successors=['PreAISingleThreaded']),
        dict(id='PreAISingleThreaded', kind='callback', successors=['PreAITerminal']),
        dict(id='PreAITerminal', kind='terminal'),
    ]
    handlers = {name: dict(version='synthetic-v1', callback=callback)
                for name, callback in [('gather', gather), ('refresh', refresh), ('followup', followup)]}
    scheduler = MixedScheduler(definitions, handlers=handlers)

    def finish_callback(name):
        token = scheduler.reserve(name)
        scheduler.execute_callback(token)
        scheduler.finish_dispatch(token)

    def observe(stage):
        jobs = scheduler.snapshot()['jobs']
        observations.append(dict(request=request, stage=stage,
            remaining=jobs['Category4']['remaining'], executions=jobs['Category4']['executions'],
            category5_started=jobs['Category5']['started'],
            terminal_begins=jobs['PreAITerminal']['terminal_begins']))

    for request in (1, 2):
        # Harness submits again only after the partial terminal. This is not
        # execution of the original EndFrame rearm graph.
        scheduler.submit('BeforeAISetup')
        finish_callback('BeforeAISetup')
        tokens = [scheduler.reserve('Category4') for _ in range(2)]
        span = scheduler.claim_range(tokens[0])
        observe('claimed')
        scheduler.execute_range(tokens[0], span)
        scheduler.finish_dispatch(tokens[0])
        observe('callback returned, second reservation pending')
        assert scheduler.claim_range(tokens[1]) is None
        scheduler.finish_dispatch(tokens[1])
        observe('last reservation returned')
        scheduler.run_ready()
        observe('partial terminal reached')
    return dict(scope='Recovered partial dependency chain with synthetic populations, evaluator, two serial reservations and harness-controlled resubmission. No native replay or full frame graph.',
                events=events, observations=observations,
                final_sample=struct.unpack_from('<f', actions['steer'], 0x60)[0])


if __name__ == '__main__':
    print(json.dumps(run_probe(), indent=2))
