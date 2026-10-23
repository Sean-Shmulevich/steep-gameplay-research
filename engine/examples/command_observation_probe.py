"""Synthetic overflow illustration; no game launch, addresses or captured data."""
import json
from engine.command_observation import summarize_deliveries


def main():
    records = [dict(result=rid, function_storage=100, thread=7, caller=200,
                    entry_tick=i*2, exit_tick=i*2+1)
               for i, rid in enumerate((1, 2, 2, 2))]
    print(json.dumps(dict(evidence='authored illustration of validated overflow pattern',
                         report=summarize_deliveries([1, 2, 3, 4], records)), indent=2))


if __name__ == '__main__':
    main()
