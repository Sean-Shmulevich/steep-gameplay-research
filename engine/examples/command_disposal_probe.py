"""Synthetic wrapped command-buffer disposal, without game files."""
import json
from engine.command_disposal import release_buffer


def main():
    ring = dict(storage='synthetic-buffer', capacity=4, count=3, read=3,
                write=2, owns_storage=True)
    events = []
    def cleanup(storage, slot):
        events.append(dict(operation='cleanup_record', slot=slot))
    def lookup(storage):
        events.append(dict(operation='allocation_lookup', storage=storage))
        return 'synthetic-allocation-info'
    def free(storage, info):
        events.append(dict(operation='free', storage=storage, info=info))
    release_buffer(ring, cleanup=cleanup, allocation_lookup=lookup, free=free)
    print(json.dumps(dict(evidence='synthetic reconstruction example', events=events,
                          ring=ring, gameplay_callbacks_executed=0,
                          native_shutdown_path_proved=False), indent=2))


if __name__ == '__main__':
    main()
