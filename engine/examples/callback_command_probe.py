"""Show full-ring admission and repeated callbacks with synthetic descriptors."""
import json
import struct
from engine.callback_commands import submit_callback, drain_counted_callbacks
from engine.command_counter_transfer import replay_counter_transfers


def run():
    queue = []
    deferred = 0
    submissions = []
    for identity in (1, 2):
        descriptor = struct.pack('<4Q', identity, 0, 0x1003, 0x2000)
        receipt = submit_callback(queue, descriptor, capacity=1, deferred=deferred)
        deferred = receipt['deferred']
        submissions.append(dict(identity=identity, **receipt))
    transfer = replay_counter_transfers({'A':[0,deferred],'B':[0,0]},
                                       [('exchange','A',None),('add','A',None)])
    invoked = []
    result = drain_counted_callbacks(queue, active=transfer['counters']['A'][0],
                  dispatch=lambda descriptor: invoked.append(struct.unpack_from('<Q',descriptor)[0]))
    return dict(evidence='synthetic descriptors and owned serial queue using recovered local flow',
                submissions=submissions, invoked_identities=invoked, drain=result,
                live_occurrence_proved=False, native_submission_safe=False)


if __name__ == '__main__':
    print(json.dumps(run(), indent=2))
