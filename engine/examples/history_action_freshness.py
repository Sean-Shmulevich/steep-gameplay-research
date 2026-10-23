"""Run with python3 -m engine.examples.history_action_freshness."""
import json
from engine.history_action_bench import inspect_history_action


def inspect():
    return inspect_history_action([
        dict(kind='update',vector=[0,1,0,0],now=9000),
        dict(kind='evaluate',clocks=[100],ownership=[False,False]),
        dict(kind='evaluate',clocks=[200],ownership=[False,False]),
        dict(kind='update',vector=[0,0,0,0],now=9001),
        dict(kind='evaluate',clocks=[],ownership=[False,False]),
    ],channel=0,alternate_center=False,primary=[0,1,0,0],secondary=[1,0,0,0],
        reference=[0,1,0,0],direction_kind=0,magnitude_threshold=.5,
        mode=1,hold_delay=.1,repeat_delay=0)


if __name__ == '__main__':
    print(json.dumps(inspect(),indent=2))
