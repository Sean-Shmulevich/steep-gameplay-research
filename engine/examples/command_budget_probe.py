"""Compose recovered primary drain policy with the outer command executor."""
import json
from engine.command_drain import command_quota, drain_primary
from engine.command_executor import execute_commands


def run_case(count, bypass):
    queue = list(range(count))
    seen = []
    manager = dict(executing_byte=0, array=0, count=0, embedded=None)
    quota = command_quota(count, 8)
    clocks = iter([0] + [500] * count)
    report = {}

    def primary(owner):
        def take():
            return (True, queue.pop(0)) if queue else (False, None)
        report.update(drain_primary(quota=quota, bypass_budget=bypass, take=take,
                      process=lambda command: seen.append(['primary', command]),
                      ticks=lambda: next(clocks), frequency=1000000))
        return int(report['did_work'])

    services = {name: lambda receiver=None: None for name in ('hierarchy', 'A', 'D', 'global')}
    services.update(B=primary, C=lambda owner: seen.append(['secondary service admitted']))
    execute_commands(manager, services=services, read_slot=lambda slot: None,
                     invoke=lambda participant: None, read_global_flag=lambda: int(bypass))
    return dict(initial_count=count, bypass_budget=bypass, initial_quota=quota,
                primary_drain=report, remaining_primary=queue, events=seen)


def run():
    return dict(evidence='recovered control flow with synthetic records, clocks and opaque services',
                cases=[run_case(3, False), run_case(0, False), run_case(3, True)],
                native_command_submission_proved=False)


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
