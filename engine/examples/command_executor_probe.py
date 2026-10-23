"""Synthetic nested command invocation; run with python3 -m engine.examples.command_executor_probe."""
import json
from engine.command_executor import execute_commands


def run():
    manager = dict(executing_byte=0, array=0, count=2, embedded='synthetic embedded service')
    trace = []
    nested = False
    depth = 0

    def record(name):
        trace.append(dict(event=name, depth=depth, executing_byte=manager['executing_byte']))

    services = {name: (lambda receiver=None, name=name: record(name))
                for name in ('hierarchy', 'A', 'C', 'D', 'global')}
    services['B'] = lambda receiver: 1

    def invoke(participant):
        nonlocal nested, depth
        record(participant)
        if participant == 'first' and not nested:
            nested = True
            depth += 1
            execute_commands(manager, **args)
            depth -= 1
            record('inner returned while outer callback is active')

    args = dict(services=services, read_slot=lambda slot: ('first', 'second')[slot],
                invoke=invoke, read_global_flag=lambda: 0)
    execute_commands(manager, **args)
    return dict(evidence='authored nested invocation using recovered executor flow',
                trace=trace, final_executing_byte=manager['executing_byte'],
                live_reentrancy_observed=False, safe_unload_proved=False)


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
